"""پل CLI: اجرای pipeline بنّا و چاپ خروجی JSON برای مصرف لایهٔ وب (Next.js).

این اسکریپت **منطق دامنه ندارد**؛ فقط `app.pipeline.run` را صدا می‌زند و
`PipelineResult` را به شکلی که UI نیاز دارد سریالایز می‌کند. هر فرمول قیمت یا
زمان باید در موتورهای `app/engines/` بماند.

قرارداد خروجی:
    موفق  → JSON روی stdout، کد خروج ۰
    خطای دامنه → پیام فارسی روی stdout، کد خروج ۲ (UI آن را به کاربر نشان می‌دهد)
    خطای غیرمنتظره → پیام روی stderr، کد خروج ۱
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.engines.media import MediaValidationError  # noqa: E402
from app.engines.scope import ScopeError  # noqa: E402
from app.engines.wbs import WBSError  # noqa: E402
from app.models.domain import PHASE_LABELS_FA, SCENARIO_LABELS_FA  # noqa: E402
from app.pipeline import run  # noqa: E402

SPACE_LABELS_FA = {
    "kitchen": "آشپزخانه",
    "bathroom": "حمام و سرویس",
    "living_room": "نشیمن و پذیرایی",
    "bedroom": "اتاق خواب",
}
CONDITION_LABELS_FA = {"good": "سالم", "fair": "متوسط", "poor": "فرسوده"}

DOMAIN_ERRORS = (MediaValidationError, ScopeError, WBSError)


def summarize(description: str, area_m2: float | None) -> dict:
    result = run(description=description, total_area_m2=area_m2)

    return {
        "selected": result.selected.value,
        "total_area_m2": result.scope.total_area_m2,
        "style": result.scope.style,
        "budget_toman": result.scope.budget_toman,
        "spaces": [
            {
                "space": s.space.value,
                "label_fa": SPACE_LABELS_FA[s.space.value],
                "area_m2": round(s.area_m2, 2),
                "condition": CONDITION_LABELS_FA[s.condition.value],
                "requested_works": [PHASE_LABELS_FA[w] for w in s.requested_works],
            }
            for s in result.scope.spaces
        ],
        "scenarios": [
            {
                "kind": sc.kind.value,
                "label_fa": SCENARIO_LABELS_FA[sc.kind],
                "tier": sc.tier.value,
                "description": sc.description,
                "cost_min_toman": sc.estimate.cost_min_toman,
                "cost_max_toman": sc.estimate.cost_max_toman,
                "duration_days_min": sc.estimate.duration_days_min,
                "duration_days_max": sc.estimate.duration_days_max,
            }
            for sc in result.scenarios
        ],
        "wbs_items": [
            {
                "code": i.code,
                "title": i.title,
                "phase": i.phase.value,
                "phase_label_fa": PHASE_LABELS_FA[i.phase],
                "space": i.space.value,
                "space_label_fa": SPACE_LABELS_FA[i.space.value],
                "quantity": i.quantity,
                "unit": i.unit,
                "material": i.materials[0].name if i.materials else None,
            }
            for i in result.wbs.ordered()
        ],
        "assumptions": result.scope.assumptions,
        "missing_price_codes": result.missing_price_codes,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="اجرای pipeline بنّا و چاپ JSON")
    parser.add_argument("--description", required=True)
    parser.add_argument("--area", type=float, default=None)
    args = parser.parse_args(argv)

    try:
        payload = summarize(args.description, args.area)
    except DOMAIN_ERRORS as exc:
        # پیام فارسی موتور عیناً به UI می‌رسد (کد ۲ = خطای قابل‌نمایش به کاربر)
        print(str(exc))
        return 2
    except Exception as exc:  # pragma: no cover - خطای غیرمنتظره
        print(f"خطای غیرمنتظره در موتور: {exc}", file=sys.stderr)
        return 1

    json.dump(payload, sys.stdout, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
