from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..core.security import get_current_user
from ..models.db_models import User, Patient, Inconsistency
from ..models.schemas import InconsistencyResponse
from ..services.conflict_detector import scan_and_record_conflicts
from ..services.audit_service import log_audit_event

router = APIRouter(tags=["Cross-Record Conflicts"])

@router.get("/patients/{patient_id}/conflicts", response_model=List[InconsistencyResponse])
def get_patient_conflicts(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves all flagged discrepancies across intake, previous reports, and current reports.
    Always triggers a fresh scan to ensure up-to-date detection.
    """
    patient = db.query(Patient).filter(
        Patient.id == patient_id,
        Patient.created_by_user_id == current_user.id
    ).first()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    # Run scanner to discover any new conflicts
    scan_and_record_conflicts(patient_id=patient.id, db=db)

    conflicts = db.query(Inconsistency).filter(
        Inconsistency.patient_id == patient.id
    ).order_by(Inconsistency.created_at.desc()).all()

    return [InconsistencyResponse.model_validate(c) for c in conflicts]

@router.post("/conflicts/{conflict_id}/acknowledge", response_model=InconsistencyResponse)
def acknowledge_conflict(
    conflict_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Marks a flagged conflict as reviewed & acknowledged by the clinician."""
    conflict = db.query(Inconsistency).filter(Inconsistency.id == conflict_id).first()
    if not conflict:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conflict not found")

    # Authorize clinician has access to this conflict's patient
    patient = db.query(Patient).filter(
        Patient.id == conflict.patient_id,
        Patient.created_by_user_id == current_user.id
    ).first()
    if not patient:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    conflict.resolution_status = "ACKNOWLEDGED"
    db.commit()
    db.refresh(conflict)

    log_audit_event(
        db=db,
        user_id=current_user.id,
        action="ACKNOWLEDGE_CONFLICT",
        patient_id=conflict.patient_id,
        entity_affected=conflict.entity_name,
        details={"conflict_id": conflict.id, "category": conflict.category}
    )

    return InconsistencyResponse.model_validate(conflict)
