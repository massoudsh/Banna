"""تست brief renderer (Issue #11)."""

import pytest

from app.engines.brief import format_toman, render
from app.engines.material import apply
from app.engines.scenario import build_all
from app.engines.scope import analyze
from app.engines.wbs import generate
from app.models.domain import (
    MaterialTier,
    RenovationBrief,
    Scenario,
    ScenarioKind,
    ScopeSummary,
    SpaceType,
    WBS,
)


def _brief(text="آشپزخانه و حمام بازسازی کامل", area=80, title="آپارتمان ۸۰ متری"):
    scope = analyze(text, total_area_m2=area)
    wbs, _ = apply(generate(scope), MaterialTier.STANDARD)
    scenarios = build_all(wbs)
    return RenovationBrief(
        project_title=title,
        scope=scope,
        wbs=wbs,
        scenarios=scenarios,
        selected=ScenarioKind.STANDARD,
    )


class TestFormatToman:
    @pytest.mark.parametrize(
        "amount,expected",
        [
            (450_000_000, "450 میلیون تومان"),
            (1_500_000_000, "1.5 میلیارد تومان"),
            (2_000_000_000, "2 میلیارد تومان"),
            (85_000_000, "85 میلیون تومان"),
        ],
    )
    def test_formats_readably(self, amount, expected):
        assert format_toman(amount) == expected

    def test_billion_has_no_trailing_zeros(self):
        assert "0 میلیارد" not in format_toman(3_000_000_000)


class TestRender:
    def test_returns_html_document(self):
        html = render(_brief())
        assert html.startswith("<!DOCTYPE html>")
        assert "</html>" in html

    def test_is_rtl_persian(self):
        html = render(_brief())
        assert 'dir="rtl"' in html
        assert 'lang="fa"' in html

    def test_contains_project_title(self):
        html = render(_brief(title="آپارتمان ونک"))
        assert "آپارتمان ونک" in html

    def test_contains_cost_range_not_point_estimate(self):
        brief = _brief()
        html = render(brief)
        standard = next(s for s in brief.scenarios if s.kind == ScenarioKind.STANDARD)
        assert format_toman(standard.estimate.cost_min_toman) in html
        assert format_toman(standard.estimate.cost_max_toman) in html

    def test_contains_duration(self):
        brief = _brief()
        standard = next(s for s in brief.scenarios if s.kind == ScenarioKind.STANDARD)
        html = render(brief)
        assert str(standard.estimate.duration_days_min) in html

    def test_lists_all_four_scenarios(self):
        html = render(_brief())
        for label in ("اقتصادی", "استاندارد", "باکیفیت", "مناسب اجاره"):
            assert label in html

    def test_contains_wbs_items(self):
        brief = _brief()
        html = render(brief)
        for item in brief.wbs.items:
            assert item.title in html

    def test_contains_phase_labels(self):
        html = render(_brief())
        for phase in ("تخریب", "تأسیسات", "پوشش کف و دیوار"):
            assert phase in html

    def test_contains_space_labels(self):
        html = render(_brief())
        assert "آشپزخانه" in html and "حمام و سرویس" in html

    def test_budget_shown_when_provided(self):
        brief = _brief(text="آشپزخانه بازسازی کامل، بودجه 500 میلیون تومان", area=80)
        html = render(brief)
        assert "بودجه" in html
        assert "500 میلیون تومان" in html

    def test_budget_absent_handled(self):
        html = render(_brief(text="آشپزخانه بازسازی کامل"))
        assert "ثبت نشده" in html

    def test_in_budget_badge(self):
        brief = _brief(text="آشپزخانه بازسازی کامل، بودجه 5 میلیارد تومان", area=80)
        assert "در بودجه" in render(brief)

    def test_over_budget_badge(self):
        brief = _brief(text="آشپزخانه بازسازی کامل، بودجه 10 میلیون تومان", area=80)
        assert "بالاتر از بودجه" in render(brief)

    def test_assumptions_section_when_present(self):
        brief = _brief(text="آشپزخانه بازسازی کامل")  # متراژ ذکر نشده → فرض ثبت می‌شود
        html = render(brief)
        assert "فرض‌ها و محدودیت‌ها" in html
        assert brief.scope.assumptions

    def test_uncertainty_note_included(self):
        brief = _brief()
        assert brief.scenarios[0].estimate.uncertainty_note in render(brief)

    def test_escapes_html_in_user_title(self):
        """رگرسیون امنیتی: ورودی کاربر نباید HTML تزریق کند."""
        brief = _brief(title='<script>alert("xss")</script>')
        html = render(brief)
        assert "<script>alert" not in html
        assert "&lt;script&gt;" in html

    def test_raises_without_scenarios(self):
        scope = analyze("آشپزخانه بازسازی کامل", total_area_m2=80)
        wbs = generate(scope)
        empty = RenovationBrief(project_title="خالی", scope=scope, wbs=wbs, scenarios=[])
        with pytest.raises(ValueError):
            render(empty)

    def test_falls_back_to_first_scenario_when_selection_missing(self):
        brief = _brief()
        brief.selected = ScenarioKind.RENTAL
        html = render(brief)
        assert "مناسب اجاره" in html

    def test_tables_are_well_formed(self):
        html = render(_brief())
        assert html.count("<table>") == html.count("</table>")
        assert html.count("<tr>") == html.count("</tr>")

    def test_render_is_deterministic(self):
        brief = _brief()
        assert render(brief) == render(brief)
