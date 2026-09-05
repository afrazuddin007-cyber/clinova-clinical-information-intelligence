import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models.db_models import User, Patient, MedicalReport

client = TestClient(app)

def get_auth_token():
    email = "security_test_dr@clinova.test"
    password = "SecurityPassword123!"
    reg_res = client.post("/api/v1/auth/register", json={
        "email": email,
        "password": password,
        "full_name": "Dr. Security Auditor",
        "role": "doctor"
    })
    login_res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    return login_res.json()["access_token"], email

def test_security_headers_present():
    """Verify that HTTP security headers are attached by middleware."""
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    assert res.headers.get("X-Content-Type-Options") == "nosniff"
    assert res.headers.get("X-Frame-Options") == "DENY"
    assert "1; mode=block" in res.headers.get("X-XSS-Protection", "")
    assert res.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "max-age=" in res.headers.get("Strict-Transport-Security", "")

def test_report_comparison_cross_patient_isolation():
    """Verify cross-patient report comparison is rejected with 400."""
    token, email = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        assert user is not None

        p1 = Patient(patient_id="CL-SEC01", full_name="Patient SecOne", age=30, sex="female", created_by_user_id=user.id)
        p2 = Patient(patient_id="CL-SEC02", full_name="Patient SecTwo", age=35, sex="male", created_by_user_id=user.id)
        db.add_all([p1, p2])
        db.commit()
        db.refresh(p1)
        db.refresh(p2)

        r1 = MedicalReport(
            patient_id=p1.id,
            file_name="p1_rep.pdf",
            original_file_name="p1_rep.pdf",
            file_type="application/pdf",
            file_size_bytes=100,
            file_hash="hash_p1_rep_sec",
            storage_path="uploads/p1_rep.pdf",
            processing_status="EXTRACTED",
            uploaded_by_user_id=user.id
        )
        r2 = MedicalReport(
            patient_id=p2.id,
            file_name="p2_rep.pdf",
            original_file_name="p2_rep.pdf",
            file_type="application/pdf",
            file_size_bytes=100,
            file_hash="hash_p2_rep_sec",
            storage_path="uploads/p2_rep.pdf",
            processing_status="EXTRACTED",
            uploaded_by_user_id=user.id
        )
        db.add_all([r1, r2])
        db.commit()
        db.refresh(r1)
        db.refresh(r2)

        comp_res = client.get(
            f"/api/v1/patients/{p1.id}/compare?report_a={r1.id}&report_b={r2.id}",
            headers=headers
        )
        assert comp_res.status_code == 400
        assert "belong to the specified patient" in comp_res.json()["detail"]
    finally:
        db.close()

def test_file_path_traversal_prevention():
    """Verify that path traversal in file download is strictly prevented."""
    token, email = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        assert user is not None

        p = Patient(patient_id="CL-TRAV99", full_name="Traversal Test", age=40, sex="male", created_by_user_id=user.id)
        db.add(p)
        db.commit()
        db.refresh(p)

        r = MedicalReport(
            patient_id=p.id,
            file_name="evil.pdf",
            original_file_name="evil.pdf",
            file_type="application/pdf",
            file_size_bytes=100,
            file_hash="hash_evil_99",
            storage_path="../../etc/passwd",
            processing_status="EXTRACTED",
            uploaded_by_user_id=user.id
        )
        db.add(r)
        db.commit()
        db.refresh(r)

        res = client.get(f"/api/v1/reports/{r.id}/file", headers=headers)
        assert res.status_code == 400
        assert "Invalid file path" in res.json()["detail"]
    finally:
        db.close()
