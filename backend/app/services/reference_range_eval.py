import re
from typing import Tuple, Optional

def parse_float_safe(val_str: Optional[str]) -> Optional[float]:
    """Extracts first valid float from a string, stripping commas and extra characters."""
    if not val_str:
        return None
    # Match standard integer or decimal numbers
    m = re.search(r"[-+]?\d*\.?\d+", val_str.replace(",", "").strip())
    if m:
        try:
            return float(m.group(0))
        except ValueError:
            return None
    return None

def evaluate_reference_range(
    result_val_str: str,
    ref_range_str: Optional[str]
) -> Tuple[str, Optional[float], Optional[float], Optional[float]]:
    """
    Deterministically evaluates LOW / NORMAL / HIGH strictly against the source-provided reference range.
    NEVER assumes, substitutes, or looks up external clinical reference ranges.

    Returns:
        (range_status, numeric_result, ref_low, ref_high)
        range_status is strictly one of:
          - 'LOW'
          - 'NORMAL'
          - 'HIGH'
          - 'REFERENCE_RANGE_UNAVAILABLE'
    """
    num_val = parse_float_safe(result_val_str)

    # If reference range is missing, empty, or explicit 'N/A'/'none'
    if not ref_range_str or not ref_range_str.strip():
        return "REFERENCE_RANGE_UNAVAILABLE", num_val, None, None

    clean_range = ref_range_str.replace("≥", ">=").replace("≤", "<=").strip()
    lower_range = clean_range.lower()

    if lower_range in ["n/a", "none", "not established", "reference range unavailable", "-", "--"]:
        return "REFERENCE_RANGE_UNAVAILABLE", num_val, None, None

    # Handle Qualitative / Non-numeric results
    if num_val is None:
        clean_res = result_val_str.strip().lower()
        # Qualitative checks (e.g., negative / normal / non-reactive)
        if any(term in clean_res for term in ["neg", "non-reactive", "normal"]):
            return "NORMAL", None, None, None
        elif any(term in clean_res for term in ["pos", "reactive", "abnormal"]):
            return "HIGH", None, None, None
        return "REFERENCE_RANGE_UNAVAILABLE", None, None, None

    # Pattern 1: Bounded interval: e.g. "12.0 - 16.0", "12 – 16", "12 to 16", "12.0-16.0"
    # Matches two numbers separated by hyphen, en-dash, em-dash, or 'to'
    bounded_match = re.search(
        r"(\d+(?:\.\d+)?)\s*(?:-|–|—|·|\xb7|to)\s*(\d+(?:\.\d+)?)",
        clean_range,
        re.IGNORECASE
    )
    if bounded_match:
        try:
            val_a = float(bounded_match.group(1))
            val_b = float(bounded_match.group(2))
            low = min(val_a, val_b)
            high = max(val_a, val_b)

            # Inclusive comparison
            if num_val < low:
                return "LOW", num_val, low, high
            elif num_val > high:
                return "HIGH", num_val, low, high
            else:
                return "NORMAL", num_val, low, high
        except ValueError:
            pass

    # Pattern 2: Upper bound threshold: e.g. "< 200", "<= 5.7", "less than 100", "up to 140"
    upper_match = re.search(
        r"(?:<|<=|less than|up to)\s*(\d+(?:\.\d+)?)",
        clean_range,
        re.IGNORECASE
    )
    if upper_match:
        try:
            high = float(upper_match.group(1))
            # Standard medical interpretation: at or below threshold is normal, above is high
            if num_val <= high:
                return "NORMAL", num_val, None, high
            else:
                return "HIGH", num_val, None, high
        except ValueError:
            pass

    # Pattern 3: Lower bound threshold: e.g. "> 60", ">= 90", "greater than 50"
    lower_match = re.search(
        r"(?:>|>=|greater than)\s*(\d+(?:\.\d+)?)",
        clean_range,
        re.IGNORECASE
    )
    if lower_match:
        try:
            low = float(lower_match.group(1))
            # Standard medical interpretation: at or above threshold is normal, below is low
            if num_val >= low:
                return "NORMAL", num_val, low, None
            else:
                return "LOW", num_val, low, None
        except ValueError:
            pass

    # If reference range format is unrecognized or unparseable
    return "REFERENCE_RANGE_UNAVAILABLE", num_val, None, None
