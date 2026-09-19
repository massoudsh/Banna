"""تست scope engine (Issue #6)."""

import pytest

from app.engines.scope import (
    ScopeError,
    analyze,
    analyze_with_vision,
    detect_condition,
    detect_spaces,
    detect_style,
    detect_works,
    parse_budget,
    parse_total_area,
)
from app.models.domain import Condition, MediaAsset, ScopeSummary, SpaceType, WorkPhase


class TestSpaceDetection:
    def test_detects_persian_space_names(self):
        assert detect_spaces("آشپزخانه و حمام") == [SpaceType.KITCHEN, SpaceType.BATHROOM]

    def test_keeps_order_of_appearance(self):
        assert detect_spaces("حمام و آشپزخانه") == [SpaceType.BATHROOM, SpaceType.KITCHEN]

    def test_matches_colloquial_spelling(self):
        assert SpaceType.KITCHEN in detect_spaces("آشپزخونه رو عوض کنم")

    def test_matches_english(self):
        assert SpaceType.BEDROOM in detect_spaces("the bedroom needs work")

    def test_no_match_returns_empty(self):
        assert detect_spaces("سلام") == []


class TestWorkDetection:
    def test_full_renovation_returns_all_phases(self):
        assert detect_works("بازسازی کامل") == list(WorkPhase)

    def test_partial_mention_returns_only_those(self):
        works = detect_works("فقط کاشی و رنگ")
        assert WorkPhase.COVERING in works
        assert WorkPhase.FINISH in works
        assert WorkPhase.DEMOLITION not in works

    def test_default_when_nothing_matched(self):
        assert detect_works("نمی‌دونم") == [WorkPhase.COVERING, WorkPhase.FINISH]

    def test_detects_plumbing_and_electrical(self):
        works = detect_works("لوله‌کشی و برق‌کشی لازمه")
        assert WorkPhase.MEP in works


class TestConditionAndStyle:
    def test_poor_condition(self):
        assert detect_condition("خیلی قدیمی و فرسوده‌ست") is Condition.POOR

    def test_good_condition(self):
        assert detect_condition("تازه نوساز شده") is Condition.GOOD

    def test_default_is_fair(self):
        assert detect_condition("سلام") is Condition.FAIR

    def test_specific_keyword_beats_generic(self):
        # «قدیمی» (POOR) باید بر «معمولی» (FAIR) اولویت داشته باشد.
        assert detect_condition("قدیمی ولی معمولیه") is Condition.POOR

    def test_style_detection(self):
        assert detect_style("سبک مدرن می‌خوام") == "modern"
        assert detect_style("لوکس و مجلل") == "luxury"
        assert detect_style("هیچ ایده‌ای ندارم") == "modern"


class TestParsing:
    @pytest.mark.parametrize(
        "text,expected",
        [
            ("80 متر", 80.0),
            ("75.5 مترمربع", 75.5),
            ("90 m2", 90.0),
            ("120 متر", 120.0),
        ],
    )
    def test_parse_total_area(self, text, expected):
        assert parse_total_area(text) == expected

    @pytest.mark.parametrize("text,expected", [("۸۰ متر", 80.0), ("۹۵ مترمربع", 95.0)])
    def test_parse_persian_digits(self, text, expected):
        """ارقام فارسی باید مثل ارقام لاتین کار کنند — کاربر ایرانی این‌طور می‌نویسد."""
        assert parse_total_area(text) == expected

    def test_area_out_of_domain_rejected(self):
        assert parse_total_area("2000 متر") is None

    @pytest.mark.parametrize(
        "text,expected",
        [
            ("بودجه 500 میلیون", 500_000_000),
            ("بودجه 2 میلیارد تومان", 2_000_000_000),
            ("تا 300 میلیون تومان دارم", 300_000_000),
        ],
    )
    def test_parse_budget(self, text, expected):
        assert parse_budget(text) == expected

    def test_budget_without_unit_is_none(self):
        assert parse_budget("بودجه 500 دارم") is None


class TestAnalyze:
    def test_raises_without_any_input(self):
        with pytest.raises(ScopeError):
            analyze("")

    def test_mentioned_spaces_only(self):
        scope = analyze("آشپزخانه و حمام قدیمی بازسازی کامل", total_area_m2=80)
        assert len(scope.spaces) == 2

    def test_kitchen_area_is_realistic(self):
        """رگرسیون: آشپزخانه نباید بیشتر متراژ کل بگیرد."""
        scope = analyze("آشپزخانه و حمام بازسازی کامل", total_area_m2=80)
        kitchen = next(s for s in scope.spaces if s.space == SpaceType.KITCHEN)
        assert kitchen.area_m2 < 80 * 0.5

    def test_areas_never_exceed_total(self):
        scope = analyze("آشپزخانه بازسازی کامل", total_area_m2=80)
        assert scope.total_area_m2 <= 80

    def test_all_spaces_when_none_named(self):
        scope = analyze("می‌خوام خونه رو مدرن کنم", total_area_m2=80)
        assert len(scope.spaces) == 4
        assert abs(scope.total_area_m2 - 80) < 0.1

    def test_default_area_assumption_recorded(self):
        scope = analyze("آشپزخانه بازسازی کامل")
        assert any("۷۵" in a for a in scope.assumptions)

    def test_confidence_lower_for_unmentioned_spaces(self):
        scope = analyze("آشپزخانه بازسازی کامل", total_area_m2=80)
        kitchen = next(s for s in scope.spaces if s.space == SpaceType.KITCHEN)
        assert kitchen.confidence == 0.75

    def test_budget_extracted(self):
        scope = analyze("آشپزخانه، بودجه 400 میلیون تومان", total_area_m2=80)
        assert scope.budget_toman == 400_000_000


class _FakeAnalyzer:
    def observe(self, assets, text):
        return ScopeSummary(spaces=[], style="fake")


class _BrokenAnalyzer:
    def observe(self, assets, text):
        raise RuntimeError("vision API down")


def _asset() -> MediaAsset:
    return MediaAsset(
        filename="a.jpg", content_type="image/jpeg", size_bytes=100, stored_path="/tmp/a.jpg"
    )


class TestVisionFallback:
    def test_uses_analyzer_when_provided(self):
        result = analyze_with_vision([_asset()], "آشپزخانه", analyzer=_FakeAnalyzer())
        assert result.style == "fake"

    def test_falls_back_on_analyzer_failure(self):
        result = analyze_with_vision(
            [_asset()], "آشپزخانه بازسازی کامل", analyzer=_BrokenAnalyzer(), total_area_m2=80
        )
        assert result.spaces
        assert any("تحلیل بصری ناموفق" in a for a in result.assumptions)

    def test_notes_when_no_analyzer(self):
        result = analyze_with_vision([_asset()], "آشپزخانه بازسازی کامل", total_area_m2=80)
        assert any("تحلیل بصری غیرفعال" in a for a in result.assumptions)
