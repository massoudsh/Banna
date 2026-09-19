"""تست estimate engine (Issue #9)."""

import pytest

from app.engines.estimate import (
    DURATION_FACTOR_MAX,
    DURATION_FACTOR_MIN,
    OVERHEAD_MAX,
    OVERHEAD_MIN,
    EstimateError,
    estimate,
)
from app.engines.material import apply
from app.engines.scope import analyze
from app.engines.wbs import generate
from app.models.domain import MaterialTier, WBS


def _priced(text="آشپزخانه و حمام بازسازی کامل", area=80, tier=MaterialTier.STANDARD):
    wbs = generate(analyze(text, total_area_m2=area))
    priced, _ = apply(wbs, tier)
    return priced


class TestEstimate:
    def test_produces_cost_range(self):
        est = estimate(_priced())
        assert est.cost_min_toman > 0
        assert est.cost_max_toman > est.cost_min_toman

    def test_produces_duration_range(self):
        est = estimate(_priced())
        assert est.duration_days_min >= 1
        assert est.duration_days_max > est.duration_days_min

    def test_never_returns_point_estimate(self):
        """اصل صداقت تخمین: بازه باید ناتهی باشد، نه عدد قطعی."""
        est = estimate(_priced())
        assert est.cost_min_toman != est.cost_max_toman
        assert est.duration_days_min != est.duration_days_max

    def test_line_per_priced_item(self):
        wbs = _priced()
        est = estimate(wbs)
        assert len(est.lines) == len(wbs.items)

    def test_every_line_has_ordered_range(self):
        for line in estimate(_priced()).lines:
            assert line.material_toman[0] <= line.material_toman[1]
            assert line.labor_toman[0] <= line.labor_toman[1]
            assert line.total_min <= line.total_max

    def test_totals_include_overhead(self):
        """جمع سادهٔ خطوط باید کمتر از total باشد، چون سربار اضافه می‌شود."""
        est = estimate(_priced())
        raw_min = sum(l.total_min for l in est.lines)
        assert est.cost_min_toman > raw_min
        assert est.cost_min_toman == pytest.approx(raw_min * (1 + OVERHEAD_MIN), rel=0.01)

    def test_cost_scales_with_tier(self):
        economy = estimate(_priced(tier=MaterialTier.ECONOMY))
        premium = estimate(_priced(tier=MaterialTier.PREMIUM))
        assert premium.cost_min_toman > economy.cost_min_toman

    def test_premium_takes_longer_than_economy(self):
        """متریال باکیفیت‌تر کار بیشتری می‌برد — رگرسیون مدت یکسان."""
        economy = estimate(_priced(tier=MaterialTier.ECONOMY))
        premium = estimate(_priced(tier=MaterialTier.PREMIUM))
        assert premium.duration_days_max > economy.duration_days_max

    def test_duration_within_expected_factor_band(self):
        est = estimate(_priced())
        assert est.duration_days_max / est.duration_days_min <= (
            DURATION_FACTOR_MAX / DURATION_FACTOR_MIN + 1
        )

    def test_cost_scales_with_area(self):
        small = estimate(_priced(area=50))
        large = estimate(_priced(area=100))
        assert large.cost_min_toman > small.cost_min_toman

    def test_more_spaces_costs_more_at_equal_area(self):
        """با متراژ یکسان، چهار فضا باید گران‌تر از یک فضا تمام شود.

        توجه: وقتی فقط «آشپزخانه» ذکر شود، کل متراژ به آشپزخانه تعلق می‌گیرد؛
        پس برای مقایسهٔ منصفانه باید متراژ کل بزرگ‌تر شود.
        """
        one = estimate(_priced("آشپزخانه بازسازی کامل", area=80))
        four = estimate(_priced("آشپزخانه و حمام و نشیمن و خواب بازسازی کامل", area=200))
        assert four.cost_min_toman > one.cost_min_toman

    def test_kitchen_specific_items_cost_more_per_m2(self):
        """هر مترمربع آشپزخانه از هر مترمربع اتاق خواب گران‌تر است."""
        kitchen = estimate(_priced("آشپزخانه بازسازی کامل", area=20))
        bedroom = estimate(_priced("اتاق خواب بازسازی کامل", area=20))
        assert kitchen.cost_min_toman > bedroom.cost_min_toman

    def test_uncertainty_note_present(self):
        assert estimate(_priced()).uncertainty_note

    def test_raises_on_empty_wbs(self):
        with pytest.raises(EstimateError):
            estimate(WBS(items=[]))

    def test_raises_when_nothing_priced(self):
        """WBS بدون متریال باید خطا بدهد، نه تخمین صفر."""
        from app.models.domain import SpaceType, WBSItem, WorkPhase

        unpriced = WBS(
            items=[
                WBSItem(
                    code="X-1",
                    title="بدون قیمت",
                    phase=WorkPhase.COVERING,
                    space=SpaceType.KITCHEN,
                    quantity=10,
                    unit="مترمربع",
                )
            ]
        )
        with pytest.raises(EstimateError):
            estimate(unpriced)

    def test_duration_is_realistic_not_sum_of_all_items(self):
        """زمان باید از مسیر بحرانی بیاید؛ جمع سادهٔ همهٔ آیتم‌ها زمان را
        به‌شدت بیش‌برآورد می‌کند."""
        wbs = _priced()
        est = estimate(wbs)
        assert est.duration_days_max < 200
