# CLINOVA — AI-Powered Clinical Information Intelligence

> **"One patient. One record. Every insight traceable."**  
> *Healthcare information-management platform for clinicians and healthcare organizations.*

Clinova transforms fragmented patient information and medical reports into a structured, understandable, traceable, and reviewable patient record. **Clinova is NOT a diagnostic or treatment system.** Every insight is grounded, reference-range aware, conflict-flagged, and traceable to original source evidence.

---

## 🌟 Core Pillars & Feature Implementation

### 1. Unique Patient ID (`CL-XXXXXX`)
- Every patient is automatically assigned a distinct alphanumeric Patient ID (e.g. `CL-8F29K4`).
- Unambiguous character set (eliminates confusing glyphs like `0/O`, `1/I`).
- Connects all longitudinal reports, clinical intake, lab results, and audit trails.

### 2. Clinical Intake & Provenance Differentiation
- Structured capture of Symptoms, Existing Conditions, Allergies, Medications, and Medical History.
- Clearly distinguishes manually keyed information with `[USER_PROVIDED]` tags from `[AI_EXTRACTED]` findings.

### 3. AI Extraction & Multimodal Document Processing
- Supports PDF, PNG, and JPEG formats (enforced max 10MB).
- Strict MIME magic-bytes validation and SHA-256 integrity hashing.
- Powered by **Google Gemini 2.5 Flash** with strict Pydantic JSON schemas (`response_schema=ReportExtractionStructuredOutput`, temperature `0.0`).
- Extracts **ONLY** information explicitly present in the source report.

### 4. Deterministic Reference-Range Awareness
- **Zero-Assumption Rule**: The AI never calculates or assumes reference ranges. The backend performs this mathematically.
- Evaluates `LOW`, `NORMAL`, and `HIGH` **strictly** against the reference range printed in that exact source report.
- If no reference range is documented in the source report, status is strictly set to `"REFERENCE_RANGE_UNAVAILABLE"`.
- Handles bounded intervals (`12.0 - 16.0`), upper bounds (`< 200`), lower bounds (`> 60`), and qualitative values.

### 5. Evidence-First Design & Traceability
- Every lab value retains its source document, page number, verbatim source quote, and extraction timestamp.
- Clinicians can click any data point to open the **Source Evidence & Provenance Inspector**, displaying the exact quotation and the original PDF page.

### 6. Report Comparison (Diff Engine)
- Deterministic diffing between any two historical reports (Baseline vs Target).
- Categorizes all findings into `NEW`, `CHANGED`, `UNCHANGED`, and `INCOMPARABLE` (e.g. unit disparity).
- Computes exact numeric deltas and percentage changes (e.g. `Hemoglobin 10.2 -> 11.8 g/dL (+15.7%)`) without drawing medical conclusions.

### 7. Cross-Record Conflict & Inconsistency Detection
- Automatically scans for discrepancies between Intake vs Reports, and across historical reports.
- Flags contradictory allergies (e.g. Intake states *"No known allergies"*, but report documents *"Penicillin allergy"*).
- Flags medication dosage disparities (e.g. *"Metformin 500mg daily"* vs *"Metformin 1000mg BID"*).
- **Safety Mandate**: The system flags conflicts with side-by-side evidence; it **never** decides medical truth.

### 8. Human Verification & Audit Trail
- Verification workflow states: `AI_EXTRACTED` -> `PENDING_VERIFICATION` -> `HUMAN_VERIFIED` or `REJECTED`.
- Editing an extraction preserves the original AI value, re-evaluates the reference range deterministically, records the clinical rationale, and logs the user ID and timestamp.

### 9. "What Changed?" Doctor Intelligence Assistant
- Doctor-facing conversational assistant grounded purely in the patient's structured records.
- Direct quick prompts for common clinical reviews.
- Generates factual answers with inline citation chips linking to report name and page number.
- **Responsible AI Guardrail**: If asked for diagnoses or prescriptions, Clinova intercepts the query and explicitly reminds the clinician of its scope as an information organization tool.

---

## 🚀 Quick Start (Local Development)

### Prerequisites
- Python 3.11+
- Node.js v18+ & npm
- (Optional) `GEMINI_API_KEY` for live Gemini 2.5 Flash calls (Clinova includes a high-fidelity deterministic parser for offline evaluator testing).

### 1. Clone & Configure Environment
```bash
git clone https://github.com/your-repo/clinova.git
cd clinova

# Copy environment settings
cp .env.example .env
```

### 2. Backend Setup
```bash
# Activate virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt
```

### 3. Seed Synthetic Demo Patient (1-Click)
Run the standalone CLI seeder to instantly populate demo clinician credentials and Eleanor Vance (`CL-8F29K4`):
```bash
python seed_demo.py
```

### 4. Run the Backend Server
```bash
uvicorn backend.app.main:app --host 127.0.0.1 --port 8080 --reload
```
- Interactive Swagger API Documentation: [http://127.0.0.1:8080/docs](http://127.0.0.1:8080/docs)
- Health Check Endpoint: [http://127.0.0.1:8080/api/v1/health](http://127.0.0.1:8080/api/v1/health)

### 5. Run the Frontend (Vite)
In a separate terminal:
```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser!

> **Default Evaluation Clinician**:
> - Email: `doctor@clinova.health`
> - Password: `clinova2026`
> - *Or click the "1-Click Doctor Login" button directly on the login screen.*

---

## 🧪 Automated Testing Suite

Clinova includes comprehensive automated test coverage for reference-range mathematics, report diffing, conflict scanning, and authentication:

```bash
# Run backend test suite
pytest backend/tests/ -v
```

### Test Coverage Highlights:
- `test_reference_range.py`: Validates bounded intervals (`12-16`), inclusive thresholds, upper/lower bounds (`< 200`, `> 60`), missing ranges (`REFERENCE_RANGE_UNAVAILABLE`), and qualitative items.
- `test_api_endpoints.py`: Tests user registration, JWT login, patient creation with `CL-` IDs, report comparisons, conflict detection, verification workflows, and responsible AI safety interceptors.

---

## 🐳 Containerization & Google Cloud Run Deployment

Clinova is packaged as a **single unified container** (multi-stage Dockerfile) where FastAPI serves both the REST API and the compiled React SPA on port `8080`.

### 1. Build and Run via Docker Locally
```bash
docker build -t clinova .
docker run -p 8080:8080 -e GEMINI_API_KEY="your_api_key_here" clinova
```
Visit [http://localhost:8080](http://localhost:8080).

### 2. Deploy to Google Cloud Run (1 Command)
```bash
# Authenticate and set project
gcloud auth login
gcloud config set project YOUR_GCP_PROJECT_ID

# Deploy directly from source
gcloud run deploy clinova \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8080 \
  --memory 1Gi \
  --cpu 1 \
  --set-env-vars GEMINI_API_KEY="your_gemini_api_key",JWT_SECRET="production_jwt_secret"
```

---

## 🔒 Security & Responsible AI Audit

- **No Secrets in Frontend**: `GEMINI_API_KEY` and database credentials are strictly isolated to backend runtime environment variables.
- **Strict Input Sanitization**: Uploaded files are validated against magic byte signatures (`%PDF-`, PNG, JPEG), hashed with SHA-256, and stored with UUID identifiers to prevent path traversal.
- **Tenant Isolation**: All clinical records are scoped to authorized clinicians; unauthorized access returns HTTP 401/403.
- **Responsible AI Disclaimer**: Persistent clinical disclaimers remind users that Clinova is an information management system, not a licensed practitioner.
