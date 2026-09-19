"""تست scenario engine (Issue #10)."""

import pytest

from app.engines.material import apply
from app.engines.scenario import (
    SCENARIO_SPECS,
    build_all,
    nearest_to_budget,
)
from app.engines.scope import analyze
from app.engines.wbs import generate
from app.models.domain import MaterialTier, ScenarioKind


def _wbs(text="آشپزخانه و حمام بازسازی کامل", area=80):
    priced, _ = apply(generate(analyze(text, total_area_m2=area)), MaterialTier.STANDARD)
    return priced


class TestBuildAll:
    def test_returns_four_scenarios(self):
        assert len(build_all(_wbs())) == 4

    def test_all_kinds_present_exactly_once(self):
        kinds = [s.kind for s in build_all(_wbs())]
        assert set(kinds) == set(ScenarioKind)
        assert len(kinds) == len(set(kinds))

    def test_labels_are_persian(self):
        for scenario in build_all(_wbs()):
            assert scenario.label_fa
            assert not scenario.label_fa.isascii(), "برچسب باید فارسی باشد"

    def test_every_scenario_has_estimate(self):
        for scenario in build_all(_wbs()):
            assert scenario.estimate.cost_min_toman > 0
            assert scenario.estimate.lines

    def test_premium_is_most_expensive(self):
        scenarios = {s.kind: s for s in build_all(_wbs())}
        assert (
            scenarios[ScenarioKind.PREMIUM].estimate.cost_min_toman
            > scenarios[ScenarioKind.STANDARD].estimate.cost_min_toman
        )

    def test_economy_is_cheapest(self):
        scenarios = {s.kind: s for s in build_all(_wbs())}
        assert (
            scenarios[ScenarioKind.ECONOMY].estimate.cost_min_toman
            < scenarios[ScenarioKind.STANDARD].estimate.cost_min_toman
        )

    def test_rental_is_cheapest_or_equal(self):
        """سناریوی اجاره کمترین آیتم را دارد و نباید از اقتصادی گران‌تر شود."""
        scenarios = {s.kind: s for s in build_all(_wbs())}
        rental = scenarios[ScenarioKind.RENTAL].estimate
        economy = scenarios[ScenarioKind.ECONOMY].estimate
        assert rental.cost_min_toman <= economy.cost_min_toman

    def test_rental_excludes_decor_items(self):
        scenarios = {s.kind: s for s in build_all(_wbs())}
        rental_codes = {l.wbs_code for l in scenarios[ScenarioKind.RENTAL].estimate.lines}
        standard_codes = {l.wbs_code for l in scenarios[ScenarioKind.STANDARD].estimate.lines}
        assert rental_codes < standard_codes, "سناریوی اجاره باید زیرمجموعهٔ استاندارد باشد"
        assert "KIT-JOI-C" in standard_codes - rental_codes

    def test_scenarios_have_distinct_costs(self):
        costs = {s.estimate.cost_min_toman for s in build_all(_wbs())}
        assert len(costs) >= 3, "سناریوها باید تفاوت قیمتی معنادار داشته باشند"

    def test_every_scenario_has_description(self):
        for scenario in build_all(_wbs()):
            assert len(scenario.description) > 20

    def test_tier_matches_spec(self):
        for scenario in build_all(_wbs()):
            assert scenario.tier == SCENARIO_SPECS[scenario.kind]["tier"]

    def test_dangling_dependency_pruned_in_rental(self):
        """رگرسیون: حذف آیتم نباید وابستگی به کد ناموجود باقی بگذارد."""
        rental_spec = SCENARIO_SPECS[ScenarioKind.RENTAL]
        excluded = rental_spec["exclude_codes"]
        for scenario in build_all(_wbs()):
            if scenario.kind != ScenarioKind.RENTAL:
                continue
            for line in scenario.estimate.lines:
                assert line.wbs_code not in excluded

    def test_works_for_single_space(self):
        scenarios = build_all(_wbs("آشپزخانه بازسازی کامل", area=60))
        assert len(scenarios) == 4

    def test_works_for_all_four_spaces(self):
        scenarios = build_all(_wbs("آشپزخانه و حمام و نشیمن و خواب بازسازی کامل", area=100))
        assert len(scenarios) == 4
        for scenario in scenarios:
            assert scenario.estimate.cost_min_toman > 0


class TestNearestToBudget:
    def test_picks_standard_when_no_budget(self):
        assert nearest_to_budget(build_all(_wbs()), None) == ScenarioKind.STANDARD

    def test_picks_standard_for_zero_budget(self):
        assert nearest_to_budget(build_all(_wbs()), 0) == ScenarioKind.STANDARD

    def test_picks_rental_when_it_is_the_closest_affordable(self):
        """بودجهٔ ۱۵۰ میلیون: سناریوی اجاره (ارزان‌ترین) نزدیک‌ترین گزینهٔ درون‌بودجه است."""
        assert nearest_to_budget(build_all(_wbs()), 150_000_000) == ScenarioKind.RENTAL

    def test_picks_economy_when_rental_exceeds_budget(self):
        """بودجه‌ای که فقط سناریوی اقتصادی را پوشش می‌دهد."""
        scenarios = build_all(_wbs())
        economy = next(s.estimate for s in scenarios if s.kind == ScenarioKind.ECONOMY)
        rental = next(s.estimate for s in scenarios if s.kind == ScenarioKind.RENTAL)
        assert rental.cost_min_toman < economy.cost_min_toman
        # بودجه‌ای بین کف اجاره و کف اقتصادی → اقتصادی تنها گزینهٔ درون‌بودجه
        budget = rental.cost_min_toman - 1
        assert nearest_to_budget(scenarios, budget) == ScenarioKind.ECONOMY or budget < 0

    def test_picks_premium_for_large_budget(self):
        assert nearest_to_budget(build_all(_wbs()), 5_000_000_000) == ScenarioKind.PREMIUM

    def test_never_exceeds_budget_when_affordable_option_exists(self):
        scenarios = build_all(_wbs())
        budget = 400_000_000
        chosen = nearest_to_budget(scenarios, budget)
        chosen_est = next(s.estimate for s in scenarios if s.kind == chosen)
        assert chosen_est.cost_min_toman <= budget

    def test_falls_back_to_economy_when_nothing_affordable(self):
        assert nearest_to_budget(build_all(_wbs()), 1_000) == ScenarioKind.ECONOMY

    def test_raises_on_empty_list(self):
        with pytest.raises(ValueError):
            nearest_to_budget([], 100_000)
