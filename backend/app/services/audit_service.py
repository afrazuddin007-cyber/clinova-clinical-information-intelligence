from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from ..models.db_models import AuditLog

def log_audit_event(
    db: Session,
    user_id: str,
    action: str,
    patient_id: Optional[str] = None,
    entity_affected: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> AuditLog:
    """
    Records a lightweight audit log entry.
    Avoids logging sensitive patient text or PII unnecessarily.
    """
    log_entry = AuditLog(
        patient_id=patient_id,
        user_id=user_id,
        action=action,
        entity_affected=entity_affected,
        details=details or {}
    )
    db.add(log_entry)
    db.commit()
    return log_entry
