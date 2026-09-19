"""CLI بنّا — تولید Brief از خط فرمان (نمایشی و تست سریع جریان کامل)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.engines.media import MediaValidationError
from app.engines.scope import ScopeError
from app.pipeline import run_to_file


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="banna-brief",
        description="تولید Brief بازسازی از توضیح متنی و متراژ.",
    )
    parser.add_argument("description", help="توضیح پروژه به فارسی")
    parser.add_argument("--area", type=float, default=None, help="متراژ کل (مترمربع)")
    parser.add_argument(
        "--title", default="پروژهٔ بازسازی", help="عنوان پروژه در سند"
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("outputs/brief.html"),
        help="مسیر فایل خروجی HTML",
    )
    args = parser.parse_args(argv)

    try:
        result = run_to_file(
            description=args.description,
            output_path=args.out,
            title=args.title,
            total_area_m2=args.area,
        )
    except (ScopeError, MediaValidationError) as exc:
        print(f"خطا: {exc}", file=sys.stderr)
        return 1

    selected = next(s for s in result.scenarios if s.kind == result.selected)
    fmt = lambda v: f"{v / 1_000_000:,.0f} میلیون تومان"  # noqa: E731
    print(f"سند تولید شد: {args.out}")
    print(f"سناریوی پیشنهادی: {selected.label_fa}")
    print(
        f"بازهٔ هزینه: {fmt(selected.estimate.cost_min_toman)} "
        f"تا {fmt(selected.estimate.cost_max_toman)}"
    )
    print(
        f"مدت اجرا: {selected.estimate.duration_days_min} تا "
        f"{selected.estimate.duration_days_max} روز"
    )
    if result.missing_price_codes:
        print(f"هشدار — آیتم بدون قیمت: {', '.join(result.missing_price_codes)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
