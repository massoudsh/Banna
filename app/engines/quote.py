"""Quote normalization engine — مقایسهٔ quote مجریان با تخمین پایه (Issue #15).

مسئله‌ای که حل می‌کند: هر مجری با فرمت خودش قیمت می‌دهد (ردیفی، کلی، با کد
متفاوت)، پس کارفرما نمی‌تواند apple-to-apple مقایسه کند. این موتور همهٔ
quoteها را روی **همان WBS** می‌نشاند و انحرافشان را از تخمین پایه می‌سنجد.

دو اصل غیرقابل‌مذاکره:
۱. quote ناقص «ارزان» گزارش نمی‌شود — اگر مجری ۵ آیتم از ۱۵ آیتم را قیمت بدهد،
   جمعش قطعاً کمتر است و مقایسهٔ خام گمراه‌کننده است. چنین quoteی
   `is_comparable=False` می‌گیرد و در رتبه‌بندی وارد نمی‌شود.
۲. کد ناشناخته بی‌صدا حذف نمی‌شود — در `unknown_codes` گزارش می‌شود تا
   کارفرما بداند مجری آیتمی را قیمت داده که در سند نبوده.
"""

from __future__ import annotations

import statistics

from app.models.domain import (
    ContractorQuote,
    NormalizedQuote,
    NormalizedQuoteLine,
    QuoteComparison,
    Scenario,
    ScenarioKind,
    WBS,
    WBSItem,
)

# آستانهٔ بی‌ثباتی مبنای مقایسه — همراستا با docs/specs/acceptance-testing.md
UNSTABLE_SPREAD_PCT = 30.0
# زیر این نسبت پوشش، جمع quote قابل‌مقایسه نیست.
MIN_COVERAGE_PCT = 80.0


class QuoteError(Exception):
    """خطای ورودی quote — پیام فارسی و قابل‌نمایش به کاربر."""


def _lines_by_code(quote: ContractorQuote) -> tuple[dict[str, int], list[str], list[str]]:
    """جمع‌کردن ردیف‌های quote به تفکیک کد، با گزارش تکرار و کدهای خالی."""
    prices: dict[str, int] = {}
    duplicates: list[str] = []
    unknown_blank: list[str] = []

    for line in quote.lines:
        code = line.code.strip().upper()
        if not code:
            unknown_blank.append(line.code)
            continue
        if code in prices:
            duplicates.append(code)
            continue
        prices[code] = line.price_toman

    return prices, duplicates, unknown_blank


def _deviation_pct(value: int, median: float) -> float:
    if median <= 0:
        return 0.0
    return (value - median) / median * 100


def normalize(
    quote: ContractorQuote,
    wbs: WBS,
    baseline: Scenario,
) -> NormalizedQuote:
    """یک quote را روی WBS پروژه می‌نشاند و با سناریوی پایه می‌سنجد."""
    if not wbs.items:
        raise QuoteError("WBS پروژه خالی است؛ مقایسهٔ quote ممکن نیست.")

    prices, duplicates, blank = _lines_by_code(quote)

    lines: list[NormalizedQuoteLine] = []
    missing: list[str] = []

    for item in wbs.ordered():
        price = prices.get(item.code)
        if price is None:
            missing.append(item.code)
            continue
        lines.append(_match_line(item, price, baseline))

    wbs_codes = {i.code for i in wbs.items}
    unknown = sorted(c for c in prices if c not in wbs_codes)

    if quote.total_toman is not None:
        total = quote.total_toman
    else:
        total = sum(line.price_toman for line in lines)

    baseline_median = (baseline.estimate.cost_min_toman + baseline.estimate.cost_max_toman) / 2
    coverage = len(lines) / len(wbs.items) * 100 if wbs.items else 0.0
    comparable = not missing and not unknown and not duplicates

    notes: list[str] = []
    if quote.total_toman is not None:
        notes.append("مجری مبلغ کل اعلام کرده، نه قیمت ردیفی.")
    if missing:
        notes.append(
            f"{len(missing)} آیتم از {len(wbs.items)} آیتم WBS قیمت نگرفته؛ "
            "جمع این quote با بقیه قابل‌مقایسه نیست."
        )
    if unknown:
        notes.append(
            "کدهای ناشناخته در quote (در WBS این پروژه نیستند): " + "، ".join(unknown)
        )
    if duplicates:
        notes.append("کد تکراری در quote (فقط اولین قیمت لحاظ شد): " + "، ".join(duplicates))
    if blank:
        notes.append("ردیف بدون کد نادیده گرفته شد.")

    return NormalizedQuote(
        contractor_id=quote.contractor_id,
        contractor_name=quote.contractor_name or quote.contractor_id,
        total_toman=total,
        lines=lines,
        missing_codes=missing,
        unknown_codes=unknown,
        duplicate_codes=duplicates,
        itemized=quote.total_toman is None,
        deviation_pct=_deviation_pct(total, baseline_median),
        coverage_pct=coverage,
        is_comparable=comparable,
        notes=notes,
    )


def _match_line(item: WBSItem, price: int, baseline: Scenario) -> NormalizedQuoteLine:
    """قیمت مجری را با سهم تخمینی همان آیتم می‌سنجد."""
    cost_line = next(
        (line for line in baseline.estimate.lines if line.wbs_code == item.code), None
    )
    est_min = cost_line.total_min if cost_line else 0
    est_max = cost_line.total_max if cost_line else 0
    est_median = (est_min + est_max) / 2

    return NormalizedQuoteLine(
        code=item.code,
        title=item.title,
        phase=item.phase,
        space=item.space,
        unit=item.unit,
        quantity=item.quantity,
        price_toman=price,
        estimate_min_toman=est_min,
        estimate_max_toman=est_max,
        deviation_pct=_deviation_pct(price, est_median),
        within_estimate_range=est_min <= price <= est_max,
    )


def compare(
    quotes: list[ContractorQuote],
    wbs: WBS,
    baseline: Scenario,
) -> QuoteComparison:
    """همهٔ quoteها را نرمال و با تخمین پایه مقایسه می‌کند."""
    if not quotes:
        raise QuoteError("هیچ quote‌ای برای مقایسه ثبت نشده است.")

    normalized = [normalize(q, wbs, baseline) for q in quotes]
    baseline_median = (baseline.estimate.cost_min_toman + baseline.estimate.cost_max_toman) / 2

    comparable = [q for q in normalized if q.is_comparable]
    totals = [q.total_toman for q in comparable]

    spread = 0.0
    if len(totals) > 1:
        median_total = statistics.median(totals)
        if median_total > 0:
            spread = (max(totals) - min(totals)) / median_total * 100

    cheapest = min(comparable, key=lambda q: q.total_toman) if comparable else None
    highest = max(comparable, key=lambda q: q.total_toman) if comparable else None

    return QuoteComparison(
        baseline_kind=baseline.kind,
        baseline_min_toman=baseline.estimate.cost_min_toman,
        baseline_max_toman=baseline.estimate.cost_max_toman,
        baseline_median_toman=int(baseline_median),
        quotes=normalized,
        cheapest_comparable_id=cheapest.contractor_id if cheapest else None,
        highest_comparable_id=highest.contractor_id if highest else None,
        spread_pct=spread,
        spread_is_stable=spread <= UNSTABLE_SPREAD_PCT,
    )


def baseline_for(scenarios: list[Scenario], kind: ScenarioKind) -> Scenario:
    """سناریوی پایه برای مقایسه — همان سناریوی انتخابی Brief."""
    for scenario in scenarios:
        if scenario.kind == kind:
            return scenario
    raise QuoteError(f"سناریوی پایه با عنوان «{kind.value}» پیدا نشد.")
