"""Estimate engine — تخمین هزینه و زمان از WBS و متریال (Issue #9).

اصول:
  - خروجی همیشه **بازه** است، هرگز عدد قطعی (سند architecture، بخش ۴).
  - زمان از **مسیر بحرانی** زنجیرهٔ وابستگی محاسبه می‌شود، نه جمع سادهٔ همهٔ
    آیتم‌ها؛ چون فازهای یک فضا پشت سر هم اجرا می‌شوند ولی فضاهای مختلف
    می‌توانند هم‌زمان پیش بروند.
"""

from __future__ import annotations

from app.engines import material as material_engine
from app.models.domain import CostLine, Estimate, WBS, WBSItem

# ضریب بهره‌وری: زمان واقعی اجرا در سایت مسکونی از زمان تئوریک بیشتر است
# (دسترسی محدود، هماهنگی ساکن، تأخیر تحویل متریال).
DURATION_FACTOR_MIN = 1.15
DURATION_FACTOR_MAX = 1.60

# چند اکیپ می‌توانند هم‌زمان کار کنند (فضاهای مختلف).
MAX_PARALLEL_SPACES = 2

# متریال باکیفیت‌تر کار بیشتری می‌برد: برش دقیق‌تر، بندکشی اپوکسی، نصب
# وارداتی. متریال اقتصادی برعکس سریع‌تر نصب می‌شود.
TIER_SPEED: dict[str, float] = {"economy": 0.90, "standard": 1.0, "premium": 1.25}

# سربار پروژه: نظارت، حمل، هزینه‌های پیش‌بینی‌نشده.
OVERHEAD_MIN = 0.08
OVERHEAD_MAX = 0.15


class EstimateError(ValueError):
    """WBS برای تخمین معتبر نیست."""


def _line_for(item: WBSItem, tier) -> CostLine | None:
    if not item.materials:
        return None

    option = item.materials[0]
    material_range = (
        int(round(option.unit_price_min * item.quantity)),
        int(round(option.unit_price_max * item.quantity)),
    )

    labor = material_engine.labor_range(item)
    if labor is None:
        return None
    labor_range = (
        int(round(labor[0] * item.quantity)),
        int(round(labor[1] * item.quantity)),
    )

    return CostLine(
        wbs_code=item.code,
        title=item.title,
        material_toman=material_range,
        labor_toman=labor_range,
    )


def _critical_path_days(items: list[WBSItem], durations: dict[str, float]) -> float:
    """طولانی‌ترین زنجیرهٔ وابستگی — با memoization روی گراف DAG."""
    by_code = {i.code: i for i in items}
    memo: dict[str, float] = {}
    visiting: set[str] = set()

    def length(code: str) -> float:
        if code in memo:
            return memo[code]
        if code in visiting:  # محافظت از چرخهٔ ناخواسته در دیتا
            return 0.0
        visiting.add(code)

        item = by_code[code]
        own = durations.get(code, 0.0)
        deps = [length(d) for d in item.depends_on if d in by_code]
        total = own + (max(deps) if deps else 0.0)

        visiting.discard(code)
        memo[code] = total
        return total

    return max((length(c) for c in by_code), default=0.0)


def _tier_of(wbs: WBS) -> str:
    """سطح متریال غالب WBS — از خود آیتم‌ها خوانده می‌شود تا صریح پاس نشود."""
    for item in wbs.items:
        if item.materials:
            return item.materials[0].tier.value
    return "standard"


def estimate(wbs: WBS) -> Estimate:
    """تخمین هزینه و زمان برای یک WBS قیمت‌گذاری‌شده."""
    if not wbs.items:
        raise EstimateError("WBS خالی است — تخمین ممکن نیست.")

    speed = TIER_SPEED.get(_tier_of(wbs), 1.0)
    lines: list[CostLine] = []
    durations: dict[str, float] = {}
    skipped: list[str] = []

    for item in wbs.items:
        line = _line_for(item, None)
        if line is None:
            skipped.append(item.code)
            continue
        lines.append(line)

        prod = material_engine.productivity(item)
        if prod and prod > 0:
            durations[item.code] = (item.quantity / prod) * speed
        else:
            durations[item.code] = 0.0

    if not lines:
        raise EstimateError("هیچ آیتمی قیمت‌گذاری نشد — دیتاست قیمت را بررسی کنید.")

    cost_min = round(sum(l.total_min for l in lines) * (1 + OVERHEAD_MIN))
    cost_max = round(sum(l.total_max for l in lines) * (1 + OVERHEAD_MAX))

    critical = _critical_path_days(wbs.items, durations)
    # فضاهای موازی زنجیرهٔ بحرانی را کوتاه می‌کنند، ولی نه متناسب با تعداد؛
    # دو اکیپ حداکثر حدود ۳۵٪ کوتاه‌سازی واقع‌بینانه می‌دهند.
    if len({i.space for i in wbs.items}) > 1:
        critical *= 1 / (1 + 0.35 * (MAX_PARALLEL_SPACES - 1))

    duration_min = max(1, round(critical * DURATION_FACTOR_MIN))
    duration_max = max(duration_min + 1, round(critical * DURATION_FACTOR_MAX))

    note = "بازهٔ هزینه بر پایهٔ قیمت بازار تهران و بازهٔ زمانی با ضریب بهره‌وری سایت محاسبه شده است."
    if skipped:
        note += f" {len(skipped)} آیتم بدون قیمت در دیتاست، از تخمین حذف شد."

    return Estimate(
        lines=lines,
        cost_min_toman=cost_min,
        cost_max_toman=cost_max,
        duration_days_min=duration_min,
        duration_days_max=duration_max,
        uncertainty_note=note,
    )
