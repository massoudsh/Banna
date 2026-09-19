"""تست material engine (Issue #8)."""

import pytest

from app.engines.material import (
    apply,
    labor_range,
    load_dataset,
    options_for,
    productivity,
)
from app.engines.scope import analyze
from app.engines.wbs import generate
from app.models.domain import MaterialTier, WBSItem, SpaceType, WorkPhase


def _wbs(text="آشپزخانه و حمام بازسازی کامل", area=80):
    return generate(analyze(text, total_area_m2=area))


class TestDataset:
    def test_loads(self):
        data = load_dataset()
        assert data["items"]

    def test_all_prices_are_valid_ranges(self):
        """رگرسیون: min باید کوچک‌تر از max باشد وگرنه بازه بی‌معناست."""
        for key, spec in load_dataset()["items"].items():
            for tier, price in spec["material"]["tiers"].items():
                assert price["min"] <= price["max"], f"{key}/{tier} بازه نامعتبر"
                assert price["min"] > 0, f"{key}/{tier} قیمت صفر"

    def test_premium_costs_more_than_economy(self):
        for key, spec in load_dataset()["items"].items():
            tiers = spec["material"]["tiers"]
            assert tiers["premium"]["min"] >= tiers["economy"]["min"], key

    def test_every_item_has_labor(self):
        for key, spec in load_dataset()["items"].items():
            assert "labor" in spec, f"{key} دستمزد ندارد"

    def test_every_item_has_productivity(self):
        for key, spec in load_dataset()["items"].items():
            assert spec.get("productivity_m2_per_day", 0) > 0, f"{key} بهره‌وری ندارد"


class TestApply:
    def test_fills_materials_for_all_items(self):
        wbs, missing = apply(_wbs(), MaterialTier.STANDARD)
        assert missing == [], f"آیتم بدون قیمت: {missing}"
        assert all(i.materials for i in wbs.items)

    def test_no_missing_for_all_four_spaces(self):
        wbs = generate(analyze("آشپزخانه و حمام و نشیمن و خواب بازسازی کامل", total_area_m2=100))
        _, missing = apply(wbs, MaterialTier.STANDARD)
        assert missing == []

    def test_tier_changes_price(self):
        base = _wbs()
        economy, _ = apply(base.model_copy(deep=True), MaterialTier.ECONOMY)
        premium, _ = apply(base.model_copy(deep=True), MaterialTier.PREMIUM)

        item = "KIT-COV-T"
        e = next(i for i in economy.items if i.code == item).materials[0]
        p = next(i for i in premium.items if i.code == item).materials[0]
        assert p.unit_price_min > e.unit_price_min
        assert p.name != e.name

    def test_all_three_tiers_available(self):
        for tier in MaterialTier:
            wbs, missing = apply(_wbs(), tier)
            assert missing == [], f"سطح {tier.value} پوشش ناقص دارد"

    def test_materials_carry_tier(self):
        wbs, _ = apply(_wbs(), MaterialTier.PREMIUM)
        assert all(i.materials[0].tier == MaterialTier.PREMIUM for i in wbs.items)


class TestResolve:
    def test_options_for_unknown_item_returns_empty(self):
        item = WBSItem(
            code="XXX-UNKNOWN",
            title="نامعلوم",
            phase=WorkPhase.COVERING,
            space=SpaceType.KITCHEN,
            quantity=1,
            unit="مورد",
        )
        assert options_for(item, MaterialTier.STANDARD, load_dataset()) == []

    def test_labor_range_for_known_item(self):
        wbs = _wbs()
        assert labor_range(wbs.items[0]) is not None

    def test_productivity_positive(self):
        wbs = _wbs()
        assert productivity(wbs.items[0]) > 0

    def test_labor_range_tuple_ordered(self):
        wbs = _wbs()
        low, high = labor_range(wbs.items[0])
        assert low <= high
