"""Агрегаты дашборда бенч: карточки, фильтры, годы на оси не сливаются."""

from __future__ import annotations

import pytest
from app.core.exceptions import ValidationError
from app.portal_bench.services._metrics import build_dashboard, filter_catalog, filter_records

_REC_JAN_IOS_2025 = {
    "year": 2025,
    "month": "Январь",
    "month_num": 1,
    "developer": "А iOS",
    "specialization": "iOS",
    "cv_sent": 10,
    "screening": 2,
    "internal_interview": 1,
    "tech_stage_1": 1,
    "final_stage": 1,
    "osup": 0,
    "rejection": 1,
    "offer": 2,
    "project_start": 1,
    "comment": "выход 20.01",
    "rate": 2000.0,
    "start_date": "20.01.2025",
    "request_date": "01.01.2025",
}
_REC_JAN_IOS_2026 = {
    **_REC_JAN_IOS_2025,
    "year": 2026,
    "request_date": "01.01.2026",
    "start_date": "10.01.2026",
    "cv_sent": 5,
    "offer": 1,
    "project_start": 1,
    "rate": 3000.0,
}
_REC_FEB_ANDROID = {
    "year": 2026,
    "month": "Февраль",
    "month_num": 2,
    "developer": "Б Android",
    "specialization": "Android",
    "cv_sent": 8,
    "screening": 0,
    "internal_interview": 0,
    "tech_stage_1": 0,
    "final_stage": 0,
    "osup": 0,
    "rejection": 2,
    "offer": 0,
    "project_start": 0,
    "comment": "",
    "rate": 2500.0,
    "start_date": None,
    "request_date": "01.02.2026",
}
_REC_NEGATIVE_TTH = {
    **_REC_JAN_IOS_2026,
    "developer": "В iOS",
    "start_date": "01.12.2025",
    "request_date": "01.01.2026",
    "cv_sent": 0,
    "offer": 0,
    "project_start": 0,
    "rate": None,
}


def test_filter_by_year_spec_month() -> None:
    all_rows = [_REC_JAN_IOS_2025, _REC_JAN_IOS_2026, _REC_FEB_ANDROID]
    only_2026 = filter_records(all_rows, year=2026)
    assert [r["developer"] for r in only_2026] == ["А iOS", "Б Android"]
    only_ios = filter_records(all_rows, specialization="iOS")
    assert all(r["specialization"] == "iOS" for r in only_ios)
    only_feb = filter_records(all_rows, month=2)
    assert only_feb == [_REC_FEB_ANDROID]


def test_filter_by_multiple_specializations() -> None:
    all_rows = [_REC_JAN_IOS_2025, _REC_JAN_IOS_2026, _REC_FEB_ANDROID]
    both = filter_records(all_rows, specialization=["iOS", "Android"])
    assert {r["specialization"] for r in both} == {"iOS", "Android"}
    assert len(both) == 3
    only_ios = filter_records(all_rows, specialization=["iOS"])
    assert all(r["specialization"] == "iOS" for r in only_ios)
    none = filter_records(all_rows, specialization=["Go"])
    assert none == []
    unfiltered = filter_records(all_rows, specialization=None)
    assert unfiltered == all_rows


def test_filter_rejects_partial_date_range() -> None:
    with pytest.raises(ValidationError, match="обе даты"):
        filter_records([_REC_JAN_IOS_2026], date_from="2026-01-01")


def test_filter_by_date_range_includes_overlapping_month() -> None:
    rows = filter_records(
        [_REC_JAN_IOS_2026, _REC_FEB_ANDROID],
        date_from="2026-01-15",
        date_to="2026-01-31",
    )
    assert rows == [_REC_JAN_IOS_2026]


def test_cards_rate_tth_skip_negative() -> None:
    dash = build_dashboard([_REC_JAN_IOS_2026, _REC_NEGATIVE_TTH])
    assert dash["cards"]["avg_rate"] == 3000
    # TTH: 10.01.2026 - 01.01.2026 = 9 дней; отрицательный отброшен
    assert dash["cards"]["avg_time_to_hire_days"] == 9
    assert dash["cards"]["offers"] == 1
    assert dash["cards"]["project_starts"] == 1
    assert dash["cards"]["offer_conversion"] == 20.0


def test_monthly_dynamics_does_not_merge_years() -> None:
    dash = build_dashboard([_REC_JAN_IOS_2025, _REC_JAN_IOS_2026])
    labels = [p["label"] for p in dash["monthly_dynamics"]]
    assert labels == ["Январь 2025", "Январь 2026"]
    assert dash["monthly_dynamics"][0]["offers"] == 2
    assert dash["monthly_dynamics"][1]["offers"] == 1


def test_filter_catalog_keeps_all_years_and_specs_after_year_slice() -> None:
    all_rows = [_REC_JAN_IOS_2025, _REC_JAN_IOS_2026, _REC_FEB_ANDROID]
    catalog = filter_catalog(all_rows)
    assert catalog["years"] == [2025, 2026]
    assert catalog["specializations"] == ["Android", "iOS"]
    sliced = build_dashboard(filter_records(all_rows, year=2026))
    assert sliced["years"] == [2026]
    assert sliced["specializations"] == ["Android", "iOS"]
    assert sliced["monthly_summary"]["years"] == [2026]


def test_conversion_includes_spec_with_offers_and_zero_cv() -> None:
    da_no_cv = {
        **_REC_FEB_ANDROID,
        "developer": "Г DA",
        "specialization": "DA",
        "cv_sent": 0,
        "offer": 1,
        "project_start": 2,
        "rejection": 0,
    }
    dash = build_dashboard([_REC_JAN_IOS_2026, da_no_cv])
    assert dash["cards"]["offers"] == 2
    assert dash["cards"]["project_starts"] == 3
    by_spec = {row["specialization"]: row for row in dash["conversion_by_spec"]}
    assert "DA" in by_spec
    assert by_spec["DA"]["offer_conversion"] > 0
    assert by_spec["DA"]["project_conversion"] > 0


def test_empty_records_give_empty_cards() -> None:
    dash = build_dashboard([])
    assert dash["cards"]["avg_rate"] is None
    assert dash["cards"]["avg_time_to_hire_days"] is None
    assert dash["cards"]["offers"] == 0
    assert dash["monthly_summary"]["years"] == []
