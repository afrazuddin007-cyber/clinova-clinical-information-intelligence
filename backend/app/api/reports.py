import hashlib
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..core.security import get_current_user
from ..core.config import settings
from ..models.db_models import (
    User, Patient, MedicalReport, ExtractedLabResult, ExtractedClinicalEntity
)
from ..models.schemas import (
    MedicalReportResponse, ExtractedLabResultResponse, ExtractedClinicalEntityResponse
)
from ..services.gemini_extractor import extract_structured_report
from ..services.reference_range_eval import evaluate_reference_range
from ..services.conflict_detector import scan_and_record_conflicts
from ..services.audit_service import log_audit_event

router = APIRouter(tags=["Reports & Extractions"])

MAGIC_BYTES = {
    b"%PDF-": "application/pdf",
    b"\x89PNG": "image/png",
    b"\xff\xd8\xff": "image/jpeg",
}

def detect_mime_from_bytes(header: bytes) -> str:
    """Detects actual file MIME type from initial header bytes"""
    for magic, mime in MAGIC_BYTES.items():
        if header.startswith(magic):
            return mime
    return "application/octet-stream"

@router.post("/patients/{patient_id}/reports", response_model=MedicalReportResponse, status_code=status.HTTP_201_CREATED)
async def upload_and_process_report(
    patient_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Uploads a medical report (PDF or Image), executes structured extraction via Gemini 2.5 Flash,
    evaluates reference ranges deterministically, and scans for cross-record conflicts.
    """
    patient = db.query(Patient).filter(
        Patient.id == patient_id,
        Patient.created_by_user_id == current_user.id
    ).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient '{patient_id}' not found or unauthorized."
        )

    # 1. Read file bytes and validate size
    content = await file.read()
    file_size = len(content)
    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is completely empty (0 bytes)."
        )

    if file_size > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {settings.MAX_FILE_SIZE_MB}MB."
        )

    # 2. Magic bytes validation (reject fake extensions)
    detected_mime = detect_mime_from_bytes(content[:8])
    if detected_mime not in settings.ALLOWED_FILE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file format. Clinova supports PDF, PNG, and JPEG documents only (detected: {detected_mime})."
        )

    # 3. Compute SHA-256 integrity hash
    file_hash = hashlib.sha256(content).hexdigest()

    # 4. Save securely to disk with UUID filename (prevent path traversal)
    ext = Path(file.filename or "report.pdf").suffix.lower()
    if not ext:
        ext = ".pdf" if detected_mime == "application/pdf" else ".png"

    safe_stored_name = f"{uuid.uuid4()}{ext}"
    safe_path = Path(settings.UPLOAD_DIR) / safe_stored_name

    with open(safe_path, "wb") as f:
        f.write(content)

    # 5. Create database record
    report_date = datetime.now(timezone.utc)
    new_report = MedicalReport(
        patient_id=patient.id,
        file_name=safe_stored_name,
        original_file_name=file.filename or "Medical_Report.pdf",
        file_type=detected_mime,
        file_size_bytes=file_size,
        file_hash=file_hash,
        storage_path=str(safe_path),
        report_date=report_date,
        processing_status="PROCESSING",
        uploaded_by_user_id=current_user.id
    )
    db.add(new_report)
    db.commit()
    db.refresh(new_report)

    # 6. Execute AI Extraction Pipeline
    try:
        extracted_data = extract_structured_report(str(safe_path), new_report.original_file_name)
        new_report.report_title = extracted_data.report_title
        new_report.facility_name = extracted_data.facility_name
        
        # Parse date if available with flexible format fallbacks
        if extracted_data.report_date:
            parsed_date = None
            try:
                parsed_date = datetime.fromisoformat(extracted_data.report_date)
            except Exception:
                for fmt in ["%d %b %Y", "%d-%b-%Y", "%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"]:
                    try:
                        parsed_date = datetime.strptime(extracted_data.report_date, fmt)
                        break
                    except Exception:
                        pass
            if parsed_date:
                new_report.report_date = parsed_date

        # 7. Process Lab Tests with Deterministic Reference-Range Parser
        # ONLY entries in laboratory_results are saved as ExtractedLabResult
        for raw_lab in extracted_data.laboratory_results:
            range_status, num_val, ref_low, ref_high = evaluate_reference_range(
                result_val_str=raw_lab.value,
                ref_range_str=raw_lab.reference_range
            )

            lab_record = ExtractedLabResult(
                report_id=new_report.id,
                patient_id=patient.id,
                test_name=raw_lab.test_name,
                raw_value=raw_lab.value,
                numeric_value=num_val,
                unit=raw_lab.unit,
                raw_reference_range=raw_lab.reference_range,
                ref_low=ref_low,
                ref_high=ref_high,
                range_status=range_status,
                observations=raw_lab.observation,
                page_number=raw_lab.source_page,
                source_snippet=raw_lab.source_snippet,
                provenance_type="AI_EXTRACTED",
                verification_status="PENDING_VERIFICATION"
            )
            db.add(lab_record)

        # 8. Process Clinical Entities (Medications, Conditions, Allergies, Symptoms, Observations)
        for raw_ent in extracted_data.clinical_entities:
            ent_record = ExtractedClinicalEntity(
                report_id=new_report.id,
                patient_id=patient.id,
                entity_type=raw_ent.entity_type,
                entity_name=raw_ent.entity_name,
                details=raw_ent.details,
                page_number=raw_ent.source_page,
                source_snippet=raw_ent.source_snippet,
                provenance_type="AI_EXTRACTED",
                verification_status="PENDING_VERIFICATION"
            )
            db.add(ent_record)

        new_report.processing_status = "EXTRACTED"
        db.commit()

        # 9. Run Cross-Record Conflict Scanner
        scan_and_record_conflicts(patient_id=patient.id, db=db)

        # 10. Log Audit Event
        log_audit_event(
            db=db,
            user_id=current_user.id,
            action="UPLOAD_AND_EXTRACT_REPORT",
            patient_id=patient.id,
            entity_affected=new_report.original_file_name,
            details={
                "report_id": new_report.id,
                "labs_extracted": len(extracted_data.lab_tests),
                "entities_extracted": len(extracted_data.clinical_entities)
            }
        )

    except Exception as e:
        new_report.processing_status = "ERROR"
        new_report.error_message = str(e)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Report uploaded, but AI extraction pipeline encountered an error: {str(e)}"
        )

    resp = MedicalReportResponse.model_validate(new_report)
    resp.lab_count = len(new_report.lab_results)
    resp.entity_count = len(new_report.clinical_entities)
    return resp

@router.get("/patients/{patient_id}/reports", response_model=List[MedicalReportResponse])
def list_patient_reports(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lists all uploaded reports for a patient chronologically."""
    patient = db.query(Patient).filter(
        Patient.id == patient_id,
        Patient.created_by_user_id == current_user.id
    ).first()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    reports = db.query(MedicalReport).filter(
        MedicalReport.patient_id == patient.id
    ).order_by(MedicalReport.report_date.desc()).all()

    res = []
    for r in reports:
        item = MedicalReportResponse.model_validate(r)
        item.lab_count = len(r.lab_results)
        item.entity_count = len(r.clinical_entities)
        res.append(item)
    return res

@router.get("/reports", response_model=List[MedicalReportResponse])
def list_all_organization_reports(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lists all uploaded medical records across the clinician's organization."""
    patient_ids = [p[0] for p in db.query(Patient.id).filter(Patient.created_by_user_id == current_user.id).all()]
    if not patient_ids:
        return []
    reports = db.query(MedicalReport).filter(
        MedicalReport.patient_id.in_(patient_ids)
    ).order_by(MedicalReport.report_date.desc()).all()
    res = []
    for r in reports:
        item = MedicalReportResponse.model_validate(r)
        item.lab_count = len(r.lab_results)
        item.entity_count = len(r.clinical_entities)
        res.append(item)
    return res

@router.get("/reports/{report_id}/file")
def get_report_file(
    report_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Streams original report PDF or image for in-app document & provenance viewer."""
    report = db.query(MedicalReport).filter(MedicalReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    # Authorize clinician has access to this report's patient
    patient = db.query(Patient).filter(
        Patient.id == report.patient_id,
        Patient.created_by_user_id == current_user.id
    ).first()
    if not patient:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    if not os.path.exists(report.storage_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Original document file not found on server")

    return FileResponse(
        path=report.storage_path,
        media_type=report.file_type,
        filename=report.original_file_name
    )

@router.get("/patients/{patient_id}/labs", response_model=List[ExtractedLabResultResponse])
def get_all_patient_labs(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Returns all structured laboratory results across all patient reports."""
    patient = db.query(Patient).filter(
        Patient.id == patient_id,
        Patient.created_by_user_id == current_user.id
    ).first()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    labs = db.query(ExtractedLabResult).filter(
        ExtractedLabResult.patient_id == patient.id
    ).order_by(ExtractedLabResult.created_at.desc()).all()

    results = []
    for l in labs:
        res = ExtractedLabResultResponse.model_validate(l)
        if l.report:
            res.report_file_name = l.report.original_file_name
            res.report_date = l.report.report_date
        results.append(res)
    return results

@router.get("/patients/{patient_id}/entities", response_model=List[ExtractedClinicalEntityResponse])
def get_all_patient_entities(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Returns all extracted clinical entities (medications, conditions, allergies)."""
    patient = db.query(Patient).filter(
        Patient.id == patient_id,
        Patient.created_by_user_id == current_user.id
    ).first()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    entities = db.query(ExtractedClinicalEntity).filter(
        ExtractedClinicalEntity.patient_id == patient.id
    ).order_by(ExtractedClinicalEntity.created_at.desc()).all()

    return [ExtractedClinicalEntityResponse.model_validate(e) for e in entities]
