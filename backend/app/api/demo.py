import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
import fitz  # PyMuPDF to generate synthetic PDF reports
from ..core.database import get_db
from ..core.security import get_current_user
from ..core.config import settings
from ..models.db_models import (
    User, Patient, MedicalReport, ExtractedLabResult, ExtractedClinicalEntity, Inconsistency
)
from ..services.conflict_detector import scan_and_record_conflicts
from ..services.audit_service import log_audit_event

router = APIRouter(prefix="/demo", tags=["Demo Seeder"])

def _create_synthetic_pdf(filepath: str, title: str, date_str: str, patient_name: str, lab_rows: list[str]):
    """Generates a clean, synthetic PDF report using PyMuPDF."""
    doc = fitz.open()
    page = doc.new_page()

    # Header
    page.insert_text((50, 50), "METROPOLITAN CLINICAL LABORATORIES", fontsize=14, fontname="helv", color=(0.1, 0.2, 0.4))
    page.insert_text((50, 68), "Accredited Medical Diagnostic Center - Clinical Pathology", fontsize=9, fontname="helv", color=(0.4, 0.4, 0.4))
    page.draw_line((50, 78), (550, 78), color=(0.7, 0.7, 0.7))

    # Patient info
    page.insert_text((50, 100), f"Patient: {patient_name}", fontsize=11, fontname="helv")
    page.insert_text((350, 100), f"Report Date: {date_str}", fontsize=10, fontname="helv")
    page.insert_text((50, 118), f"Report Title: {title}", fontsize=11, fontname="helv", color=(0.0, 0.3, 0.5))
    page.insert_text((350, 118), "Physician: Dr. J. Martinez, MD", fontsize=10, fontname="helv")
    page.draw_line((50, 130), (550, 130), color=(0.8, 0.8, 0.8))

    # Table Header
    page.insert_text((50, 155), "TEST NAME", fontsize=9, fontname="helv", color=(0.3, 0.3, 0.3))
    page.insert_text((220, 155), "RESULT", fontsize=9, fontname="helv", color=(0.3, 0.3, 0.3))
    page.insert_text((300, 155), "UNITS", fontsize=9, fontname="helv", color=(0.3, 0.3, 0.3))
    page.insert_text((400, 155), "REFERENCE RANGE", fontsize=9, fontname="helv", color=(0.3, 0.3, 0.3))
    page.draw_line((50, 165), (550, 165), color=(0.5, 0.5, 0.5))

    # Table Rows
    y = 185
    for row in lab_rows:
        parts = row.split(" | ")
        if len(parts) >= 4:
            page.insert_text((50, y), parts[0], fontsize=10, fontname="helv")
            page.insert_text((220, y), parts[1], fontsize=10, fontname="helv")
            page.insert_text((300, y), parts[2], fontsize=10, fontname="helv")
            page.insert_text((400, y), parts[3], fontsize=10, fontname="helv")
        y += 24

    # Footer Disclaimer
    page.draw_line((50, 750), (550, 750), color=(0.8, 0.8, 0.8))
    page.insert_text((50, 765), "SYNTHETIC DEMO RECORD FOR CLINICAL SOFTWARE TESTING. NOT FOR ACTUAL PATIENT CARE.", fontsize=8, fontname="helv", color=(0.5, 0.5, 0.5))
    page.insert_text((50, 778), "Clinova Provenance Verified Document. Page 1 of 1.", fontsize=8, fontname="helv", color=(0.2, 0.5, 0.5))

    doc.save(filepath)
    doc.close()

@router.post("/seed", status_code=status.HTTP_201_CREATED)
def seed_demo_patient(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Seeds a rich, realistic synthetic patient profile for demonstration:
      - Patient: Eleanor Vance (ID: CL-8F29K4)
      - Intake: Allergies: 'No known allergies', Meds: 'Metformin 500mg daily'
      - Report 1 (Baseline, 30 days ago): Low Hemoglobin, Fasting Glucose High, eGFR Low
      - Report 2 (Follow-up, 3 days ago): Improved Hemoglobin (+1.6 g/dL), eGFR normalized, New HbA1c test
      - Conflicts: Discovered allergy to Penicillin and dosage increase to 1000mg BID
      - Verification: Mix of AI_EXTRACTED, PENDING_VERIFICATION, and HUMAN_VERIFIED
    """
    demo_patient_id = "CL-8F29K4"
    
    # Remove existing demo patient if already seeded to allow re-seeding
    existing = db.query(Patient).filter(
        Patient.patient_id == demo_patient_id
    ).first()
    if existing:
        db.delete(existing)
        db.commit()

    patient = Patient(
        patient_id=demo_patient_id,
        full_name="Eleanor Vance",
        age=58,
        sex="female",
        symptoms="Persistent mild fatigue, post-exertional dyspnea, morning joint stiffness",
        existing_conditions="Type 2 Diabetes Mellitus, Essential Hypertension",
        allergies="No known drug allergies (NKDA)",
        current_medications="Metformin 500mg daily, Lisinopril 10mg once daily",
        medical_history="Diagnosed T2D in 2021; mild microalbuminuria on annual screen",
        additional_notes="Patient scheduled for 1-month routine metabolic follow-up",
        created_by_user_id=current_user.id
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)

    # 1. Create Baseline Report (30 days ago)
    date_a = datetime.now(timezone.utc) - timedelta(days=30)
    pdf_a_name = f"demo_baseline_cbc_{patient.id[:8]}.pdf"
    pdf_a_path = os.path.join(settings.UPLOAD_DIR, pdf_a_name)
    _create_synthetic_pdf(
        filepath=pdf_a_path,
        title="Complete Blood Count & Basic Metabolic Panel",
        date_str=date_a.strftime("%Y-%m-%d"),
        patient_name="Eleanor Vance",
        lab_rows=[
            "Hemoglobin | 10.2 | g/dL | 12.0 - 16.0 g/dL",
            "White Blood Cell (WBC) | 6.8 | 10^3/uL | 4.5 - 11.0 10^3/uL",
            "Platelets | 210 | 10^3/uL | 150 - 450 10^3/uL",
            "Fasting Glucose | 142 | mg/dL | < 100 mg/dL",
            "eGFR | 58 | mL/min/1.73m2 | > 60 mL/min/1.73m2",
            "Serum Ferritin | 14 | ng/mL | N/A"
        ]
    )

    rep_a = MedicalReport(
        patient_id=patient.id,
        file_name=pdf_a_name,
        original_file_name="Baseline_Metabolic_Panel_08052026.pdf",
        file_type="application/pdf",
        file_size_bytes=os.path.getsize(pdf_a_path),
        file_hash="demo_hash_rep_a_8f29k4",
        storage_path=pdf_a_path,
        report_date=date_a,
        facility_name="Metropolitan Clinical Laboratories",
        report_title="Complete Blood Count & Basic Metabolic Panel",
        processing_status="EXTRACTED",
        uploaded_by_user_id=current_user.id
    )
    db.add(rep_a)
    db.commit()
    db.refresh(rep_a)

    # Add Baseline Labs
    baseline_labs = [
        ("Hemoglobin", "10.2", 10.2, "g/dL", "12.0 - 16.0 g/dL", 12.0, 16.0, "LOW", "AI_EXTRACTED", "HUMAN_VERIFIED"),
        ("White Blood Cell (WBC)", "6.8", 6.8, "10^3/uL", "4.5 - 11.0 10^3/uL", 4.5, 11.0, "NORMAL", "AI_EXTRACTED", "HUMAN_VERIFIED"),
        ("Platelets", "210", 210.0, "10^3/uL", "150 - 450 10^3/uL", 150.0, 450.0, "NORMAL", "AI_EXTRACTED", "HUMAN_VERIFIED"),
        ("Fasting Glucose", "142", 142.0, "mg/dL", "< 100 mg/dL", None, 100.0, "HIGH", "AI_EXTRACTED", "HUMAN_VERIFIED"),
        ("eGFR", "58", 58.0, "mL/min/1.73m2", "> 60 mL/min/1.73m2", 60.0, None, "LOW", "AI_EXTRACTED", "HUMAN_VERIFIED"),
        ("Serum Ferritin", "14", 14.0, "ng/mL", "N/A", None, None, "REFERENCE_RANGE_UNAVAILABLE", "AI_EXTRACTED", "HUMAN_VERIFIED"),
    ]
    for name, val, num, unit, ref, low, high, stat, prov, verif in baseline_labs:
        db.add(ExtractedLabResult(
            report_id=rep_a.id,
            patient_id=patient.id,
            test_name=name,
            raw_value=val,
            numeric_value=num,
            unit=unit,
            raw_reference_range=ref,
            ref_low=low,
            ref_high=high,
            range_status=stat,
            page_number=1,
            source_snippet=f"{name}: {val} {unit} (Ref: {ref})",
            provenance_type=prov,
            verification_status=verif,
            verified_by_user_id=current_user.id if verif == "HUMAN_VERIFIED" else None,
            verified_at=datetime.now(timezone.utc) if verif == "HUMAN_VERIFIED" else None
        ))

    db.add(ExtractedClinicalEntity(
        report_id=rep_a.id,
        patient_id=patient.id,
        entity_type="MEDICATION",
        entity_name="Metformin",
        details="500mg daily",
        page_number=1,
        source_snippet="Documented Meds: Metformin 500mg daily",
        provenance_type="AI_EXTRACTED",
        verification_status="HUMAN_VERIFIED"
    ))

    # 2. Create Follow-up Report (3 days ago)
    date_b = datetime.now(timezone.utc) - timedelta(days=3)
    pdf_b_name = f"demo_followup_cbc_{patient.id[:8]}.pdf"
    pdf_b_path = os.path.join(settings.UPLOAD_DIR, pdf_b_name)
    _create_synthetic_pdf(
        filepath=pdf_b_path,
        title="Follow-up Metabolic Panel & Hematology",
        date_str=date_b.strftime("%Y-%m-%d"),
        patient_name="Eleanor Vance",
        lab_rows=[
            "Hemoglobin | 11.8 | g/dL | 12.0 - 16.0 g/dL",
            "White Blood Cell (WBC) | 6.9 | 10^3/uL | 4.5 - 11.0 10^3/uL",
            "Platelets | 210 | 10^3/uL | 150 - 450 10^3/uL",
            "Fasting Glucose | 128 | mg/dL | < 100 mg/dL",
            "eGFR | 64 | mL/min/1.73m2 | > 60 mL/min/1.73m2",
            "Serum Ferritin | 22 | ng/mL | 15 - 150 ng/mL",
            "HbA1c | 7.1 | % | < 5.7 %"
        ]
    )

    rep_b = MedicalReport(
        patient_id=patient.id,
        file_name=pdf_b_name,
        original_file_name="Followup_Metabolic_Panel_09022026.pdf",
        file_type="application/pdf",
        file_size_bytes=os.path.getsize(pdf_b_path),
        file_hash="demo_hash_rep_b_8f29k4",
        storage_path=pdf_b_path,
        report_date=date_b,
        facility_name="Metropolitan Clinical Laboratories",
        report_title="Follow-up Metabolic Panel & Hematology",
        processing_status="EXTRACTED",
        uploaded_by_user_id=current_user.id
    )
    db.add(rep_b)
    db.commit()
    db.refresh(rep_b)

    followup_labs = [
        ("Hemoglobin", "11.8", 11.8, "g/dL", "12.0 - 16.0 g/dL", 12.0, 16.0, "LOW", "AI_EXTRACTED", "PENDING_VERIFICATION"),
        ("White Blood Cell (WBC)", "6.9", 6.9, "10^3/uL", "4.5 - 11.0 10^3/uL", 4.5, 11.0, "NORMAL", "AI_EXTRACTED", "PENDING_VERIFICATION"),
        ("Platelets", "210", 210.0, "10^3/uL", "150 - 450 10^3/uL", 150.0, 450.0, "NORMAL", "AI_EXTRACTED", "HUMAN_VERIFIED"),
        ("Fasting Glucose", "128", 128.0, "mg/dL", "< 100 mg/dL", None, 100.0, "HIGH", "AI_EXTRACTED", "PENDING_VERIFICATION"),
        ("eGFR", "64", 64.0, "mL/min/1.73m2", "> 60 mL/min/1.73m2", 60.0, None, "NORMAL", "AI_EXTRACTED", "PENDING_VERIFICATION"),
        ("Serum Ferritin", "22", 22.0, "ng/mL", "15 - 150 ng/mL", 15.0, 150.0, "NORMAL", "AI_EXTRACTED", "PENDING_VERIFICATION"),
        ("HbA1c", "7.1", 7.1, "%", "< 5.7 %", None, 5.7, "HIGH", "AI_EXTRACTED", "PENDING_VERIFICATION")
    ]
    for name, val, num, unit, ref, low, high, stat, prov, verif in followup_labs:
        db.add(ExtractedLabResult(
            report_id=rep_b.id,
            patient_id=patient.id,
            test_name=name,
            raw_value=val,
            numeric_value=num,
            unit=unit,
            raw_reference_range=ref,
            ref_low=low,
            ref_high=high,
            range_status=stat,
            page_number=1,
            source_snippet=f"{name}: {val} {unit} (Ref: {ref})",
            provenance_type=prov,
            verification_status=verif,
            verified_by_user_id=current_user.id if verif == "HUMAN_VERIFIED" else None,
            verified_at=datetime.now(timezone.utc) if verif == "HUMAN_VERIFIED" else None
        ))

    # Followup Clinical Entities with intentional contradictions
    db.add(ExtractedClinicalEntity(
        report_id=rep_b.id,
        patient_id=patient.id,
        entity_type="MEDICATION",
        entity_name="Metformin",
        details="1000mg BID",
        page_number=1,
        source_snippet="Prescribed Discharge Meds: Metformin 1000mg twice daily (BID)",
        provenance_type="AI_EXTRACTED",
        verification_status="PENDING_VERIFICATION"
    ))

    db.add(ExtractedClinicalEntity(
        report_id=rep_b.id,
        patient_id=patient.id,
        entity_type="ALLERGY",
        entity_name="Penicillin",
        details="Reaction: urticaria and acute rash",
        page_number=1,
        source_snippet="Allergies documented: Penicillin (urticaria / rash)",
        provenance_type="AI_EXTRACTED",
        verification_status="PENDING_VERIFICATION"
    ))

    db.commit()

    # Scan and flag conflicts automatically
    scan_and_record_conflicts(patient_id=patient.id, db=db)

    log_audit_event(
        db=db,
        user_id=current_user.id,
        action="SEED_DEMO_PATIENT",
        patient_id=patient.id,
        details={"patient_id": patient.patient_id, "reports_created": 2}
    )

    return {
        "message": "Synthetic demo patient seeded successfully.",
        "patient_id": patient.patient_id,
        "id": patient.id,
        "name": patient.full_name,
        "reports_count": 2,
        "labs_count": len(baseline_labs) + len(followup_labs)
    }
