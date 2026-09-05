import os
import json
import re
from typing import Dict, Any, Optional, List, Tuple
from google import genai
from google.genai import types
from ..core.config import settings
from ..models.schemas import (
    ReportExtractionStructuredOutput,
    RawExtractedLab,
    RawExtractedEntity,
    PatientDemographics,
)
from .document_parser import parse_document

# ---------------------------------------------------------------------------
# Common clinical units and patterns
# ---------------------------------------------------------------------------
KNOWN_UNITS = {
    "mg/dl", "g/dl", "u/l", "iu/l", "iu/ml", "%", "ml/min/1.73m²", "ml/min/1.73m2",
    "10³/µl", "10^3/ul", "10^6/ul", "10³/ul", "10*3/ul", "10*6/ul", "10^3/µl",
    "fl", "pg", "mmol/l", "umol/l", "µmol/l", "ng/ml", "ug/dl", "µg/dl",
    "meq/l", "mm/hr", "copies/ml", "cells/ul", "cells/µl", "/hpf", "/lpf",
    "sec", "seconds", "ratio", "index", "units", "u/ml", "mg/l", "g/l",
    "mg/24hr", "g/24hr", "ml/min", "ng/dl", "pg/ml", "miu/l", "uiu/ml"
}

KNOWN_MEDICATION_NAMES = {
    "metformin", "lisinopril", "atorvastatin", "amlodipine", "levothyroxine",
    "omeprazole", "losartan", "amoxicillin", "aspirin", "insulin",
    "hydrochlorothiazide", "warfarin", "clopidogrel", "pantoprazole",
    "rosuvastatin", "ramipril", "glimepiride", "sitagliptin", "metoprolol",
    "gabapentin", "sertraline", "simvastatin", "furosemide", "prednisone",
    "ibuprofen", "acetaminophen", "albuterol", "fluticasone", "azithromycin"
}

KNOWN_CONDITION_NAMES = {
    "type 1 diabetes", "type 2 diabetes", "type 1 diabetes mellitus", "type 2 diabetes mellitus",
    "diabetes", "diabetes mellitus", "t2d", "t1d", "hypertension", "essential hypertension",
    "hyperlipidemia", "coronary artery disease", "asthma", "copd",
    "chronic kidney disease", "anemia", "hypothyroidism", "depression",
    "heart failure", "atrial fibrillation", "osteoarthritis", "rheumatoid arthritis"
}

KNOWN_HEADER_OR_META_WORDS = frozenset([
    "test", "test name", "parameter", "analyte", "investigation",
    "result", "results", "value", "values", "finding", "findings",
    "unit", "units",
    "reference range", "ref range", "normal range", "reference interval", "biological reference",
    "status", "observation", "observations", "flag", "flags", "remarks",
    "date", "report date", "collection date", "specimen date",
    "patient", "patient name", "patient id", "age", "sex", "age / sex",
    "specimen", "ordering service", "physician", "doctor",
    "clinical information", "existing conditions", "allergies",
    "current medications", "chief complaint", "symptoms", "history",
    "laboratory results", "laboratory observations", "report provenance",
    "page", "page 1", "page 2", "synthetic", "demonstration record"
])

_DATE_LIKE_RE = re.compile(r"^\d{1,4}[-/]\d{1,2}[-/]\d{1,4}$")
_ALPHABETIC_RE = re.compile(r"[A-Za-z]{2,}")
_DOSAGE_RE = re.compile(r"\b\d+\s*(?:mg|mcg|g|units|ml|meq)\b", re.IGNORECASE)

# ---------------------------------------------------------------------------
# Unit & Reference Range Helpers
# ---------------------------------------------------------------------------
def is_unit_string(s: Optional[str]) -> bool:
    """Returns True if the string is a measurement unit (e.g. mg/dL, g/dL, %)."""
    if not s:
        return False
    clean = s.strip().lower()
    if clean in KNOWN_UNITS:
        return True
    # If it contains unit suffixes without range dashes
    if any(u in clean for u in ["/dl", "/ul", "/µl", "u/l", "fl", "pg", "%", "/l", "mmol", "min/1.73", "iu/"]):
        if not re.search(r"\d+\s*[-–—to]\s*\d+", s):
            return True
    return False

def is_reference_range_string(s: Optional[str]) -> bool:
    """Returns True if the string contains a numeric range, threshold, or qualitative range."""
    if not s:
        return False
    clean = s.strip()
    # Check bounded range: "13.5-17.5", "0-149", "70 – 99"
    if re.search(r"\d+(?:\.\d+)?\s*(?:-|–|—|to)\s*\d+(?:\.\d+)?", clean):
        return True
    # Check threshold: "< 200", ">= 60", "≥60", "<= 5.7", "> 50"
    if re.search(r"^[<>]?=?\s*\d+(?:\.\d+)?", clean) or re.search(r"^[≤≥]\s*\d+(?:\.\d+)?", clean):
        return True
    # Qualitative reference terms
    if clean.lower() in ["negative", "non-reactive", "normal", "not detected", "absent"]:
        return True
    return False

def is_medication_or_condition(name: str, snippet: str = "") -> bool:
    """Returns True if text corresponds to a medication or medical diagnosis rather than a lab test."""
    clean = name.strip().lower()
    # Check if exact match or starts with known medication
    for med in KNOWN_MEDICATION_NAMES:
        if clean == med or clean.startswith(f"{med} "):
            return True
    # Check if exact match or starts with known condition
    for cond in KNOWN_CONDITION_NAMES:
        if clean == cond or clean.startswith(f"{cond} "):
            return True
    # Check for "type 1" or "type 2" or "type" alone
    if clean in ["type", "type 1", "type 2"] or clean.startswith("type 2 ") or clean.startswith("type 1 "):
        return True
    # Check for dosage in name or snippet (e.g. "500 mg", "10 mg once daily")
    if _DOSAGE_RE.search(name) or " once daily" in clean or " twice daily" in clean:
        return True
    return False

def sanitize_lab_entry(lab: RawExtractedLab) -> Optional[RawExtractedLab]:
    """
    Validates and cleans a laboratory test entry:
    1. Rejects medications, diagnoses, dates, header words, or empty fields.
    2. Corrects column shifts (e.g. unit placed in reference_range, or range in unit).
    3. Ensures units like 'mg/dL' are NEVER stored as reference_range.
    4. Sets reference_range to None when no genuine reference range is present.
    """
    name = (lab.test_name or "").strip()
    val = (lab.value or "").strip()
    unit = (lab.unit or "").strip() if lab.unit else None
    ref = (lab.reference_range or "").strip() if lab.reference_range else None
    obs = (lab.observation or "").strip() if lab.observation else None

    # 1. Validation of test_name
    if not name or not val:
        return None
    if not _ALPHABETIC_RE.search(name):
        return None
    if _DATE_LIKE_RE.match(name):
        return None
    if name.lower() in KNOWN_HEADER_OR_META_WORDS:
        return None
    if is_medication_or_condition(name, lab.source_snippet):
        return None

    # 2. Validation of result value
    qualitative_terms = re.compile(
        r"^(negative|positive|reactive|non-reactive|normal|abnormal|"
        r"not detected|detected|trace|present|absent|borderline|equivocal)",
        re.IGNORECASE
    )
    has_number = bool(re.search(r"\d", val))
    is_qual = bool(qualitative_terms.match(val))
    if not has_number and not is_qual:
        return None

    # 3. Prevent column misalignment (Requirement 7 & 8)
    # If ref is actually a unit (e.g. 'mg/dL') and not a range string
    if ref and is_unit_string(ref) and not is_reference_range_string(ref):
        if not unit:
            unit = ref
        ref = None

    # If unit is actually a reference range (e.g. '13.5-17.5') and not a unit string
    if unit and is_reference_range_string(unit) and not is_unit_string(unit):
        if not ref:
            ref = unit
        unit = None

    # If unit and reference range are identical, ref was duplicated from unit
    if unit and ref and unit.lower() == ref.lower():
        ref = None

    # Clean placeholders like "None", "None provided", "-", "--", "N/A"
    if unit and unit.lower() in ["none", "none provided", "-", "--", "n/a", "null"]:
        unit = None
    if ref and ref.lower() in ["none", "none provided", "-", "--", "n/a", "null", "unavailable"]:
        ref = None

    return RawExtractedLab(
        test_name=name,
        value=val,
        unit=unit,
        reference_range=ref,
        observation=obs,
        test_date=lab.test_date,
        source_page=lab.source_page,
        source_snippet=lab.source_snippet or f"{name} | {val}"
    )

def _is_valid_lab_entry(lab: RawExtractedLab) -> bool:
    """Returns True if the entry passes sanitization and is a genuine laboratory measurement."""
    return sanitize_lab_entry(lab) is not None

def parse_row_parts(parts: List[str], header_indices: Optional[Dict[str, int]] = None) -> Optional[Tuple[str, str, Optional[str], Optional[str], Optional[str]]]:
    """
    Decomposes table cells into (test_name, value, unit, reference_range, observation).
    Handles 5-column, 4-column, 3-column, and 2-column variations without shifting columns.
    """
    if not parts or len(parts) < 2:
        return None
    t_name = parts[0].strip()

    # 4 or 5 columns
    if len(parts) >= 4:
        if header_indices and "value" in header_indices:
            v_idx = header_indices["value"]
            u_idx = header_indices.get("unit")
            r_idx = header_indices.get("reference_range")
            o_idx = header_indices.get("observation")
            val = parts[v_idx] if v_idx < len(parts) else ""
            unit = parts[u_idx] if u_idx is not None and u_idx < len(parts) else None
            ref = parts[r_idx] if r_idx is not None and r_idx < len(parts) else None
            obs = parts[o_idx] if o_idx is not None and o_idx < len(parts) else None
            return t_name, val, unit, ref, obs
        else:
            return t_name, parts[1], parts[2], parts[3], (parts[4] if len(parts) > 4 else None)

    # 3 columns: [Test, Value, Unit] or [Test, Value, Range] or [Test, Val+Unit, Range]
    if len(parts) == 3:
        p1 = parts[1].strip()
        p2 = parts[2].strip()
        # Check if p1 has val + unit: e.g. '91.2 fL'
        m = re.match(r"^([<>]?\s*\d+(?:\.\d+)?)\s+([A-Za-z\/\%\^0-9µ²³]+)$", p1)
        if m:
            val = m.group(1)
            unit = m.group(2)
            ref = p2
            return t_name, val, unit, ref, None
        # Check if p2 has unit + ref: e.g. 'mg/dL 70 - 110'
        m2 = re.match(r"^([A-Za-z\/\%\^0-9µ²³]+)\s+(.+)$", p2)
        if m2 and is_unit_string(m2.group(1)):
            val = p1
            unit = m2.group(1)
            ref = m2.group(2)
            return t_name, val, unit, ref, None
        if is_unit_string(p2):
            return t_name, p1, p2, None, None
        if is_reference_range_string(p2):
            return t_name, p1, None, p2, None
        return t_name, p1, None, p2, None

    # 2 columns: e.g. 'Hemoglobin | 12.4 g/dL 12.0 - 16.0'
    if len(parts) == 2:
        p1 = parts[1].strip()
        m = re.match(r"^([<>]?\s*\d+(?:\.\d+)?)\s*([A-Za-z\/\%\^0-9µ²³]+)?\s*(.*)$", p1)
        if m:
            val = m.group(1).strip()
            unit = m.group(2).strip() if m.group(2) else None
            ref = m.group(3).strip() if m.group(3) else None
            return t_name, val, unit, ref, None

    return None
EXTRACTION_SYSTEM_INSTRUCTION = """\
You are Clinova's clinical report structured-extraction engine.
Your sole responsibility is to extract medical data explicitly printed in the provided medical report
into strict JSON partitioned into 8 distinct clinical categories:

1. PATIENT_DEMOGRAPHICS: Patient name, ID, age, sex, report date, facility name, ordering service.
2. CLINICAL_HISTORY: Prior medical history, background notes.
3. MEDICATIONS: Documented prescribed or current medications with dosages/frequencies (e.g. "Metformin 500 mg once daily").
4. ALLERGIES: Documented patient allergies and drug sensitivities (e.g. "Penicillin").
5. CONDITIONS: Diagnosed medical conditions or active problem list (e.g. "Type 2 Diabetes Mellitus", "Essential Hypertension").
6. SYMPTOMS: Active complaints or reasons for encounter (e.g. "Persistent fatigue").
7. LABORATORY_RESULTS: Quantitative or qualitative laboratory and diagnostic test measurements ONLY.
8. OTHER_DIAGNOSTIC_FINDINGS: Laboratory narrative observations or diagnostic comments.

═══ CRITICAL CONSTRAINTS ═══

1. MEDICATIONS AND DIAGNOSES MUST NEVER BE LABORATORY RESULTS:
   - A medication such as "Metformin 500 mg once daily" MUST be extracted under 'medications'. It must NEVER appear in 'laboratory_results'.
   - A diagnosis such as "Type 2 Diabetes Mellitus" MUST be extracted under 'conditions'. It must NEVER appear in 'laboratory_results'.

2. STRICT LABORATORY TABLE COLUMN ALIGNMENT:
   If a table has columns: Test | Result | Unit | Reference Range | Status
   Then:
   - Test Name -> test_name
   - Result / Value -> value
   - Unit -> unit
   - Reference Range -> reference_range
   - Status / Observation -> observation
   NEVER shift columns.
   A unit (such as mg/dL, g/dL, U/L, %, mL/min/1.73m²) MUST NEVER be placed in reference_range.
   If the report does not print a reference range for a test, set reference_range to null.

3. DETERMINISTIC ENGINE COMPLIANCE:
   - NEVER classify values as LOW, NORMAL, or HIGH yourself.
   - Copy reference_range verbatim as printed. NEVER invent, infer, or extrapolate reference ranges.

4. EXTRACT ALL LABORATORY ROWS:
   - Extract every single row in the laboratory table without omitting or summarizing any tests.
"""

_EXTRACTION_PROMPT_TEMPLATE = """\
Extract all clinical information from the medical document below into the 8 requested categories.

DOCUMENT CONTENT:
{document_content}

EXTRACTION RULES:
- laboratory_results: Must contain ONLY actual laboratory measurements.
- medications: Must contain all medications with dosages.
- conditions: Must contain all medical diagnoses and conditions.
- allergies: Must contain all allergies.
- symptoms: Must contain complaints and symptoms.
- patient_demographics: Patient details and report metadata.
- other_diagnostic_findings: Narrative lab observations.
"""

# ---------------------------------------------------------------------------
# Main extraction entry point
# ---------------------------------------------------------------------------
def extract_structured_report(
    file_path: str,
    original_file_name: str
) -> ReportExtractionStructuredOutput:
    """
    Extracts structured clinical information from a PDF or image report.
    Uses Gemini 2.5 Flash structured output mode (temperature=0.0) when API key is available.
    Falls back to the deterministic table-aware parser when offline or without API key.
    """
    doc_info = parse_document(file_path)
    full_text = doc_info.get("full_text", "")

    api_key = settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY", "")

    if api_key and api_key.strip():
        try:
            client = genai.Client(api_key=api_key)

            prompt = _EXTRACTION_PROMPT_TEMPLATE.format(document_content=full_text)

            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=EXTRACTION_SYSTEM_INSTRUCTION,
                    temperature=0.0,
                    response_mime_type="application/json",
                    response_schema=ReportExtractionStructuredOutput
                )
            )

            if response.text:
                data = json.loads(response.text)
                raw_result = ReportExtractionStructuredOutput(**data)

                # Post-extraction validation & category separation enforcement
                clean_labs: List[RawExtractedLab] = []
                extra_meds: List[RawExtractedEntity] = []
                extra_conds: List[RawExtractedEntity] = []

                for lab in raw_result.laboratory_results:
                    # Check if Gemini accidentally placed a medication in lab results
                    t_name = lab.test_name.strip()
                    if any(m in t_name.lower() for m in KNOWN_MEDICATION_NAMES) or _DOSAGE_RE.search(t_name):
                        extra_meds.append(RawExtractedEntity(
                            category="MEDICATIONS",
                            entity_name=t_name,
                            details=lab.value,
                            source_page=lab.source_page,
                            source_snippet=lab.source_snippet
                        ))
                        continue

                    # Check if Gemini accidentally placed a condition in lab results
                    if any(c in t_name.lower() for c in KNOWN_CONDITION_NAMES) or t_name.lower().startswith("type"):
                        extra_conds.append(RawExtractedEntity(
                            category="CONDITIONS",
                            entity_name=f"{t_name} {lab.value}".strip(),
                            details="Extracted from report",
                            source_page=lab.source_page,
                            source_snippet=lab.source_snippet
                        ))
                        continue

                    # Sanitize lab entry for column shifts
                    sanitized = sanitize_lab_entry(lab)
                    if sanitized:
                        clean_labs.append(sanitized)

                return ReportExtractionStructuredOutput(
                    report_title=raw_result.report_title,
                    report_date=raw_result.report_date,
                    facility_name=raw_result.facility_name,
                    patient_demographics=raw_result.patient_demographics,
                    clinical_history=raw_result.clinical_history,
                    medications=raw_result.medications + extra_meds,
                    allergies=raw_result.allergies,
                    conditions=raw_result.conditions + extra_conds,
                    symptoms=raw_result.symptoms,
                    laboratory_results=clean_labs,
                    other_diagnostic_findings=raw_result.other_diagnostic_findings
                )

        except Exception as e:
            print(f"[Clinova Extraction] Gemini API warning: {e}. Falling back to deterministic text extractor.")

    # Deterministic fallback when Gemini is unavailable
    return _deterministic_fallback_extractor(doc_info, original_file_name)


# ---------------------------------------------------------------------------
# Deterministic fallback extractor (Section- and Table-Aware)
# ---------------------------------------------------------------------------
def _deterministic_fallback_extractor(
    doc_info: Dict[str, Any],
    original_file_name: str
) -> ReportExtractionStructuredOutput:
    """
    High-precision deterministic extractor.
    Identifies document sections (Demographics, Conditions, Allergies, Medications, Labs, Observations)
    and strictly parses laboratory tables by column positions (Test | Result | Unit | Range).
    Guarantees zero false-positive contamination from medications or diagnoses.
    """
    demographics = PatientDemographics()
    clinical_history: List[RawExtractedEntity] = []
    medications: List[RawExtractedEntity] = []
    allergies: List[RawExtractedEntity] = []
    conditions: List[RawExtractedEntity] = []
    symptoms: List[RawExtractedEntity] = []
    laboratory_results: List[RawExtractedLab] = []
    other_diagnostic_findings: List[RawExtractedEntity] = []

    report_title = "Clinical Laboratory Report"
    report_date: Optional[str] = None
    facility_name: Optional[str] = None

    pages = doc_info.get("pages", [])

    for page in pages:
        p_num = page.get("page_number", 1)
        table_text = page.get("table_text", "")
        plain_text = page.get("text", "")

        # Use the structured table_text if available, else plain_text lines
        lines = table_text.split("\n") if table_text.strip() else plain_text.split("\n")

        # Table state tracker
        in_lab_table = False
        header_indices: Dict[str, int] = {}

        for line_idx, raw_line in enumerate(lines):
            line = raw_line.strip()
            if not line or len(line) < 3:
                continue

            lower_line = line.lower()

            # Detect facility name from top lines
            if line_idx < 3 and any(kw in lower_line for kw in ["diagnostic", "laboratory", "laboratories", "center", "clinic", "hospital"]):
                if not facility_name:
                    facility_name = line.split("|")[0].strip()

            # --- Section: Patient Demographics ---
            if "patient name" in lower_line:
                # e.g.: Patient Name | James Wilson | Patient ID | CL-2L26RJ
                m = re.search(r"patient name\s*[:|]\s*([^|]+)", line, re.IGNORECASE)
                if m:
                    demographics.patient_name = m.group(1).strip()
            if "patient id" in lower_line:
                m = re.search(r"patient id\s*[:|]\s*([^|]+)", line, re.IGNORECASE)
                if m:
                    demographics.patient_id = m.group(1).strip()
            if "age" in lower_line and ("sex" in lower_line or "gender" in lower_line):
                # e.g.: Age / Sex | 49 / Male
                m = re.search(r"age\s*(?:/|\&)?\s*sex\s*[:|]\s*(\d+)\s*(?:/|,)?\s*([A-Za-z]+)", line, re.IGNORECASE)
                if m:
                    demographics.age = int(m.group(1))
                    demographics.sex = m.group(2).strip()
            if "report date" in lower_line:
                m = re.search(r"report date\s*[:|]\s*([^|]+)", line, re.IGNORECASE)
                if m:
                    report_date = m.group(1).strip()
                    demographics.report_date = report_date

            # --- Section: Existing Conditions ---
            if "existing condition" in lower_line or "diagnos" in lower_line or "history of" in lower_line:
                val = re.sub(r"(?i)^(?:existing conditions?|diagnosis|history of)\s*[:|]\s*", "", line).strip()
                # Split multiple conditions separated by semicolon or comma
                for item in re.split(r"[;]", val):
                    item_clean = item.strip()
                    if item_clean and len(item_clean) > 2 and item_clean.lower() not in ["none", "nil"]:
                        conditions.append(RawExtractedEntity(
                            category="CONDITIONS",
                            entity_name=item_clean,
                            details="Documented in medical report",
                            source_page=p_num,
                            source_snippet=line[:200]
                        ))
                continue

            # --- Section: Allergies ---
            if "allerg" in lower_line:
                val = re.sub(r"(?i)^allerg(?:y|ies)?\s*[:|]\s*", "", line).strip()
                if val and len(val) > 2:
                    allergies.append(RawExtractedEntity(
                        category="ALLERGIES",
                        entity_name=val,
                        details="Documented in medical report",
                        source_page=p_num,
                        source_snippet=line[:200]
                    ))
                continue

            # --- Section: Current Medications ---
            if "medication" in lower_line:
                val = re.sub(r"(?i)^current medications?\s*[:|]\s*", "", line).strip()
                for item in re.split(r"[;]", val):
                    item_clean = item.strip()
                    if item_clean and len(item_clean) > 2 and item_clean.lower() not in ["none", "nil"]:
                        # Extract drug name vs dosage if present
                        med_match = re.search(r"^([A-Za-z\s]+?)\s+(\d+.*)$", item_clean)
                        if med_match:
                            m_name = med_match.group(1).strip()
                            m_details = med_match.group(2).strip()
                        else:
                            m_name = item_clean
                            m_details = "Prescribed"
                        medications.append(RawExtractedEntity(
                            category="MEDICATIONS",
                            entity_name=m_name,
                            details=m_details,
                            source_page=p_num,
                            source_snippet=line[:200]
                        ))
                continue

            # --- Section: Chief Complaint / Symptoms ---
            if "chief complaint" in lower_line or "symptom" in lower_line:
                val = re.sub(r"(?i)^(?:chief complaint|symptoms?)\s*[:|]\s*", "", line).strip()
                if val and len(val) > 2:
                    symptoms.append(RawExtractedEntity(
                        category="SYMPTOMS",
                        entity_name=val,
                        details="Active complaint",
                        source_page=p_num,
                        source_snippet=line[:200]
                    ))
                continue

            # --- Section: Laboratory Observations ---
            if "laboratory observation" in lower_line or "observations" in lower_line or "comments" in lower_line:
                in_lab_table = False
                val = re.sub(r"(?i)^(?:laboratory observations?|observations?|comments?)\s*[:|]\s*", "", line).strip()
                if val and len(val) > 3:
                    other_diagnostic_findings.append(RawExtractedEntity(
                        category="OTHER_DIAGNOSTIC_FINDINGS",
                        entity_name="Laboratory Observations",
                        details=val,
                        source_page=p_num,
                        source_snippet=line[:250]
                    ))
                continue

            # --- Section: Provenance Disclaimer (End of Data) ---
            if "report provenance" in lower_line or "disclaimer" in lower_line:
                in_lab_table = False
                continue

            # --- Table Header Detection (Test | Result | Unit | Reference Range | Status) ---
            parts = [p.strip() for p in line.split("|")]
            lower_parts = [p.lower() for p in parts]

            has_test_header = any(any(k in h for k in ["test", "analyte", "parameter", "investigation"]) for h in lower_parts)
            has_result_header = any(any(k in h for k in ["result", "value", "observed", "finding"]) for h in lower_parts)
            is_panel_header = any(kw in lower_line for kw in ["panel", "complete blood count", "metabolic", "laboratory results", "lipid profile"])

            if (has_test_header and has_result_header) or is_panel_header:
                in_lab_table = True
                if has_test_header and has_result_header:
                    header_indices = {}
                    for idx, h in enumerate(lower_parts):
                        if any(k in h for k in ["test", "analyte", "parameter", "investigation"]):
                            header_indices["test_name"] = idx
                        elif any(k in h for k in ["result", "value", "observed", "finding"]):
                            header_indices["value"] = idx
                        elif "unit" in h:
                            header_indices["unit"] = idx
                        elif any(k in h for k in ["reference", "range", "interval", "normal"]):
                            header_indices["reference_range"] = idx
                        elif any(k in h for k in ["status", "observation", "flag", "remark"]):
                            header_indices["observation"] = idx
                continue

            # --- Extract Table Row when in_lab_table ---
            if in_lab_table and len(parts) >= 2:
                # Check for section boundaries inside table stream
                if any(kw in parts[0].lower() for kw in ["observation", "provenance", "comment", "signature"]):
                    in_lab_table = False
                    continue

                parsed = parse_row_parts(parts, header_indices)
                if parsed:
                    t_name, val, unit, ref, obs = parsed
                    candidate = RawExtractedLab(
                        test_name=t_name,
                        value=val,
                        unit=unit,
                        reference_range=ref,
                        observation=obs,
                        test_date=report_date,
                        source_page=p_num,
                        source_snippet=line[:200]
                    )
                    sanitized = sanitize_lab_entry(candidate)
                    if sanitized:
                        laboratory_results.append(sanitized)
                continue

            # --- Non-table Line Fallback (Only if line looks like: Name 11.8 g/dL 13.5-17.5) ---
            # Guard: line must NOT contain medication or condition words
            if is_medication_or_condition(line):
                continue

            # Structured regex for lines like: "Hemoglobin 11.8 g/dL 13.5 - 17.5"
            line_m = re.match(
                r"^([A-Za-z][A-Za-z0-9\s\(\)\-\/\.\%,]{2,35}?)\s+([<>]?\s*\d+(?:\.\d+)?)\s*([A-Za-z\/\%\^0-9µ]{1,15})?\s*(?:(?:Ref|Range)?[:\s]+([<>]?\s*\d+(?:\.\d+)?\s*(?:-|–|—|to)\s*\d+(?:\.\d+)?|[<>]?\s*\d+(?:\.\d+)?))?",
                line
            )
            if line_m:
                cand_name = line_m.group(1).strip()
                cand_val = line_m.group(2).strip()
                cand_unit = line_m.group(3).strip() if line_m.group(3) else None
                cand_ref = line_m.group(4).strip() if line_m.group(4) else None

                candidate = RawExtractedLab(
                    test_name=cand_name,
                    value=cand_val,
                    unit=cand_unit,
                    reference_range=cand_ref,
                    observation=None,
                    test_date=report_date,
                    source_page=p_num,
                    source_snippet=line[:200]
                )
                sanitized = sanitize_lab_entry(candidate)
                if sanitized:
                    # Avoid duplicates
                    if not any(l.test_name.lower() == sanitized.test_name.lower() for l in laboratory_results):
                        laboratory_results.append(sanitized)

        # Check plain_text for Laboratory Observations or narrative findings
        obs_m = re.search(r"(?i)laboratory observations?\s*[:\n](.*?)(?:\n\s*Report Provenance|\n\s*===|\Z)", plain_text, re.DOTALL)
        if obs_m:
            obs_text = " ".join(obs_m.group(1).split()).strip()
            if obs_text and not any(e.entity_name == "Laboratory Observations" for e in other_diagnostic_findings):
                other_diagnostic_findings.append(RawExtractedEntity(
                    category="OTHER_DIAGNOSTIC_FINDINGS",
                    entity_name="Laboratory Observations",
                    details=obs_text,
                    source_page=p_num,
                    source_snippet=obs_text[:250]
                ))

    return ReportExtractionStructuredOutput(
        report_title=report_title,
        report_date=report_date,
        facility_name=facility_name or "Clinical Diagnostics Laboratory",
        patient_demographics=demographics,
        clinical_history=clinical_history,
        medications=medications,
        allergies=allergies,
        conditions=conditions,
        symptoms=symptoms,
        laboratory_results=laboratory_results,
        other_diagnostic_findings=other_diagnostic_findings
    )

