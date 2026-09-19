"""مدل‌های ورودی/خروجی HTTP — لایهٔ نازک روی قرارداد دامنه."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CostRangeOut(BaseModel):
    min_toman: int
    max_toman: int


class ScenarioOut(BaseModel):
    kind: str
    label_fa: str
    tier: str
    description: str
    cost: CostRangeOut
    duration_days: CostRangeOut


class SpaceOut(BaseModel):
    space: str
    label_fa: str
    area_m2: float
    condition: str
    confidence: float
    requested_works: list[str]


class WBSItemOut(BaseModel):
    code: str
    title: str
    phase: str
    phase_label_fa: str
    space: str
    quantity: float
    unit: str
    material: str | None = None
    depends_on: list[str] = Field(default_factory=list)


class ProjectOut(BaseModel):
    """خروجی کامل یک پروژه — معادل PipelineResult برای مصرف UI."""

    project_id: str
    title: str
    total_area_m2: float
    style: str
    budget_toman: int | None
    spaces: list[SpaceOut]
    scenarios: list[ScenarioOut]
    selected: str
    wbs_items: list[WBSItemOut]
    assumptions: list[str]
    missing_price_codes: list[str]
    brief_url: str


class ErrorOut(BaseModel):
    """خطای قابل‌نمایش به کاربر — همیشه فارسی و قابل‌فهم."""

    detail: str
