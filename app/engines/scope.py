"""Scope engine — استخراج Scope Summary از ورودی چندرسانه‌ای و متنی (Issue #6).

دو مسیر:
  1. `analyze()` — قاعده‌محور، بدون شبکه، قابل تست و قطعی (پیش‌فرض MVP).
  2. `analyze_with_vision()` — adapter اختیاری برای LLM چندوجهی؛ در نبود کلید
     یا شبکه، بی‌صدا به مسیر قاعده‌محور برمی‌گردد و این را در `assumptions`
     اعلام می‌کند تا کاربر بداند خروجی از چه مسیری آمده.
"""

from __future__ import annotations

import re
from typing import Protocol

from app.models.domain import Condition, MediaAsset, ScopeSummary, SpaceObservation, SpaceType, WorkPhase

# --- واژگان بازار (Issue #3) — نزدیک به اصطلاح رایج، نه صرفاً مهندسی ---

SPACE_KEYWORDS: dict[SpaceType, tuple[str, ...]] = {
    SpaceType.KITCHEN: ("آشپزخانه", "آشپزخونه", "kitchen", "کابینت", "کابینت‌بندی"),
    SpaceType.BATHROOM: ("حمام", "سرویس", "دستشویی", "bathroom", "توالت"),
    SpaceType.LIVING_ROOM: ("نشیمن", "پذیرایی", "هال", "living", "پذیرایی‌کننده"),
    SpaceType.BEDROOM: ("خواب", "اتاق خواب", "bedroom", "اتاق‌خواب"),
}

# ترتیب مهم است: عبارات خاص‌تر (باکیفیت) قبل از عمومی‌تر (استاندارد) بررسی شوند.
CONDITION_KEYWORDS: tuple[tuple[Condition, tuple[str, ...]], ...] = (
    (Condition.POOR, ("خرابه", "فرسوده", "قدیمی", "کلنگی", "داغون", "باید عوض بشه", "بازسازی کامل")),
    (Condition.FAIR, ("معمولی", "قابل استفاده", "نیاز به تغییر", "نسبتاً سالم")),
    (Condition.GOOD, ("نو", "تازه", "سالم", "نوساز", "بدون مشکل")),
)

# عبارت‌هایی که به‌معنای «همهٔ فازها» هستند؛ بازسازی کامل بدون تخریب و
# تأسیسات از نظر فنی بی‌معناست.
FULL_SCOPE_KEYWORDS: tuple[str, ...] = (
    "بازسازی کامل",
    "کامل بازسازی",
    "از صفر",
    "کل بازسازی",
    "همه چیز عوض",
    "همه‌چیز عوض",
    "اساسی بازسازی",
)

WORK_KEYWORDS: tuple[tuple[WorkPhase, tuple[str, ...]], ...] = (
    (WorkPhase.DEMOLITION, ("تخریب", "برداشتن", "کندن", "خراب کردن")),
    (WorkPhase.MEP, ("لوله", "برق", "سیم‌کشی", "تأسیسات", "آب", "گاز", "پکیج", "کولر")),
    (WorkPhase.STRUCTURE, ("دیوار", "سازه", "پارتیشن", "سقف کاذب", "سفیدکاری", "گچ")),
    (WorkPhase.COVERING, ("کاشی", "سرامیک", "کفپوش", "پارکت", "لمینت", "سنگ", "کاغذ دیواری")),
    (WorkPhase.JOINERY, ("کابینت", "درب", "کمد", "بوفه", "مبلمان ثابت")),
    (WorkPhase.FINISH, ("رنگ", "دکور", "نورپردازی", "لوستر", "پرده")),
)

STYLE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "modern": ("مدرن", "مینیمال", "modern", "ساده"),
    "classic": ("کلاسیک", "classic", "سنتی", "قاجاری"),
    "scandinavian": ("اسکاندیناوی", "روشن", "چوبی روشن", "scandinavian"),
    "luxury": ("لوکس", "لاکچری", "مجلل", "luxury"),
}

# سهم پیش‌فرض هر فضا وقتی کاربر متراژ تفکیکی نمی‌دهد (Issue #3/#4).
DEFAULT_SPACE_SHARE: dict[SpaceType, float] = {
    SpaceType.KITCHEN: 0.30,
    SpaceType.BATHROOM: 0.12,
    SpaceType.LIVING_ROOM: 0.36,
    SpaceType.BEDROOM: 0.22,
}

_TOTAL_AREA_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:متر|مترمربع|م2|m2|sqm)")
_BUDGET_RE = re.compile(r"(?:بودجه|بودجه‌ام|تا|حدود)\s*(\d[\d,،\.]*)\s*(میلیون|میلیارد|تومان)?")


class VisionAnalyzer(Protocol):
    """قرارداد adapter تحلیل بصری — پیاده‌سازی واقعی بیرون از این ماژول است."""

    def observe(self, assets: list[MediaAsset], text: str) -> ScopeSummary: ...


class ScopeError(ValueError):
    """ورودی برای استخراج scope کافی نیست."""


def detect_spaces(text: str) -> list[SpaceType]:
    """فضاهای ذکرشده در متن کاربر، به ترتیب ظهور."""
    ordered: list[tuple[int, SpaceType]] = []
    for space, keywords in SPACE_KEYWORDS.items():
        positions = [text.find(k) for k in keywords if k in text]
        if positions:
            ordered.append((min(positions), space))
    return [space for _, space in sorted(ordered)]


def detect_works(text: str) -> list[WorkPhase]:
    """فازهای کاری موردنیاز از متن کاربر.

    «بازسازی کامل» یعنی همهٔ فازها؛ در غیر این صورت فقط فازهای ذکرشده و اگر
    هیچ فازی ذکر نشد، پوشش و رنگ به‌عنوان کمترین کار محتمل فرض می‌شود.
    """
    if any(k in text for k in FULL_SCOPE_KEYWORDS):
        return list(WorkPhase)
    found = [phase for phase, kws in WORK_KEYWORDS if any(k in text for k in kws)]
    return found or [WorkPhase.COVERING, WorkPhase.FINISH]


def detect_condition(text: str) -> Condition:
    for condition, keywords in CONDITION_KEYWORDS:
        if any(k in text for k in keywords):
            return condition
    return Condition.FAIR


def detect_style(text: str) -> str:
    for style, keywords in STYLE_KEYWORDS.items():
        if any(k in text for k in keywords):
            return style
    return "modern"


def parse_total_area(text: str) -> float | None:
    match = _TOTAL_AREA_RE.search(text)
    if match:
        value = float(match.group(1))
        if 0 < value <= 1000:
            return value
    return None


def parse_budget(text: str) -> int | None:
    """بودجه به تومان. تنها وقتی برمی‌گرداند که واحد صریح باشد."""
    match = _BUDGET_RE.search(text)
    if not match:
        return None
    raw = match.group(1).replace(",", "").replace("،", "").replace(".", "")
    try:
        amount = int(raw)
    except ValueError:
        return None
    unit = match.group(2) or ("تومان" if "تومان" in text else None)
    if unit == "میلیون":
        return amount * 1_000_000
    if unit == "میلیارد":
        return amount * 1_000_000_000
    if unit == "تومان":
        return amount
    return None


def _normalize_area(
    total_area_m2: float,
    spaces: list[SpaceType],
    mentioned: list[SpaceType],
    assumptions: list[str],
) -> dict[SpaceType, float]:
    """توزیع متراژ کل بین فضاهای درگیر.

    اگر کاربر فقط بخشی از فضاها را نام برده باشد، متراژ اعلام‌شده به همان
    فضاها نسبت داده نمی‌شود؛ در عوض سهم فضاهای نام‌برده‌نشده از کل کسر
    می‌شود تا متراژ هر فضا واقع‌گرایانه بماند (مثال: آشپزخانهٔ ۵۷ متری در
    آپارتمان ۸۰ متری غلط است).
    """
    if not mentioned:
        # هیچ فضایی نام برده نشده → توزیع کامل پیش‌فرض.
        return {space: total_area_m2 * DEFAULT_SPACE_SHARE[space] for space in spaces}

    mentioned_share = sum(DEFAULT_SPACE_SHARE[s] for s in mentioned)
    remaining_share = max(0.0, 1.0 - mentioned_share)

    if remaining_share == 0.0:
        # همهٔ فضاها نام برده شده‌اند → توزیع متناسب با کل متراژ.
        return {space: total_area_m2 * DEFAULT_SPACE_SHARE[space] for space in spaces}

    assumptions.append(
        "متراژ اعلام‌شده مربوط به کل واحد است؛ سهم فضاهای دیگر از آن کسر شد. "
        "برای دقت بیشتر متراژ هر فضا را جداگانه ذکر کنید."
    )
    # فضاهای نام‌برده‌نشده با سهم پیش‌فرض خودشان از کل باقی می‌مانند.
    unmentioned = [s for s in spaces if s not in mentioned]
    unmentioned_share = sum(DEFAULT_SPACE_SHARE[s] for s in unmentioned)
    areas = {space: total_area_m2 * DEFAULT_SPACE_SHARE[space] for space in unmentioned}

    # باقی‌مانده به نسبت سهم پیش‌فرض بین فضاهای نام‌برده‌شده پخش می‌شود.
    for space in mentioned:
        areas[space] = total_area_m2 * remaining_share * (DEFAULT_SPACE_SHARE[space] / mentioned_share)
    return areas


def analyze(text: str, *, total_area_m2: float | None = None) -> ScopeSummary:
    """استخراج قاعده‌محور Scope — قطعی و قابل تست (بدون شبکه)."""
    if not text and total_area_m2 is None:
        raise ScopeError("برای استخراج Scope حداقل به توضیح متنی یا متراژ نیاز است.")

    spaces = detect_spaces(text)
    if not spaces:
        # بدون اشارهٔ صریح، کل آپارتمان با توزیع پیش‌فرض فرض می‌شود.
        spaces = list(DEFAULT_SPACE_SHARE.keys())

    area = total_area_m2 or parse_total_area(text)
    conditions = detect_condition(text)
    works = detect_works(text)
    assumptions: list[str] = []

    if area is None:
        area = 75.0
        assumptions.append("متراژ اعلام نشد؛ ۷۵ مترمربع به‌عنوان فرض پیش‌فرض در نظر گرفته شد.")
    if conditions is Condition.FAIR and not any(k in text for kws in CONDITION_KEYWORDS for _, kws2 in [kws] for k in kws2):
        assumptions.append("وضعیت فعلی فضا از متن قابل تشخیص نبود؛ «متوسط» فرض شد.")

    mentioned = detect_spaces(text)
    normalized_area = _normalize_area(area, spaces, mentioned, assumptions)

    observations: list[SpaceObservation] = []
    for space in spaces:
        observations.append(
            SpaceObservation(
                space=space,
                area_m2=round(normalized_area[space], 2),
                condition=conditions,
                confidence=0.75 if space in mentioned else 0.45,
                requested_works=works,
            )
        )

    if len(spaces) == len(DEFAULT_SPACE_SHARE):
        assumptions.append("فضای مشخصی ذکر نشد؛ همهٔ فضاهای استاندارد آپارتمان در نظر گرفته شد.")

    return ScopeSummary(
        spaces=observations,
        style=detect_style(text),
        budget_toman=parse_budget(text),
        assumptions=assumptions,
    )


def analyze_with_vision(
    assets: list[MediaAsset],
    text: str,
    *,
    analyzer: VisionAnalyzer | None = None,
    total_area_m2: float | None = None,
) -> ScopeSummary:
    """مسیر تحلیل بصری با fallback شفاف به قاعده‌محور."""
    if analyzer is not None and assets:
        try:
            return analyzer.observe(assets, text)
        except Exception as exc:  # noqa: BLE001 — هر خطای adapter نباید جریان را قطع کند
            summary = analyze(text, total_area_m2=total_area_m2)
            summary.assumptions.append(
                f"تحلیل بصری ناموفق بود ({type(exc).__name__})؛ نتیجه از تحلیل متنی آمده است."
            )
            return summary

    summary = analyze(text, total_area_m2=total_area_m2)
    if assets:
        summary.assumptions.append(
            "تحلیل بصری غیرفعال است؛ از توضیح متنی استفاده شد. "
            "برای دقت بیشتر، وضعیت هر فضا را متنی هم توضیح دهید."
        )
    return summary
