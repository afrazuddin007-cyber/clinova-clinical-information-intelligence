from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from ..models.db_models import MedicalReport, ExtractedLabResult
from ..models.schemas import ReportComparisonResponse, ComparisonItem

def compare_two_reports(
    report_a_id: str,
    report_b_id: str,
    db: Session
) -> ReportComparisonResponse:
    """
    Compares Report A (older baseline) and Report B (newer target).
    Identifies:
      - NEW
      - CHANGED (with numeric delta & % change)
      - UNCHANGED
      - INCOMPARABLE (unit mismatches, qualitative differences)
    Does NOT make clinical or medical conclusions from changes.
    """
    rep_a = db.query(MedicalReport).filter(MedicalReport.id == report_a_id).first()
    rep_b = db.query(MedicalReport).filter(MedicalReport.id == report_b_id).first()

    if not rep_a or not rep_b:
        raise ValueError("One or both reports not found")

    labs_a: List[ExtractedLabResult] = db.query(ExtractedLabResult).filter(
        ExtractedLabResult.report_id == report_a_id,
        ExtractedLabResult.verification_status != "REJECTED"
    ).all()

    labs_b: List[ExtractedLabResult] = db.query(ExtractedLabResult).filter(
        ExtractedLabResult.report_id == report_b_id,
        ExtractedLabResult.verification_status != "REJECTED"
    ).all()

    # Index by normalized test name
    map_a: Dict[str, ExtractedLabResult] = {lab.test_name.strip().lower(): lab for lab in labs_a}
    map_b: Dict[str, ExtractedLabResult] = {lab.test_name.strip().lower(): lab for lab in labs_b}

    all_test_keys = list(dict.fromkeys(list(map_a.keys()) + list(map_b.keys())))
    
    comparison_items: List[ComparisonItem] = []
    new_count = 0
    changed_count = 0
    unchanged_count = 0
    incomparable_count = 0

    for key in all_test_keys:
        item_a = map_a.get(key)
        item_b = map_b.get(key)

        # Case 1: NEW (Present in B, not in A)
        if item_b and not item_a:
            new_count += 1
            comparison_items.append(ComparisonItem(
                test_name=item_b.test_name,
                status_tag="NEW",
                unit=item_b.unit,
                report_a_value=None,
                report_b_value=item_b.raw_value,
                report_a_range=None,
                report_b_range=item_b.raw_reference_range,
                report_a_status=None,
                report_b_status=item_b.range_status,
                numeric_delta=None,
                percentage_delta=None,
                delta_display="Newly added in latest report",
                notes="Test was not present in the baseline report."
            ))

        # Case 2: Only in A (Not reported in B)
        elif item_a and not item_b:
            comparison_items.append(ComparisonItem(
                test_name=item_a.test_name,
                status_tag="INCOMPARABLE",
                unit=item_a.unit,
                report_a_value=item_a.raw_value,
                report_b_value=None,
                report_a_range=item_a.raw_reference_range,
                report_b_range=None,
                report_a_status=item_a.range_status,
                report_b_status=None,
                numeric_delta=None,
                percentage_delta=None,
                delta_display="Not tested in latest report",
                notes="Present in baseline report, omitted in latest report."
            ))
            incomparable_count += 1

        # Case 3: Present in both A and B
        elif item_a and item_b:
            # Check unit compatibility
            unit_a = (item_a.unit or "").strip().lower()
            unit_b = (item_b.unit or "").strip().lower()

            if unit_a and unit_b and unit_a != unit_b:
                incomparable_count += 1
                comparison_items.append(ComparisonItem(
                    test_name=item_b.test_name,
                    status_tag="INCOMPARABLE",
                    unit=f"{item_a.unit} vs {item_b.unit}",
                    report_a_value=item_a.raw_value,
                    report_b_value=item_b.raw_value,
                    report_a_range=item_a.raw_reference_range,
                    report_b_range=item_b.raw_reference_range,
                    report_a_status=item_a.range_status,
                    report_b_status=item_b.range_status,
                    numeric_delta=None,
                    percentage_delta=None,
                    delta_display="Unit Discrepancy",
                    notes=f"Different units ({item_a.unit} vs {item_b.unit}). Quantitative delta cannot be calculated."
                ))
                continue

            # Compare numeric values
            val_a = item_a.numeric_value
            val_b = item_b.numeric_value

            if val_a is not None and val_b is not None:
                delta = round(val_b - val_a, 3)
                pct_delta = round((delta / val_a) * 100, 1) if val_a != 0 else None
                
                sign = "+" if delta > 0 else ""
                pct_str = f" ({sign}{pct_delta}%)" if pct_delta is not None else ""
                unit_str = f" {item_b.unit}" if item_b.unit else ""
                delta_display = f"{sign}{delta}{unit_str}{pct_str}"

                if delta == 0:
                    unchanged_count += 1
                    status_tag = "UNCHANGED"
                    delta_display = "No change (0.0)"
                else:
                    changed_count += 1
                    status_tag = "CHANGED"

                comparison_items.append(ComparisonItem(
                    test_name=item_b.test_name,
                    status_tag=status_tag,
                    unit=item_b.unit,
                    report_a_value=item_a.raw_value,
                    report_b_value=item_b.raw_value,
                    report_a_range=item_a.raw_reference_range,
                    report_b_range=item_b.raw_reference_range,
                    report_a_status=item_a.range_status,
                    report_b_status=item_b.range_status,
                    numeric_delta=delta,
                    percentage_delta=pct_delta,
                    delta_display=delta_display,
                    notes=f"Changed from {item_a.raw_value} to {item_b.raw_value}." if delta != 0 else "Result is identical."
                ))
            else:
                # Qualitative comparison
                if item_a.raw_value.strip().lower() == item_b.raw_value.strip().lower():
                    unchanged_count += 1
                    comparison_items.append(ComparisonItem(
                        test_name=item_b.test_name,
                        status_tag="UNCHANGED",
                        unit=item_b.unit,
                        report_a_value=item_a.raw_value,
                        report_b_value=item_b.raw_value,
                        report_a_range=item_a.raw_reference_range,
                        report_b_range=item_b.raw_reference_range,
                        report_a_status=item_a.range_status,
                        report_b_status=item_b.range_status,
                        numeric_delta=None,
                        percentage_delta=None,
                        delta_display="Identical qualitative result",
                        notes="No change observed."
                    ))
                else:
                    changed_count += 1
                    comparison_items.append(ComparisonItem(
                        test_name=item_b.test_name,
                        status_tag="CHANGED",
                        unit=item_b.unit,
                        report_a_value=item_a.raw_value,
                        report_b_value=item_b.raw_value,
                        report_a_range=item_a.raw_reference_range,
                        report_b_range=item_b.raw_reference_range,
                        report_a_status=item_a.range_status,
                        report_b_status=item_b.range_status,
                        numeric_delta=None,
                        percentage_delta=None,
                        delta_display=f"{item_a.raw_value} → {item_b.raw_value}",
                        notes=f"Qualitative result changed from '{item_a.raw_value}' to '{item_b.raw_value}'."
                    ))

    return ReportComparisonResponse(
        report_a_id=rep_a.id,
        report_b_id=rep_b.id,
        report_a_name=rep_a.original_file_name,
        report_b_name=rep_b.original_file_name,
        report_a_date=rep_a.report_date or rep_a.uploaded_at,
        report_b_date=rep_b.report_date or rep_b.uploaded_at,
        items=comparison_items,
        new_count=new_count,
        changed_count=changed_count,
        unchanged_count=unchanged_count,
        incomparable_count=incomparable_count
    )
