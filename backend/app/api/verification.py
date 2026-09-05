from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..core.security import get_current_user
from ..models.db_models import User, ExtractedLabResult, ExtractedClinicalEntity, Patient
from ..models.schemas import (
    VerifyItemRequest, EditItemRequest, RejectItemRequest, ExtractedLabResultResponse
)
from ..services.reference_range_eval import evaluate_reference_range
from ..services.audit_service import log_audit_event

router = APIRouter(prefix="/results", tags=["Human Verification Workflow"])

@router.get("/pending", response_model=list[ExtractedLabResultResponse])
def get_all_pending_verifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Returns all pending verification items across all organization patients."""
    patient_ids = [p[0] for p in db.query(Patient.id).filter(Patient.created_by_user_id == current_user.id).all()]
    if not patient_ids:
        return []
    labs = db.query(ExtractedLabResult).filter(
        ExtractedLabResult.patient_id.in_(patient_ids),
        ExtractedLabResult.verification_status == "PENDING_VERIFICATION"
    ).order_by(ExtractedLabResult.created_at.desc()).all()
    results = []
    for l in labs:
        res = ExtractedLabResultResponse.model_validate(l)
        if l.report:
            res.report_file_name = l.report.original_file_name
            res.report_date = l.report.report_date
        results.append(res)
    return results

@router.post("/{result_id}/verify", response_model=ExtractedLabResultResponse)
def verify_lab_result(
    result_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Marks an AI-extracted lab result as HUMAN_VERIFIED by a clinician."""
    lab = db.query(ExtractedLabResult).filter(ExtractedLabResult.id == result_id).first()
    if not lab:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lab result not found")

    lab.verification_status = "HUMAN_VERIFIED"
    lab.provenance_type = "HUMAN_VERIFIED"
    lab.verified_by_user_id = current_user.id
    lab.verified_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(lab)

    log_audit_event(
        db=db,
        user_id=current_user.id,
        action="VERIFY_LAB_RESULT",
        patient_id=lab.patient_id,
        entity_affected=lab.test_name,
        details={"result_id": lab.id, "value": lab.raw_value}
    )

    res = ExtractedLabResultResponse.model_validate(lab)
    if lab.report:
        res.report_file_name = lab.report.original_file_name
        res.report_date = lab.report.report_date
    return res

@router.put("/{result_id}/edit", response_model=ExtractedLabResultResponse)
def edit_lab_result(
    result_id: str,
    edit_in: EditItemRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Allows clinician to edit an extracted result.
    Preserves original AI-extracted value, re-evaluates reference range deterministically,
    and updates provenance status to HUMAN_VERIFIED with an audit trail.
    """
    lab = db.query(ExtractedLabResult).filter(ExtractedLabResult.id == result_id).first()
    if not lab:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lab result not found")

    # Store original AI extraction before edit if not already stored
    if not lab.original_ai_value:
        lab.original_ai_value = lab.raw_value

    new_val = edit_in.new_value.strip()
    new_range = edit_in.new_reference_range.strip() if edit_in.new_reference_range else lab.raw_reference_range
    new_unit = edit_in.new_unit.strip() if edit_in.new_unit else lab.unit

    # Re-evaluate reference range deterministically with updated values
    range_status, num_val, ref_low, ref_high = evaluate_reference_range(
        result_val_str=new_val,
        ref_range_str=new_range
    )

    lab.raw_value = new_val
    lab.numeric_value = num_val
    lab.unit = new_unit
    lab.raw_reference_range = new_range
    lab.ref_low = ref_low
    lab.ref_high = ref_high
    lab.range_status = range_status
    lab.human_override_notes = edit_in.edit_reason
    lab.verification_status = "HUMAN_VERIFIED"
    lab.provenance_type = "HUMAN_VERIFIED"
    lab.verified_by_user_id = current_user.id
    lab.verified_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(lab)

    log_audit_event(
        db=db,
        user_id=current_user.id,
        action="EDIT_LAB_RESULT",
        patient_id=lab.patient_id,
        entity_affected=lab.test_name,
        details={
            "result_id": lab.id,
            "original_ai_value": lab.original_ai_value,
            "new_value": lab.raw_value,
            "reason": edit_in.edit_reason
        }
    )

    res = ExtractedLabResultResponse.model_validate(lab)
    if lab.report:
        res.report_file_name = lab.report.original_file_name
        res.report_date = lab.report.report_date
    return res

@router.post("/{result_id}/reject", response_model=ExtractedLabResultResponse)
def reject_lab_result(
    result_id: str,
    reject_in: RejectItemRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Rejects an erroneous or hallucinated extraction item with reason."""
    lab = db.query(ExtractedLabResult).filter(ExtractedLabResult.id == result_id).first()
    if not lab:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lab result not found")

    lab.verification_status = "REJECTED"
    lab.human_override_notes = f"Rejected: {reject_in.rejection_reason}"
    lab.verified_by_user_id = current_user.id
    lab.verified_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(lab)

    log_audit_event(
        db=db,
        user_id=current_user.id,
        action="REJECT_LAB_RESULT",
        patient_id=lab.patient_id,
        entity_affected=lab.test_name,
        details={"result_id": lab.id, "rejection_reason": reject_in.rejection_reason}
    )

    res = ExtractedLabResultResponse.model_validate(lab)
    if lab.report:
        res.report_file_name = lab.report.original_file_name
        res.report_date = lab.report.report_date
    return res
