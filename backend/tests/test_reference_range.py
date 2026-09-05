import pytest
from app.services.reference_range_eval import evaluate_reference_range

def test_bounded_range_low():
    status, num_val, low, high = evaluate_reference_range("10.2", "12–16 g/dL")
    assert status == "LOW"
    assert num_val == 10.2
    assert low == 12.0
    assert high == 16.0

def test_bounded_range_normal():
    status, num_val, low, high = evaluate_reference_range("14.5", "12.0 - 16.0")
    assert status == "NORMAL"
    assert num_val == 14.5
    assert low == 12.0
    assert high == 16.0

def test_bounded_range_high():
    status, num_val, low, high = evaluate_reference_range("18.4", "12.0 to 16.0")
    assert status == "HIGH"
    assert num_val == 18.4
    assert low == 12.0
    assert high == 16.0

def test_inclusive_boundaries():
    # Exactly at lower boundary
    status, _, low, high = evaluate_reference_range("12.0", "12.0 - 16.0")
    assert status == "NORMAL"
    # Exactly at upper boundary
    status, _, low, high = evaluate_reference_range("16.0", "12.0 - 16.0")
    assert status == "NORMAL"

def test_upper_bound_only():
    # Less than 200 mg/dL
    status, num_val, low, high = evaluate_reference_range("185", "< 200 mg/dL")
    assert status == "NORMAL"
    assert high == 200.0

    status, num_val, low, high = evaluate_reference_range("220", "< 200")
    assert status == "HIGH"

def test_lower_bound_only():
    # eGFR > 60 mL/min
    status, num_val, low, high = evaluate_reference_range("45", "> 60 mL/min")
    assert status == "LOW"
    assert low == 60.0

    status, num_val, low, high = evaluate_reference_range("85", "> 60")
    assert status == "NORMAL"

def test_missing_reference_range():
    # CRITICAL: If no reference range is provided, it must be REFERENCE_RANGE_UNAVAILABLE
    status, num_val, low, high = evaluate_reference_range("10.2", None)
    assert status == "REFERENCE_RANGE_UNAVAILABLE"

    status, num_val, low, high = evaluate_reference_range("10.2", "")
    assert status == "REFERENCE_RANGE_UNAVAILABLE"

    status, num_val, low, high = evaluate_reference_range("10.2", "N/A")
    assert status == "REFERENCE_RANGE_UNAVAILABLE"

    status, num_val, low, high = evaluate_reference_range("10.2", "Not established")
    assert status == "REFERENCE_RANGE_UNAVAILABLE"

def test_qualitative_results():
    status, num_val, low, high = evaluate_reference_range("Negative", "Negative")
    assert status == "NORMAL"

    status, num_val, low, high = evaluate_reference_range("Positive", "Negative")
    assert status == "HIGH"
