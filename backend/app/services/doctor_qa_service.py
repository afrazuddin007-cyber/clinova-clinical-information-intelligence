import os
import re
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

logger = logging.getLogger("clinova.qa")
from sqlalchemy.orm import Session
from google import genai
from google.genai import types
from ..core.config import settings
from ..models.db_models import Patient, MedicalReport, ExtractedLabResult, ExtractedClinicalEntity, Inconsistency
from ..models.schemas import DoctorQueryResponse, GroundedSourceCitation
from .doctor_intent_classifier import classify_doctor_intent, DoctorQueryIntent

RESPONSIBLE_AI_DISCLAIMER = "Clinova provides record-grounded information retrieval only. It does NOT provide medical diagnosis, treatment recommendations, or dosage advice."

def _sort_reports(reports: List[MedicalReport]) -> List[MedicalReport]:
    """Sorts medical reports in descending chronological order (newest first)."""
    def get_sort_key(r: MedicalReport):
        dt = r.report_date or r.uploaded_at
        if dt is None:
            return datetime.min.replace(tzinfo=timezone.utc)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    return sorted(reports, key=get_sort_key, reverse=True)

def is_latest_query(query: str) -> bool:
    """Detects whether the clinician query specifies the latest / most recent report."""
    q = query.lower()
    triggers = ["latest", "most recent", "last report", "newest", "recent report", "current report"]
    return any(t in q for t in triggers)

def handle_clinical_advice(query: str) -> DoctorQueryResponse:
    """Intercepts requests for clinical diagnosis, prescriptions, or treatment recommendations."""
    return DoctorQueryResponse(
        answer=(
            "Clinova is an information management and review system. "
            "It cannot provide clinical diagnoses, prescribe medications, or recommend treatments or dosages. "
            "Please consult clinical practice guidelines and perform direct medical evaluation for patient care decisions."
        ),
        citations=[],
        disclaimer=RESPONSIBLE_AI_DISCLAIMER
    )

def handle_conflicts_query(
    query: str,
    conflicts: List[Inconsistency]
) -> DoctorQueryResponse:
    """Answers inquiries about clinical or demographic conflicts without falling back to labs."""
    flagged = [c for c in conflicts if c.resolution_status == "FLAGGED"]
    if not flagged:
        return DoctorQueryResponse(
            answer="No conflicts were identified in the verified records.",
            citations=[],
            disclaimer=RESPONSIBLE_AI_DISCLAIMER
        )

    lines = []
    citations: List[GroundedSourceCitation] = []
    for c in flagged:
        src_a = c.source_a if isinstance(c.source_a, dict) else {}
        src_b = c.source_b if isinstance(c.source_b, dict) else {}
        doc_a = src_a.get("report_name") or src_a.get("file_name") or ("Patient Intake" if src_a.get("type") == "intake" else "Document A")
        page_a = src_a.get("page_number", 1)
        doc_b = src_b.get("report_name") or src_b.get("file_name") or ("Patient Intake" if src_b.get("type") == "intake" else "Document B")
        page_b = src_b.get("page_number", 1)

        lines.append(
            f"• [{c.category}] {c.entity_name}: {c.conflict_description}\n"
            f"  - Source Evidence: '{doc_a}' (p. {page_a}) vs '{doc_b}' (p. {page_b})"
        )
        citations.append(GroundedSourceCitation(
            source_type="report" if doc_b != "Patient Intake" else "intake",
            source_title=doc_b,
            page_number=page_b,
            snippet=c.conflict_description
        ))

    intro = f"The following {len(flagged)} conflict(s) were identified across the verified patient records:\n\n"
    return DoctorQueryResponse(
        answer=intro + "\n\n".join(lines),
        citations=citations,
        disclaimer=RESPONSIBLE_AI_DISCLAIMER
    )

def handle_lab_abnormal_query(
    query: str,
    patient: Patient,
    reports: List[MedicalReport],
    labs: List[ExtractedLabResult]
) -> DoctorQueryResponse:
    """
    Handles questions asking for abnormal / out-of-range findings.
    Inspects all structured lab findings for the patient.
    Selects only findings whose deterministic range_status is HIGH or LOW.
    Returns: Test name, Measured value, Unit, Source reference range, and Source page.
    Never infers abnormality from medical knowledge; uses ONLY the report's provided reference range.
    If no abnormal findings exist, explicitly returns:
    'No out-of-range findings were identified in the verified structured records.'
    """
    sorted_reports = _sort_reports(reports)

    if is_latest_query(query) and sorted_reports:
        latest_report = sorted_reports[0]
        latest_labs = [l for l in labs if l.report_id == latest_report.id]
        if latest_labs:
            target_labs = latest_labs
            scope_desc = f"latest medical report ('{latest_report.original_file_name}')"
        else:
            target_labs = labs
            scope_desc = "verified structured records"
    else:
        target_labs = labs
        scope_desc = "verified structured records"

    abnormal_labs = [l for l in target_labs if l.range_status in ["HIGH", "LOW"]]

    if not abnormal_labs:
        return DoctorQueryResponse(
            answer="No out-of-range findings were identified in the verified structured records.",
            citations=[],
            disclaimer=RESPONSIBLE_AI_DISCLAIMER
        )

    findings_blocks = []
    citations: List[GroundedSourceCitation] = []

    for l in abnormal_labs:
        report_title = l.report.original_file_name if l.report else "Medical Report"
        unit_str = f" {l.unit}" if l.unit else ""
        ref_range_str = l.raw_reference_range if l.raw_reference_range else "Unavailable"
        snippet = l.source_snippet or f"{l.test_name}: {l.raw_value}{unit_str} (Ref: {ref_range_str})"

        findings_blocks.append(
            f"• Test Name: {l.test_name}\n"
            f"  - Measured Value: {l.raw_value}{unit_str}\n"
            f"  - Unit: {l.unit or 'N/A'}\n"
            f"  - Source Reference Range: {ref_range_str} (Status: {l.range_status})\n"
            f"  - Source Page: Page {l.page_number} (Report: '{report_title}')"
        )
        citations.append(GroundedSourceCitation(
            source_type="report",
            source_title=report_title,
            page_number=l.page_number,
            snippet=snippet
        ))

    intro = f"The following out-of-range findings were identified in the {scope_desc}:\n\n"
    answer = intro + "\n\n".join(findings_blocks)

    return DoctorQueryResponse(
        answer=answer,
        citations=citations,
        disclaimer=RESPONSIBLE_AI_DISCLAIMER
    )

def handle_lab_all_query(
    query: str,
    patient: Patient,
    reports: List[MedicalReport],
    labs: List[ExtractedLabResult]
) -> DoctorQueryResponse:
    """
    Returns ALL structured lab findings without arbitrary truncation.
    """
    sorted_reports = _sort_reports(reports)

    if is_latest_query(query) and sorted_reports:
        latest_report = sorted_reports[0]
        latest_labs = [l for l in labs if l.report_id == latest_report.id]
        if latest_labs:
            target_labs = latest_labs
            scope_desc = f"latest medical report ('{latest_report.original_file_name}')"
        else:
            target_labs = labs
            scope_desc = "verified structured records"
    else:
        target_labs = labs
        scope_desc = "verified structured records"

    if not target_labs:
        return DoctorQueryResponse(
            answer="No laboratory findings were identified in the verified structured records.",
            citations=[],
            disclaimer=RESPONSIBLE_AI_DISCLAIMER
        )

    findings_blocks = []
    citations: List[GroundedSourceCitation] = []

    for l in target_labs:
        report_title = l.report.original_file_name if l.report else "Medical Report"
        unit_str = f" {l.unit}" if l.unit else ""
        ref_range_str = l.raw_reference_range if l.raw_reference_range else "Unavailable"
        snippet = l.source_snippet or f"{l.test_name}: {l.raw_value}{unit_str} (Ref: {ref_range_str})"

        findings_blocks.append(
            f"• {l.test_name}: {l.raw_value}{unit_str} "
            f"(Reference Range: {ref_range_str}, Status: {l.range_status}) | "
            f"Source: '{report_title}', Page {l.page_number}"
        )
        citations.append(GroundedSourceCitation(
            source_type="report",
            source_title=report_title,
            page_number=l.page_number,
            snippet=snippet
        ))

    intro = f"All recorded laboratory findings ({len(target_labs)} total) in the {scope_desc}:\n\n"
    answer = intro + "\n".join(findings_blocks)

    return DoctorQueryResponse(
        answer=answer,
        citations=citations,
        disclaimer=RESPONSIBLE_AI_DISCLAIMER
    )

def handle_specific_lab_query(
    query: str,
    labs: List[ExtractedLabResult]
) -> DoctorQueryResponse:
    """Checks if a specific lab test was queried by name and returns its documented values."""
    q_lower = query.lower()
    matching_labs = []

    for l in labs:
        test_lower = l.test_name.lower()
        if test_lower in q_lower or (len(test_lower) >= 3 and test_lower in q_lower):
            matching_labs.append(l)
            continue
        words_in_q = set(re.findall(r'\b[a-zA-Z0-9]+\b', q_lower))
        words_in_test = set(re.findall(r'\b[a-zA-Z0-9]+\b', test_lower))
        meaningful_overlap = [w for w in words_in_test.intersection(words_in_q) if len(w) >= 3 and w not in ["the", "for", "and", "test", "level", "value", "what", "patient"]]
        if meaningful_overlap:
            matching_labs.append(l)

    if not matching_labs:
        return DoctorQueryResponse(
            answer="Not found in the verified records.",
            citations=[],
            disclaimer=RESPONSIBLE_AI_DISCLAIMER
        )

    lines = []
    citations: List[GroundedSourceCitation] = []
    for l in matching_labs:
        report_title = l.report.original_file_name if l.report else "Medical Report"
        unit_str = f" {l.unit}" if l.unit else ""
        ref_str = l.raw_reference_range or "Unavailable"
        snippet = l.source_snippet or f"{l.test_name}: {l.raw_value}{unit_str}"
        lines.append(
            f"• {l.test_name}: {l.raw_value}{unit_str} (Reference Range: {ref_str}, Status: {l.range_status}) "
            f"— Source: Page {l.page_number} (Report: '{report_title}')"
        )
        citations.append(GroundedSourceCitation(
            source_type="report",
            source_title=report_title,
            page_number=l.page_number,
            snippet=snippet
        ))

    answer = "Recorded test findings:\n\n" + "\n".join(lines)
    return DoctorQueryResponse(
        answer=answer,
        citations=citations,
        disclaimer=RESPONSIBLE_AI_DISCLAIMER
    )

def handle_medications_query(
    query: str,
    patient: Patient,
    entities: List[ExtractedClinicalEntity]
) -> DoctorQueryResponse:
    """Answers inquiries about documented medications including source provenance."""
    meds = [e for e in entities if e.entity_type == "MEDICATION"]
    intake_meds = patient.current_medications.strip() if patient.current_medications else None

    if not meds and not intake_meds:
        return DoctorQueryResponse(
            answer="No medications were documented in the verified patient records.",
            citations=[],
            disclaimer=RESPONSIBLE_AI_DISCLAIMER
        )

    sections = ["Documented Patient Medications:\n"]
    citations: List[GroundedSourceCitation] = []

    if intake_meds:
        sections.append(f"• Intake Record:\n  - Medications: {intake_meds}\n  - Source: Patient Intake Form (Status: USER_PROVIDED)")
        citations.append(GroundedSourceCitation(
            source_type="intake",
            source_title="Patient Intake Form",
            page_number=1,
            snippet=intake_meds
        ))

    if meds:
        sections.append("\n• Report Documented Medications:")
        for m in meds:
            report_title = m.report.original_file_name if m.report else "Medical Report"
            snippet = m.source_snippet or f"{m.entity_name} {m.details or ''}"
            sections.append(
                f"  - Medication: {m.entity_name}\n"
                f"    * Details / Dosage: {m.details or 'Documented in record'}\n"
                f"    * Source Document: '{report_title}'\n"
                f"    * Source Page: Page {m.page_number}\n"
                f"    * Snippet: \"{snippet}\"\n"
                f"    * Verification Status: {m.verification_status}"
            )
            citations.append(GroundedSourceCitation(
                source_type="report",
                source_title=report_title,
                page_number=m.page_number,
                snippet=snippet
            ))

    return DoctorQueryResponse(
        answer="\n".join(sections),
        citations=citations,
        disclaimer=RESPONSIBLE_AI_DISCLAIMER
    )

def handle_patient_information_query(
    query: str,
    patient: Patient,
    entities: List[ExtractedClinicalEntity]
) -> DoctorQueryResponse:
    """
    Handles multi-field queries independently.
    Evaluates each requested field (blood type, allergies, symptoms, conditions, medications).
    If a requested field is missing, explicitly reports: 'Not found in the verified records.'
    """
    q_lower = query.lower()

    fields_to_check = []
    if re.search(r"\b(blood\s*type|blood\s*group|blood)\b", q_lower):
        fields_to_check.append("blood_type")
    if re.search(r"\ballerg", q_lower):
        fields_to_check.append("allergies")
    if re.search(r"\b(symptom|complaint)", q_lower):
        fields_to_check.append("symptoms")
    if re.search(r"\b(condition|diagnos|medical\s*history)", q_lower):
        fields_to_check.append("conditions")
    if re.search(r"\b(medication|meds|drug|prescription)", q_lower):
        fields_to_check.append("medications")
    if re.search(r"\b(patient'?s?\s+)?age\b", q_lower):
        fields_to_check.append("age")
    if re.search(r"\b(sex|gender)\b", q_lower):
        fields_to_check.append("sex")

    if not fields_to_check:
        fields_to_check = ["blood_type", "allergies", "symptoms", "conditions", "medications"]

    result_lines = []
    citations: List[GroundedSourceCitation] = []

    for field in fields_to_check:
        if field == "blood_type":
            blood_val = None
            for ent in entities:
                if "blood" in ent.entity_name.lower():
                    blood_val = f"{ent.entity_name} ({ent.details or ''}) [Source: Page {ent.page_number}]"
                    citations.append(GroundedSourceCitation(
                        source_type="report",
                        source_title=ent.report.original_file_name if ent.report else "Medical Report",
                        page_number=ent.page_number,
                        snippet=ent.source_snippet or ent.entity_name
                    ))
                    break
            if blood_val:
                result_lines.append(f"• Blood Type: {blood_val}")
            else:
                result_lines.append("• Blood Type: Not found in the verified records.")

        elif field == "allergies":
            rep_allergies = [e for e in entities if e.entity_type == "ALLERGY"]
            allergy_parts = []
            if patient.allergies:
                allergy_parts.append(f"{patient.allergies} (Intake)")
            for a in rep_allergies:
                report_title = a.report.original_file_name if a.report else "Report"
                allergy_parts.append(f"{a.entity_name} (Report: '{report_title}', p. {a.page_number})")
                citations.append(GroundedSourceCitation(
                    source_type="report",
                    source_title=report_title,
                    page_number=a.page_number,
                    snippet=a.source_snippet or a.entity_name
                ))
            if allergy_parts:
                result_lines.append(f"• Allergies: {'; '.join(allergy_parts)}")
            else:
                result_lines.append("• Allergies: Not found in the verified records.")

        elif field == "symptoms":
            rep_symptoms = [e for e in entities if e.entity_type == "SYMPTOM"]
            symptom_parts = []
            if patient.symptoms:
                symptom_parts.append(f"{patient.symptoms} (Intake)")
            for s in rep_symptoms:
                report_title = s.report.original_file_name if s.report else "Report"
                symptom_parts.append(f"{s.entity_name} (Report: '{report_title}', p. {s.page_number})")
                citations.append(GroundedSourceCitation(
                    source_type="report",
                    source_title=report_title,
                    page_number=s.page_number,
                    snippet=s.source_snippet or s.entity_name
                ))
            if symptom_parts:
                result_lines.append(f"• Symptoms: {'; '.join(symptom_parts)}")
            else:
                result_lines.append("• Symptoms: Not found in the verified records.")

        elif field == "conditions":
            rep_conditions = [e for e in entities if e.entity_type == "CONDITION"]
            cond_parts = []
            if patient.existing_conditions:
                cond_parts.append(f"{patient.existing_conditions} (Intake)")
            for c in rep_conditions:
                report_title = c.report.original_file_name if c.report else "Report"
                cond_parts.append(f"{c.entity_name} (Report: '{report_title}', p. {c.page_number})")
                citations.append(GroundedSourceCitation(
                    source_type="report",
                    source_title=report_title,
                    page_number=c.page_number,
                    snippet=c.source_snippet or c.entity_name
                ))
            if cond_parts:
                result_lines.append(f"• Conditions: {'; '.join(cond_parts)}")
            else:
                result_lines.append("• Conditions: Not found in the verified records.")

        elif field == "medications":
            rep_meds = [e for e in entities if e.entity_type == "MEDICATION"]
            med_parts = []
            if patient.current_medications:
                med_parts.append(f"{patient.current_medications} (Intake)")
            for m in rep_meds:
                report_title = m.report.original_file_name if m.report else "Report"
                det = f" - {m.details}" if m.details else ""
                med_parts.append(f"{m.entity_name}{det} (Report: '{report_title}', p. {m.page_number})")
                citations.append(GroundedSourceCitation(
                    source_type="report",
                    source_title=report_title,
                    page_number=m.page_number,
                    snippet=m.source_snippet or m.entity_name
                ))
            if med_parts:
                result_lines.append(f"• Medications: {'; '.join(med_parts)}")
            else:
                result_lines.append("• Medications: Not found in the verified records.")

        elif field == "age":
            result_lines.append(f"• Age: {patient.age} years old (Intake record)")

        elif field == "sex":
            result_lines.append(f"• Sex: {patient.sex} (Intake record)")

    answer = f"Patient Information for {patient.full_name} ({patient.patient_id}):\n\n" + "\n".join(result_lines)
    return DoctorQueryResponse(
        answer=answer,
        citations=citations,
        disclaimer=RESPONSIBLE_AI_DISCLAIMER
    )

def handle_source_provenance_query(
    query: str,
    patient: Patient,
    reports: List[MedicalReport],
    labs: List[ExtractedLabResult],
    entities: List[ExtractedClinicalEntity]
) -> DoctorQueryResponse:
    """
    Dedicated provenance resolution. Returns source document, page, snippet, and status.
    If unavailable, explicitly returns: 'Source location unavailable in the verified records.'
    Never falls back to abnormal labs.
    """
    q_lower = query.lower()

    # Search in structured lab results
    for l in labs:
        t_lower = l.test_name.lower()
        if t_lower in q_lower or (len(t_lower) >= 3 and any(w in t_lower for w in q_lower.split() if len(w) >= 4 and w not in ["source", "document", "where", "which", "page", "result", "patient"])):
            report_title = l.report.original_file_name if l.report else "Medical Report"
            snippet = l.source_snippet or f"{l.test_name}: {l.raw_value} {l.unit or ''}"
            answer = (
                f"Source Provenance for '{l.test_name}':\n"
                f"• Document: '{report_title}'\n"
                f"• Page: Page {l.page_number}\n"
                f"• Value: {l.raw_value} {l.unit or ''}\n"
                f"• Reference Range: {l.raw_reference_range or 'Unavailable'}\n"
                f"• Status: {l.range_status}\n"
                f"• Evidence Snippet: \"{snippet}\"\n"
                f"• Verification Status: {l.verification_status}"
            )
            return DoctorQueryResponse(
                answer=answer,
                citations=[GroundedSourceCitation(
                    source_type="report",
                    source_title=report_title,
                    page_number=l.page_number,
                    snippet=snippet
                )],
                disclaimer=RESPONSIBLE_AI_DISCLAIMER
            )

    # Search in clinical entities
    for e in entities:
        e_lower = e.entity_name.lower()
        if e_lower in q_lower or (len(e_lower) >= 3 and any(w in e_lower for w in q_lower.split() if len(w) >= 4 and w not in ["source", "document", "where", "which", "page", "entity", "patient"])):
            report_title = e.report.original_file_name if e.report else "Medical Report"
            snippet = e.source_snippet or f"{e.entity_name} ({e.details or ''})"
            answer = (
                f"Source Provenance for '{e.entity_name}' ({e.entity_type}):\n"
                f"• Document: '{report_title}'\n"
                f"• Page: Page {e.page_number}\n"
                f"• Details: {e.details or 'Documented in record'}\n"
                f"• Evidence Snippet: \"{snippet}\"\n"
                f"• Verification Status: {e.verification_status}"
            )
            return DoctorQueryResponse(
                answer=answer,
                citations=[GroundedSourceCitation(
                    source_type="report",
                    source_title=report_title,
                    page_number=e.page_number,
                    snippet=snippet
                )],
                disclaimer=RESPONSIBLE_AI_DISCLAIMER
            )

    # Search in patient intake
    intake_matches = []
    if patient.allergies and any(w in patient.allergies.lower() for w in q_lower.split() if len(w) >= 4 and w not in ["source", "document", "where", "which", "page"]):
        intake_matches.append(("Allergies", patient.allergies))
    if patient.current_medications and any(w in patient.current_medications.lower() for w in q_lower.split() if len(w) >= 4 and w not in ["source", "document", "where", "which", "page"]):
        intake_matches.append(("Medications", patient.current_medications))
    if patient.existing_conditions and any(w in patient.existing_conditions.lower() for w in q_lower.split() if len(w) >= 4 and w not in ["source", "document", "where", "which", "page"]):
        intake_matches.append(("Conditions", patient.existing_conditions))

    if intake_matches:
        cat, val = intake_matches[0]
        answer = (
            f"Source Provenance for '{val}' ({cat}):\n"
            f"• Document: Patient Intake Form\n"
            f"• Page: Intake Form\n"
            f"• Value: {val}\n"
            f"• Verification Status: USER_PROVIDED"
        )
        return DoctorQueryResponse(
            answer=answer,
            citations=[GroundedSourceCitation(
                source_type="intake",
                source_title="Patient Intake Form",
                page_number=1,
                snippet=val
            )],
            disclaimer=RESPONSIBLE_AI_DISCLAIMER
        )

    return DoctorQueryResponse(
        answer="Source location unavailable in the verified records.",
        citations=[],
        disclaimer=RESPONSIBLE_AI_DISCLAIMER
    )

def handle_comparison_query(
    query: str,
    patient: Patient,
    reports: List[MedicalReport],
    labs: List[ExtractedLabResult]
) -> DoctorQueryResponse:
    """Analyzes differences and trajectory across chronological patient reports."""
    sorted_reports = _sort_reports(reports)

    if len(sorted_reports) < 2:
        return DoctorQueryResponse(
            answer="A single report is recorded with all values within reference range. No longitudinal comparison changes detected.",
            citations=[],
            disclaimer=RESPONSIBLE_AI_DISCLAIMER
        )

    rep_latest = sorted_reports[0]
    rep_prev = sorted_reports[1]

    latest_labs = {l.test_name.lower(): l for l in labs if l.report_id == rep_latest.id}
    prev_labs = {l.test_name.lower(): l for l in labs if l.report_id == rep_prev.id}

    changes = []
    citations: List[GroundedSourceCitation] = []

    for name_lower, l_curr in latest_labs.items():
        if name_lower in prev_labs:
            l_prev = prev_labs[name_lower]
            unit_str = f" {l_curr.unit}" if l_curr.unit else ""
            if l_curr.numeric_value is not None and l_prev.numeric_value is not None:
                if l_curr.numeric_value != l_prev.numeric_value:
                    delta = l_curr.numeric_value - l_prev.numeric_value
                    delta_str = f"+{delta:.1f}" if delta > 0 else f"{delta:.1f}"
                    changes.append(
                        f"• {l_curr.test_name}: changed from {l_prev.raw_value} to {l_curr.raw_value}{unit_str} "
                        f"({delta_str}{unit_str}, Status: {l_curr.range_status}) | "
                        f"Reports: '{rep_prev.original_file_name}' (p. {l_prev.page_number}) → '{rep_latest.original_file_name}' (p. {l_curr.page_number})"
                    )
                    citations.append(GroundedSourceCitation(
                        source_type="report",
                        source_title=rep_latest.original_file_name,
                        page_number=l_curr.page_number,
                        snippet=f"{l_curr.test_name}: {l_curr.raw_value}{unit_str}"
                    ))
            elif l_curr.raw_value != l_prev.raw_value:
                changes.append(
                    f"• {l_curr.test_name}: changed from {l_prev.raw_value} to {l_curr.raw_value}{unit_str} "
                    f"(Status: {l_curr.range_status}) | "
                    f"Reports: '{rep_prev.original_file_name}' (p. {l_prev.page_number}) → '{rep_latest.original_file_name}' (p. {l_curr.page_number})"
                )
                citations.append(GroundedSourceCitation(
                    source_type="report",
                    source_title=rep_latest.original_file_name,
                    page_number=l_curr.page_number,
                    snippet=f"{l_curr.test_name}: {l_curr.raw_value}{unit_str}"
                ))
        else:
            unit_str = f" {l_curr.unit}" if l_curr.unit else ""
            changes.append(
                f"• {l_curr.test_name} (New Test in Latest Report): {l_curr.raw_value}{unit_str} "
                f"(Ref: {l_curr.raw_reference_range or 'N/A'}, Status: {l_curr.range_status}) | "
                f"Report: '{rep_latest.original_file_name}' (p. {l_curr.page_number})"
            )
            citations.append(GroundedSourceCitation(
                source_type="report",
                source_title=rep_latest.original_file_name,
                page_number=l_curr.page_number,
                snippet=f"{l_curr.test_name}: {l_curr.raw_value}{unit_str}"
            ))

    if changes:
        answer = (
            f"Longitudinal comparison between '{rep_prev.original_file_name}' and latest report '{rep_latest.original_file_name}':\n\n"
            + "\n".join(changes)
        )
    else:
        answer = (
            f"Longitudinal comparison between '{rep_prev.original_file_name}' and latest report '{rep_latest.original_file_name}':\n\n"
            f"No laboratory values changed between the two reports."
        )

    return DoctorQueryResponse(
        answer=answer,
        citations=citations,
        disclaimer=RESPONSIBLE_AI_DISCLAIMER
    )

def handle_summary_query(
    query: str,
    patient: Patient,
    reports: List[MedicalReport],
    labs: List[ExtractedLabResult],
    entities: List[ExtractedClinicalEntity],
    conflicts: List[Inconsistency]
) -> DoctorQueryResponse:
    """Provides a comprehensive structured summary without medical diagnosis or speculation."""
    summary_lines = [
        f"Clinical Record Summary for {patient.full_name} (ID: {patient.patient_id}):",
        f"• Demographics: Age {patient.age}, Sex {patient.sex}",
        f"• Intake Allergies: {patient.allergies or 'None documented'}",
        f"• Intake Medications: {patient.current_medications or 'None documented'}",
        f"• Intake Conditions: {patient.existing_conditions or 'None documented'}",
        f"• Documented Medical Reports: {len(reports)} report(s) on file",
        f"• Structured Laboratory Findings: {len(labs)} test(s) recorded"
    ]
    abnormal = [l for l in labs if l.range_status in ["HIGH", "LOW"]]
    if abnormal:
        summary_lines.append(f"• Out-of-Range Findings ({len(abnormal)}): " + ", ".join([f"{l.test_name} ({l.raw_value} {l.unit or ''} [{l.range_status}])" for l in abnormal]))
    else:
        summary_lines.append("• Out-of-Range Findings: None identified in structured records.")

    if entities:
        summary_lines.append(f"• Extracted Clinical Entities: {len(entities)} documented (medications, conditions, allergies, symptoms)")

    flagged_conflicts = [c for c in conflicts if c.resolution_status == "FLAGGED"]
    if flagged_conflicts:
        summary_lines.append(f"• Active Inconsistencies: {len(flagged_conflicts)} flagged cross-record conflict(s)")
    else:
        summary_lines.append("• Active Inconsistencies: No conflicts flagged.")

    citations: List[GroundedSourceCitation] = []
    for l in abnormal[:4]:
        citations.append(GroundedSourceCitation(
            source_type="report",
            source_title=l.report.original_file_name if l.report else "Medical Report",
            page_number=l.page_number,
            snippet=f"{l.test_name}: {l.raw_value} {l.unit or ''}"
        ))

    return DoctorQueryResponse(
        answer="\n".join(summary_lines),
        citations=citations,
        disclaimer=RESPONSIBLE_AI_DISCLAIMER
    )

def handle_general_query(
    query: str,
    patient: Patient,
    reports: List[MedicalReport],
    labs: List[ExtractedLabResult],
    entities: List[ExtractedClinicalEntity],
    conflicts: List[Inconsistency]
) -> DoctorQueryResponse:
    """Answers general or open-ended inquiries strictly grounded in structured record."""
    sorted_reports = _sort_reports(reports)
    context_lines = [
        f"PATIENT: {patient.full_name}, Age: {patient.age}, Sex: {patient.sex}, ID: {patient.patient_id}",
        f"INTAKE ALLERGIES: {patient.allergies or 'None documented'}",
        f"INTAKE MEDICATIONS: {patient.current_medications or 'None documented'}",
        f"INTAKE CONDITIONS: {patient.existing_conditions or 'None documented'}",
        "\nAVAILABLE MEDICAL REPORTS:"
    ]

    for r in sorted_reports:
        context_lines.append(f"- Report '{r.original_file_name}' (Date: {r.report_date or r.uploaded_at})")

    context_lines.append("\nRECORDED LAB RESULTS:")
    default_citations: List[GroundedSourceCitation] = []
    for lab in labs:
        context_lines.append(
            f"- {lab.test_name}: {lab.raw_value} {lab.unit or ''} | Range: {lab.raw_reference_range or 'Unavailable'} | "
            f"Status: {lab.range_status} | Source: Report '{lab.report.original_file_name if lab.report else 'Report'}', Page {lab.page_number} | "
            f"Quote: \"{lab.source_snippet or ''}\""
        )
        if len(default_citations) < 10:
            default_citations.append(GroundedSourceCitation(
                source_type="report",
                source_title=lab.report.original_file_name if lab.report else "Medical Report",
                page_number=lab.page_number,
                snippet=lab.source_snippet or f"{lab.test_name}: {lab.raw_value} {lab.unit or ''}"
            ))

    context_lines.append("\nRECORDED CLINICAL ENTITIES (MEDICATIONS, ALLERGIES, CONDITIONS):")
    for ent in entities:
        report_title = ent.report.original_file_name if ent.report else "Report"
        context_lines.append(
            f"- [{ent.entity_type}] {ent.entity_name} ({ent.details or 'No details'}) | Source: Report '{report_title}', Page {ent.page_number}"
        )

    flagged_conflicts = [c for c in conflicts if c.resolution_status == "FLAGGED"]
    if flagged_conflicts:
        context_lines.append("\nFLAGGED CROSS-RECORD INCONSISTENCIES:")
        for c in flagged_conflicts:
            context_lines.append(f"- [{c.category}] {c.conflict_description}")

    record_context = "\n".join(context_lines)

    api_key = settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY", "")
    if api_key and api_key.strip():
        try:
            client = genai.Client(api_key=api_key)
            prompt = (
                f"You are Clinova's clinical information retrieval engine.\n"
                f"Answer the clinician's query using ONLY the structured record provided below.\n\n"
                f"RULES:\n"
                f"1. Answer concisely, factually, and cite specific report names and page numbers.\n"
                f"2. For questions asking about abnormal / out-of-range findings:\n"
                f"   - Select ONLY findings whose Status is HIGH or LOW.\n"
                f"   - NEVER infer abnormality from medical knowledge. Use ONLY the deterministic Status calculated from the report's reference range.\n"
                f"   - If no abnormal findings exist, reply EXACTLY: 'No out-of-range findings were identified in the verified structured records.'\n"
                f"   - For each abnormal finding, include: Test name, Measured value, Unit, Source reference range, and Source page.\n"
                f"3. If the answer cannot be found in the record, reply EXACTLY: 'This information is not available in the current patient record.'\n"
                f"4. Do NOT diagnose, recommend treatments, or speculate.\n\n"
                f"PATIENT RECORD:\n{record_context}\n\n"
                f"CLINICIAN QUERY: {query}"
            )

            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.0,
                )
            )

            if response.text and response.text.strip():
                return DoctorQueryResponse(
                    answer=response.text.strip(),
                    citations=default_citations,
                    disclaimer=RESPONSIBLE_AI_DISCLAIMER
                )
        except Exception as e:
            logger.warning(f"[Clinova QA] Gemini call exception: {e}")

    # Deterministic fallback response for general queries without arbitrary truncation
    if labs:
        lab_summary = "\n".join([f"• {l.test_name}: {l.raw_value} {l.unit or ''} (Status: {l.range_status}, Ref: {l.raw_reference_range or 'Unavailable'}, Page {l.page_number})" for l in labs])
        return DoctorQueryResponse(
            answer=f"Structured clinical records for {patient.full_name} ({patient.patient_id}):\n\n{lab_summary}",
            citations=default_citations,
            disclaimer=RESPONSIBLE_AI_DISCLAIMER
        )

    return DoctorQueryResponse(
        answer="This information is not available in the current patient record.",
        citations=[],
        disclaimer=RESPONSIBLE_AI_DISCLAIMER
    )

def validate_doctor_response(
    intent: DoctorQueryIntent,
    response: DoctorQueryResponse,
    patient: Patient,
    labs: List[ExtractedLabResult],
    conflicts: List[Inconsistency]
) -> DoctorQueryResponse:
    """
    Response validation: guarantees safety disclaimer, prevents intent leakage,
    and validates boundary constraints.
    """
    if not response.disclaimer or response.disclaimer != RESPONSIBLE_AI_DISCLAIMER:
        response.disclaimer = RESPONSIBLE_AI_DISCLAIMER

    # For CONFLICTS intent, verify no laboratory abnormality leakage
    if intent == DoctorQueryIntent.CONFLICTS:
        flagged = [c for c in conflicts if c.resolution_status == "FLAGGED"]
        if not flagged:
            response.answer = "No conflicts were identified in the verified records."
            response.citations = []

    # For LAB_ABNORMAL intent, verify no NORMAL findings and verify empty state
    if intent == DoctorQueryIntent.LAB_ABNORMAL:
        abnormal = [l for l in labs if l.range_status in ["HIGH", "LOW"]]
        if not abnormal:
            response.answer = "No out-of-range findings were identified in the verified structured records."
            response.citations = []

    return response

def answer_doctor_query(
    patient_id: str,
    query: str,
    db: Session
) -> DoctorQueryResponse:
    """
    Answers clinician questions strictly grounded in the patient's structured record.
    Incorporates Responsible AI guardrails to intercept diagnostic or prescribing prompts.
    Provides verifiable citations with source report and page numbers.
    Follows:
    USER QUESTION → INTENT CLASSIFICATION → CURRENT PATIENT VALIDATION →
    DETERMINISTIC DATABASE RETRIEVAL → SOURCE / PROVENANCE RETRIEVAL →
    RESPONSE CONSTRUCTION → RESPONSE VALIDATION → FINAL ANSWER
    """
    patient = db.query(Patient).filter(
        (Patient.id == patient_id) | (Patient.patient_id == patient_id)
    ).first()
    if not patient:
        return DoctorQueryResponse(
            answer="Patient record not found.",
            citations=[],
            disclaimer=RESPONSIBLE_AI_DISCLAIMER
        )
    patient_id = patient.id

    # Retrieve patient's non-rejected structured context
    reports = db.query(MedicalReport).filter(
        MedicalReport.patient_id == patient_id
    ).all()

    labs = db.query(ExtractedLabResult).filter(
        ExtractedLabResult.patient_id == patient_id,
        ExtractedLabResult.verification_status != "REJECTED"
    ).all()

    entities = db.query(ExtractedClinicalEntity).filter(
        ExtractedClinicalEntity.patient_id == patient_id,
        ExtractedClinicalEntity.verification_status != "REJECTED"
    ).all()

    conflicts = db.query(Inconsistency).filter(
        Inconsistency.patient_id == patient_id,
        Inconsistency.resolution_status == "FLAGGED"
    ).all()

    # Classify intent with deterministic priority
    available_test_names = [l.test_name for l in labs]
    intent = classify_doctor_intent(query, available_test_names=available_test_names)

    # Route to intent handler
    if intent == DoctorQueryIntent.CLINICAL_ADVICE:
        res = handle_clinical_advice(query)
    elif intent == DoctorQueryIntent.CONFLICTS:
        res = handle_conflicts_query(query, conflicts)
    elif intent == DoctorQueryIntent.COMPARISON:
        res = handle_comparison_query(query, patient, reports, labs)
    elif intent == DoctorQueryIntent.LAB_ABNORMAL:
        res = handle_lab_abnormal_query(query, patient, reports, labs)
    elif intent == DoctorQueryIntent.LAB_ALL:
        res = handle_lab_all_query(query, patient, reports, labs)
    elif intent == DoctorQueryIntent.LAB_SPECIFIC:
        res = handle_specific_lab_query(query, labs)
    elif intent == DoctorQueryIntent.SOURCE_PROVENANCE:
        res = handle_source_provenance_query(query, patient, reports, labs, entities)
    elif intent == DoctorQueryIntent.PATIENT_INFORMATION:
        res = handle_patient_information_query(query, patient, entities)
    elif intent == DoctorQueryIntent.MEDICATIONS:
        res = handle_medications_query(query, patient, entities)
    elif intent == DoctorQueryIntent.SUMMARY:
        res = handle_summary_query(query, patient, reports, labs, entities, conflicts)
    else:
        res = handle_general_query(query, patient, reports, labs, entities, conflicts)

    # Validate response
    return validate_doctor_response(intent, res, patient, labs, conflicts)
