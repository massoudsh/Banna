"""Brief renderer — تبدیل خروجی نهایی به سند قابل‌اشتراک با مجری (Issue #11).

خروجی HTML با ساختار RTL و فونت فارسی است؛ تولید PDF با تبدیل همین HTML
انجام می‌شود (موتور PDF قابل تعویض است). متن سند عمداً برای مجری غیرفنی
نوشته می‌شود: هر آیتم با مقدار، واحد و بازهٔ قیمت مشخص.
"""

from __future__ import annotations

from html import escape

from app.models.domain import (
    PHASE_LABELS_FA,
    RenovationBrief,
    Scenario,
    ScenarioKind,
    SpaceType,
)

SPACE_LABELS_FA: dict[SpaceType, str] = {
    SpaceType.KITCHEN: "آشپزخانه",
    SpaceType.BATHROOM: "حمام و سرویس",
    SpaceType.LIVING_ROOM: "نشیمن و پذیرایی",
    SpaceType.BEDROOM: "اتاق خواب",
}


def format_toman(amount: int) -> str:
    """قالب‌بندی مبلغ به‌صورت خوانا برای ایرانی (میلیون/میلیارد تومان)."""
    if amount >= 1_000_000_000:
        return f"{amount / 1_000_000_000:.2f}".rstrip("0").rstrip(".") + " میلیارد تومان"
    return f"{amount / 1_000_000:.0f} میلیون تومان"


def _scenario_row(scenario: Scenario, budget_toman: int | None) -> str:
    est = scenario.estimate
    badge = ""
    if budget_toman and est.cost_min_toman <= budget_toman:
        badge = '<span class="badge">در بودجه</span>'
    if budget_toman and est.cost_min_toman > budget_toman:
        badge = '<span class="badge warn">بالاتر از بودجه</span>'

    return f"""
      <tr>
        <td>{escape(scenario.label_fa)} {badge}</td>
        <td>{format_toman(est.cost_min_toman)} تا {format_toman(est.cost_max_toman)}</td>
        <td>{est.duration_days_min} تا {est.duration_days_max} روز</td>
      </tr>"""


def _items_rows(brief: RenovationBrief) -> str:
    rows = []
    for item in brief.wbs.ordered():
        material = item.materials[0].name if item.materials else "—"
        rows.append(
            f"""
      <tr>
        <td>{escape(PHASE_LABELS_FA[item.phase])}</td>
        <td>{escape(SPACE_LABELS_FA[item.space])}</td>
        <td>{escape(item.title)}</td>
        <td>{item.quantity:g} {escape(item.unit)}</td>
        <td>{escape(material)}</td>
      </tr>"""
        )
    return "".join(rows)


def _scope_section(brief: RenovationBrief) -> str:
    rows = []
    for space in brief.scope.spaces:
        works = "، ".join(PHASE_LABELS_FA[w] for w in space.requested_works)
        condition = {"good": "سالم", "fair": "متوسط", "poor": "فرسوده"}[space.condition.value]
        rows.append(
            f"""
      <tr>
        <td>{escape(SPACE_LABELS_FA[space.space])}</td>
        <td>{space.area_m2:g} مترمربع</td>
        <td>{condition}</td>
        <td>{escape(works)}</td>
      </tr>"""
        )
    return "".join(rows)


def _assumptions_section(brief: RenovationBrief) -> str:
    if not brief.scope.assumptions:
        return ""
    items = "".join(f"<li>{escape(a)}</li>" for a in brief.scope.assumptions)
    return f"""
    <section>
      <h2>فرض‌ها و محدودیت‌ها</h2>
      <ul class="assumptions">{items}</ul>
    </section>"""


def render(brief: RenovationBrief) -> str:
    """تولید HTML سند Brief."""
    selected = next(
        (s for s in brief.scenarios if s.kind == brief.selected),
        brief.scenarios[0] if brief.scenarios else None,
    )
    if selected is None:
        raise ValueError("Brief بدون سناریو قابل تولید نیست.")

    budget = brief.scope.budget_toman
    budget_line = (
        f"<p>بودجهٔ اعلام‌شدهٔ کارفرما: <strong>{format_toman(budget)}</strong></p>"
        if budget
        else "<p>بودجهٔ اعلام‌شده: ثبت نشده</p>"
    )

    est = selected.estimate
    return f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
  <meta charset="utf-8">
  <title>بریف بازسازی — {escape(brief.project_title)}</title>
  <style>
    body {{ font-family: "IRANSans", "Tahoma", sans-serif; background: #f7f7f8;
           color: #1a1a1a; line-height: 1.9; padding: 2rem; max-width: 900px; margin: auto; }}
    h1 {{ font-size: 1.6rem; border-bottom: 3px solid #2f6f4e; padding-bottom: .5rem; }}
    h2 {{ font-size: 1.15rem; margin-top: 2rem; color: #2f6f4e; }}
    table {{ width: 100%; border-collapse: collapse; background: #fff; margin-top: .75rem; }}
    th, td {{ border: 1px solid #e2e2e6; padding: .55rem .7rem; text-align: right; font-size: .92rem; }}
    th {{ background: #eef4f0; }}
    .summary {{ background: #fff; border: 1px solid #e2e2e6; border-radius: 8px;
                padding: 1rem 1.25rem; margin-top: 1rem; }}
    .price {{ font-size: 1.25rem; font-weight: bold; color: #2f6f4e; }}
    .badge {{ background: #e3f3e9; color: #22603f; border-radius: 4px;
              padding: .1rem .4rem; font-size: .75rem; }}
    .badge.warn {{ background: #fdecec; color: #a12626; }}
    .assumptions {{ color: #666; font-size: .85rem; }}
    footer {{ margin-top: 2rem; font-size: .78rem; color: #888; }}
  </style>
</head>
<body>
  <h1>بریف بازسازی — {escape(brief.project_title)}</h1>
  <p>این سند خلاصهٔ کار، ترتیب اجرا و بازهٔ هزینه/زمان پروژه است و برای ارسال به مجری تهیه شده.
     همهٔ مبالغ <strong>بازه</strong> هستند، نه قیمت قطعی.</p>

  <section class="summary">
    <h2>خلاصهٔ سناریوی انتخابی: {escape(selected.label_fa)}</h2>
    {budget_line}
    <p class="price">{format_toman(est.cost_min_toman)} تا {format_toman(est.cost_max_toman)}</p>
    <p>مدت اجرا: <strong>{est.duration_days_min} تا {est.duration_days_max} روز</strong></p>
    <p>{escape(selected.description)}</p>
  </section>

  <section>
    <h2>وضعیت فضاها</h2>
    <table>
      <tr><th>فضا</th><th>متراژ</th><th>وضعیت فعلی</th><th>کارهای موردنیاز</th></tr>{_scope_section(brief)}
    </table>
  </section>

  <section>
    <h2>مقایسهٔ سناریوها</h2>
    <table>
      <tr><th>سناریو</th><th>بازهٔ هزینه</th><th>مدت اجرا</th></tr>{"".join(_scenario_row(s, budget) for s in brief.scenarios)}
    </table>
  </section>

  <section>
    <h2>فهرست کارها (WBS) با ترتیب اجرا</h2>
    <table>
      <tr><th>فاز</th><th>فضا</th><th>شرح کار</th><th>مقدار</th><th>متریال پیشنهادی</th></tr>{_items_rows(brief)}
    </table>
  </section>

  {_assumptions_section(brief)}

  <footer>
    <p>{escape(est.uncertainty_note)}</p>
    <p>تهیه‌شده با بنّا — کوپایلوت برنامه‌ریزی بازسازی.</p>
  </footer>
</body>
</html>"""
