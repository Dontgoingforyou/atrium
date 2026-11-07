"""Фильтры и агрегаты дашборда бенч."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any, TypedDict

from app.core.exceptions import ValidationError
from app.portal_bench.services._ingest import MONTHS, BenchRecord

DashboardPayload = dict[str, Any]


class FilterCatalog(TypedDict):
    years: list[int]
    specializations: list[str]


def _parse_ru_date(value: object) -> date | None:
    if not value:
        return None
    parts = str(value).split(".")
    if len(parts) != 3:
        return None
    try:
        day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
        return date(year, month, day)
    except ValueError:
        return None


def _parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _month_overlaps(record: BenchRecord, date_from: date, date_to: date) -> bool:
    year = int(record.get("year") or 2025)
    month_num = int(record.get("month_num") or 1)
    month_start = date(year, month_num, 1)
    if month_num == 12:
        month_end = date(year, 12, 31)
    else:
        month_end = date(year, month_num + 1, 1)
        month_end = date.fromordinal(month_end.toordinal() - 1)
    return month_start <= date_to and month_end >= date_from


def require_complete_date_range(date_from: str | None, date_to: str | None) -> None:
    if (date_from is None) ^ (date_to is None):
        raise ValidationError("Укажите обе даты периода: date_from и date_to")


def _allowed_specializations(specialization: str | list[str] | None) -> frozenset[str] | None:
    """Пустой список или None — все специализации; иначе точное вхождение в набор."""
    if specialization is None:
        return None
    if isinstance(specialization, str):
        values = [specialization] if specialization.strip() else []
    else:
        values = [item for item in specialization if item and str(item).strip()]
    if not values:
        return None
    return frozenset(values)


def filter_records(
    records: list[BenchRecord],
    *,
    year: int | None = None,
    specialization: str | list[str] | None = None,
    month: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> list[BenchRecord]:
    require_complete_date_range(date_from, date_to)
    filtered = records
    if year is not None:
        filtered = [r for r in filtered if int(r.get("year") or 2025) == year]
    allowed_specs = _allowed_specializations(specialization)
    if allowed_specs is not None:
        filtered = [r for r in filtered if r.get("specialization") in allowed_specs]
    if month is not None:
        filtered = [r for r in filtered if int(r.get("month_num") or 0) == month]
    start = _parse_iso_date(date_from)
    end = _parse_iso_date(date_to)
    if start and end:
        filtered = [r for r in filtered if _month_overlaps(r, start, end)]
    return filtered


def filter_catalog(records: list[BenchRecord]) -> FilterCatalog:
    """Годы и специализации для фильтров — с полного набора записей, не со среза."""
    years = sorted({int(r.get("year") or 2025) for r in records})
    specializations = sorted({str(r.get("specialization") or "Other") for r in records})
    return {"years": years, "specializations": specializations}


def _parse_rate(value: object) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value) if value == value else None  # NaN check
    try:
        cleaned = str(value).replace("$", "").replace("€", "").replace("₽", "").replace(" ", "").replace(",", ".")
        return float(cleaned)
    except ValueError:
        return None


def _tth_days(record: BenchRecord) -> int | None:
    start = _parse_ru_date(record.get("start_date"))
    request = _parse_ru_date(record.get("request_date"))
    if start is None or request is None:
        return None
    days = (start - request).days
    return days if days >= 0 else None


def build_dashboard(records: list[BenchRecord]) -> DashboardPayload:
    total_cv = sum(int(r.get("cv_sent") or 0) for r in records)
    total_offers = sum(int(r.get("offer") or 0) for r in records)
    total_starts = sum(int(r.get("project_start") or 0) for r in records)
    total_rejections = sum(int(r.get("rejection") or 0) for r in records)
    rates = [rate for r in records if (rate := _parse_rate(r.get("rate"))) is not None]
    tth_values = [days for r in records if (days := _tth_days(r)) is not None]
    offer_conversion = round(total_offers / total_cv * 100, 2) if total_cv else 0.0

    spec_stats: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "cv_sent": 0,
            "offers": 0,
            "project_starts": 0,
            "rejections": 0,
            "screening": 0,
            "internal_interview": 0,
            "tech_stage_1": 0,
            "final_stage": 0,
            "rates": [],
        }
    )
    for record in records:
        spec = str(record.get("specialization") or "Other")
        bucket = spec_stats[spec]
        bucket["cv_sent"] += int(record.get("cv_sent") or 0)
        bucket["offers"] += int(record.get("offer") or 0)
        bucket["project_starts"] += int(record.get("project_start") or 0)
        bucket["rejections"] += int(record.get("rejection") or 0)
        bucket["screening"] += int(record.get("screening") or 0)
        bucket["internal_interview"] += int(record.get("internal_interview") or 0)
        bucket["tech_stage_1"] += int(record.get("tech_stage_1") or 0)
        bucket["final_stage"] += int(record.get("final_stage") or 0)
        rate = _parse_rate(record.get("rate"))
        if rate is not None:
            bucket["rates"].append(rate)

    specialization_rows: list[dict[str, Any]] = []
    for spec, bucket in spec_stats.items():
        cv = bucket["cv_sent"]
        # Нет CV, но есть офферы/выходы — бар на графике конверсии не должен быть 0%.
        if cv:
            offer_conv = round(bucket["offers"] / cv * 100, 2)
            project_conv = round(bucket["project_starts"] / cv * 100, 2)
        else:
            offer_conv = 100.0 if bucket["offers"] else 0.0
            project_conv = 100.0 if bucket["project_starts"] else 0.0
        avg_rate = round(sum(bucket["rates"]) / len(bucket["rates"])) if bucket["rates"] else None
        specialization_rows.append(
            {
                "specialization": spec,
                "avg_rate": avg_rate,
                "cv_sent": bucket["cv_sent"],
                "offers": bucket["offers"],
                "project_starts": bucket["project_starts"],
                "rejections": bucket["rejections"],
                "offer_conversion": offer_conv,
                "project_conversion": project_conv,
            }
        )
    specialization_rows.sort(key=lambda row: row["cv_sent"], reverse=True)

    catalog = filter_catalog(records)
    years = catalog["years"]
    show_year = len(years) > 1
    monthly_dynamics: list[dict[str, Any]] = []
    for year in years:
        for month_num, month_name in MONTHS.items():
            rows = [r for r in records if int(r.get("year") or 2025) == year and r.get("month") == month_name]
            if not rows:
                continue
            monthly_dynamics.append(
                {
                    "label": f"{month_name} {year}" if show_year else month_name,
                    "year": year,
                    "month": month_name,
                    "month_num": month_num,
                    "cv_sent": sum(int(r.get("cv_sent") or 0) for r in rows),
                    "offers": sum(int(r.get("offer") or 0) for r in rows),
                    "project_starts": sum(int(r.get("project_start") or 0) for r in rows),
                }
            )

    monthly_rows: list[dict[str, Any]] = []
    totals: dict[int, dict[str, int]] = {y: {"offers": 0, "starts": 0} for y in years}
    for month_num, month_name in MONTHS.items():
        by_year: dict[int, dict[str, int]] = {}
        for year in years:
            offers = sum(
                int(r.get("offer") or 0)
                for r in records
                if int(r.get("year") or 2025) == year and r.get("month") == month_name
            )
            starts = sum(
                int(r.get("project_start") or 0)
                for r in records
                if int(r.get("year") or 2025) == year and r.get("month") == month_name
            )
            by_year[year] = {"offers": offers, "starts": starts}
            totals[year]["offers"] += offers
            totals[year]["starts"] += starts
        monthly_rows.append({"month": month_name, "month_num": month_num, "by_year": by_year})

    specs = catalog["specializations"]
    return {
        "cards": {
            "avg_rate": round(sum(rates) / len(rates)) if rates else None,
            "avg_time_to_hire_days": round(sum(tth_values) / len(tth_values)) if tth_values else None,
            "offers": total_offers,
            "offer_conversion": offer_conversion,
            "project_starts": total_starts,
            "cv_sent": total_cv,
            "rejections": total_rejections,
        },
        "funnel": {
            "cv_sent": total_cv,
            "screening": sum(int(r.get("screening") or 0) for r in records),
            "internal_interview": sum(int(r.get("internal_interview") or 0) for r in records),
            "tech_stage_1": sum(int(r.get("tech_stage_1") or 0) for r in records),
            "final_stage": sum(int(r.get("final_stage") or 0) for r in records),
            "offers": total_offers,
            "project_starts": total_starts,
        },
        "specialization_stats": specialization_rows,
        "monthly_dynamics": monthly_dynamics,
        "conversion_by_spec": [
            {
                "specialization": row["specialization"],
                "offer_conversion": row["offer_conversion"],
                "project_conversion": row["project_conversion"],
            }
            for row in specialization_rows
        ],
        "monthly_summary": {
            "years": years,
            "rows": monthly_rows,
            "totals": totals,
        },
        "years": years,
        "specializations": specs,
    }
