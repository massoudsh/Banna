"""تست quote normalization engine (Issue #15)."""

import pytest

from app.engines import quote as quote_engine
from app.engines.quote import (
    MIN_COVERAGE_PCT,
    QuoteError,
    UNSTABLE_SPREAD_PCT,
    baseline_for,
    compare,
    normalize,
)
from app.models.domain import ContractorQuote, QuoteLine, ScenarioKind
from app.pipeline import run


def _project(text="آشپزخانه و حمام بازسازی کامل", area=80):
    """یک اجرای واقعی pipeline — تست روی داده ساختگی موتور نیست."""
    result = run(description=text, total_area_m2=area)
    baseline = baseline_for(result.scenarios, result.selected)
    return result, baseline


def _line_for(baseline, code, multiplier=1.0):
    cl = next(line for line in baseline.estimate.lines if line.wbs_code == code)
    mid = (cl.total_min + cl.total_max) / 2
    return QuoteLine(code=code, price_toman=int(mid * multiplier))


def _full_quote(baseline, wbs, contractor_id, multiplier=1.0):
    return ContractorQuote(
        contractor_id=contractor_id,
        contractor_name=f"مجری {contractor_id}",
        lines=[_line_for(baseline, item.code, multiplier) for item in wbs.ordered()],
    )


class TestNormalize:
    def test_complete_itemized_quote_is_comparable(self):
        result, baseline = _project()
        n = normalize(_full_quote(baseline, result.wbs, "C1"), result.wbs, baseline)
        assert n.is_comparable
        assert n.itemized
        assert n.coverage_pct == 100
        assert n.missing_codes == []

    def test_incomplete_quote_is_not_comparable(self):
        """رگرسیون: جمع کمتر نباید مجری را بی‌دلیل ارزان نشان دهد."""
        result, baseline = _project()
        partial = ContractorQuote(
            contractor_id="P",
            lines=[_line_for(baseline, i.code) for i in result.wbs.ordered()[:5]],
        )
        n = normalize(partial, result.wbs, baseline)

        assert not n.is_comparable
        assert len(n.missing_codes) == len(result.wbs.items) - 5
        assert n.coverage_pct < MIN_COVERAGE_PCT
        assert any("قابل‌مقایسه نیست" in note for note in n.notes)

    def test_unknown_code_is_reported_not_dropped(self):
        result, baseline = _project()
        quote = _full_quote(baseline, result.wbs, "U")
        quote.lines.append(QuoteLine(code="XXX-YYY", price_toman=1000))

        n = normalize(quote, result.wbs, baseline)
        assert n.unknown_codes == ["XXX-YYY"]
        assert not n.is_comparable

    def test_duplicate_code_keeps_first_price(self):
        result, baseline = _project()
        quote = _full_quote(baseline, result.wbs, "D")
        first = result.wbs.ordered()[0].code
        quote.lines.append(_line_for(baseline, first, 3.0))

        n = normalize(quote, result.wbs, baseline)
        assert n.duplicate_codes == [first]
        assert not n.is_comparable

    def test_lump_sum_quote_is_flagged(self):
        result, baseline = _project()
        lump = ContractorQuote(contractor_id="L", total_toman=600_000_000)
        n = normalize(lump, result.wbs, baseline)

        assert not n.itemized
        assert not n.is_comparable
        assert n.total_toman == 600_000_000
        assert any("مبلغ کل" in note for note in n.notes)

    def test_lowercase_codes_match(self):
        """ تطبیق کد باید نسبت به بزرگی/کوچکی حروف بی‌تفاوت باشد."""
        result, baseline = _project()
        quote = ContractorQuote(
            contractor_id="LC",
            lines=[
                _line_for(baseline, i.code).model_copy(update={"code": i.code.lower()})
                for i in result.wbs.ordered()
            ],
        )
        n = normalize(quote, result.wbs, baseline)
        assert n.is_comparable

    def test_deviation_sign_is_positive_when_pricier(self):
        result, baseline = _project()
        cheap = normalize(_full_quote(baseline, result.wbs, "A", 0.8), result.wbs, baseline)
        pricey = normalize(_full_quote(baseline, result.wbs, "B", 1.2), result.wbs, baseline)

        assert cheap.deviation_pct < 0
        assert pricey.deviation_pct > 0

    def test_prices_inside_estimate_range_are_flagged(self):
        result, baseline = _project()
        n = normalize(_full_quote(baseline, result.wbs, "C"), result.wbs, baseline)
        assert any(line.within_estimate_range for line in n.lines)

    def test_line_estimate_comes_from_the_baseline_scenario(self):
        result, baseline = _project()
        n = normalize(_full_quote(baseline, result.wbs, "C"), result.wbs, baseline)
        for line in n.lines:
            source = next(
                l for l in baseline.estimate.lines if l.wbs_code == line.code
            )
            assert line.estimate_min_toman == source.total_min
            assert line.estimate_max_toman == source.total_max

    def test_every_wbs_item_appears_once_across_lines_and_missing(self):
        result, baseline = _project()
        n = normalize(_full_quote(baseline, result.wbs, "C"), result.wbs, baseline)
        assert len(n.lines) + len(n.missing_codes) == len(result.wbs.items)

    def test_empty_wbs_raises(self):
        from app.models.domain import WBS

        _, baseline = _project()
        with pytest.raises(QuoteError):
            normalize(ContractorQuote(contractor_id="X"), WBS(items=[]), baseline)


class TestCompare:
    def test_ranks_cheapest_and_highest(self):
        result, baseline = _project()
        comparison = compare(
            [
                _full_quote(baseline, result.wbs, "A", 0.9),
                _full_quote(baseline, result.wbs, "B", 1.0),
                _full_quote(baseline, result.wbs, "C", 1.15),
            ],
            result.wbs,
            baseline,
        )
        assert comparison.cheapest_comparable_id == "A"
        assert comparison.highest_comparable_id == "C"

    def test_incomplete_quotes_are_excluded_from_ranking(self):
        """مجری با quote ناقص نباید «ارزان‌ترین» شود."""
        result, baseline = _project()
        partial = ContractorQuote(
            contractor_id="CHEAP-BUT-PARTIAL",
            lines=[QuoteLine(code=result.wbs.ordered()[0].code, price_toman=1)],
        )
        comparison = compare(
            [_full_quote(baseline, result.wbs, "REAL", 1.0), partial],
            result.wbs,
            baseline,
        )
        assert comparison.cheapest_comparable_id == "REAL"

    def test_spread_uses_comparable_quotes_only(self):
        result, baseline = _project()
        comparison = compare(
            [
                _full_quote(baseline, result.wbs, "A", 0.9),
                _full_quote(baseline, result.wbs, "B", 1.0),
                ContractorQuote(contractor_id="P", lines=[]),
            ],
            result.wbs,
            baseline,
        )
        assert comparison.spread_pct > 0
        assert comparison.spread_is_stable

    def test_wide_spread_is_flagged_unstable(self):
        result, baseline = _project()
        comparison = compare(
            [
                _full_quote(baseline, result.wbs, "X", 0.6),
                _full_quote(baseline, result.wbs, "Y", 1.4),
            ],
            result.wbs,
            baseline,
        )
        assert comparison.spread_pct > UNSTABLE_SPREAD_PCT
        assert not comparison.spread_is_stable

    def test_baseline_matches_the_selected_scenario(self):
        result, baseline = _project()
        comparison = compare(
            [_full_quote(baseline, result.wbs, "A")], result.wbs, baseline
        )
        assert comparison.baseline_kind == result.selected
        assert comparison.baseline_min_toman == baseline.estimate.cost_min_toman
        assert comparison.baseline_max_toman == baseline.estimate.cost_max_toman

    def test_all_quotes_are_returned_even_uncomparable(self):
        result, baseline = _project()
        comparison = compare(
            [
                _full_quote(baseline, result.wbs, "A"),
                ContractorQuote(contractor_id="BAD", lines=[]),
            ],
            result.wbs,
            baseline,
        )
        assert {q.contractor_id for q in comparison.quotes} == {"A", "BAD"}

    def test_empty_quote_list_raises(self):
        result, baseline = _project()
        with pytest.raises(QuoteError):
            compare([], result.wbs, baseline)


class TestBaselineFor:
    def test_finds_each_scenario_kind(self):
        result, _ = _project()
        for kind in ScenarioKind:
            assert baseline_for(result.scenarios, kind).kind == kind

    def test_missing_kind_raises(self):
        with pytest.raises(QuoteError):
            baseline_for([], ScenarioKind.STANDARD)


class TestContractCoverage:
    def test_threshold_constants_match_the_acceptance_spec(self):
        assert UNSTABLE_SPREAD_PCT == 30.0
        assert MIN_COVERAGE_PCT == 80.0
