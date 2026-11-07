"""Контракт GET /portal/bench/dashboard."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class BenchCards(BaseModel):
    avg_rate: int | None = None
    avg_time_to_hire_days: int | None = None
    offers: int = 0
    offer_conversion: float = 0.0
    project_starts: int = 0
    cv_sent: int = 0
    rejections: int = 0


class BenchFunnel(BaseModel):
    cv_sent: int = 0
    screening: int = 0
    internal_interview: int = 0
    tech_stage_1: int = 0
    final_stage: int = 0
    offers: int = 0
    project_starts: int = 0


class BenchSpecializationRow(BaseModel):
    specialization: str
    avg_rate: int | None = None
    cv_sent: int = 0
    offers: int = 0
    project_starts: int = 0
    rejections: int = 0
    offer_conversion: float = 0.0
    project_conversion: float = 0.0


class BenchMonthlyPoint(BaseModel):
    label: str
    year: int
    month: str
    month_num: int
    cv_sent: int = 0
    offers: int = 0
    project_starts: int = 0


class BenchConversionBySpec(BaseModel):
    specialization: str
    offer_conversion: float = 0.0
    project_conversion: float = 0.0


class BenchDashboardRead(BaseModel):
    cards: BenchCards
    funnel: BenchFunnel
    specialization_stats: list[BenchSpecializationRow]
    monthly_dynamics: list[BenchMonthlyPoint]
    conversion_by_spec: list[BenchConversionBySpec]
    monthly_summary: dict[str, Any] = Field(default_factory=dict)
    years: list[int] = Field(default_factory=list)
    specializations: list[str] = Field(default_factory=list)
    last_success_at: str | None = None
    is_stale: bool = False
    stale_message: str | None = None
