import io
import os
import tempfile
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "degraded"]
    assert data["app_name"] == "CLINOVA"
    assert data["database_connected"] is True

def test_auth_workflow_and_patient_creation():
    # 1. Register new doctor
    reg_payload = {
        "email": "test_doc@clinova.test",
        "password": "Password123!",
        "full_name": "Dr. Test Clinician, MD",
        "role": "doctor"
    }
    reg_res = client.post("/api/v1/auth/register", json=reg_payload)
    # Could be 201 or 400 if already exists
    if reg_res.status_code == 400:
        login_res = client.post("/api/v1/auth/login", json={"email": "test_doc@clinova.test", "password": "Password123!"})
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]
    else:
        assert reg_res.status_code == 201
        token = reg_res.json()["access_token"]

    headers = {"Authorization": f"Bearer {token}"}

    # 2. Test Get Me
    me_res = client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "test_doc@clinova.test"

    # 3. Create Patient with Unique ID
    patient_payload = {
        "full_name": "Marcus Aurelius",
        "age": 42,
        "sex": "male",
        "symptoms": "Occasional mild headache",
        "existing_conditions": "None",
        "allergies": "No known allergies",
        "current_medications": "None",
        "medical_history": "Annual executive physicals clear"
    }
    pat_res = client.post("/api/v1/patients", json=patient_payload, headers=headers)
    assert pat_res.status_code == 201
    pat_data = pat_res.json()
    assert pat_data["full_name"] == "Marcus Aurelius"
    assert pat_data["patient_id"].startswith("CL-")
    assert len(pat_data["patient_id"]) == 9  # e.g. CL-8F29K4

def test_organization_registration():
    org_payload = {
        "organization_name": "MVSR Medical Center",
        "admin_name": "Dr. Administrator",
        "email": "admin@mvsr-medical.org",
        "password": "AdminPassword123!"
    }
    res = client.post("/api/v1/auth/register-org", json=org_payload)
    if res.status_code == 400:
        login_res = client.post("/api/v1/auth/login", json={"email": "admin@mvsr-medical.org", "password": "AdminPassword123!"})
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]
    else:
        assert res.status_code == 201
        token = res.json()["access_token"]

    headers = {"Authorization": f"Bearer {token}"}
    me_res = client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["organization_name"] == "MVSR Medical Center"

def test_unauthorized_access():
    # Attempting to access patients without token
    res = client.get("/api/v1/patients")
    assert res.status_code == 401

def test_demo_seeder_and_longitudinal_continuity():
    # Login as default doctor
    login_res = client.post("/api/v1/auth/login", json={"email": "doctor@clinova.health", "password": "clinova2026"})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Trigger Demo Seed
    seed_res = client.post("/api/v1/demo/seed", headers=headers)
    assert seed_res.status_code == 201
    seed_data = seed_res.json()
    assert seed_data["patient_id"] == "CL-8F29K4"
    patient_db_id = seed_data["id"]

    # 2. Verify Patient Reports
    reps_res = client.get(f"/api/v1/patients/{patient_db_id}/reports", headers=headers)
    assert reps_res.status_code == 200
    reports = reps_res.json()
    assert len(reports) >= 2

    report_a_id = reports[1]["id"]  # Baseline
    report_b_id = reports[0]["id"]  # Follow-up

    # 3. Test Report Comparison Diff
    comp_res = client.get(f"/api/v1/patients/{patient_db_id}/compare?report_a={report_a_id}&report_b={report_b_id}", headers=headers)
    assert comp_res.status_code == 200
    comp_data = comp_res.json()
    assert comp_data["changed_count"] >= 1
    # Check Hemoglobin diff item
    hb_item = next((item for item in comp_data["items"] if "hemoglobin" in item["test_name"].lower()), None)
    assert hb_item is not None
    assert hb_item["status_tag"] == "CHANGED"
    assert hb_item["report_a_value"] == "10.2"
    assert hb_item["report_b_value"] == "11.8"
    assert hb_item["numeric_delta"] == 1.6

    # 4. Test Cross-Record Conflicts Detection
    conflicts_res = client.get(f"/api/v1/patients/{patient_db_id}/conflicts", headers=headers)
    assert conflicts_res.status_code == 200
    conflicts = conflicts_res.json()
    assert len(conflicts) >= 1
    # Verify allergy or medication conflict is flagged
    allergy_conflict = next((c for c in conflicts if c["category"] == "ALLERGY"), None)
    assert allergy_conflict is not None
    assert "penicillin" in allergy_conflict["entity_name"].lower()
    assert allergy_conflict["resolution_status"] == "FLAGGED"

    # 5. Test Human Verification Workflow
    labs_res = client.get(f"/api/v1/patients/{patient_db_id}/labs", headers=headers)
    assert labs_res.status_code == 200
    labs = labs_res.json()
    assert len(labs) > 0
    target_lab = labs[0]

    # Verify action
    verif_res = client.post(f"/api/v1/results/{target_lab['id']}/verify", headers=headers)
    assert verif_res.status_code == 200
    assert verif_res.json()["verification_status"] == "HUMAN_VERIFIED"
    assert verif_res.json()["provenance_type"] == "HUMAN_VERIFIED"

    # Edit action with audit reason
    edit_payload = {
        "new_value": "12.4",
        "new_unit": "g/dL",
        "new_reference_range": "12.0 - 16.0 g/dL",
        "edit_reason": "Corrected typographical entry from lab requisition slip"
    }
    edit_res = client.put(f"/api/v1/results/{target_lab['id']}/edit", json=edit_payload, headers=headers)
    assert edit_res.status_code == 200
    edited_data = edit_res.json()
    assert edited_data["raw_value"] == "12.4"
    assert edited_data["range_status"] == "NORMAL"
    assert edited_data["human_override_notes"] == "Corrected typographical entry from lab requisition slip"
    assert edited_data["original_ai_value"] is not None

    # 6. Test Doctor Intelligence "What Changed?"
    query_payload = {"query": "What changed between the reports?"}
    qa_res = client.post(f"/api/v1/patients/{patient_db_id}/ask", json=query_payload, headers=headers)
    assert qa_res.status_code == 200
    assert len(qa_res.json()["answer"]) > 10

    # 7. Test Responsible AI Guardrail Interception
    safety_payload = {"query": "Does this patient have cancer and should I prescribe chemo?"}
    safe_res = client.post(f"/api/v1/patients/{patient_db_id}/ask", json=safety_payload, headers=headers)
    assert safe_res.status_code == 200
    assert "cannot provide clinical diagnoses" in safe_res.json()["answer"].lower()

    # 8. Test Organization-Wide Global Endpoints
    org_reports_res = client.get("/api/v1/reports", headers=headers)
    assert org_reports_res.status_code == 200
    assert len(org_reports_res.json()) >= 2

    org_pending_res = client.get("/api/v1/results/pending", headers=headers)
    assert org_pending_res.status_code == 200

    org_audit_res = client.get("/api/v1/audit/logs", headers=headers)
    assert org_audit_res.status_code == 200
    assert len(org_audit_res.json()) >= 1


# ─────────────────────────────────────────────────────────────────────────────
# EXTRACTION PIPELINE REGRESSION TESTS
# These tests verify the extraction quality fixes without requiring Gemini.
# ─────────────────────────────────────────────────────────────────────────────

def test_fallback_extractor_multi_row_lab_report():
    """
    Regression: deterministic fallback extractor must extract EVERY lab row from
    a synthetic multi-row lab report and must NOT produce false-positive entries
    from dates, headings, or isolated text fragments like 'Type 2'.
    """
    import fitz
    from app.services.gemini_extractor import _deterministic_fallback_extractor

    # Build a synthetic single-page PDF with 12 lab test rows + known false-positive bait
    SYNTHETIC_LAB_CONTENT = """\
CLINICAL DIAGNOSTICS LABORATORY
Patient Name: John Doe         Date: 2024-03-15
Diagnosis: Type 2 Diabetes Mellitus
Allergies: Penicillin

=== COMPLETE BLOOD COUNT ===
Test Name              Result    Unit     Reference Range
Hemoglobin             12.4      g/dL     12.0 - 16.0
WBC                    7.5       10^3/uL  4.5 - 11.0
RBC                    4.2       10^6/uL  3.8 - 5.2
Hematocrit             38.5      %        36.0 - 46.0
MCV                    91.2      fL       80.0 - 100.0
MCH                    29.5      pg       27.0 - 33.0
MCHC                   32.3      g/dL     31.5 - 35.7
Platelets              210       10^3/uL  150 - 400
Neutrophils            62.1      %        40.0 - 70.0
Lymphocytes            28.4      %        20.0 - 45.0
Monocytes              6.2       %        2.0 - 10.0
Eosinophils            3.3       %        1.0 - 6.0

=== METABOLIC PANEL ===
Glucose (Fasting)      95        mg/dL    70 - 110
Creatinine             0.9       mg/dL    0.6 - 1.2
"""

    # Write to a temporary PDF
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 50), SYNTHETIC_LAB_CONTENT, fontsize=10)
        doc.save(tmp_path)
        doc.close()

        # Parse the document
        from app.services.document_parser import parse_document
        doc_info = parse_document(tmp_path)

        # Run fallback extractor
        result = _deterministic_fallback_extractor(doc_info, "synthetic_lab.pdf")

        lab_names = [lab.test_name.lower() for lab in result.lab_tests]

        # Must extract the key haematology rows
        assert any("hemoglobin" in n for n in lab_names), f"Hemoglobin missing. Got: {lab_names}"
        assert any("wbc" in n for n in lab_names), f"WBC missing. Got: {lab_names}"
        assert any("platelets" in n for n in lab_names), f"Platelets missing. Got: {lab_names}"
        assert any("glucose" in n for n in lab_names), f"Glucose missing. Got: {lab_names}"
        assert any("creatinine" in n for n in lab_names), f"Creatinine missing. Got: {lab_names}"

        # Must have extracted a meaningful number of rows (not just 3)
        assert len(result.lab_tests) >= 8, (
            f"Expected at least 8 lab rows extracted, got {len(result.lab_tests)}. "
            f"Names: {lab_names}"
        )

        # False-positive check: "Type 2" must not appear as a test name
        assert not any("type 2" in n for n in lab_names), (
            f"False positive: 'Type 2' was incorrectly extracted as a lab test. Got: {lab_names}"
        )

        # False-positive check: date strings must not appear as test names
        date_like = [n for n in lab_names if any(c.isdigit() for c in n) and "-" in n]
        assert not date_like, f"Date-like test names extracted: {date_like}"

        # False-positive check: "test name" header must not appear as a lab result
        assert not any(n == "test name" for n in lab_names), "Column header 'Test Name' extracted as lab test"

        # Allergy should be detected as an entity
        allergy_names = [e.entity_name.lower() for e in result.clinical_entities if e.entity_type == "ALLERGY"]
        assert any("penicillin" in a for a in allergy_names), (
            f"Penicillin allergy not extracted. Entities: {result.clinical_entities}"
        )

        # All extracted labs must have non-empty test_name and result_value
        for lab in result.lab_tests:
            assert lab.test_name.strip(), f"Empty test_name found: {lab}"
            assert lab.result_value.strip(), f"Empty result_value found in test '{lab.test_name}'"
            assert lab.source_snippet, f"Empty source_snippet for test '{lab.test_name}'"

    finally:
        os.unlink(tmp_path)


def test_post_extraction_validator_rejects_false_positives():
    """
    Regression: _is_valid_lab_entry must reject known false-positive patterns
    that the old extractor would have passed through.
    """
    from app.services.gemini_extractor import _is_valid_lab_entry
    from app.models.schemas import RawExtractedLab

    def make_lab(name, value):
        return RawExtractedLab(
            test_name=name,
            result_value=value,
            unit=None,
            reference_range_raw=None,
            observations=None,
            page_number=1,
            source_snippet=f"{name} {value}"
        )

    # --- Should be VALID ---
    assert _is_valid_lab_entry(make_lab("Hemoglobin", "12.4")), "Hemoglobin 12.4 should be valid"
    assert _is_valid_lab_entry(make_lab("HbA1c", "6.8")), "HbA1c 6.8 should be valid"
    assert _is_valid_lab_entry(make_lab("TSH", "2.1")), "TSH 2.1 should be valid"
    assert _is_valid_lab_entry(make_lab("HIV Antibody", "Negative")), "HIV Negative should be valid"
    assert _is_valid_lab_entry(make_lab("eGFR", ">60")), "eGFR >60 should be valid"
    assert _is_valid_lab_entry(make_lab("Glucose (Fasting)", "95")), "Glucose (Fasting) 95 should be valid"

    # --- Should be INVALID ---
    # Date as test name
    assert not _is_valid_lab_entry(make_lab("2024-03-15", "10.2")), "Date should not be valid test name"
    # Empty test name
    assert not _is_valid_lab_entry(make_lab("", "10.2")), "Empty test name should be invalid"
    # Empty result value
    assert not _is_valid_lab_entry(make_lab("Hemoglobin", "")), "Empty result value should be invalid"
    # Known header word as test name
    assert not _is_valid_lab_entry(make_lab("test name", "Result")), "Header word should be invalid"
    assert not _is_valid_lab_entry(make_lab("reference range", "12.0-16.0")), "Header word should be invalid"
    # Result value is just a word with no numeric or qualitative meaning
    assert not _is_valid_lab_entry(make_lab("Hemoglobin", "Fasting")), "Non-measurement result should be invalid"
    assert not _is_valid_lab_entry(make_lab("Type 2", "diabetes")), "Type 2 with non-measurement value should be invalid"


def test_document_parser_produces_structured_content():
    """
    Regression: document_parser must produce both 'text' and 'table_text' fields per page,
    and full_text must contain both STRUCTURED TABLE CONTENT and PLAIN TEXT CONTENT sections.
    """
    import fitz
    from app.services.document_parser import parse_document

    CONTENT = "Hemoglobin    12.4    g/dL    12.0 - 16.0\nWBC    7.5    10^3/uL    4.5 - 11.0\n"

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 50), CONTENT, fontsize=11)
        doc.save(tmp_path)
        doc.close()

        result = parse_document(tmp_path)

        assert result["page_count"] == 1
        assert "pages" in result
        assert len(result["pages"]) == 1

        page_data = result["pages"][0]
        assert "text" in page_data, "page must have 'text' field"
        assert "table_text" in page_data, "page must have 'table_text' field"
        assert page_data["page_number"] == 1

        full_text = result["full_text"]
        assert "PLAIN TEXT CONTENT" in full_text, "full_text must contain PLAIN TEXT CONTENT section"
        # Structured section is present when table_text is non-empty
        if page_data["table_text"].strip():
            assert "STRUCTURED TABLE CONTENT" in full_text, "full_text must contain STRUCTURED TABLE CONTENT section"

    finally:
        os.unlink(tmp_path)


def test_end_to_end_upload_and_category_separation():
    """
    Requirement 13 & 16:
    Performs an actual end-to-end upload of the synthetic clinical laboratory PDF
    via POST /api/v1/patients/{patient_id}/reports, then inspects and asserts:
    1. HTTP 201 Created and processing_status == EXTRACTED
    2. Exactly actual laboratory findings are present in /labs (all 11 tests)
    3. Metformin 500 mg is NEVER in /labs (it is in /entities as MEDICATION)
    4. Type 2 Diabetes Mellitus is NEVER in /labs (it is in /entities as CONDITION)
    5. Unit and reference range columns are strictly aligned (no shifting)
    6. 'mg/dL', 'g/dL', etc. are NEVER stored as reference_range
    7. Date strings are NOT treated as laboratory test names
    8. Deterministic reference-range evaluation assigns correct status (e.g. HIGH, LOW, NORMAL)
    """
    import fitz

    # 1. Register & authenticate a doctor user
    unique_email = f"dr.e2e_{tempfile.gettempprefix()}_{os.getpid()}@clinova.health"
    reg_res = client.post("/api/v1/auth/register-org", json={
        "email": unique_email,
        "password": "SecurePassword123!",
        "admin_name": "Dr. EndToEnd Tester",
        "organization_name": "Metropolitan Health System"
    })
    assert reg_res.status_code == 201
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Create patient
    pat_res = client.post("/api/v1/patients", json={
        "full_name": "James Wilson",
        "age": 49,
        "sex": "male",
        "symptoms": "Persistent fatigue",
        "existing_conditions": "None documented",
        "allergies": "None documented",
        "current_medications": "None documented"
    }, headers=headers)
    assert pat_res.status_code == 201
    patient_id = pat_res.json()["id"]

    # 3. Prepare or generate the Northstar Diagnostics synthetic medical PDF
    pdf_path = "backend/uploads/195f0fd1-0d5e-494c-92e8-169262525fb9.pdf"
    if not os.path.exists(pdf_path):
        # Generate on the fly if file is not in uploads
        doc = fitz.open()
        page = doc.new_page()
        content = """\
NORTHSTAR DIAGNOSTICS
Clinical Laboratory Report • SYNTHETIC / DEMONSTRATION RECORD
Patient Name: James Wilson
Patient ID: CL-2L26RJ
Age / Sex: 49 / Male
Report Date: 05 Sep 2026
Specimen: Blood / Serum
Ordering Service: Internal Medicine

Clinical Information
Existing Conditions: Type 2 Diabetes Mellitus; Essential Hypertension
Allergies: No known drug allergies (NKDA)
Current Medications: Metformin 500 mg once daily; Lisinopril 10 mg once daily
Chief Complaint: Persistent mild fatigue and occasional shortness of breath after exertion

Laboratory Results
Test | Result | Unit | Reference Range | Status
Hemoglobin | 11.8 | g/dL | 13.5-17.5 | LOW
WBC Count | 7.4 | 10^3/uL | 4.0-11.0 | NORMAL
Platelet Count | 245 | 10^3/uL | 150-400 | NORMAL
Fasting Glucose | 128 | mg/dL | 70-99 | HIGH
HbA1c | 7.1 | % | 4.0-5.6 | HIGH
Creatinine | 1.12 | mg/dL | 0.70-1.30 | NORMAL
eGFR | 64 | mL/min/1.73m2 | >=60 | NORMAL
ALT | 32 | U/L | 7-56 | NORMAL
LDL Cholesterol | 142 | mg/dL | 0-99 | HIGH
HDL Cholesterol | 46 | mg/dL | >=40 | NORMAL
Triglycerides | 178 | mg/dL | 0-149 | HIGH

Laboratory Observations
Hemoglobin is below the reference range stated by this laboratory. Fasting glucose, HbA1c, LDL cholesterol, and triglycerides
are above their respective source-provided reference ranges. Other listed results fall within the ranges printed above.
"""
        page.insert_text((50, 50), content, fontsize=10)
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            pdf_path = tmp.name
        doc.save(pdf_path)
        doc.close()

    # 4. End-to-end Upload Report via API
    with open(pdf_path, "rb") as f:
        upload_res = client.post(
            f"/api/v1/patients/{patient_id}/reports",
            files={"file": ("northstar_lab_report.pdf", f, "application/pdf")},
            headers=headers
        )

    assert upload_res.status_code == 201, f"Upload failed: {upload_res.text}"
    report_data = upload_res.json()
    assert report_data["processing_status"] == "EXTRACTED"

    # 5. Verify Extracted Laboratory Findings via API
    labs_res = client.get(f"/api/v1/patients/{patient_id}/labs", headers=headers)
    assert labs_res.status_code == 200
    labs = labs_res.json()

    lab_names = [l["test_name"].lower() for l in labs]

    # Critical Assertion: False-positive medications and diagnoses MUST NEVER appear in labs
    assert not any("metformin" in n for n in lab_names), (
        f"Critical Failure: 'Metformin' was incorrectly placed in laboratory findings: {lab_names}"
    )
    assert not any("type 2" in n or n == "type" for n in lab_names), (
        f"Critical Failure: 'Type 2' was incorrectly placed in laboratory findings: {lab_names}"
    )
    assert not any("diabetes" in n for n in lab_names), (
        f"Critical Failure: 'Diabetes' was placed in laboratory findings: {lab_names}"
    )

    # Critical Assertion: Date strings MUST NOT be treated as lab test names
    date_like = [n for n in lab_names if any(c.isdigit() for c in n) and ("-" in n or "/" in n or "2026" in n)]
    assert not date_like, f"Date treated as lab test name: {date_like}"

    # Critical Assertion: Expected lab test rows are all present
    expected_tests = [
        "hemoglobin", "wbc count", "platelet count", "fasting glucose",
        "hba1c", "creatinine", "egfr", "alt", "ldl cholesterol",
        "hdl cholesterol", "triglycerides"
    ]
    for exp in expected_tests:
        assert any(exp in n for n in lab_names), f"Expected lab test '{exp}' missing from: {lab_names}"

    assert len(labs) == len(expected_tests), (
        f"Expected exactly {len(expected_tests)} labs, got {len(labs)}. Names: {lab_names}"
    )

    # 6. Verify Column Alignment & Unit vs Reference Range
    trig_lab = next(l for l in labs if "triglycerides" in l["test_name"].lower())
    assert trig_lab["raw_value"] == "178"
    assert trig_lab["unit"] == "mg/dL", f"Expected unit 'mg/dL', got: {trig_lab['unit']}"
    assert trig_lab["raw_reference_range"] in ["0-149", "0–149"], f"Expected ref '0-149', got: {trig_lab['raw_reference_range']}"
    assert trig_lab["range_status"] == "HIGH", f"Expected status 'HIGH', got: {trig_lab['range_status']}"

    hdl_lab = next(l for l in labs if "hdl" in l["test_name"].lower())
    assert hdl_lab["raw_value"] == "46"
    assert hdl_lab["unit"] == "mg/dL", f"Expected unit 'mg/dL', got: {hdl_lab['unit']}"
    assert hdl_lab["raw_reference_range"] in [">=40", "≥40"], f"Expected ref '>=40', got: {hdl_lab['raw_reference_range']}"
    assert hdl_lab["range_status"] == "NORMAL", f"Expected status 'NORMAL', got: {hdl_lab['range_status']}"

    hb_lab = next(l for l in labs if "hemoglobin" in l["test_name"].lower())
    assert hb_lab["raw_value"] == "11.8"
    assert hb_lab["unit"] == "g/dL", f"Expected unit 'g/dL', got: {hb_lab['unit']}"
    assert hb_lab["raw_reference_range"] in ["13.5-17.5", "13.5–17.5"], f"Expected ref '13.5-17.5', got: {hb_lab['raw_reference_range']}"
    assert hb_lab["range_status"] == "LOW", f"Expected status 'LOW', got: {hb_lab['range_status']}"

    # Critical Assertion: Units like mg/dL, g/dL, % must NEVER be in raw_reference_range
    for lab in labs:
        ref_r = (lab.get("raw_reference_range") or "").strip().lower()
        assert ref_r != "mg/dl", f"Unit 'mg/dL' was stored as reference_range in test '{lab['test_name']}'"
        assert ref_r != "g/dl", f"Unit 'g/dL' was stored as reference_range in test '{lab['test_name']}'"
        assert ref_r != "%", f"Unit '%' was stored as reference_range in test '{lab['test_name']}'"

    # 7. Verify Extracted Clinical Entities via API
    entities_res = client.get(f"/api/v1/patients/{patient_id}/entities", headers=headers)
    assert entities_res.status_code == 200
    entities = entities_res.json()

    med_entities = [e for e in entities if e["entity_type"] == "MEDICATION"]
    cond_entities = [e for e in entities if e["entity_type"] == "CONDITION"]
    allergy_entities = [e for e in entities if e["entity_type"] == "ALLERGY"]

    # Verify Metformin is preserved as a medication entity
    assert any("metformin" in m["entity_name"].lower() for m in med_entities), (
        f"Metformin medication missing from entities: {med_entities}"
    )

    # Verify Type 2 Diabetes is preserved as a condition entity
    assert any("diabetes" in c["entity_name"].lower() for c in cond_entities), (
        f"Diabetes condition missing from entities: {cond_entities}"
    )

    # Verify Allergy is preserved
    assert len(allergy_entities) >= 1

    # 8. Verify Patient Summary incorporates documented conditions and abnormal labs
    sum_res = client.get(f"/api/v1/patients/{patient_id}/summary", headers=headers)
    assert sum_res.status_code == 200
    summary_text = sum_res.json()["summary"].lower()
    assert "diabetes" in summary_text or "metformin" in summary_text
    assert sum_res.json()["grounded_record_count"] >= len(labs)


def test_doctor_assistant_grounding_abnormal_findings():
    """
    Tests that the Doctor Intelligence Assistant answers questions using structured laboratory
    findings already extracted for the selected patient.
    Specifically tests:
      1. Inspects structured findings and selects ONLY findings with deterministic range_status HIGH or LOW.
      2. Returns Test name, Measured value, Unit, Source reference range, and Source page.
      3. Never includes normal findings.
      4. Grounded with exact citations.
      5. Explicitly returns 'No out-of-range findings were identified in the verified structured records.' when none exist.
    """
    reg_res = client.post("/api/v1/auth/register", json={
        "email": "qa_doc@clinova.test",
        "password": "Password123!",
        "full_name": "Dr. Grounding QA, MD",
        "role": "doctor"
    })
    if reg_res.status_code == 400:
        login_res = client.post("/api/v1/auth/login", json={"email": "qa_doc@clinova.test", "password": "Password123!"})
        token = login_res.json()["access_token"]
    else:
        token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Seed the rich demo patient
    seed_res = client.post("/api/v1/demo/seed", headers=headers)
    assert seed_res.status_code == 201
    patient_db_id = seed_res.json()["patient_id"]

    # 2. Query the exact clinician prompt
    clinician_query = "What are the abnormal findings in the latest medical report? Give the test name, value, reference range, and source page for each."
    res = client.post(f"/api/v1/patients/{patient_db_id}/ask", json={"query": clinician_query}, headers=headers)
    assert res.status_code == 200

    data = res.json()
    answer = data["answer"]
    citations = data["citations"]

    # Assert that required fields are present in the response
    assert "Test Name:" in answer
    assert "Measured Value:" in answer
    assert "Unit:" in answer
    assert "Source Reference Range:" in answer
    assert "Source Page:" in answer

    # Assert that the abnormal findings in Report 2 are returned
    # Report 2 (Follow-up) abnormal labs:
    # Hemoglobin: 11.8 g/dL (LOW), ref: 12.0 - 16.0 g/dL, page 1
    # Fasting Glucose: 128 mg/dL (HIGH), ref: < 100 mg/dL, page 1
    # HbA1c: 7.1 % (HIGH), ref: < 5.7 %, page 1
    assert "Hemoglobin" in answer
    assert "11.8" in answer
    assert "LOW" in answer
    assert "12.0 - 16.0 g/dL" in answer

    assert "Fasting Glucose" in answer
    assert "128" in answer
    assert "HIGH" in answer
    assert "< 100 mg/dL" in answer

    assert "HbA1c" in answer
    assert "7.1" in answer
    assert "%" in answer
    assert "< 5.7 %" in answer

    # CRITICAL: Normal findings must NOT be included as abnormal findings
    # Normal in Report 2: WBC (6.9), Platelets (210), eGFR (64), Serum Ferritin (22)
    assert "White Blood Cell" not in answer
    assert "Platelets" not in answer
    assert "Serum Ferritin" not in answer

    # Assert citations are provided and strictly match the abnormal findings
    assert len(citations) == 3
    for cit in citations:
        assert cit["source_type"] == "report"
        assert "Followup_Metabolic_Panel" in cit["source_title"]
        assert cit["page_number"] == 1
        assert cit["snippet"] is not None

    # 3. Test patient with NO abnormal findings
    # Create patient with only normal lab results
    new_patient_payload = {
        "full_name": "Healthy Baseline Patient",
        "age": 35,
        "sex": "male",
        "symptoms": "Routine checkup",
        "existing_conditions": "None",
        "allergies": "NKDA",
        "current_medications": "None"
    }
    p_res = client.post("/api/v1/patients", json=new_patient_payload, headers=headers)
    assert p_res.status_code == 201
    healthy_id = p_res.json()["id"]

    # Upload a normal report or add normal lab via database
    from app.core.database import SessionLocal
    from app.models.db_models import MedicalReport, ExtractedLabResult
    db = SessionLocal()
    try:
        norm_rep = MedicalReport(
            patient_id=healthy_id,
            file_name="normal_report.pdf",
            original_file_name="Normal_Panel.pdf",
            file_type="application/pdf",
            file_size_bytes=1024,
            file_hash="normal_hash_12345",
            storage_path="uploads/normal_report.pdf",
            report_title="Normal Lab Panel",
            processing_status="EXTRACTED",
            uploaded_by_user_id=p_res.json()["created_by_user_id"]
        )
        db.add(norm_rep)
        db.commit()
        db.refresh(norm_rep)

        db.add(ExtractedLabResult(
            report_id=norm_rep.id,
            patient_id=healthy_id,
            test_name="Hemoglobin",
            raw_value="14.5",
            numeric_value=14.5,
            unit="g/dL",
            raw_reference_range="13.5 - 17.5 g/dL",
            range_status="NORMAL",
            page_number=1,
            source_snippet="Hemoglobin: 14.5 g/dL (Ref: 13.5 - 17.5 g/dL)"
        ))
        db.add(ExtractedLabResult(
            report_id=norm_rep.id,
            patient_id=healthy_id,
            test_name="Fasting Glucose",
            raw_value="88",
            numeric_value=88.0,
            unit="mg/dL",
            raw_reference_range="70 - 99 mg/dL",
            range_status="NORMAL",
            page_number=1,
            source_snippet="Fasting Glucose: 88 mg/dL (Ref: 70 - 99 mg/dL)"
        ))
        db.commit()
    finally:
        db.close()

    # Query healthy patient for abnormal findings
    healthy_query_res = client.post(f"/api/v1/patients/{healthy_id}/ask", json={"query": clinician_query}, headers=headers)
    assert healthy_query_res.status_code == 200
    healthy_data = healthy_query_res.json()
    assert healthy_data["answer"] == "No out-of-range findings were identified in the verified structured records."
    assert len(healthy_data["citations"]) == 0



# =====================================================================
# DOCTOR INTELLIGENCE GROUNDING & RETRIEVAL REGRESSION TESTS (10 TESTS)
# =====================================================================

def _get_auth_headers(email="doc_regression@clinova.test", password="Password123!"):
    reg_payload = {
        "email": email,
        "password": password,
        "full_name": f"Dr. {email.split('@')[0]}",
        "role": "doctor"
    }
    reg_res = client.post("/api/v1/auth/register", json=reg_payload)
    if reg_res.status_code == 400:
        login_res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]
    else:
        assert reg_res.status_code == 201
        token = reg_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_doctor_intelligence_lab_all_returns_all_findings():
    """
    Test 1: A patient has 17 structured laboratory findings.
    A request for all findings must return ALL 17 findings without arbitrary truncation to 5.
    """
    from app.core.database import SessionLocal
    from app.models.db_models import MedicalReport, ExtractedLabResult

    headers = _get_auth_headers("doc_lab_all@clinova.test")
    p_res = client.post("/api/v1/patients", json={
        "full_name": "Seventeen Labs Patient",
        "age": 48,
        "sex": "female",
        "symptoms": "Fatigue",
        "existing_conditions": "None",
        "allergies": "NKDA",
        "current_medications": "None"
    }, headers=headers)
    assert p_res.status_code == 201
    patient_id = p_res.json()["id"]
    user_id = p_res.json()["created_by_user_id"]

    lab_17_names = [
        "Hemoglobin", "WBC Count", "Platelet Count", "Fasting Blood Glucose",
        "HbA1c", "Serum Creatinine", "Blood Urea Nitrogen", "Estimated GFR",
        "Serum Sodium", "Serum Potassium", "Serum Chloride", "Total Calcium",
        "Total Bilirubin", "Alkaline Phosphatase", "AST (SGOT)", "ALT (SGPT)",
        "Serum Albumin"
    ]
    assert len(lab_17_names) == 17

    db = SessionLocal()
    try:
        report = MedicalReport(
            patient_id=patient_id,
            file_name="complete_panel_17.pdf",
            original_file_name="Complete_Panel_17.pdf",
            file_type="application/pdf",
            file_size_bytes=2048,
            file_hash="hash_17_labs_panel",
            storage_path="uploads/complete_panel_17.pdf",
            report_title="Comprehensive 17-Test Panel",
            processing_status="EXTRACTED",
            uploaded_by_user_id=user_id
        )
        db.add(report)
        db.commit()
        db.refresh(report)

        for i, tname in enumerate(lab_17_names, start=1):
            db.add(ExtractedLabResult(
                report_id=report.id,
                patient_id=patient_id,
                test_name=tname,
                raw_value=f"{10 + i}",
                numeric_value=float(10 + i),
                unit="mg/dL",
                raw_reference_range="10 - 30 mg/dL",
                range_status="NORMAL",
                page_number=1,
                source_snippet=f"{tname}: {10 + i} mg/dL (Ref: 10 - 30 mg/dL)",
                verification_status="AI_EXTRACTED"
            ))
        db.commit()
    finally:
        db.close()

    # Query for all findings
    query_res = client.post(
        f"/api/v1/patients/{patient_id}/ask",
        json={"query": "List all laboratory findings for this patient"},
        headers=headers
    )
    assert query_res.status_code == 200
    data = query_res.json()
    answer = data["answer"]

    # Every single one of the 17 tests must be in the answer
    for tname in lab_17_names:
        assert tname in answer, f"Test '{tname}' missing from answer. Got: {answer}"

    # Verify that all 17 citations are returned
    assert len(data["citations"]) == 17, f"Expected 17 citations, got {len(data['citations'])}"


def test_doctor_intelligence_four_abnormal_findings_returns_all_four():
    """
    Test 2: A patient has 17 findings with exactly 4 abnormal (HIGH/LOW) and 13 normal.
    A request for abnormal findings must return ALL 4 abnormal findings and NONE of the normal ones.
    """
    from app.core.database import SessionLocal
    from app.models.db_models import MedicalReport, ExtractedLabResult

    headers = _get_auth_headers("doc_abnormal4@clinova.test")
    p_res = client.post("/api/v1/patients", json={
        "full_name": "Four Abnormals Patient",
        "age": 55,
        "sex": "male",
        "symptoms": "Polydipsia, polyuria",
        "existing_conditions": "Hypertension",
        "allergies": "NKDA",
        "current_medications": "Lisinopril 10mg"
    }, headers=headers)
    assert p_res.status_code == 201
    patient_id = p_res.json()["id"]
    user_id = p_res.json()["created_by_user_id"]

    db = SessionLocal()
    try:
        report = MedicalReport(
            patient_id=patient_id,
            file_name="metabolic_17_panel.pdf",
            original_file_name="Metabolic_17_Panel.pdf",
            file_type="application/pdf",
            file_size_bytes=2048,
            file_hash="hash_metabolic_17",
            storage_path="uploads/metabolic_17.pdf",
            report_title="Metabolic Panel with 4 Abnormals",
            processing_status="EXTRACTED",
            uploaded_by_user_id=user_id
        )
        db.add(report)
        db.commit()
        db.refresh(report)

        # 4 abnormal tests
        abnormal_specs = [
            ("Fasting Blood Glucose", "148", 148.0, "mg/dL", "70 - 99 mg/dL", "HIGH"),
            ("HbA1c", "8.4", 8.4, "%", "< 5.7 %", "HIGH"),
            ("Serum Potassium", "3.1", 3.1, "mmol/L", "3.5 - 5.0 mmol/L", "LOW"),
            ("Serum Albumin", "2.9", 2.9, "g/dL", "3.5 - 5.5 g/dL", "LOW")
        ]
        for tname, val, num, unit, ref, status in abnormal_specs:
            db.add(ExtractedLabResult(
                report_id=report.id,
                patient_id=patient_id,
                test_name=tname,
                raw_value=val,
                numeric_value=num,
                unit=unit,
                raw_reference_range=ref,
                range_status=status,
                page_number=1,
                source_snippet=f"{tname}: {val} {unit} (Ref: {ref})",
                verification_status="AI_EXTRACTED"
            ))

        # 13 normal tests
        normal_names = [
            "Hemoglobin", "WBC Count", "Platelet Count", "Serum Creatinine",
            "Blood Urea Nitrogen", "Estimated GFR", "Serum Sodium", "Serum Chloride",
            "Total Calcium", "Total Bilirubin", "Alkaline Phosphatase", "AST (SGOT)", "ALT (SGPT)"
        ]
        for tname in normal_names:
            db.add(ExtractedLabResult(
                report_id=report.id,
                patient_id=patient_id,
                test_name=tname,
                raw_value="NormalVal",
                numeric_value=20.0,
                unit="units",
                raw_reference_range="10 - 30 units",
                range_status="NORMAL",
                page_number=1,
                source_snippet=f"{tname}: NormalVal (Ref: 10 - 30 units)",
                verification_status="AI_EXTRACTED"
            ))
        db.commit()
    finally:
        db.close()

    # Query for abnormal findings
    query_res = client.post(
        f"/api/v1/patients/{patient_id}/ask",
        json={"query": "What are the abnormal findings in the medical report? Give the test name, value, reference range, and source page for each."},
        headers=headers
    )
    assert query_res.status_code == 200
    data = query_res.json()
    answer = data["answer"]

    # All 4 abnormal tests MUST be in the answer
    assert "Fasting Blood Glucose" in answer
    assert "148" in answer
    assert "HIGH" in answer

    assert "HbA1c" in answer
    assert "8.4" in answer
    assert "HIGH" in answer

    assert "Serum Potassium" in answer
    assert "3.1" in answer
    assert "LOW" in answer

    assert "Serum Albumin" in answer
    assert "2.9" in answer
    assert "LOW" in answer

    # Normal tests must NOT be present
    for norm_name in normal_names:
        assert norm_name not in answer, f"Normal test '{norm_name}' was incorrectly included in abnormal findings!"

    # Exactly 4 citations for the 4 abnormal findings
    assert len(data["citations"]) == 4


def test_doctor_intelligence_medication_retrieval_includes_provenance():
    """
    Test 3: A medication query must retrieve all explicitly recorded medications
    across intake and reports with complete provenance (name, dosage, document, page, snippet).
    """
    from app.core.database import SessionLocal
    from app.models.db_models import MedicalReport, ExtractedClinicalEntity

    headers = _get_auth_headers("doc_meds_prov@clinova.test")
    p_res = client.post("/api/v1/patients", json={
        "full_name": "Medication Provenance Patient",
        "age": 61,
        "sex": "male",
        "symptoms": "Routine follow-up",
        "existing_conditions": "Hyperlipidemia, Diabetes",
        "allergies": "NKDA",
        "current_medications": "Metformin 500mg BID, Lisinopril 10mg daily"
    }, headers=headers)
    assert p_res.status_code == 201
    patient_id = p_res.json()["id"]
    user_id = p_res.json()["created_by_user_id"]

    db = SessionLocal()
    try:
        report = MedicalReport(
            patient_id=patient_id,
            file_name="discharge_summary.pdf",
            original_file_name="Discharge_Summary_Cardio.pdf",
            file_type="application/pdf",
            file_size_bytes=1024,
            file_hash="hash_discharge_meds",
            storage_path="uploads/discharge_summary.pdf",
            report_title="Cardiology Discharge Summary",
            processing_status="EXTRACTED",
            uploaded_by_user_id=user_id
        )
        db.add(report)
        db.commit()
        db.refresh(report)

        db.add(ExtractedClinicalEntity(
            report_id=report.id,
            patient_id=patient_id,
            entity_type="MEDICATION",
            entity_name="Atorvastatin",
            details="40mg oral daily at bedtime",
            page_number=2,
            source_snippet="Rx: Atorvastatin 40mg po qhs for secondary prevention",
            verification_status="HUMAN_VERIFIED"
        ))
        db.commit()
    finally:
        db.close()

    query_res = client.post(
        f"/api/v1/patients/{patient_id}/ask",
        json={"query": "What medications is the patient taking? Give medication name, dosage, and source document/page."},
        headers=headers
    )
    assert query_res.status_code == 200
    data = query_res.json()
    answer = data["answer"]

    # Must contain intake medications
    assert "Metformin 500mg BID" in answer
    assert "Lisinopril 10mg daily" in answer
    assert "Intake Form" in answer

    # Must contain report medication with full provenance
    assert "Atorvastatin" in answer
    assert "40mg oral daily at bedtime" in answer
    assert "Discharge_Summary_Cardio.pdf" in answer
    assert "Page 2" in answer
    assert "Rx: Atorvastatin 40mg po qhs" in answer
    assert "HUMAN_VERIFIED" in answer

    # Citations must reflect both intake and report
    assert len(data["citations"]) >= 2


def test_doctor_intelligence_missing_blood_type_reported_not_found():
    """
    Test 4: Multi-field query asking for blood type, allergies, symptoms, conditions, and medications.
    Missing blood type must return 'Not found in the verified records.' while other requested
    fields return their corresponding data. Must NOT return only medications!
    """
    headers = _get_auth_headers("doc_multi_fields@clinova.test")
    p_res = client.post("/api/v1/patients", json={
        "full_name": "Multi Field Query Patient",
        "age": 39,
        "sex": "female",
        "symptoms": "Exertional dyspnea, dry cough",
        "existing_conditions": "Mild persistent asthma, GERD",
        "allergies": "Sulfa drugs, seasonal pollen",
        "current_medications": "Fluticasone/Salmeterol 250/50 mcg, Omeprazole 20mg"
    }, headers=headers)
    assert p_res.status_code == 201
    patient_id = p_res.json()["id"]

    query_res = client.post(
        f"/api/v1/patients/{patient_id}/ask",
        json={"query": "What is the patient's blood type, allergies, symptoms, conditions, and medications?"},
        headers=headers
    )
    assert query_res.status_code == 200
    data = query_res.json()
    answer = data["answer"]

    # Blood type must be explicitly reported as Not found in the verified records
    assert "Blood Type: Not found in the verified records." in answer

    # Allergies must be reported
    assert "Allergies:" in answer
    assert "Sulfa drugs" in answer

    # Symptoms must be reported
    assert "Symptoms:" in answer
    assert "Exertional dyspnea" in answer

    # Conditions must be reported
    assert "Conditions:" in answer
    assert "Mild persistent asthma" in answer

    # Medications must be reported
    assert "Medications:" in answer
    assert "Fluticasone/Salmeterol" in answer


def test_doctor_intelligence_conflict_query_does_not_return_labs():
    """
    Test 5: A conflict-detection query must return actual Inconsistency records
    and NEVER fall back to or return abnormal laboratory findings.
    """
    from app.core.database import SessionLocal
    from app.models.db_models import MedicalReport, ExtractedLabResult, Inconsistency

    headers = _get_auth_headers("doc_conflicts@clinova.test")
    p_res = client.post("/api/v1/patients", json={
        "full_name": "Conflict Query Patient",
        "age": 52,
        "sex": "female",
        "symptoms": "Chest pain",
        "existing_conditions": "Coronary artery disease",
        "allergies": "No known drug allergies (NKDA)",
        "current_medications": "Aspirin 81mg"
    }, headers=headers)
    assert p_res.status_code == 201
    patient_id = p_res.json()["id"]
    user_id = p_res.json()["created_by_user_id"]

    db = SessionLocal()
    try:
        report = MedicalReport(
            patient_id=patient_id,
            file_name="admission_report.pdf",
            original_file_name="Admission_Report.pdf",
            file_type="application/pdf",
            file_size_bytes=1024,
            file_hash="hash_admission_conflict",
            storage_path="uploads/admission_report.pdf",
            report_title="Admission Clinical Report",
            processing_status="EXTRACTED",
            uploaded_by_user_id=user_id
        )
        db.add(report)
        db.commit()
        db.refresh(report)

        # Add abnormal lab to verify it does NOT leak into conflict answer
        db.add(ExtractedLabResult(
            report_id=report.id,
            patient_id=patient_id,
            test_name="Cardiac Troponin I",
            raw_value="0.45",
            numeric_value=0.45,
            unit="ng/mL",
            raw_reference_range="< 0.04 ng/mL",
            range_status="HIGH",
            page_number=1,
            source_snippet="Cardiac Troponin I: 0.45 ng/mL (Ref: < 0.04 ng/mL)",
            verification_status="HUMAN_VERIFIED"
        ))

        # Add genuine Inconsistency
        db.add(Inconsistency(
            patient_id=patient_id,
            category="ALLERGY",
            entity_name="Penicillin",
            source_a={"type": "intake", "text": "Patient intake record states No known drug allergies (NKDA)"},
            source_b={"type": "report", "report_name": "Admission_Report.pdf", "page_number": 1, "text": "Allergy: Penicillin anaphylaxis"},
            conflict_description="Intake form records NKDA, but Admission_Report.pdf documents severe Penicillin anaphylaxis.",
            resolution_status="FLAGGED"
        ))
        db.commit()
    finally:
        db.close()

    query_res = client.post(
        f"/api/v1/patients/{patient_id}/ask",
        json={"query": "What conflicts or discrepancies exist between the patient's records?"},
        headers=headers
    )
    assert query_res.status_code == 200
    data = query_res.json()
    answer = data["answer"]

    # Inconsistency must be returned
    assert "ALLERGY" in answer
    assert "Penicillin" in answer
    assert "severe Penicillin anaphylaxis" in answer
    assert "Admission_Report.pdf" in answer

    # CRITICAL: Laboratory findings must NOT be returned in a conflicts query!
    assert "Cardiac Troponin I" not in answer
    assert "0.45" not in answer

    # Test empty state: if no conflicts flagged
    db = SessionLocal()
    try:
        inc = db.query(Inconsistency).filter(Inconsistency.patient_id == patient_id).first()
        inc.resolution_status = "RESOLVED"
        db.commit()
    finally:
        db.close()

    empty_res = client.post(
        f"/api/v1/patients/{patient_id}/ask",
        json={"query": "What conflicts exist between the patient's records?"},
        headers=headers
    )
    assert empty_res.status_code == 200
    assert empty_res.json()["answer"] == "No conflicts were identified in the verified records."
    assert len(empty_res.json()["citations"]) == 0


def test_doctor_intelligence_source_provenance_returns_metadata():
    """
    Test 6: A source-provenance query must return document, page, snippet, and verification status.
    Must not return an abnormal lab list.
    """
    from app.core.database import SessionLocal
    from app.models.db_models import MedicalReport, ExtractedLabResult

    headers = _get_auth_headers("doc_provenance@clinova.test")
    p_res = client.post("/api/v1/patients", json={
        "full_name": "Source Provenance Patient",
        "age": 44,
        "sex": "female",
        "symptoms": "Fatigue",
        "existing_conditions": "None",
        "allergies": "NKDA",
        "current_medications": "None"
    }, headers=headers)
    assert p_res.status_code == 201
    patient_id = p_res.json()["id"]
    user_id = p_res.json()["created_by_user_id"]

    db = SessionLocal()
    try:
        report = MedicalReport(
            patient_id=patient_id,
            file_name="iron_study.pdf",
            original_file_name="Iron_Deficiency_Study.pdf",
            file_type="application/pdf",
            file_size_bytes=1024,
            file_hash="hash_iron_study",
            storage_path="uploads/iron_study.pdf",
            report_title="Iron and Ferritin Evaluation",
            processing_status="EXTRACTED",
            uploaded_by_user_id=user_id
        )
        db.add(report)
        db.commit()
        db.refresh(report)

        db.add(ExtractedLabResult(
            report_id=report.id,
            patient_id=patient_id,
            test_name="Serum Ferritin",
            raw_value="11.2",
            numeric_value=11.2,
            unit="ng/mL",
            raw_reference_range="30.0 - 400.0 ng/mL",
            range_status="LOW",
            page_number=3,
            source_snippet="Serum Ferritin: 11.2 ng/mL (Ref: 30.0 - 400.0 ng/mL)",
            verification_status="HUMAN_VERIFIED"
        ))
        db.commit()
    finally:
        db.close()

    query_res = client.post(
        f"/api/v1/patients/{patient_id}/ask",
        json={"query": "What is the source document and page for the patient's Serum Ferritin result?"},
        headers=headers
    )
    assert query_res.status_code == 200
    data = query_res.json()
    answer = data["answer"]

    assert "Serum Ferritin" in answer
    assert "Iron_Deficiency_Study.pdf" in answer
    assert "Page 3" in answer
    assert "11.2 ng/mL" in answer
    assert "Serum Ferritin: 11.2 ng/mL (Ref: 30.0 - 400.0 ng/mL)" in answer
    assert "HUMAN_VERIFIED" in answer

    assert len(data["citations"]) >= 1
    assert data["citations"][0]["page_number"] == 3
    assert data["citations"][0]["source_title"] == "Iron_Deficiency_Study.pdf"


def test_doctor_intelligence_patient_isolation():
    """
    Test 7: Doctor Intelligence must enforce strict patient isolation.
    Data from Patient A must never appear in queries for Patient B.
    Clinicians cannot query patients outside their organization/access.
    """
    from app.core.database import SessionLocal
    from app.models.db_models import MedicalReport, ExtractedLabResult

    headers_doc1 = _get_auth_headers("doc_iso1@clinova.test")
    headers_doc2 = _get_auth_headers("doc_iso2@clinova.test")

    # Doctor 1 creates Patient A
    p_res1 = client.post("/api/v1/patients", json={
        "full_name": "Patient Alpha",
        "age": 50,
        "sex": "male",
        "symptoms": "Palpitations",
        "existing_conditions": "None",
        "allergies": "NKDA",
        "current_medications": "None"
    }, headers=headers_doc1)
    assert p_res1.status_code == 201
    patient_a_id = p_res1.json()["id"]
    user1_id = p_res1.json()["created_by_user_id"]

    # Doctor 2 creates Patient B
    p_res2 = client.post("/api/v1/patients", json={
        "full_name": "Patient Beta",
        "age": 30,
        "sex": "female",
        "symptoms": "Abdominal pain",
        "existing_conditions": "None",
        "allergies": "NKDA",
        "current_medications": "None"
    }, headers=headers_doc2)
    assert p_res2.status_code == 201
    patient_b_id = p_res2.json()["id"]
    user2_id = p_res2.json()["created_by_user_id"]

    db = SessionLocal()
    try:
        rep_a = MedicalReport(
            patient_id=patient_a_id,
            file_name="cardiac_a.pdf",
            original_file_name="Cardiac_Alpha.pdf",
            file_type="application/pdf",
            file_size_bytes=1024,
            file_hash="hash_cardiac_alpha",
            storage_path="uploads/cardiac_a.pdf",
            report_title="Cardiac Panel Alpha",
            processing_status="EXTRACTED",
            uploaded_by_user_id=user1_id
        )
        db.add(rep_a)
        db.commit()
        db.refresh(rep_a)

        db.add(ExtractedLabResult(
            report_id=rep_a.id,
            patient_id=patient_a_id,
            test_name="Cardiac Troponin I",
            raw_value="0.88",
            numeric_value=0.88,
            unit="ng/mL",
            raw_reference_range="< 0.04 ng/mL",
            range_status="HIGH",
            page_number=1,
            source_snippet="Cardiac Troponin I: 0.88 ng/mL",
            verification_status="HUMAN_VERIFIED"
        ))

        rep_b = MedicalReport(
            patient_id=patient_b_id,
            file_name="pancreas_b.pdf",
            original_file_name="Pancreas_Beta.pdf",
            file_type="application/pdf",
            file_size_bytes=1024,
            file_hash="hash_pancreas_beta",
            storage_path="uploads/pancreas_b.pdf",
            report_title="Pancreatic Panel Beta",
            processing_status="EXTRACTED",
            uploaded_by_user_id=user2_id
        )
        db.add(rep_b)
        db.commit()
        db.refresh(rep_b)

        db.add(ExtractedLabResult(
            report_id=rep_b.id,
            patient_id=patient_b_id,
            test_name="Serum Lipase",
            raw_value="310",
            numeric_value=310.0,
            unit="U/L",
            raw_reference_range="10 - 60 U/L",
            range_status="HIGH",
            page_number=1,
            source_snippet="Serum Lipase: 310 U/L",
            verification_status="HUMAN_VERIFIED"
        ))
        db.commit()
    finally:
        db.close()

    # Doctor 1 queries Patient A
    res_a = client.post(f"/api/v1/patients/{patient_a_id}/ask", json={"query": "What are the abnormal findings?"}, headers=headers_doc1)
    assert res_a.status_code == 200
    assert "Cardiac Troponin I" in res_a.json()["answer"]
    assert "Serum Lipase" not in res_a.json()["answer"]

    # Doctor 1 attempts to query Patient B -> Must be rejected with 404
    res_cross = client.post(f"/api/v1/patients/{patient_b_id}/ask", json={"query": "What are the abnormal findings?"}, headers=headers_doc1)
    assert res_cross.status_code == 404

    # Doctor 2 queries Patient B
    res_b = client.post(f"/api/v1/patients/{patient_b_id}/ask", json={"query": "What are the abnormal findings?"}, headers=headers_doc2)
    assert res_b.status_code == 200
    assert "Serum Lipase" in res_b.json()["answer"]
    assert "Cardiac Troponin I" not in res_b.json()["answer"]

    # Doctor 2 attempts to query Patient A -> Must be rejected with 404
    res_cross2 = client.post(f"/api/v1/patients/{patient_a_id}/ask", json={"query": "What are the abnormal findings?"}, headers=headers_doc2)
    assert res_cross2.status_code == 404


def test_doctor_intelligence_safety_guard_preserved():
    """
    Test 8: Preserves safety guardrail against clinical diagnosis and prescription prompts,
    while permitting information retrieval.
    """
    headers = _get_auth_headers("doc_safety@clinova.test")
    p_res = client.post("/api/v1/patients", json={
        "full_name": "Safety Guard Patient",
        "age": 57,
        "sex": "male",
        "symptoms": "High blood sugar",
        "existing_conditions": "Diabetes",
        "allergies": "NKDA",
        "current_medications": "Metformin 500mg"
    }, headers=headers)
    assert p_res.status_code == 201
    patient_id = p_res.json()["id"]

    # Diagnostic prompt must be intercepted
    diag_res = client.post(
        f"/api/v1/patients/{patient_id}/ask",
        json={"query": "Can you diagnose this patient and tell me what disease does he have?"},
        headers=headers
    )
    assert diag_res.status_code == 200
    diag_data = diag_res.json()
    assert "Clinova is an information management and review system" in diag_data["answer"]
    assert "cannot provide clinical diagnoses" in diag_data["answer"]
    assert len(diag_data["citations"]) == 0

    # Prescription prompt must be intercepted
    presc_res = client.post(
        f"/api/v1/patients/{patient_id}/ask",
        json={"query": "What dosage should I prescribe for his insulin?"},
        headers=headers
    )
    assert presc_res.status_code == 200
    presc_data = presc_res.json()
    assert "cannot provide clinical diagnoses, prescribe medications" in presc_data["answer"]
    assert len(presc_data["citations"]) == 0

    # Information retrieval prompt must NOT be intercepted
    info_res = client.post(
        f"/api/v1/patients/{patient_id}/ask",
        json={"query": "What medications are documented in the patient intake?"},
        headers=headers
    )
    assert info_res.status_code == 200
    assert "Metformin 500mg" in info_res.json()["answer"]


def test_doctor_intelligence_query_state_does_not_leak():
    """
    Test 9: Sequential queries across different intents on the same patient do not leak state.
    """
    from app.core.database import SessionLocal
    from app.models.db_models import MedicalReport, ExtractedLabResult

    headers = _get_auth_headers("doc_no_leak@clinova.test")
    p_res = client.post("/api/v1/patients", json={
        "full_name": "No Leak Patient",
        "age": 45,
        "sex": "female",
        "symptoms": "Fatigue",
        "existing_conditions": "None",
        "allergies": "Aspirin",
        "current_medications": "Levothyroxine 50mcg"
    }, headers=headers)
    assert p_res.status_code == 201
    patient_id = p_res.json()["id"]
    user_id = p_res.json()["created_by_user_id"]

    db = SessionLocal()
    try:
        report = MedicalReport(
            patient_id=patient_id,
            file_name="tsh_report.pdf",
            original_file_name="TSH_Report.pdf",
            file_type="application/pdf",
            file_size_bytes=1024,
            file_hash="hash_tsh_report",
            storage_path="uploads/tsh_report.pdf",
            report_title="Thyroid Evaluation",
            processing_status="EXTRACTED",
            uploaded_by_user_id=user_id
        )
        db.add(report)
        db.commit()
        db.refresh(report)

        db.add(ExtractedLabResult(
            report_id=report.id,
            patient_id=patient_id,
            test_name="Serum TSH",
            raw_value="7.8",
            numeric_value=7.8,
            unit="uIU/mL",
            raw_reference_range="0.4 - 4.0 uIU/mL",
            range_status="HIGH",
            page_number=1,
            source_snippet="Serum TSH: 7.8 uIU/mL (Ref: 0.4 - 4.0 uIU/mL)",
            verification_status="HUMAN_VERIFIED"
        ))
        db.commit()
    finally:
        db.close()

    # Query 1: Abnormal findings
    q1 = client.post(f"/api/v1/patients/{patient_id}/ask", json={"query": "What are the abnormal findings?"}, headers=headers)
    assert q1.status_code == 200
    assert "Serum TSH" in q1.json()["answer"]

    # Query 2: Conflicts -> Must NOT return abnormal labs
    q2 = client.post(f"/api/v1/patients/{patient_id}/ask", json={"query": "What conflicts or discrepancies exist between the records?"}, headers=headers)
    assert q2.status_code == 200
    assert "No conflicts were identified in the verified records." in q2.json()["answer"]
    assert "Serum TSH" not in q2.json()["answer"]

    # Query 3: Medications -> Must return Levothyroxine, NOT Serum TSH and NOT conflicts
    q3 = client.post(f"/api/v1/patients/{patient_id}/ask", json={"query": "What medications are documented?"}, headers=headers)
    assert q3.status_code == 200
    assert "Levothyroxine 50mcg" in q3.json()["answer"]
    assert "Serum TSH" not in q3.json()["answer"]

    # Query 4: Blood type -> Must return Not found in the verified records, NOT medications
    q4 = client.post(f"/api/v1/patients/{patient_id}/ask", json={"query": "What is the patient's blood type?"}, headers=headers)
    assert q4.status_code == 200
    assert "• Blood Type: Not found in the verified records." in q4.json()["answer"]
    assert "Levothyroxine" not in q4.json()["answer"]


def test_doctor_intelligence_missing_source_does_not_hallucinate():
    """
    Test 10: Asking for provenance of an unrecorded test explicitly returns
    'Source location unavailable in the verified records.' without hallucinating.
    """
    headers = _get_auth_headers("doc_no_hallucinate@clinova.test")
    p_res = client.post("/api/v1/patients", json={
        "full_name": "No Hallucination Patient",
        "age": 28,
        "sex": "male",
        "symptoms": "Cough",
        "existing_conditions": "None",
        "allergies": "NKDA",
        "current_medications": "None"
    }, headers=headers)
    assert p_res.status_code == 201
    patient_id = p_res.json()["id"]

    query_res = client.post(
        f"/api/v1/patients/{patient_id}/ask",
        json={"query": "What is the source document and page for their COVID-19 PCR test?"},
        headers=headers
    )
    assert query_res.status_code == 200
    data = query_res.json()
    assert data["answer"] == "Source location unavailable in the verified records."
    assert len(data["citations"]) == 0


def test_doctor_intelligence_eighteen_labs_all_displayed():
    """
    Test 11: A patient has exactly 18 structured laboratory findings.
    A request for all findings must return ALL 18 findings without omission,
    truncation, or pagination.
    """
    from app.core.database import SessionLocal
    from app.models.db_models import MedicalReport, ExtractedLabResult

    headers = _get_auth_headers("doc_18_labs@clinova.test")
    p_res = client.post("/api/v1/patients", json={
        "full_name": "Eighteen Labs Patient",
        "age": 58,
        "sex": "male",
        "symptoms": "Comprehensive executive checkup",
        "existing_conditions": "None",
        "allergies": "NKDA",
        "current_medications": "None"
    }, headers=headers)
    assert p_res.status_code == 201
    patient_id = p_res.json()["id"]
    user_id = p_res.json()["created_by_user_id"]

    lab_18_names = [
        "Hemoglobin", "WBC Count", "Platelet Count", "Fasting Blood Glucose",
        "HbA1c", "Serum Creatinine", "Blood Urea Nitrogen", "Estimated GFR",
        "Serum Sodium", "Serum Potassium", "Serum Chloride", "Total Calcium",
        "Total Bilirubin", "Alkaline Phosphatase", "AST (SGOT)", "ALT (SGPT)",
        "Serum Albumin", "Serum Ferritin"
    ]
    assert len(lab_18_names) == 18

    db = SessionLocal()
    try:
        report = MedicalReport(
            patient_id=patient_id,
            file_name="complete_18_panel.pdf",
            original_file_name="Complete_18_Panel.pdf",
            file_type="application/pdf",
            file_size_bytes=2048,
            file_hash="hash_18_labs_panel",
            storage_path="uploads/complete_18_panel.pdf",
            report_title="Comprehensive 18-Test Panel",
            processing_status="EXTRACTED",
            uploaded_by_user_id=user_id
        )
        db.add(report)
        db.commit()
        db.refresh(report)

        for i, tname in enumerate(lab_18_names, start=1):
            db.add(ExtractedLabResult(
                report_id=report.id,
                patient_id=patient_id,
                test_name=tname,
                raw_value=f"{20 + i}",
                numeric_value=float(20 + i),
                unit="mg/dL",
                raw_reference_range="10 - 50 mg/dL",
                range_status="NORMAL",
                page_number=1,
                source_snippet=f"{tname}: {20 + i} mg/dL (Ref: 10 - 50 mg/dL)",
                verification_status="AI_EXTRACTED"
            ))
        db.commit()
    finally:
        db.close()

    # Query for all findings
    query_res = client.post(
        f"/api/v1/patients/{patient_id}/ask",
        json={"query": "List all laboratory findings for this patient"},
        headers=headers
    )
    assert query_res.status_code == 200
    data = query_res.json()
    answer = data["answer"]

    # Every single one of the 18 tests must be in the answer
    for tname in lab_18_names:
        assert tname in answer, f"Test '{tname}' missing from answer. Got: {answer}"

    # Verify that all 18 citations are returned
    assert len(data["citations"]) == 18, f"Expected 18 citations, got {len(data['citations'])}"
