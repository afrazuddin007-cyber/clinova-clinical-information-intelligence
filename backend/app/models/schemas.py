from datetime import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field, ConfigDict

# ----------------- Auth Schemas -----------------
class UserRegister(BaseModel):
    email: str = Field(..., pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$")
    password: str = Field(min_length=6)
    full_name: str
    organization_name: Optional[str] = "MVSR Medical Center"
    role: str = "doctor"

class OrganizationRegister(BaseModel):
    organization_name: str = Field(..., min_length=2)
    admin_name: str = Field(..., min_length=2)
    email: str = Field(..., pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$")
    password: str = Field(min_length=6)

class UserLogin(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    organization_name: Optional[str] = "MVSR Medical Center"
    role: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

# ----------------- Patient Schemas -----------------
class PatientCreate(BaseModel):
    full_name: str = Field(..., min_length=2)
    age: int = Field(..., ge=0, le=130)
    sex: str = Field(..., pattern="^(male|female|other)$")
    symptoms: Optional[str] = None
    existing_conditions: Optional[str] = None
    allergies: Optional[str] = None
    current_medications: Optional[str] = None
    medical_history: Optional[str] = None
    additional_notes: Optional[str] = None

class PatientIntakeUpdate(BaseModel):
    symptoms: Optional[str] = None
    existing_conditions: Optional[str] = None
    allergies: Optional[str] = None
    current_medications: Optional[str] = None
    medical_history: Optional[str] = None
    additional_notes: Optional[str] = None

class PatientResponse(BaseModel):
    id: str
    patient_id: str
    full_name: str
    age: int
    sex: str
    symptoms: Optional[str] = None
    existing_conditions: Optional[str] = None
    allergies: Optional[str] = None
    current_medications: Optional[str] = None
    medical_history: Optional[str] = None
    additional_notes: Optional[str] = None
    created_by_user_id: str
    created_at: datetime
    updated_at: datetime
    report_count: int = 0
    pending_verifications_count: int = 0
    conflict_count: int = 0

    model_config = ConfigDict(from_attributes=True)

# ----------------- AI Structured Output Schemas -----------------
class PatientDemographics(BaseModel):
    patient_name: Optional[str] = Field(None, description="Patient full name as printed on report")
    patient_id: Optional[str] = Field(None, description="Patient medical record / ID number")
    age: Optional[int] = Field(None, description="Patient age in years")
    sex: Optional[str] = Field(None, description="Patient sex / gender")
    report_date: Optional[str] = Field(None, description="Specimen or report date (YYYY-MM-DD or as printed)")
    facility_name: Optional[str] = Field(None, description="Laboratory, clinic, or diagnostic facility name")
    ordering_service: Optional[str] = Field(None, description="Ordering physician or medical service")

class RawExtractedLab(BaseModel):
    test_name: str = Field(
        description=(
            "Exact laboratory test or biomarker name as printed in the report (e.g. 'Hemoglobin', 'HbA1c', 'Fasting Glucose', 'Creatinine'). "
            "NEVER use medications, diagnoses, dates, page numbers, or section headings as test_name. "
            "A medication (e.g. 'Metformin 500 mg') or diagnosis (e.g. 'Type 2 Diabetes') MUST NEVER be a lab finding."
        )
    )
    value: str = Field(
        description="Measured laboratory result value (e.g. '11.8', '245', 'Negative', '>=60', '<5')."
    )
    unit: Optional[str] = Field(
        None,
        description="Measurement unit (e.g. 'g/dL', 'mg/dL', '10³/µL', '%', 'mL/min/1.73m²', 'U/L'). NEVER the reference range."
    )
    reference_range: Optional[str] = Field(
        None,
        description=(
            "EXACT reference range text as printed in the document for this specific test row "
            "(e.g. '13.5–17.5', '70–99', '0–149', '>=60'). "
            "Set to null if no reference range is printed. "
            "NEVER invent or assume a reference range. NEVER store a unit (like mg/dL) here."
        )
    )
    observation: Optional[str] = Field(
        None,
        description="Specific clinical flag or observation printed in the document (e.g. 'HIGH', 'LOW', 'NORMAL', 'CRITICAL')."
    )
    test_date: Optional[str] = Field(
        None,
        description="Date the test was collected or analyzed if explicitly stated in the row or section."
    )
    source_page: int = Field(default=1, description="1-indexed page number where this result appears.")
    source_snippet: str = Field(default="", description="Verbatim text fragment from document containing this result.")

    # Seamless backward compatibility properties
    @property
    def result_value(self) -> str:
        return self.value

    @property
    def reference_range_raw(self) -> Optional[str]:
        return self.reference_range

    @property
    def observations(self) -> Optional[str]:
        return self.observation

    @property
    def page_number(self) -> int:
        return self.source_page

    def __init__(self, **data):
        if "result_value" in data and "value" not in data:
            data["value"] = data.pop("result_value")
        if "reference_range_raw" in data and "reference_range" not in data:
            data["reference_range"] = data.pop("reference_range_raw")
        if "observations" in data and "observation" not in data:
            data["observation"] = data.pop("observations")
        if "page_number" in data and "source_page" not in data:
            data["source_page"] = data.pop("page_number")
        super().__init__(**data)

class RawExtractedEntity(BaseModel):
    category: str = Field(
        description="One of: 'MEDICATIONS', 'ALLERGIES', 'CONDITIONS', 'SYMPTOMS', 'CLINICAL_HISTORY', 'OTHER_DIAGNOSTIC_FINDINGS'"
    )
    entity_name: str = Field(description="Name of medication, condition, allergen, symptom, or finding.")
    details: Optional[str] = Field(None, description="Dosage, frequency, status, severity, or notes.")
    source_page: int = Field(default=1, description="1-indexed source page number.")
    source_snippet: str = Field(default="", description="Exact verbatim text fragment from document.")

    # Backward compatibility
    @property
    def entity_type(self) -> str:
        cat = (self.category or "").upper()
        if "MEDICATION" in cat:
            return "MEDICATION"
        if "ALLERG" in cat:
            return "ALLERGY"
        if "CONDITION" in cat:
            return "CONDITION"
        if "SYMPTOM" in cat:
            return "SYMPTOM"
        if "CLINICAL_HISTORY" in cat or "HISTORY" in cat:
            return "CLINICAL_HISTORY"
        return "OBSERVATION"

    @property
    def page_number(self) -> int:
        return self.source_page

    def __init__(self, **data):
        if "entity_type" in data and "category" not in data:
            data["category"] = data.pop("entity_type")
        if "page_number" in data and "source_page" not in data:
            data["source_page"] = data.pop("page_number")
        super().__init__(**data)

class ReportExtractionStructuredOutput(BaseModel):
    report_title: Optional[str] = Field(None, description="Document title if explicitly present")
    report_date: Optional[str] = Field(None, description="Report date in YYYY-MM-DD or textual date if present")
    facility_name: Optional[str] = Field(None, description="Laboratory or clinic name")
    patient_demographics: Optional[PatientDemographics] = Field(None, description="Patient demographic details")
    clinical_history: List[RawExtractedEntity] = Field(default_factory=list, description="General clinical history")
    medications: List[RawExtractedEntity] = Field(default_factory=list, description="Prescribed / current medications with dosages")
    allergies: List[RawExtractedEntity] = Field(default_factory=list, description="Documented patient allergies and sensitivities")
    conditions: List[RawExtractedEntity] = Field(default_factory=list, description="Documented patient conditions, diagnoses, and medical problems")
    symptoms: List[RawExtractedEntity] = Field(default_factory=list, description="Active symptoms, complaints, or reasons for visit")
    laboratory_results: List[RawExtractedLab] = Field(
        default_factory=list,
        description="Actual measured laboratory test rows ONLY. NEVER medications, diagnoses, or non-lab text."
    )
    other_diagnostic_findings: List[RawExtractedEntity] = Field(default_factory=list, description="Narrative laboratory observations or other diagnostic findings")

    # Seamless backward compatibility properties
    @property
    def lab_tests(self) -> List[RawExtractedLab]:
        return self.laboratory_results

    @property
    def clinical_entities(self) -> List[RawExtractedEntity]:
        all_entities = []
        all_entities.extend(self.medications)
        all_entities.extend(self.allergies)
        all_entities.extend(self.conditions)
        all_entities.extend(self.symptoms)
        all_entities.extend(self.clinical_history)
        all_entities.extend(self.other_diagnostic_findings)
        return all_entities

    def __init__(self, **data):
        if "lab_tests" in data and "laboratory_results" not in data:
            data["laboratory_results"] = data.pop("lab_tests")
        if "clinical_entities" in data:
            ents = data.pop("clinical_entities")
            for e in ents:
                ent = e if isinstance(e, RawExtractedEntity) else RawExtractedEntity(**e)
                cat = (ent.category or "").upper()
                if "MEDICATION" in cat:
                    data.setdefault("medications", []).append(ent)
                elif "ALLERG" in cat:
                    data.setdefault("allergies", []).append(ent)
                elif "CONDITION" in cat:
                    data.setdefault("conditions", []).append(ent)
                elif "SYMPTOM" in cat:
                    data.setdefault("symptoms", []).append(ent)
                else:
                    data.setdefault("other_diagnostic_findings", []).append(ent)
        super().__init__(**data)

# ----------------- Results & Provenance Schemas -----------------
class ExtractedLabResultResponse(BaseModel):
    id: str
    report_id: str
    patient_id: str
    test_name: str
    raw_value: str
    numeric_value: Optional[float] = None
    unit: Optional[str] = None
    raw_reference_range: Optional[str] = None
    ref_low: Optional[float] = None
    ref_high: Optional[float] = None
    range_status: str  # LOW, NORMAL, HIGH, REFERENCE_RANGE_UNAVAILABLE
    observations: Optional[str] = None
    page_number: int
    source_snippet: Optional[str] = None
    provenance_type: str  # AI_EXTRACTED, HUMAN_VERIFIED
    verification_status: str  # AI_EXTRACTED, PENDING_VERIFICATION, HUMAN_VERIFIED, REJECTED
    verified_by_user_id: Optional[str] = None
    verified_at: Optional[datetime] = None
    human_override_notes: Optional[str] = None
    original_ai_value: Optional[str] = None
    created_at: datetime
    report_file_name: Optional[str] = None
    report_date: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class ExtractedClinicalEntityResponse(BaseModel):
    id: str
    report_id: str
    patient_id: str
    entity_type: str
    entity_name: str
    details: Optional[str] = None
    page_number: int
    source_snippet: Optional[str] = None
    provenance_type: str
    verification_status: str
    verified_by_user_id: Optional[str] = None
    verified_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# ----------------- Report Schemas -----------------
class MedicalReportResponse(BaseModel):
    id: str
    patient_id: str
    file_name: str
    original_file_name: str
    file_type: str
    file_size_bytes: int
    report_date: Optional[datetime] = None
    facility_name: Optional[str] = None
    report_title: Optional[str] = None
    processing_status: str
    error_message: Optional[str] = None
    uploaded_at: datetime
    lab_count: int = 0
    entity_count: int = 0

    model_config = ConfigDict(from_attributes=True)

# ----------------- Verification Action Schemas -----------------
class VerifyItemRequest(BaseModel):
    pass

class EditItemRequest(BaseModel):
    new_value: str
    new_unit: Optional[str] = None
    new_reference_range: Optional[str] = None
    edit_reason: str = Field(..., min_length=3, description="Clinical reason for edit")

class RejectItemRequest(BaseModel):
    rejection_reason: str = Field(..., min_length=3)

# ----------------- Comparison Schemas -----------------
class ComparisonItem(BaseModel):
    test_name: str
    status_tag: str  # NEW, CHANGED, UNCHANGED, INCOMPARABLE
    unit: Optional[str] = None
    report_a_value: Optional[str] = None
    report_b_value: Optional[str] = None
    report_a_range: Optional[str] = None
    report_b_range: Optional[str] = None
    report_a_status: Optional[str] = None
    report_b_status: Optional[str] = None
    numeric_delta: Optional[float] = None
    percentage_delta: Optional[float] = None
    delta_display: Optional[str] = None
    notes: Optional[str] = None

class ReportComparisonResponse(BaseModel):
    report_a_id: str
    report_b_id: str
    report_a_name: str
    report_b_name: str
    report_a_date: Optional[datetime] = None
    report_b_date: Optional[datetime] = None
    items: List[ComparisonItem]
    new_count: int
    changed_count: int
    unchanged_count: int
    incomparable_count: int

# ----------------- Conflict Schemas -----------------
class InconsistencyResponse(BaseModel):
    id: str
    patient_id: str
    category: str
    entity_name: str
    source_a: Dict[str, Any]
    source_b: Dict[str, Any]
    conflict_description: str
    resolution_status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# ----------------- Doctor Intelligence Q&A Schemas -----------------
class DoctorQueryRequest(BaseModel):
    query: str = Field(..., min_length=3)

class GroundedSourceCitation(BaseModel):
    source_type: str  # "report" | "intake"
    source_title: str
    page_number: Optional[int] = None
    snippet: Optional[str] = None

class DoctorQueryResponse(BaseModel):
    answer: str
    citations: List[GroundedSourceCitation]
    disclaimer: str = "Clinova provides information synthesis from verified patient records only. It does not diagnose, prescribe, or provide medical advice."

# ----------------- Patient Summary Schema -----------------
class PatientSummaryResponse(BaseModel):
    summary: str
    grounded_record_count: int
    disclaimer: str = "This summary organizes explicitly documented medical records. Clinova is not a diagnostic or treatment system."

# ----------------- Health Check Schema -----------------
class HealthCheckResponse(BaseModel):
    status: str
    app_name: str
    version: str
    database_connected: bool
    gemini_configured: bool
    timestamp: datetime
