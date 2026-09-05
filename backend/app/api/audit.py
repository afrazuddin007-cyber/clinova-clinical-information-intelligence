from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..core.security import get_current_user
from ..models.db_models import User, AuditLog, Patient

router = APIRouter(prefix="/audit", tags=["Audit Logs & Activity"])

class AuditLogEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: Optional[str] = None
    patient_name: Optional[str] = None
    user_id: str
    user_name: Optional[str] = None
    action: str
    entity_affected: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime

@router.get("/logs", response_model=List[AuditLogEntry])
def get_audit_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Returns recent audit events for the clinician's organization."""
    patient_map = {
        p.id: p.full_name for p in db.query(Patient.id, Patient.full_name).filter(Patient.created_by_user_id == current_user.id).all()
    }
    patient_ids = list(patient_map.keys())

    query = db.query(AuditLog)
    if patient_ids:
        query = query.filter(
            (AuditLog.user_id == current_user.id) | (AuditLog.patient_id.in_(patient_ids))
        )
    else:
        query = query.filter(AuditLog.user_id == current_user.id)

    logs = query.order_by(AuditLog.timestamp.desc()).limit(100).all()

    entries = []
    for log in logs:
        entries.append(AuditLogEntry(
            id=log.id,
            patient_id=log.patient_id,
            patient_name=patient_map.get(log.patient_id) if log.patient_id else None,
            user_id=log.user_id,
            user_name=current_user.full_name if log.user_id == current_user.id else "Clinician",
            action=log.action,
            entity_affected=log.entity_affected,
            details=log.details,
            timestamp=log.timestamp
        ))
    return entries
