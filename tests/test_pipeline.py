"""تست یکپارچهٔ pipeline کامل — از ورودی خام تا Brief (Issueهای #5 تا #13).

این فایل نقش harness تست پذیرش (Issue #13) را هم دارد: سناریوهای واقعی
بازسازی را از ابتدا تا انتها اجرا می‌کند و ثبات خروجی را می‌سنجد.
"""

import pytest

from app.engines.media import MediaValidationError, validate_request
from app.models.domain import MaterialTier, MediaAsset, ScenarioKind, SpaceType
from app.pipeline import run, run_to_file, render_brief


class TestPipelineEndToEnd:
    def test_full_run_produces_all_stages(self):
        result = run(description="آشپزخانه و حمام قدیمی بازسازی کامل", total_area_m2=80)
        assert result.scope.spaces
        assert result.wbs.items
        assert len(result.scenarios) == 4
        assert result.selected in ScenarioKind

    def test_no_missing_prices_in_happy_path(self):
        """هیچ آیتم WBS نباید بدون قیمت بماند — رگرسیون شکاف دیتاست."""
        result = run(description="آشپزخانه و حمام بازسازی کامل", total_area_m2=80)
        assert result.missing_price_codes == []

    def test_all_four_mvp_spaces(self):
        result = run(
            description="آشپزخانه و حمام و نشیمن و خواب بازسازی کامل", total_area_m2=100
        )
        assert len({s.space for s in result.scope.spaces}) == 4
        assert result.missing_price_codes == []

    def test_every_wbs_item_is_priced_and_materialized(self):
        result = run(description="آشپزخانه و حمام بازسازی کامل", total_area_m2=80)
        for item in result.wbs.items:
            assert item.materials, f"{item.code} بدون متریال"
            assert item.quantity > 0

    def test_selection_respects_budget(self):
        result = run(
            description="آشپزخانه بازسازی کامل، بودجه 500 میلیون تومان", total_area_m2=80
        )
        assert result.scope.budget_toman == 500_000_000
        chosen = next(s for s in result.scenarios if s.kind == result.selected)
        assert chosen.estimate.cost_min_toman <= result.scope.budget_toman

    def test_tier_parameter_selects_scenario(self):
        """tier سطح سناریوی پیش‌فرض را تعیین می‌کند (وقتی بودجه‌ای اعلام نشده)."""
        result = run(
            description="آشپزخانه بازسازی کامل",
            total_area_m2=80,
            tier=MaterialTier.PREMIUM,
        )
        assert result.selected == ScenarioKind.PREMIUM

    def test_economy_tier_does_not_return_rental_scenario(self):
        """رگرسیون: RENTAL هم tier اقتصادی دارد؛ تطبیق tier تنها، سناریوی اشتباه می‌دهد."""
        result = run(
            description="آشپزخانه و حمام و نشیمن بازسازی کامل",
            total_area_m2=70,
            tier=MaterialTier.ECONOMY,
        )
        assert result.selected == ScenarioKind.ECONOMY

    def test_every_tier_maps_to_its_own_scenario_kind(self):
        for tier in MaterialTier:
            result = run(
                description="آشپزخانه بازسازی کامل", total_area_m2=80, tier=tier
            )
            assert result.selected.value == tier.value, tier

    def test_budget_overrides_tier(self):
        """بودجه بر سطح درخواستی اولویت دارد."""
        result = run(
            description="آشپزخانه بازسازی کامل، بودجه 150 میلیون تومان",
            total_area_m2=80,
            tier=MaterialTier.PREMIUM,
        )
        assert result.selected == ScenarioKind.RENTAL

    def test_vision_fallback_notes_visible_to_user(self):
        asset = MediaAsset(
            filename="a.jpg",
            content_type="image/jpeg",
            size_bytes=1000,
            stored_path="/tmp/a.jpg",
        )
        result = run(
            description="آشپزخانه بازسازی کامل", total_area_m2=80, assets=[asset]
        )
        assert any("تحلیل بصری" in a for a in result.scope.assumptions)

    def test_to_brief_roundtrip(self):
        result = run(description="آشپزخانه و حمام بازسازی کامل", total_area_m2=80)
        brief = result.to_brief("آپارتمان تست")
        assert brief.selected == result.selected
        assert brief.wbs is result.wbs
        assert brief.scope is result.scope

    def test_render_brief_from_result(self):
        result = run(description="آشپزخانه و حمام بازسازی کامل", total_area_m2=80)
        html = render_brief(result, "آپارتمان تست")
        assert "آپارتمان تست" in html
        assert 'dir="rtl"' in html

    def test_writes_brief_file(self, tmp_path):
        out = tmp_path / "nested" / "brief.html"
        result = run_to_file(
            description="آشپزخانه بازسازی کامل",
            output_path=out,
            title="آپارتمان فایل",
            total_area_m2=80,
        )
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "آپارتمان فایل" in content
        assert result.wbs.items


class TestRealisticScenarios:
    """سناریوهای پذیرش (Issue #13) — سه فضای کلیدی MVP."""

    @pytest.mark.parametrize(
        "description,area,expected_space",
        [
            ("آشپزخانه قدیمی، کابینت و کاشی عوض بشه، بازسازی کامل", 25, SpaceType.KITCHEN),
            ("حمام و سرویس فرسوده، لوله‌کشی و کاشی از نو", 12, SpaceType.BATHROOM),
            ("نشیمن و پذیرایی، رنگ و کفپوش و نورپردازی مدرن", 35, SpaceType.LIVING_ROOM),
        ],
    )
    def test_scenario_produces_plausible_output(self, description, area, expected_space):
        result = run(description=description, total_area_m2=area)
        spaces = {s.space for s in result.scope.spaces}
        assert expected_space in spaces
        assert result.missing_price_codes == []

        selected = next(s for s in result.scenarios if s.kind == result.selected)
        assert selected.estimate.cost_min_toman > 0
        assert selected.estimate.duration_days_min >= 1
        # سقف واقع‌گرایی: بازسازی یک فضای کوچک نباید ماه‌ها طول بکشد
        assert selected.estimate.duration_days_max < 180

    def test_cost_per_m2_in_market_range(self):
        """رگرسیون بازار: هزینهٔ هر مترمربع بازسازی در تهران باید در بازهٔ
        معقول باشد (نه صد میلیون، نه ده میلیون)."""
        result = run(description="آشپزخانه و حمام بازسازی کامل", total_area_m2=45)
        selected = next(s for s in result.scenarios if s.kind == result.selected)
        per_m2_min = selected.estimate.cost_min_toman / 45
        assert 2_000_000 < per_m2_min < 60_000_000, f"هزینهٔ متری غیرواقعی: {per_m2_min:,.0f}"

    def test_deterministic_output(self):
        """همان ورودی باید همان خروجی را بدهد (بدون تصادف)."""
        a = run(description="آشپزخانه و حمام بازسازی کامل", total_area_m2=80)
        b = run(description="آشپزخانه و حمام بازسازی کامل", total_area_m2=80)
        assert a.scope.model_dump() == b.scope.model_dump()
        assert a.selected == b.selected
        assert [s.estimate.cost_min_toman for s in a.scenarios] == [
            s.estimate.cost_min_toman for s in b.scenarios
        ]


class TestInputValidation:
    def test_rejects_zero_area(self):
        with pytest.raises(MediaValidationError):
            validate_request(area_m2=0, media_count=1)

    def test_rejects_empty_description(self):
        from app.engines.scope import ScopeError

        with pytest.raises(ScopeError):
            run(description="", total_area_m2=None)

    def test_accepts_valid_request(self):
        validate_request(area_m2=80, media_count=2)
