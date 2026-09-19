"""Scenario engine — تولید ۴ سناریوی خروجی (Issue #10).

هر سناریو یک تکرار کامل از زنجیرهٔ متریال → تخمین است، نه یک ضریب روی
سناریوی پایه. دلیل: سطح متریال هم روی هزینه و هم روی بهره‌وری اجرا اثر دارد
و ضرب کردن یک عدد در ضریب، آن اثر را از دست می‌دهد.
"""

from __future__ import annotations

from app.engines import material as material_engine
from app.engines.estimate import estimate
from app.models.domain import (
    SCENARIO_LABELS_FA,
    MaterialTier,
    Scenario,
    ScenarioKind,
    WBS,
)

# هر سناریو: سطح متریال + شدت کار + توضیح برای کارفرما.
SCENARIO_SPECS: dict[ScenarioKind, dict] = {
    ScenarioKind.ECONOMY: {
        "tier": MaterialTier.ECONOMY,
        "description": (
            "کمترین هزینهٔ قابل‌قبول: متریال ایرانی سطح پایین‌تر، بدون جابه‌جایی "
            "تأسیسات و با حداقل تغییرات سازه‌ای. برای واحدی که فقط باید سالم و "
            "قابل‌استفاده باشد."
        ),
        "include_phases": None,
    },
    ScenarioKind.STANDARD: {
        "tier": MaterialTier.STANDARD,
        "description": (
            "تعادل هزینه و کیفیت با متریال درجه‌یک ایرانی و بازسازی کامل فضاهای "
            "درگیر. گزینهٔ پیشنهادی برای اکثر واحدهای مسکونی."
        ),
        "include_phases": None,
    },
    ScenarioKind.PREMIUM: {
        "tier": MaterialTier.PREMIUM,
        "description": (
            "بالاترین کیفیت اجرا و متریال وارداتی، با نورپردازی و دکور کامل و "
            "امکان تغییرات سازه‌ای. Suitable برای واحدهایی که ارزش‌افزودهٔ ملک مهم است."
        ),
        "include_phases": None,
    },
    ScenarioKind.RENTAL: {
        "tier": MaterialTier.ECONOMY,
        "description": (
            "بهینه برای اجارهٔ سریع: تمرکز روی ظاهر قابل‌قبول و دوام در برابر "
            "مستأجر. بدون کابینت‌بندی سفارشی و بدون دکور گران؛ فقط آنچه مستأجر "
            "می‌بیند و لمس می‌کند."
        ),
        # در سناریوی اجاره، آیتم‌های دکور و کمد سفارشی حذف می‌شوند.
        "exclude_codes": {"KIT-FIN-P", "LIV-FIN-D", "BED-JOI-D", "KIT-JOI-C"},
    },
}


def _filtered(wbs: WBS, spec: dict) -> WBS:
    excluded = spec.get("exclude_codes")
    if not excluded:
        return wbs.model_copy(deep=True)

    kept = [item.model_copy(deep=True) for item in wbs.items if item.code not in excluded]
    # وابستگی به آیتم‌های حذف‌شده باید پاک شود وگرنه مسیر بحرانی به آیتم
    # ناموجود اشاره می‌کند.
    present = {i.code for i in kept}
    for item in kept:
        item.depends_on = [d for d in item.depends_on if d in present]
    return WBS(items=kept)


def build_all(wbs: WBS) -> list[Scenario]:
    """تولید هر چهار سناریو از یک WBS پایه."""
    scenarios: list[Scenario] = []

    for kind, spec in SCENARIO_SPECS.items():
        variant = _filtered(wbs, spec)
        priced, _ = material_engine.apply(variant, spec["tier"])
        scenarios.append(
            Scenario(
                kind=kind,
                label_fa=SCENARIO_LABELS_FA[kind],
                tier=spec["tier"],
                estimate=estimate(priced),
                description=spec["description"],
            )
        )

    return scenarios


def nearest_to_budget(scenarios: list[Scenario], budget_toman: int | None) -> ScenarioKind:
    """سناریویی که کف بازهٔ هزینه‌اش به بودجه نزدیک‌ترین است (بدون عبور از بودجه)."""
    if not scenarios:
        raise ValueError("فهرست سناریوها خالی است.")

    if budget_toman is None or budget_toman <= 0:
        return ScenarioKind.STANDARD

    affordable = [s for s in scenarios if s.estimate.cost_min_toman <= budget_toman]
    if not affordable:
        return ScenarioKind.ECONOMY

    return max(affordable, key=lambda s: s.estimate.cost_min_toman).kind
