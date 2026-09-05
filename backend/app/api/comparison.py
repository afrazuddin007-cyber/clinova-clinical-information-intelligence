from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..core.security import get_current_user
from ..models.db_models import User, Patient
from ..models.schemas import ReportComparisonResponse
from ..services.comparison_service import compare_two_reports
from ..services.audit_service import log_audit_event

router = APIRouter(tags=["Report Comparison"])

@router.get("/patients/{patient_id}/compare", response_model=ReportComparisonResponse)
def compare_patient_reports(
    patient_id: str,
    report_a: str = Query(..., description="ID of baseline/older report"),
    report_b: str = Query(..., description="ID of latest/newer report"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Compares two reports for a patient.
    Outputs: NEW, CHANGED (with % deltas), UNCHANGED, INCOMPARABLE items.
    """
    patient = db.query(Patient).filter(
        Patient.id == patient_id,
        Patient.created_by_user_id == current_user.id
    ).first()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    try:
        comparison_res = compare_two_reports(report_a_id=report_a, report_b_id=report_b, db=db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    log_audit_event(
        db=db,
        user_id=current_user.id,
        action="COMPARE_REPORTS",
        patient_id=patient.id,
        details={
            "report_a": report_a,
            "report_b": report_b,
            "changed_count": comparison_res.changed_count,
            "new_count": comparison_res.new_count
        }
    )

    return comparison_res
