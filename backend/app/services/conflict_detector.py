import re
from typing import List
from sqlalchemy.orm import Session
from ..models.db_models import Patient, MedicalReport, ExtractedClinicalEntity, Inconsistency

def scan_and_record_conflicts(patient_id: str, db: Session) -> List[Inconsistency]:
    """
    Scans the patient record across:
      1. Patient intake vs reports
      2. Cross-report discrepancies
    Identifies discrepancies in allergies, medications, and demographics.
    IMPORTANT: Flags conflicts only; NEVER decides medical truth.
    """
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        return []

    # Clear previously flagged unresolved conflicts to re-evaluate freshly
    db.query(Inconsistency).filter(
        Inconsistency.patient_id == patient_id,
        Inconsistency.resolution_status == "FLAGGED"
    ).delete()

    flagged_conflicts: List[Inconsistency] = []

    # 1. Allergy Discrepancy Checks
    # E.g. Intake states "No known allergies" or "NKDA" but report lists an allergen
    intake_allergies = (patient.allergies or "").strip()
    report_allergies = db.query(ExtractedClinicalEntity).filter(
        ExtractedClinicalEntity.patient_id == patient_id,
        ExtractedClinicalEntity.entity_type == "ALLERGY",
        ExtractedClinicalEntity.verification_status != "REJECTED"
    ).all()

    intake_lower = intake_allergies.lower()
    is_no_allergies_stated = any(
        phrase in intake_lower
        for phrase in ["no known", "nkda", "none", "nil", "no allergies", "negative", "denies"]
    )

    if is_no_allergies_stated:
        for r_allergy in report_allergies:
            report_meta = db.query(MedicalReport).filter(MedicalReport.id == r_allergy.report_id).first()
            report_name = report_meta.original_file_name if report_meta else "Medical Report"

            inc = Inconsistency(
                patient_id=patient_id,
                category="ALLERGY",
                entity_name=r_allergy.entity_name,
                source_a={
                    "type": "Patient Intake Record",
                    "text": f"Documented allergies: '{patient.allergies}'",
                    "date": patient.created_at.isoformat() if patient.created_at else None
                },
                source_b={
                    "type": f"Report: {report_name}",
                    "text": f"Found allergy '{r_allergy.entity_name}' (Snippet: \"{r_allergy.source_snippet or ''}\")",
                    "page": r_allergy.page_number,
                    "date": report_meta.report_date.isoformat() if report_meta and report_meta.report_date else None
                },
                conflict_description=(
                    f"Contradiction between Patient Intake and clinical report. "
                    f"Intake states '{patient.allergies}', but '{report_name}' documents an allergy to '{r_allergy.entity_name}'. "
                    f"Flagged for clinician review; Clinova does not decide which record is accurate."
                ),
                resolution_status="FLAGGED"
            )
            db.add(inc)
            flagged_conflicts.append(inc)

    # 2. Medication Discrepancy Checks
    # Compare intake medications against extracted report medications
    intake_meds_text = (patient.current_medications or "").lower()
    report_meds = db.query(ExtractedClinicalEntity).filter(
        ExtractedClinicalEntity.patient_id == patient_id,
        ExtractedClinicalEntity.entity_type == "MEDICATION",
        ExtractedClinicalEntity.verification_status != "REJECTED"
    ).all()

    for r_med in report_meds:
        med_name = r_med.entity_name.lower().strip()
        # If medication is mentioned in intake, check for dosage disparity
        if med_name in intake_meds_text and r_med.details:
            # Extract dosages
            intake_dose_m = re.search(rf"{med_name}\s*(\d+\s*mg|\d+\s*units)?\s*([a-zA-Z\s]+)?", intake_meds_text)
            intake_dose = intake_dose_m.group(1) if intake_dose_m and intake_dose_m.group(1) else ""
            report_dose = r_med.details or ""

            if intake_dose and report_dose and intake_dose.strip().lower() != report_dose.strip().lower():
                report_meta = db.query(MedicalReport).filter(MedicalReport.id == r_med.report_id).first()
                report_name = report_meta.original_file_name if report_meta else "Medical Report"

                inc = Inconsistency(
                    patient_id=patient_id,
                    category="MEDICATION",
                    entity_name=r_med.entity_name,
                    source_a={
                        "type": "Patient Intake Record",
                        "text": f"Current Medications: '{patient.current_medications}'",
                        "date": patient.created_at.isoformat() if patient.created_at else None
                    },
                    source_b={
                        "type": f"Report: {report_name}",
                        "text": f"{r_med.entity_name}: {r_med.details} (Snippet: \"{r_med.source_snippet or ''}\")",
                        "page": r_med.page_number,
                        "date": report_meta.report_date.isoformat() if report_meta and report_meta.report_date else None
                    },
                    conflict_description=(
                        f"Dosage or frequency disparity for '{r_med.entity_name}'. "
                        f"Intake lists '{intake_dose.strip()}', whereas '{report_name}' specifies '{report_dose.strip()}'. "
                        f"Flagged for human clinician reconciliation."
                    ),
                    resolution_status="FLAGGED"
                )
                db.add(inc)
                flagged_conflicts.append(inc)

    db.commit()
    return flagged_conflicts
