"""تحلیل دادهٔ اعتبارسنجی و تست پذیرش — Issues #1 و #13.

این ماژول **تحلیل** می‌کند، نه جمع‌آوری. ورودی می‌تواند مصاحبهٔ واقعی یا دیتاست
ساختگی باشد؛ تشخیص این دو کار `is_synthetic()` است و در گزارش صریح اعلام می‌شود.
"""

from __future__ import annotations

import json
import statistics
from dataclasses import dataclass, field
from pathlib import Path

from app.pipeline import run

INTERVIEWS_PATH = Path(__file__).resolve().parent.parent / "data" / "mock" / "interviews.json"
QUOTES_PATH = Path(__file__).resolve().parent.parent / "data" / "mock" / "quotes.json"

# آستانه‌های قفل‌شده در docs/specs/mvp-scope-lock.md
THRESHOLD_MEDIAN_ERROR = 25.0
THRESHOLD_WORST_ERROR = 50.0
THRESHOLD_RANGE_COVERAGE = 60.0
THRESHOLD_QUALITATIVE_PCT = 70.0
THRESHOLD_QUOTE_SPREAD = 30.0
THRESHOLD_MAX_QUOTE_SPREAD_CLAIM = 20.0
THRESHOLD_QUALITATIVE_MEAN = 3.5
THRESHOLD_QUALITATIVE_Q1 = 4.0
THRESHOLD_CONTRACTOR_NO_QUESTIONS = 80.0

HYPOTHESES = {
    "H1": "scope مبهم منبع اصلی اختلاف است",
    "H2": "قیمت‌ها برای کار یکسان غیرقابل‌مقایسه‌اند",
    "H3": "تغییر وسط کار شایع و گران است",
    "H4": "مجری وقت زیادی صرف فهم scope می‌کند",
    "H5": "کارفرما حاضر به پرداخت است",
}
HYPOTHESIS_MIN_MENTIONS = 3
# H5 با شمارش نقل‌قول سنجیده نمی‌شود؛ معیارش پاسخ مثبت به سؤال ۱۰ پرسش‌نامه است.
WILLINGNESS_CONFIRM_PCT = 50.0
MAX_QUOTES_PER_HYPOTHESIS = 3


class ValidationError(Exception):
    pass


def load_json(path: Path) -> dict:
    if not path.exists():
        raise ValidationError(f"فایل داده پیدا نشد: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def is_synthetic(data: dict) -> bool:
    return bool(data.get("synthetic"))


# ---------------------------------------------------------------- مصاحبه‌ها


@dataclass
class HypothesisResult:
    code: str
    statement: str
    mentions: int
    verdict: str  # تایید شد / رد شد / تایید نشد


@dataclass
class InterviewAnalysis:
    total: int
    employers: int
    contractors: int
    hypotheses: list[HypothesisResult] = field(default_factory=list)
    willing_yes: int = 0
    willing_total: int = 0
    willingness_pct: float = 0.0
    willingness_median_toman: int | None = None
    quotes_by_hypothesis: dict[str, list[str]] = field(default_factory=dict)
    synthetic: bool = True


def analyze_interviews(data: dict) -> InterviewAnalysis:
    interviews = data.get("interviews", [])
    if not interviews:
        raise ValidationError("دیتاست مصاحبه خالی است.")

    mentions = {code: 0 for code in HYPOTHESES}
    by_topic: dict[str, list[str]] = {code: [] for code in HYPOTHESES}
    for item in interviews:
        for q in item.get("quotes", []):
            text = q.get("quote", "")
            for topic in q.get("topics", []):
                if topic not in mentions:
                    continue
                mentions[topic] += 1
                if text and len(by_topic[topic]) < MAX_QUOTES_PER_HYPOTHESIS:
                    by_topic[topic].append(text)

    employers = [i for i in interviews if i.get("role") == "employer"]
    contractors = [i for i in interviews if i.get("role") == "contractor"]

    willing = [i for i in employers if i.get("answered_concept_payment") == "yes"]
    amounts = sorted(
        i["willing_to_pay_toman"] for i in willing if i.get("willing_to_pay_toman")
    )
    willingness_pct = round(len(willing) / len(employers) * 100, 1) if employers else 0.0

    hypotheses = [
        HypothesisResult(
            code=code,
            statement=HYPOTHESES[code],
            mentions=mentions[code],
            verdict=_verdict(code, mentions[code], willingness_pct),
        )
        for code in HYPOTHESES
    ]

    return InterviewAnalysis(
        total=len(interviews),
        employers=len(employers),
        contractors=len(contractors),
        hypotheses=hypotheses,
        willing_yes=len(willing),
        willing_total=len(employers),
        willingness_pct=willingness_pct,
        willingness_median_toman=(
            int(statistics.median(amounts)) if amounts else None
        ),
        quotes_by_hypothesis=by_topic,
        synthetic=is_synthetic(data),
    )


def _verdict(code: str, mentions: int, willingness_pct: float) -> str:
    if code == "H5":
        return "تایید شد" if willingness_pct >= WILLINGNESS_CONFIRM_PCT else "رد شد"
    return "تایید شد" if mentions >= HYPOTHESIS_MIN_MENTIONS else "تایید نشد"


def render_validation_report(analysis: InterviewAnalysis) -> str:
    src = (
        "دیتاست **ساختگی (synthetic)** — سناریوهای محتمل، نه مصاحبهٔ واقعی"
        if analysis.synthetic
        else "دادهٔ میدانی واقعی"
    )
    lines = [
        "# گزارش اعتبارسنجی مسئله (Issue #1)",
        "",
        f"> منبع داده: {src}",
        "",
        "## ۱. نمونه",
        "",
        f"- مجموع: **{analysis.total}** مصاحبه",
        f"- کارفرما: **{analysis.employers}** · مجری: **{analysis.contractors}**",
        "",
        "## ۲. وضعیت فرضیه‌ها",
        "",
        "| فرضیه | گزاره | تکرار | حکم |",
        "|---|---|---|---|",
    ]
    for h in analysis.hypotheses:
        mentions = h.mentions if h.code != "H5" else f"{analysis.willingness_pct}% مثبت"
        lines.append(f"| {h.code} | {h.statement} | {mentions} | {h.verdict} |")

    unknown = [h.code for h in analysis.hypotheses if h.verdict == "تایید نشد"]
    rejected = [h.code for h in analysis.hypotheses if h.verdict == "رد شد"]
    confirmed = [h.code for h in analysis.hypotheses if h.verdict == "تایید شد"]
    lines += [
        "",
        f"**حکم کلی:** {len(confirmed)} تایید شد"
        + (f" · {len(rejected)} رد شد ({'، '.join(rejected)})" if rejected else "")
        + (f" · {len(unknown)} تایید نشد ({'، '.join(unknown)})" if unknown else ""),
        "",
        f"> H1–H4 با شمارش نقل‌قول (آستانه {HYPOTHESIS_MIN_MENTIONS} تکرار) سنجیده می‌شوند؛",
        f"> H5 با نرخ پاسخ مثبت به سؤال ۱۰ پرسش‌نامه (آستانه {WILLINGNESS_CONFIRM_PCT:.0f}%).",
        "",
        "## ۳. تمایل به پرداخت (کارفرما)",
        "",
        f"- پاسخ مثبت: **{analysis.willing_yes}** از {analysis.willing_total} "
        f"({analysis.willingness_pct}%)",
    ]
    if analysis.willingness_median_toman:
        lines.append(
            f"- میانهٔ مبلغ اعلامی: **{analysis.willingness_median_toman:,} تومان**"
        )
    else:
        lines.append("- میانهٔ مبلغ اعلامی: دادهٔ کافی نبود")

    lines += ["", "## ۴. نقل‌قول‌های مستقیم به تفکیک موضوع", ""]
    for code, quotes in analysis.quotes_by_hypothesis.items():
        if not quotes:
            continue
        lines.append(f"**{code} — {HYPOTHESES[code]}**")
        lines += [f"- «{q}»" for q in quotes]
        lines.append("")

    lines += [
        "",
        "## ۵. محدودیت‌ها",
        "",
        "- این گزارش با دادهٔ ساختگی تولید شده است. تایید/رد فرضیه‌ها **اعتبار",
        "  میدانی ندارد** و فقط نشان می‌دهد ابزار تحلیل و مسیر رسیدن به حکم درست",
        "  کار می‌کند. مصاحبهٔ واقعی (۲۰ مورد) کار انسان است.",
        "- فرضیهٔ ردشده (اگر وجود داشته باشد) یعنی بازنگری محصول، نه نادیده‌گرفتن آن.",
        f"- برای «تایید شد» حداقل {HYPOTHESIS_MIN_MENTIONS} تکرار لازم است (وفق `docs/specs/validation-interviews.md`).",
        "",
    ]
    return "\n".join(lines)


# ------------------------------------------------------------ تست پذیرش


@dataclass
class ProjectResult:
    project_id: str
    area_m2: float
    spaces: list[str]
    scenario: str
    estimate_min: int
    estimate_max: int
    quotes: list[int]
    quote_median: float
    error_pct: float
    in_range_count: int
    spread_pct: float
    valid_for_error: bool
    qualitative_ok: bool


@dataclass
class AcceptanceAnalysis:
    projects: list[ProjectResult] = field(default_factory=list)
    median_error: float = 0.0
    worst_error: float = 0.0
    range_coverage_pct: float = 0.0
    qualitative_pct: float = 0.0
    qualitative_mean: float = 0.0
    contractor_no_questions_pct: float = 0.0
    passed: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    decision: str = ""
    synthetic: bool = True
    max_quote_spread: float = 0.0

    @property
    def criteria_met(self) -> int:
        return len(self.passed)


def analyze_acceptance(data: dict) -> AcceptanceAnalysis:
    projects = data.get("projects", [])
    if not projects:
        raise ValidationError("دیتاست تست پذیرش خالی است.")

    results: list[ProjectResult] = []
    for p in projects:
        result = run(
            description=p["description"],
            total_area_m2=p["area_m2"],
            tier=_tier_for(p),
        )
        scenario = next(s for s in result.scenarios if s.kind == result.selected)
        est = scenario.estimate
        mid = (est.cost_min_toman + est.cost_max_toman) / 2
        quotes = sorted(p["quotes_toman"])
        quote_median = statistics.median(quotes)
        spread = (
            (quotes[-1] - quotes[0]) / quote_median * 100 if len(quotes) > 1 else 0.0
        )
        in_range = sum(1 for q in quotes if est.cost_min_toman <= q <= est.cost_max_toman)

        results.append(
            ProjectResult(
                project_id=p["id"],
                area_m2=p["area_m2"],
                spaces=[s.space.value for s in result.scope.spaces],
                scenario=scenario.label_fa,
                estimate_min=est.cost_min_toman,
                estimate_max=est.cost_max_toman,
                quotes=quotes,
                quote_median=quote_median,
                error_pct=abs(mid - quote_median) / quote_median * 100,
                in_range_count=in_range,
                spread_pct=spread,
                valid_for_error=spread <= THRESHOLD_QUOTE_SPREAD,
                qualitative_ok=bool(p.get("qualitative_ok", False)),
            )
        )

    return _summarize(results, data)


def _tier_for(project: dict):
    from app.models.domain import MaterialTier

    return MaterialTier(project.get("tier", "standard"))


def _summarize(results: list[ProjectResult], data: dict) -> AcceptanceAnalysis:
    valid = [r for r in results if r.valid_for_error]
    errors = [r.error_pct for r in valid] or [r.error_pct for r in results]

    total_quotes = sum(len(r.quotes) for r in results)
    in_range = sum(r.in_range_count for r in results)
    coverage = in_range / total_quotes * 100 if total_quotes else 0.0
    qual_ok = sum(1 for r in results if r.qualitative_ok)
    qual_pct = qual_ok / len(results) * 100

    qualitative = data.get("qualitative", {})
    q_scores = qualitative.get("employer_scores", [])
    q_means = [statistics.mean(s["scores"]) for s in q_scores if s.get("scores")]
    qual_mean = statistics.mean(q_means) if q_means else 0.0

    contractor = data.get("contractor_feedback", [])
    no_questions = sum(1 for c in contractor if not c.get("asked_extra_questions"))
    no_q_pct = no_questions / len(contractor) * 100 if contractor else 0.0

    median_error = statistics.median(errors) if errors else 0.0
    worst_error = max(errors) if errors else 0.0

    passed, failed = [], []
    checks = [
        ("میانهٔ خطا ≤ ۲۵٪", median_error <= THRESHOLD_MEDIAN_ERROR, f"{median_error:.1f}%"),
        ("بدترین مورد ≤ ۵۰٪", worst_error <= THRESHOLD_WORST_ERROR, f"{worst_error:.1f}%"),
        (
            "پوشش بازه ≥ ۶۰٪",
            coverage >= THRESHOLD_RANGE_COVERAGE,
            f"{coverage:.1f}%",
        ),
        (
            "کیفی «درست و قابل‌فهم» ≥ ۷۰٪",
            qual_pct >= THRESHOLD_QUALITATIVE_PCT,
            f"{qual_pct:.1f}%",
        ),
    ]
    for label, ok, value in checks:
        (passed if ok else failed).append(f"{label} — {value}")

    if len(passed) >= 3:
        decision = "ورود به فاز ۲ (Issues #14 و #15) مجاز است."
    elif median_error > 40:
        decision = "بازگشت به کالیبراسیون دیتاست قیمت (Issue #2) پیش از فاز ۲."
    else:
        decision = "کالیبراسیون تکمیلی لازم است؛ فاز ۲ فعال نمی‌شود."

    return AcceptanceAnalysis(
        projects=results,
        median_error=median_error,
        worst_error=worst_error,
        range_coverage_pct=coverage,
        qualitative_pct=qual_pct,
        qualitative_mean=qual_mean,
        contractor_no_questions_pct=no_q_pct,
        passed=passed,
        failed=failed,
        decision=decision,
        synthetic=is_synthetic(data),
        max_quote_spread=max((r.spread_pct for r in results), default=0.0),
    )


def render_acceptance_report(a: AcceptanceAnalysis) -> str:
    src = (
        "**دادهٔ ساختگی (synthetic)** — quoteها ساخته‌شده‌اند، نه گردآوری‌شده از بازار"
        if a.synthetic
        else "دادهٔ میدانی واقعی"
    )
    lines = [
        "# گزارش تست پذیرش MVP (Issue #13)",
        "",
        f"> منبع داده: {src}",
        "> معیارها طبق `docs/specs/mvp-scope-lock.md` — تخمین = میانهٔ بازهٔ سناریوی انتخابی.",
        "",
        "## ۱. نتیجهٔ هر پروژه",
        "",
        "| پروژه | متراژ | فضاها | سناریو | تخمین (میلیون) | quoteها (میلیون) | خطا٪ | داخل بازه | پراکندگی quote |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in a.projects:
        quotes = " / ".join(f"{q/1e6:,.0f}" for q in r.quotes)
        est = f"{(r.estimate_min+r.estimate_max)/2e6:,.0f} ({r.estimate_min/1e6:,.0f}–{r.estimate_max/1e6:,.0f})"
        space_labels = ", ".join(_SPACE_FA.get(s, s) for s in r.spaces)
        mark = "" if r.valid_for_error else " ⚠️ نامعتبر برای خطا"
        lines.append(
            f"| {r.project_id} | {r.area_m2:g} | {space_labels} | {r.scenario} | {est} | "
            f"{quotes} | {r.error_pct:.1f}{mark} | {r.in_range_count}/{len(r.quotes)} | {r.spread_pct:.1f}% |"
        )

    lines += [
        "",
        f"> پروژه‌ای که پراکندگی quoteهایش از {THRESHOLD_QUOTE_SPREAD:.0f}% بیشتر باشد برای سنجش خطا نامعتبر است (مبنا بی‌ثبات) ولی برای سنجش کیفی معتبر می‌ماند.",
        "",
        "## ۲. معیارهای عددی",
        "",
        "| معیار | آستانه | نتیجه | وضعیت |",
        "|---|---|---|---|",
        f"| میانهٔ خطا | ≤ {THRESHOLD_MEDIAN_ERROR:.0f}% | {a.median_error:.1f}% | {'✅' if a.median_error <= THRESHOLD_MEDIAN_ERROR else '❌'} |",
        f"| بدترین مورد | ≤ {THRESHOLD_WORST_ERROR:.0f}% | {a.worst_error:.1f}% | {'✅' if a.worst_error <= THRESHOLD_WORST_ERROR else '❌'} |",
        f"| نرخ پوشش بازه | ≥ {THRESHOLD_RANGE_COVERAGE:.0f}% | {a.range_coverage_pct:.1f}% | {'✅' if a.range_coverage_pct >= THRESHOLD_RANGE_COVERAGE else '❌'} |",
        f"| کیفی «درست و قابل‌فهم» | ≥ {THRESHOLD_QUALITATIVE_PCT:.0f}% | {a.qualitative_pct:.1f}% | {'✅' if a.qualitative_pct >= THRESHOLD_QUALITATIVE_PCT else '❌'} |",
        "",
        "## ۳. پرسش‌نامهٔ کیفی کارفرما",
        "",
        f"- میانگین نمرات (سؤالات ۱–۶): **{a.qualitative_mean:.2f}** از ۵ "
        f"(آستانه {THRESHOLD_QUALITATIVE_MEAN})",
        "",
        "## ۴. کیفیت Brief از دید مجری",
        "",
        f"- مجریانی که سؤال اضافه نپرسیدند: **{a.contractor_no_questions_pct:.0f}%** "
        f"(آستانه {THRESHOLD_CONTRACTOR_NO_QUESTIONS:.0f}%)",
        "",
        "## ۵. نقاط ضعف مشاهده‌شده",
        "",
    ]
    weak = [r for r in a.projects if r.error_pct > THRESHOLD_MEDIAN_ERROR]
    if weak:
        for r in weak:
            lines.append(
                f"- **{r.project_id}** خطای {r.error_pct:.1f}% — "
                f"{'پروژهٔ تک‌فضا؛ کل متراژ واحد به همان فضا نسبت داده می‌شود' if len(r.spaces) == 1 else 'انحراف چندفضایی'}."
            )
        lines.append(
            "- الگو: در پروژهٔ تک‌فضا، نبودِ متراژ اختصاصیِ همان فضا بزرگ‌ترین منبع"
        )
        lines.append(
            "  خطاست. اصلاح پیشنهادی: گرفتن متراژ هر فضا به‌صورت جداگانه در فرم ورودی."
        )
    else:
        lines.append("- پروژه‌ای با خطای بالاتر از آستانهٔ میانه مشاهده نشد.")

    lines += [
        "",
        "## ۶. تصمیم",
        "",
        f"- معیارهای پاس‌شده: **{a.criteria_met} از ۴**",
    ]
    if a.failed:
        lines += ["- معیارهای ردشده: " + " · ".join(a.failed)]
    lines += [
        "",
        f"**{a.decision}**",
        "",
        "## ۷. محدودیت‌های این اجرا",
        "",
        "- quoteها ساختگی‌اند و از هیچ مجری واقعی گرفته نشده‌اند. پس این گزارش",
        "  **تصمیم ورود به فاز ۲ را مستند نمی‌کند**؛ فقط مسیر محاسبه و آستانه‌ها را",
        "  قفل می‌کند. اجرای میدانی (۱۰ پروژه + ۲ مجری هر پروژه) کار انسان است.",
        "- بزرگ‌ترین پراکندگی quote در نمونه: "
        f"**{a.max_quote_spread:.1f}%** (آستانهٔ اعتبارسنجی خطا {THRESHOLD_QUOTE_SPREAD:.0f}%).",
        "",
    ]
    return "\n".join(lines)


_SPACE_FA = {
    "kitchen": "آشپزخانه",
    "bathroom": "حمام/سرویس",
    "living_room": "نشیمن",
    "bedroom": "اتاق خواب",
}


def main(argv: list[str] | None = None) -> int:
    """تولید هر دو گزارش در outputs/ — `python -m app.validation`."""
    import argparse

    parser = argparse.ArgumentParser(description="تولید گزارش اعتبارسنجی و تست پذیرش")
    parser.add_argument("--interviews", type=Path, default=INTERVIEWS_PATH)
    parser.add_argument("--quotes", type=Path, default=QUOTES_PATH)
    parser.add_argument("--out", type=Path, default=Path("outputs"))
    args = parser.parse_args(argv)

    args.out.mkdir(parents=True, exist_ok=True)

    interviews = render_validation_report(analyze_interviews(load_json(args.interviews)))
    (args.out / "validation-report.md").write_text(interviews, encoding="utf-8")

    acceptance = analyze_acceptance(load_json(args.quotes))
    (args.out / "acceptance-report.md").write_text(
        render_acceptance_report(acceptance), encoding="utf-8"
    )

    print(f"گزارش‌ها در {args.out} نوشته شدند.")
    print(f"معیارهای پاس‌شده: {acceptance.criteria_met} از ۴ — {acceptance.decision}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
