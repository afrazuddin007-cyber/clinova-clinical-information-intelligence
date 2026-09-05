import secrets
import string
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..core.security import get_current_user
from ..models.db_models import User, Patient, MedicalReport, ExtractedLabResult, Inconsistency
from ..models.schemas import (
    PatientCreate, PatientIntakeUpdate, PatientResponse, PatientSummaryResponse
)
from ..services.patient_summary_service import generate_patient_summary
from ..services.audit_service import log_audit_event

router = APIRouter(prefix="/patients", tags=["Patients"])

def generate_unique_patient_id(db: Session) -> str:
    """Generates a non-confusing alphanumeric Patient ID matching pattern: CL-XXXXXX"""
    # Exclude confusing characters: 0, O, 1, I
    alphabet = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
    for _ in range(20):
        code = "".join(secrets.choice(alphabet) for _ in range(6))
        candidate = f"CL-{code}"
        existing = db.query(Patient).filter(Patient.patient_id == candidate).first()
        if not existing:
            return candidate
    # Fallback with extra random digits
    return f"CL-{secrets.token_hex(3).upper()}"

@router.get("", response_model=List[PatientResponse])
def list_patients(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lists all patients authorized for the current clinician."""
    patients = db.query(Patient).filter(
        Patient.created_by_user_id == current_user.id
    ).order_by(Patient.updated_at.desc()).all()

    if not patients:
        return []

    from sqlalchemy import func

    patient_ids = [p.id for p in patients]

    # Bulk fetch report counts
    rep_counts = dict(
        db.query(MedicalReport.patient_id, func.count(MedicalReport.id))
        .filter(MedicalReport.patient_id.in_(patient_ids))
        .group_by(MedicalReport.patient_id)
        .all()
    )

    # Bulk fetch pending verification counts
    pending_counts = dict(
        db.query(ExtractedLabResult.patient_id, func.count(ExtractedLabResult.id))
        .filter(
            ExtractedLabResult.patient_id.in_(patient_ids),
            ExtractedLabResult.verification_status == "PENDING_VERIFICATION"
        )
        .group_by(ExtractedLabResult.patient_id)
        .all()
    )

    # Bulk fetch active conflict counts
    conflict_counts = dict(
        db.query(Inconsistency.patient_id, func.count(Inconsistency.id))
        .filter(
            Inconsistency.patient_id.in_(patient_ids),
            Inconsistency.resolution_status == "FLAGGED"
        )
        .group_by(Inconsistency.patient_id)
        .all()
    )

    result = []
    for p in patients:
        resp = PatientResponse.model_validate(p)
        resp.report_count = rep_counts.get(p.id, 0)
        resp.pending_verifications_count = pending_counts.get(p.id, 0)
        resp.conflict_count = conflict_counts.get(p.id, 0)
        result.append(resp)

    return result

@router.post("", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
def create_patient(
    patient_in: PatientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Creates a new patient profile with unique ID and initial clinical intake."""
    unique_pid = generate_unique_patient_id(db)

    new_patient = Patient(
        patient_id=unique_pid,
        full_name=patient_in.full_name.strip(),
        age=patient_in.age,
        sex=patient_in.sex,
        symptoms=patient_in.symptoms,
        existing_conditions=patient_in.existing_conditions,
        allergies=patient_in.allergies,
        current_medications=patient_in.current_medications,
        medical_history=patient_in.medical_history,
        additional_notes=patient_in.additional_notes,
        created_by_user_id=current_user.id
    )
    db.add(new_patient)
    db.commit()
    db.refresh(new_patient)

    log_audit_event(
        db=db,
        user_id=current_user.id,
        action="CREATE_PATIENT",
        patient_id=new_patient.id,
        details={"patient_id": new_patient.patient_id, "name": new_patient.full_name}
    )

    resp = PatientResponse.model_validate(new_patient)
    resp.report_count = 0
    resp.pending_verifications_count = 0
    resp.conflict_count = 0
    return resp

@router.get("/{patient_id}", response_model=PatientResponse)
def get_patient(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieves patient details with security authorization."""
    patient = db.query(Patient).filter(
        Patient.id == patient_id,
        Patient.created_by_user_id == current_user.id
    ).first()

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient record '{patient_id}' not found or access denied."
        )

    rep_count = db.query(MedicalReport).filter(MedicalReport.patient_id == patient.id).count()
    pending_count = db.query(ExtractedLabResult).filter(
        ExtractedLabResult.patient_id == patient.id,
        ExtractedLabResult.verification_status == "PENDING_VERIFICATION"
    ).count()
    conflicts_count = db.query(Inconsistency).filter(
        Inconsistency.patient_id == patient.id,
        Inconsistency.resolution_status == "FLAGGED"
    ).count()

    resp = PatientResponse.model_validate(patient)
    resp.report_count = rep_count
    resp.pending_verifications_count = pending_count
    resp.conflict_count = conflicts_count
    return resp

@router.put("/{patient_id}/intake", response_model=PatientResponse)
def update_patient_intake(
    patient_id: str,
    intake_in: PatientIntakeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Updates manual clinical intake information."""
    patient = db.query(Patient).filter(
        Patient.id == patient_id,
        Patient.created_by_user_id == current_user.id
    ).first()

    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    if intake_in.symptoms is not None:
        patient.symptoms = intake_in.symptoms
    if intake_in.existing_conditions is not None:
        patient.existing_conditions = intake_in.existing_conditions
    if intake_in.allergies is not None:
        patient.allergies = intake_in.allergies
    if intake_in.current_medications is not None:
        patient.current_medications = intake_in.current_medications
    if intake_in.medical_history is not None:
        patient.medical_history = intake_in.medical_history
    if intake_in.additional_notes is not None:
        patient.additional_notes = intake_in.additional_notes

    db.commit()
    db.refresh(patient)

    log_audit_event(
        db=db,
        user_id=current_user.id,
        action="UPDATE_INTAKE",
        patient_id=patient.id,
        details={"updated_fields": list(intake_in.model_dump(exclude_unset=True).keys())}
    )

    return get_patient(patient_id, db, current_user)

@router.get("/{patient_id}/summary", response_model=PatientSummaryResponse)
def get_patient_summary(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generates an AI-powered, record-grounded patient summary."""
    patient = db.query(Patient).filter(
        Patient.id == patient_id,
        Patient.created_by_user_id == current_user.id
    ).first()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    return generate_patient_summary(patient_id=patient.id, db=db)
