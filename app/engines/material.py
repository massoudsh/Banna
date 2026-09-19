"""Material engine — نگاشت آیتم‌های WBS به گزینه‌های متریال قیمت‌گذاری‌شده (Issue #8).

منبع قیمت: `data/price_dataset.json` (Issue #2). اگر آیتمی در دیتاست نباشد،
آیتم بدون متریال باقی می‌ماند و در `missing_codes` گزارش می‌شود — تخمین
بی‌صدا عدد ناقص تولید نمی‌کند.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from app.models.domain import MaterialOption, MaterialTier, WBS, WBSItem

DATASET_PATH = Path(__file__).resolve().parents[2] / "data" / "price_dataset.json"

# کدهای آیتم در WBS پسوند فضایی دارند (KIT-) ولی دیتاست هم کلید فضایی و هم
# کلید عمومی دارد. این نگاشت ترتیب تلاش برای یافتن قیمت را تعیین می‌کند.
_SPACE_PREFIXES = {"kitchen": "KIT", "bathroom": "BAT", "living_room": "LIV", "bedroom": "BED"}


class MaterialError(ValueError):
    """دیتاست قیمت معتبر نیست."""


@lru_cache(maxsize=1)
def load_dataset() -> dict:
    if not DATASET_PATH.exists():
        raise MaterialError(f"دیتاست قیمت پیدا نشد: {DATASET_PATH.name}")
    data = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    if "items" not in data or not data["items"]:
        raise MaterialError("دیتاست قیمت خالی است.")
    return data


def _resolve_key(item: WBSItem, items: dict) -> str | None:
    """کلید دیتاست برای یک آیتم WBS.

    کد WBS به شکل `KIT-COV-T` است؛ کلید دیتاست `KIT-COV-T` یا عمومی `COV-T`.
    """
    prefix = _SPACE_PREFIXES[item.space.value]
    suffix = item.code[len(prefix) + 1 :] if item.code.startswith(prefix + "-") else item.code

    for candidate in (item.code, f"{prefix}-{suffix}", suffix):
        if candidate in items:
            return candidate
    return None


def options_for(item: WBSItem, tier: MaterialTier, dataset: dict) -> list[MaterialOption]:
    """گزینه‌های متریال برای یک آیتم در سطح کیفیت مشخص."""
    key = _resolve_key(item, dataset["items"])
    if key is None:
        return []

    spec = dataset["items"][key]
    tiers = spec["material"]["tiers"]
    chosen = tiers.get(tier.value)
    if chosen is None:
        return []

    return [
        MaterialOption(
            name=chosen["name"],
            tier=tier,
            unit=spec["material"]["unit"],
            unit_price_min=chosen["min"],
            unit_price_max=chosen["max"],
        )
    ]


def apply(wbs: WBS, tier: MaterialTier = MaterialTier.STANDARD) -> tuple[WBS, list[str]]:
    """متریال هر آیتم WBS را بر اساس سطح کیفیت پر می‌کند.

    Returns:
        (WBS به‌روزشده, فهرست کد آیتم‌هایی که قیمتی برایشان پیدا نشد)
    """
    dataset = load_dataset()
    missing: list[str] = []

    for item in wbs.items:
        options = options_for(item, tier, dataset)
        if options:
            item.materials = options
        elif item.code not in missing:
            missing.append(item.code)

    return wbs, missing


def labor_range(item: WBSItem, dataset: dict | None = None) -> tuple[int, int] | None:
    """بازهٔ دستمزد اجرای یک آیتم (تومان)."""
    data = dataset or load_dataset()
    key = _resolve_key(item, data["items"])
    if key is None:
        return None
    labor = data["items"][key].get("labor")
    if not labor:
        return None
    return (labor["min"], labor["max"])


def productivity(item: WBSItem, dataset: dict | None = None) -> float | None:
    """متراژ یا مقدار کار انجام‌شده در روز برای آیتم (برای تخمین زمان)."""
    data = dataset or load_dataset()
    key = _resolve_key(item, data["items"])
    if key is None:
        return None
    return data["items"][key].get("productivity_m2_per_day")
