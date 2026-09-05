from enum import Enum
import re
from typing import Optional, List, Dict, Any

class DoctorQueryIntent(str, Enum):
    CLINICAL_ADVICE = "CLINICAL_ADVICE"
    SOURCE_PROVENANCE = "SOURCE_PROVENANCE"
    CONFLICTS = "CONFLICTS"
    MEDICATIONS = "MEDICATIONS"
    PATIENT_INFORMATION = "PATIENT_INFORMATION"
    LAB_ALL = "LAB_ALL"
    LAB_ABNORMAL = "LAB_ABNORMAL"
    LAB_SPECIFIC = "LAB_SPECIFIC"
    COMPARISON = "COMPARISON"
    SUMMARY = "SUMMARY"
    GENERAL = "GENERAL"

def classify_doctor_intent(query: str, available_test_names: Optional[List[str]] = None) -> DoctorQueryIntent:
    """
    Determines query intent with deterministic priority.
    Distinguishes information-retrieval requests from clinical advice requests.
    """
    q = query.strip().lower()

    # 1. Check for CLINICAL_ADVICE (Requests for medical action, diagnosis, prescription, or dosage change)
    advice_patterns = [
        r"\bdiagnose\s+(this|the|a)?\s*patient\b",
        r"\bdiagnose\s+him\b",
        r"\bdiagnose\s+her\b",
        r"\bdiagnose\s+them\b",
        r"\bdiagnose\s+the\s+patient\b",
        r"\bcan\s+you\s+diagnose\b",
        r"\bgive\s+(a|me\s+a)?\s*diagnosis\b",
        r"\bwhat\s+disease\s+does\b",
        r"\bwhat\s+treatment\s+(should|do\s+they\s+need)\b",
        r"\brecommend\s+treatment\b",
        r"\bhow\s+(should\s+i|to)\s+treat\b",
        r"\bshould\s+i\s+(prescribe|give|increase|decrease|change|administer)\b",
        r"\bwhat\s+(medication|drug)\s+should\s+i\s+prescribe\b",
        r"\bwhat\s+dosage\s+should\s+(i|we)\b",
        r"\bshould\s+(they|the\s+patient)\s+take\b",
        r"\bhow\s+to\s+cure\b",
        r"\bwhat\s+is\s+the\s+prognosis\b",
        r"\bprescribe\s+(chemo|antibiotic|treatment|dosage)\b"
    ]

    is_advice = False
    for pat in advice_patterns:
        if re.search(pat, q):
            is_advice = True
            break

    if is_advice:
        if not (any(k in q for k in ["recorded", "documented", "listed in the report", "already prescribed"]) and not any(k in q for k in ["should i", "tell me what treatment they need", "diagnose this patient"])):
            return DoctorQueryIntent.CLINICAL_ADVICE

    # 2. Check for CONFLICTS
    conflict_triggers = [
        "conflict", "conflicts", "conflicting", "inconsisten",
        "contradict", "discrepan"
    ]
    if any(t in q for t in conflict_triggers):
        return DoctorQueryIntent.CONFLICTS

    # 3. Check for COMPARISON
    comparison_triggers = [
        "what changed", "between the reports", "between the two reports",
        "between reports", "compare reports", "compare the latest",
        "comparison between", "difference between the reports", "what is different"
    ]
    if any(t in q for t in comparison_triggers):
        return DoctorQueryIntent.COMPARISON

    # 4. Check for LAB_ABNORMAL
    abnormal_triggers = [
        "abnormal findings", "abnormal laboratory", "abnormal results", "abnormal labs",
        "out of range", "out-of-range", "high or low", "high and low", "high / low",
        "outside range", "outside reference range", "elevated results", "elevated findings"
    ]
    if any(t in q for t in abnormal_triggers) or (("abnormal" in q or "out-of-range" in q or "out of range" in q) and not (q.startswith("what is the source") or q.startswith("where was") or q.startswith("which page"))):
        return DoctorQueryIntent.LAB_ABNORMAL

    # 5. Check for LAB_ALL (Request for all findings / complete panel)
    all_lab_triggers = [
        "all laboratory", "all lab", "every laboratory", "every lab",
        "complete laboratory", "complete lab", "all 17", "all findings",
        "every finding", "all tests", "full panel", "complete panel",
        "all results", "every result", "list every laboratory", "list every lab"
    ]
    if any(t in q for t in all_lab_triggers):
        return DoctorQueryIntent.LAB_ALL

    # 6. Check for SOURCE_PROVENANCE
    # Dedicated queries asking specifically for the source document, page, or evidence of a specific item
    source_query_patterns = [
        r"\bwhat\s+is\s+the\s+source\b",
        r"\bgive\s+(the\s+)?source\s+(document|page|evidence|location)\b",
        r"\b(which|what)\s+page\s+(contains|is|has|mentions)\b",
        r"\bwhere\s+(was|is|did|does)\s+.*\s+(found|appear|state|document|come\s+from|listed)\b",
        r"\b(evidence|provenance)\s+(of|for)\b"
    ]
    for pat in source_query_patterns:
        if re.search(pat, q):
            return DoctorQueryIntent.SOURCE_PROVENANCE

    # 7. Check for PATIENT_INFORMATION vs MEDICATIONS
    clinical_patterns = {
        "blood_type": r"\b(blood\s*type|blood\s*group)\b",
        "allergies": r"\b(allergy|allergies|allergic)\b",
        "symptoms": r"\b(symptom|symptoms|complaint|complaints)\b",
        "conditions": r"\b(condition|conditions|diagnos|diagnoses|medical\s*history)\b",
        "medications": r"\b(medication|medications|meds|drugs|prescriptions|prescribed)\b",
        "age": r"\b(patient'?s?\s+)?age\b",
        "sex": r"\b(sex|gender)\b",
        "demographics": r"\bdemographics?\b"
    }

    matched_categories = [cat for cat, pat in clinical_patterns.items() if re.search(pat, q)]

    # If blood type explicitly requested, it's always PATIENT_INFORMATION
    if "blood_type" in matched_categories:
        return DoctorQueryIntent.PATIENT_INFORMATION

    # If multiple distinct clinical categories (e.g. allergies + conditions, or medications + symptoms)
    if len(matched_categories) >= 2:
        return DoctorQueryIntent.PATIENT_INFORMATION

    # If only medications requested (e.g. "What medications is the patient taking? Give dosage and document/page")
    if matched_categories == ["medications"]:
        return DoctorQueryIntent.MEDICATIONS

    # If single category like symptoms or allergies or conditions without lab words
    if any(cat in matched_categories for cat in ["allergies", "symptoms", "conditions", "demographics", "age", "sex"]) and not any(l in q for l in ["lab", "finding", "test", "result"]):
        return DoctorQueryIntent.PATIENT_INFORMATION

    # 8. Fallback Check for MEDICATIONS
    med_triggers = ["medication", "medications", "meds", "drugs", "prescriptions", "prescribed discharge meds"]
    if any(m in q for m in med_triggers):
        return DoctorQueryIntent.MEDICATIONS

    # 9. Check for SUMMARY
    summary_triggers = ["summarize", "summary", "overview", "clinical summary"]
    if any(t in q for t in summary_triggers):
        return DoctorQueryIntent.SUMMARY

    # 10. Check for LAB_SPECIFIC
    if available_test_names:
        for tname in available_test_names:
            tname_clean = tname.strip().lower()
            if len(tname_clean) >= 3 and tname_clean in q:
                return DoctorQueryIntent.LAB_SPECIFIC

    common_tests = [
        "hemoglobin", "glucose", "wbc", "white blood cell", "platelet",
        "egfr", "creatinine", "ferritin", "hba1c", "vitamin d",
        "cholesterol", "ldl", "hdl", "triglyceride", "alt", "ast",
        "potassium", "sodium", "calcium", "tsh", "bilirubin"
    ]
    if any(t in q for t in common_tests):
        return DoctorQueryIntent.LAB_SPECIFIC

    if any(l in q for l in ["laboratory", "labs", "lab results", "test results"]):
        return DoctorQueryIntent.LAB_ALL

    return DoctorQueryIntent.GENERAL
