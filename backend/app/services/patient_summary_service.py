import os
import logging
from sqlalchemy.orm import Session
from google import genai
from google.genai import types

logger = logging.getLogger("clinova.summary")
from ..core.config import settings
from ..models.db_models import Patient, MedicalReport, ExtractedLabResult, ExtractedClinicalEntity
from ..models.schemas import PatientSummaryResponse

SUMMARY_DISCLAIMER = (
    "This summary organizes explicitly documented medical records. "
    "Clinova is an information management system, not a diagnostic or treatment tool. "
    "Do not alter treatment or medication without consulting a licensed physician."
)

def generate_patient_summary(patient_id: str, db: Session) -> PatientSummaryResponse:
    """
    Generates a concise, plain-language patient summary.
    Strictly factual, without diagnosis or treatment advice.
    """
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        return PatientSummaryResponse(
            summary="Patient record not found.",
            grounded_record_count=0,
            disclaimer=SUMMARY_DISCLAIMER
        )

    labs = db.query(ExtractedLabResult).filter(
        ExtractedLabResult.patient_id == patient_id,
        ExtractedLabResult.verification_status != "REJECTED"
    ).all()

    entities = db.query(ExtractedClinicalEntity).filter(
        ExtractedClinicalEntity.patient_id == patient_id,
        ExtractedClinicalEntity.verification_status != "REJECTED"
    ).all()

    reports = db.query(MedicalReport).filter(MedicalReport.patient_id == patient_id).all()

    if not reports and not labs and not entities:
        return PatientSummaryResponse(
            summary=f"Patient {patient.full_name} ({patient.patient_id}) has no uploaded reports or lab records yet. Manual intake notes: {patient.symptoms or 'None recorded'}.",
            grounded_record_count=0,
            disclaimer=SUMMARY_DISCLAIMER
        )

    # Build factual record description
    abnormal_labs = [l for l in labs if l.range_status in ["LOW", "HIGH"]]
    meds = [e for e in entities if e.entity_type == "MEDICATION"]
    allergies = [e for e in entities if e.entity_type == "ALLERGY"]
    conditions = [e for e in entities if e.entity_type == "CONDITION"]
    symptoms = [e for e in entities if e.entity_type == "SYMPTOM"]

    # Consolidate and deduplicate medications
    unique_med_map = {}
    for m in meds:
        name_clean = m.entity_name.strip()
        if name_clean not in unique_med_map:
            unique_med_map[name_clean] = m.details or ""
        elif m.details and m.details not in unique_med_map[name_clean]:
            unique_med_map[name_clean] += f"; subsequent record notes {m.details}"
    unique_med_strs = [f"{k} ({v})" if v else k for k, v in unique_med_map.items()]

    # Consolidate and deduplicate allergies, conditions, symptoms
    unique_allergies = list(dict.fromkeys([a.entity_name.strip() for a in allergies]))
    unique_conditions = list(dict.fromkeys([c.entity_name.strip() for c in conditions]))
    unique_symptoms = list(dict.fromkeys([s.entity_name.strip() for s in symptoms]))

    api_key = settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY", "")
    if api_key and api_key.strip():
        try:
            client = genai.Client(api_key=api_key)
            prompt = (
                f"You are a medical record summarizer for Clinova.\n"
                f"Write a concise, factual, patient-friendly summary (2-3 short paragraphs) organizing the information below.\n"
                f"STRICT RULES:\n"
                f"1. Summarize ONLY what is explicitly recorded.\n"
                f"2. Do NOT diagnose any diseases or conditions.\n"
                f"3. Do NOT recommend treatments, dosage adjustments, or lifestyle changes.\n"
                f"4. Clearly mention which tests were marked LOW or HIGH based on their laboratory reference range.\n"
                f"5. Consolidate repeated medication mentions; do NOT list the same drug name repeatedly.\n"
                f"6. State documented conditions (e.g. Type 2 Diabetes, Hypertension) as recorded medical history, not new diagnoses.\n\n"
                f"PATIENT DATA:\n"
                f"Name: {patient.full_name}, Age: {patient.age}, Sex: {patient.sex}\n"
                f"Documented Conditions: {', '.join(unique_conditions) or patient.existing_conditions or 'None'}\n"
                f"Active Symptoms / Complaints: {', '.join(unique_symptoms) or patient.symptoms or 'None'}\n"
                f"Total Reports Uploaded: {len(reports)}\n"
                f"{l.test_name} ({l.raw_value} {l.unit or ''}, status: {l.range_status})"
                f"Documented Medications: {', '.join(unique_med_strs) or patient.current_medications or 'None'}\n"
                f"Documented Allergies: {', '.join(unique_allergies) or patient.allergies or 'None'}"
            )

            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.0)
            )

            if response.text and response.text.strip():
                return PatientSummaryResponse(
                    summary=response.text.strip(),
                    grounded_record_count=len(labs) + len(entities),
                    disclaimer=SUMMARY_DISCLAIMER
                )
        except Exception as e:
            logger.warning(f"[Clinova Summary] Gemini call error: {e}")

    # Deterministic factual fallback summary
    summary_parts = [
        f"Record overview for {patient.full_name} ({patient.patient_id}): A total of {len(reports)} medical report(s) are currently on file.",
    ]
    if unique_conditions:
        summary_parts.append(f"Documented conditions: {', '.join(unique_conditions)}.")
    elif patient.existing_conditions:
        summary_parts.append(f"Documented intake conditions: {patient.existing_conditions}.")

    if abnormal_labs:
        abn_text = "; ".join([f"{l.test_name}: {l.raw_value} {l.unit or ''} ({l.range_status}, ref: {l.raw_reference_range or 'unavailable'})" for l in abnormal_labs])
        summary_parts.append(f"Out-of-range laboratory values: {abn_text}.")
    else:
        summary_parts.append("All extracted laboratory values are within their respective source-documented reference ranges.")

    if unique_med_strs:
        summary_parts.append(f"Documented medications: {', '.join(unique_med_strs)}.")
    elif patient.current_medications:
        summary_parts.append(f"Documented intake medications: {patient.current_medications}.")

    if unique_allergies:
        summary_parts.append(f"Recorded allergies: {', '.join(unique_allergies)}.")

    if unique_symptoms:
        summary_parts.append(f"Documented symptoms: {', '.join(unique_symptoms)}.")

    return PatientSummaryResponse(
        summary=" ".join(summary_parts),
        grounded_record_count=len(labs) + len(entities),
        disclaimer=SUMMARY_DISCLAIMER
    )
