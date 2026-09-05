from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..core.security import get_current_user
from ..models.db_models import User, Patient
from ..models.schemas import DoctorQueryRequest, DoctorQueryResponse
from ..services.doctor_qa_service import answer_doctor_query
from ..services.audit_service import log_audit_event

router = APIRouter(tags=["Doctor Intelligence ('What Changed?')"])

@router.post("/patients/{patient_id}/ask", response_model=DoctorQueryResponse)
def ask_patient_intelligence(
    patient_id: str,
    query_in: DoctorQueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Doctor-facing record-grounded query interface.
    Answers strictly from structured patient record with source citations and responsible AI guardrails.
    """
    patient = db.query(Patient).filter(
        (Patient.id == patient_id) | (Patient.patient_id == patient_id),
        Patient.created_by_user_id == current_user.id
    ).first()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    response = answer_doctor_query(patient_id=patient.id, query=query_in.query, db=db)

    log_audit_event(
        db=db,
        user_id=current_user.id,
        action="DOCTOR_QUERY",
        patient_id=patient.id,
        details={"query_length": len(query_in.query), "citations_returned": len(response.citations)}
    )

    return response
