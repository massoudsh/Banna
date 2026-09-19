"""WBS engine — تبدیل Scope Summary به ساختار شکست کار (Issue #7).

مبنا: WBS مرجع و ترتیب فازها از Issue #3 و `data/wbs_reference.json`.
خروجی همیشه به ترتیب استاندارد فازها مرتب می‌شود و آیتم‌های وابسته صریح
علامت‌گذاری می‌شوند تا موتور زمان‌بندی (#9) بتواند مسیر بحرانی را حساب کند.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from app.models.domain import (
    PHASE_ORDER,
    ScopeSummary,
    SpaceObservation,
    SpaceType,
    WBS,
    WBSItem,
    WorkPhase,
)

REFERENCE_PATH = Path(__file__).resolve().parents[2] / "data" / "wbs_reference.json"

# آیتم‌هایی که پیش‌نیاز منطقی آیتم‌های فاز بعدی هستند.
_PHASE_PRECEDENCE: dict[WorkPhase, WorkPhase | None] = {
    WorkPhase.DEMOLITION: None,
    WorkPhase.MEP: WorkPhase.DEMOLITION,
    WorkPhase.STRUCTURE: WorkPhase.MEP,
    WorkPhase.COVERING: WorkPhase.STRUCTURE,
    WorkPhase.JOINERY: WorkPhase.COVERING,
    WorkPhase.FINISH: WorkPhase.JOINERY,
}


class WBSError(ValueError):
    """Scope برای تولید WBS معتبر نیست."""


@lru_cache(maxsize=1)
def load_reference() -> dict:
    if not REFERENCE_PATH.exists():
        raise WBSError(f"WBS مرجع پیدا نشد: {REFERENCE_PATH.name}")
    return json.loads(REFERENCE_PATH.read_text(encoding="utf-8"))


def _items_for_space(space: SpaceObservation, reference: dict) -> list[WBSItem]:
    space_key = space.space.value
    spec = reference["spaces"].get(space_key)
    if spec is None:
        return []

    requested = set(space.requested_works)
    items: list[WBSItem] = []

    for entry in spec["items"]:
        phase = WorkPhase(entry["phase"])
        if phase not in requested:
            continue

        # آیتم‌های با مقدار ثابت (مثل «تخریب») به متراژ وابسته نیستند.
        if entry["unit"] == "fixed":
            quantity = 1.0
            unit = "مورد"
        else:
            quantity = round(space.area_m2 * entry.get("factor", 1.0), 2)
            unit = entry["unit"]

        if quantity <= 0:
            continue

        items.append(
            WBSItem(
                code=f"{space_key[:3].upper()}-{entry['code']}",
                title=entry["title"],
                phase=phase,
                space=space.space,
                quantity=quantity,
                unit=unit,
                depends_on=[
                    f"{space_key[:3].upper()}-{dep}" for dep in entry.get("depends_on", [])
                ],
            )
        )

    return items


def generate(scope: ScopeSummary) -> WBS:
    """تولید WBS از Scope، مرتب‌شده به ترتیب استاندارد فازها."""
    if not scope.spaces:
        raise WBSError("Scope بدون فضا — WBS قابل تولید نیست.")

    reference = load_reference()
    items: list[WBSItem] = []

    for space in scope.spaces:
        if space.space not in SpaceType:
            continue
        items.extend(_items_for_space(space, reference))

    if not items:
        raise WBSError("هیچ آیتم کاری برای فضاهای شناسایی‌شده تولید نشد.")

    # وابستگی بین فازی: هر آیتم به آخرین آیتم فاز قبل در همان فضا وابسته است.
    by_space_phase: dict[tuple[SpaceType, WorkPhase], str] = {}
    for item in items:
        by_space_phase[(item.space, item.phase)] = item.code

    for item in items:
        prev_phase = _PHASE_PRECEDENCE[item.phase]
        if prev_phase is None:
            continue
        prev_code = by_space_phase.get((item.space, prev_phase))
        if prev_code and prev_code not in item.depends_on:
            item.depends_on.append(prev_code)

    return WBS(items=sorted(items, key=lambda i: (PHASE_ORDER.index(i.phase), i.code)))
