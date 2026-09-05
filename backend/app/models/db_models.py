import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Integer, Float, DateTime, ForeignKey, Text, JSON
)
from sqlalchemy.orm import relationship
from ..core.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    organization_name = Column(String(255), default="MVSR Medical Center", nullable=True)
    role = Column(String(50), default="doctor")  # doctor, reviewer, admin
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    patients = relationship("Patient", back_populates="creator")

class Patient(Base):
    __tablename__ = "patients"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    patient_id = Column(String(32), unique=True, index=True, nullable=False)  # e.g. CL-8F29K4
    full_name = Column(String(255), nullable=False)
    age = Column(Integer, nullable=False)
    sex = Column(String(20), nullable=False)  # male, female, other
    
    # Clinical intake fields (Distinguished as USER_PROVIDED)
    symptoms = Column(Text, nullable=True)
    existing_conditions = Column(Text, nullable=True)
    allergies = Column(Text, nullable=True)
    current_medications = Column(Text, nullable=True)
    medical_history = Column(Text, nullable=True)
    additional_notes = Column(Text, nullable=True)

    created_by_user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    creator = relationship("User", back_populates="patients")
    reports = relationship("MedicalReport", back_populates="patient", cascade="all, delete-orphan", order_by="desc(MedicalReport.report_date)")
    lab_results = relationship("ExtractedLabResult", back_populates="patient", cascade="all, delete-orphan")
    clinical_entities = relationship("ExtractedClinicalEntity", back_populates="patient", cascade="all, delete-orphan")
    conflicts = relationship("Inconsistency", back_populates="patient", cascade="all, delete-orphan")

class MedicalReport(Base):
    __tablename__ = "medical_reports"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    patient_id = Column(String(36), ForeignKey("patients.id"), nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    original_file_name = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    file_hash = Column(String(64), nullable=False)  # SHA-256
    storage_path = Column(String(512), nullable=False)
    report_date = Column(DateTime, nullable=True)
    facility_name = Column(String(255), nullable=True)
    report_title = Column(String(255), nullable=True)
    
    # Status: UPLOADED, EXTRACTING, EXTRACTED, ERROR
    processing_status = Column(String(50), default="UPLOADED")
    error_message = Column(Text, nullable=True)

    uploaded_by_user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    uploaded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    patient = relationship("Patient", back_populates="reports")
    lab_results = relationship("ExtractedLabResult", back_populates="report", cascade="all, delete-orphan")
    clinical_entities = relationship("ExtractedClinicalEntity", back_populates="report", cascade="all, delete-orphan")

class ExtractedLabResult(Base):
    __tablename__ = "extracted_lab_results"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    report_id = Column(String(36), ForeignKey("medical_reports.id"), nullable=False, index=True)
    patient_id = Column(String(36), ForeignKey("patients.id"), nullable=False, index=True)
    
    test_name = Column(String(255), nullable=False, index=True)
    raw_value = Column(String(100), nullable=False)
    numeric_value = Column(Float, nullable=True)
    unit = Column(String(50), nullable=True)
    
    # Reference range explicitly from report
    raw_reference_range = Column(String(100), nullable=True)
    ref_low = Column(Float, nullable=True)
    ref_high = Column(Float, nullable=True)
    
    # Status: LOW, NORMAL, HIGH, REFERENCE_RANGE_UNAVAILABLE
    range_status = Column(String(50), nullable=False)
    observations = Column(Text, nullable=True)

    # Provenance tracking
    page_number = Column(Integer, default=1)
    source_snippet = Column(Text, nullable=True)
    provenance_type = Column(String(50), default="AI_EXTRACTED")  # AI_EXTRACTED, HUMAN_VERIFIED
    
    # Verification workflow: AI_EXTRACTED, PENDING_VERIFICATION, HUMAN_VERIFIED, REJECTED
    verification_status = Column(String(50), default="PENDING_VERIFICATION", index=True)
    verified_by_user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    verified_at = Column(DateTime, nullable=True)
    human_override_notes = Column(Text, nullable=True)
    original_ai_value = Column(String(100), nullable=True)  # Auditing original value before edit

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    report = relationship("MedicalReport", back_populates="lab_results")
    patient = relationship("Patient", back_populates="lab_results")

class ExtractedClinicalEntity(Base):
    __tablename__ = "extracted_clinical_entities"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    report_id = Column(String(36), ForeignKey("medical_reports.id"), nullable=False, index=True)
    patient_id = Column(String(36), ForeignKey("patients.id"), nullable=False, index=True)
    
    # MEDICATION, CONDITION, ALLERGY, OBSERVATION
    entity_type = Column(String(50), nullable=False, index=True)
    entity_name = Column(String(255), nullable=False)
    details = Column(Text, nullable=True)  # dosage, frequency, status, etc.
    
    # Provenance
    page_number = Column(Integer, default=1)
    source_snippet = Column(Text, nullable=True)
    provenance_type = Column(String(50), default="AI_EXTRACTED")
    
    # Verification
    verification_status = Column(String(50), default="PENDING_VERIFICATION")
    verified_by_user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    verified_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    report = relationship("MedicalReport", back_populates="clinical_entities")
    patient = relationship("Patient", back_populates="clinical_entities")

class Inconsistency(Base):
    __tablename__ = "inconsistencies"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    patient_id = Column(String(36), ForeignKey("patients.id"), nullable=False, index=True)
    
    # ALLERGY, MEDICATION, DEMOGRAPHIC, CLINICAL
    category = Column(String(50), nullable=False)
    entity_name = Column(String(255), nullable=False)
    source_a = Column(JSON, nullable=False)  # {type: "intake"|"report", id, text, date}
    source_b = Column(JSON, nullable=False)  # {type: "intake"|"report", id, text, date}
    conflict_description = Column(Text, nullable=False)
    
    # FLAGGED, ACKNOWLEDGED
    resolution_status = Column(String(50), default="FLAGGED")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    patient = relationship("Patient", back_populates="conflicts")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    patient_id = Column(String(36), nullable=True, index=True)
    user_id = Column(String(36), nullable=False)
    action = Column(String(100), nullable=False)  # CREATE_PATIENT, UPLOAD_REPORT, VERIFY_ITEM, EDIT_ITEM, REJECT_ITEM
    entity_affected = Column(String(100), nullable=True)
    details = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
