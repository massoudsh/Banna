"""قرارداد دادهٔ بنّا — تنها مدل‌های مجاز برای تبادل بین موتورها."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class SpaceType(str, Enum):
    KITCHEN = "kitchen"
    BATHROOM = "bathroom"
    LIVING_ROOM = "living_room"
    BEDROOM = "bedroom"


class WorkPhase(str, Enum):
    """ترتیب استاندارد اجرا — Issue #3 / #7."""

    DEMOLITION = "demolition"
    MEP = "mep"
    STRUCTURE = "structure"
    COVERING = "covering"
    JOINERY = "joinery"
    FINISH = "finish"


PHASE_ORDER: tuple[WorkPhase, ...] = (
    WorkPhase.DEMOLITION,
    WorkPhase.MEP,
    WorkPhase.STRUCTURE,
    WorkPhase.COVERING,
    WorkPhase.JOINERY,
    WorkPhase.FINISH,
)

PHASE_LABELS_FA: dict[WorkPhase, str] = {
    WorkPhase.DEMOLITION: "تخریب",
    WorkPhase.MEP: "تأسیسات",
    WorkPhase.STRUCTURE: "سازه و دیوار",
    WorkPhase.COVERING: "پوشش کف و دیوار",
    WorkPhase.JOINERY: "کابینت و درب",
    WorkPhase.FINISH: "رنگ و دکور",
}


class MaterialTier(str, Enum):
    ECONOMY = "economy"
    STANDARD = "standard"
    PREMIUM = "premium"


class Condition(str, Enum):
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"


class MediaAsset(BaseModel):
    """خروجی media pipeline (Issue #5)."""

    filename: str
    content_type: str
    size_bytes: int = Field(ge=0)
    stored_path: str
    is_video: bool = False
    frame_count: int = 0


class SpaceObservation(BaseModel):
    """یک فضا که از ورودی کاربر استخراج شده (Issue #6)."""

    space: SpaceType
    area_m2: float = Field(gt=0)
    condition: Condition = Condition.FAIR
    confidence: float = Field(ge=0.0, le=1.0, default=0.7)
    requested_works: list[WorkPhase] = Field(default_factory=list)
    notes: str = ""


class ScopeSummary(BaseModel):
    """خروجی scope engine (Issue #6)."""

    spaces: list[SpaceObservation] = Field(default_factory=list)
    style: str = "modern"
    budget_toman: int | None = None
    assumptions: list[str] = Field(default_factory=list)

    @property
    def total_area_m2(self) -> float:
        return round(sum(s.area_m2 for s in self.spaces), 2)


class MaterialOption(BaseModel):
    """یک گزینهٔ متریال با قیمت از دیتاست (Issue #8)."""

    name: str
    tier: MaterialTier
    unit: str
    unit_price_min: int = Field(ge=0)
    unit_price_max: int = Field(ge=0)


class WBSItem(BaseModel):
    """یک آیتم کاری (Issue #7)."""

    code: str
    title: str
    phase: WorkPhase
    space: SpaceType
    quantity: float = Field(gt=0)
    unit: str
    materials: list[MaterialOption] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list)


class WBS(BaseModel):
    items: list[WBSItem] = Field(default_factory=list)

    def ordered(self) -> list[WBSItem]:
        return sorted(self.items, key=lambda i: (PHASE_ORDER.index(i.phase), i.code))


class CostLine(BaseModel):
    wbs_code: str
    title: str
    material_toman: tuple[int, int]
    labor_toman: tuple[int, int]

    @property
    def total_min(self) -> int:
        return self.material_toman[0] + self.labor_toman[0]

    @property
    def total_max(self) -> int:
        return self.material_toman[1] + self.labor_toman[1]


class Estimate(BaseModel):
    """خروجی estimate engine (Issue #9) — همیشه بازه، هرگز عدد قطعی."""

    lines: list[CostLine] = Field(default_factory=list)
    cost_min_toman: int = 0
    cost_max_toman: int = 0
    duration_days_min: int = 0
    duration_days_max: int = 0
    uncertainty_note: str = ""


class ScenarioKind(str, Enum):
    ECONOMY = "economy"
    STANDARD = "standard"
    PREMIUM = "premium"
    RENTAL = "rental"


SCENARIO_LABELS_FA: dict[ScenarioKind, str] = {
    ScenarioKind.ECONOMY: "اقتصادی",
    ScenarioKind.STANDARD: "استاندارد",
    ScenarioKind.PREMIUM: "باکیفیت",
    ScenarioKind.RENTAL: "مناسب اجاره",
}


class Scenario(BaseModel):
    """یک سناریوی کامل خروجی (Issue #10)."""

    kind: ScenarioKind
    label_fa: str
    tier: MaterialTier
    estimate: Estimate
    description: str = ""


class RenovationBrief(BaseModel):
    """خروجی نهایی قابل‌اشتراک با مجری (Issue #11)."""

    project_title: str
    scope: ScopeSummary
    wbs: WBS
    scenarios: list[Scenario] = Field(default_factory=list)
    selected: ScenarioKind = ScenarioKind.STANDARD
