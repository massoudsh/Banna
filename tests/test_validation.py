"""تست ماژول تحلیل اعتبارسنجی و تست پذیرش (Issues #1 و #13)."""

import json

import pytest

from app.validation import (
    HYPOTHESIS_MIN_MENTIONS,
    INTERVIEWS_PATH,
    QUOTES_PATH,
    THRESHOLD_MEDIAN_ERROR,
    THRESHOLD_QUALITATIVE_PCT,
    THRESHOLD_QUOTE_SPREAD,
    THRESHOLD_RANGE_COVERAGE,
    THRESHOLD_WORST_ERROR,
    ValidationError,
    analyze_acceptance,
    analyze_interviews,
    is_synthetic,
    load_json,
    main,
    render_acceptance_report,
    render_validation_report,
)


@pytest.fixture(scope="module")
def interviews():
    return load_json(INTERVIEWS_PATH)


@pytest.fixture(scope="module")
def quotes():
    return load_json(QUOTES_PATH)


@pytest.fixture(scope="module")
def acceptance(quotes):
    return analyze_acceptance(quotes)


class TestDatasets:
    def test_mock_data_is_labelled_synthetic(self, interviews, quotes):
        """دادهٔ ساختگی باید صریح علامت بخورد تا با دادهٔ میدانی اشتباه نشود."""
        assert is_synthetic(interviews)
        assert is_synthetic(quotes)

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(ValidationError):
            load_json(tmp_path / "nope.json")

    def test_interview_sample_meets_spec_size(self, interviews):
        """سند مصاحبه حداقل ۱۰ کارفرما و ۱۰ مجری می‌خواهد."""
        roles = [i["role"] for i in interviews["interviews"]]
        assert roles.count("employer") >= 10
        assert roles.count("contractor") >= 10

    def test_acceptance_sample_meets_spec_size(self, quotes):
        assert len(quotes["projects"]) >= 10

    def test_every_project_has_at_least_two_quotes(self, quotes):
        """معیار خطا به میانهٔ quoteها وابسته است؛ یک quote مبنا نمی‌سازد."""
        for p in quotes["projects"]:
            assert len(p["quotes_toman"]) >= 2, p["id"]

    def test_all_mvp_spaces_appear_at_least_twice(self, acceptance):
        counts: dict[str, int] = {}
        for r in acceptance.projects:
            for space in r.spaces:
                counts[space] = counts.get(space, 0) + 1
        for space in ("kitchen", "bathroom", "living_room", "bedroom"):
            assert counts.get(space, 0) >= 2, space

    def test_sample_includes_single_space_projects(self, acceptance):
        single = [r for r in acceptance.projects if len(r.spaces) == 1]
        assert len(single) >= 3


class TestInterviewAnalysis:
    def test_counts_roles(self, interviews):
        a = analyze_interviews(interviews)
        assert a.total == a.employers + a.contractors

    def test_all_hypotheses_get_a_verdict(self, interviews):
        a = analyze_interviews(interviews)
        assert {h.code for h in a.hypotheses} == {"H1", "H2", "H3", "H4", "H5"}
        assert all(h.verdict in {"تایید شد", "رد شد", "تایید نشد"} for h in a.hypotheses)

    def test_verdict_follows_mention_threshold(self, interviews):
        a = analyze_interviews(interviews)
        for h in a.hypotheses:
            if h.code == "H5":
                continue
            expected = "تایید شد" if h.mentions >= HYPOTHESIS_MIN_MENTIONS else "تایید نشد"
            assert h.verdict == expected, h.code

    def test_h5_uses_willingness_not_mentions(self):
        """H5 با نرخ پاسخ مثبت سنجیده می‌شود، نه تعداد نقل‌قول."""
        data = {
            "synthetic": True,
            "interviews": [
                {
                    "role": "employer",
                    "answered_concept_payment": "no",
                    "quotes": [{"quote": "الف", "topics": ["H5"]}] * 9,
                }
            ],
        }
        a = analyze_interviews(data)
        h5 = next(h for h in a.hypotheses if h.code == "H5")
        assert h5.mentions == 9
        assert h5.verdict == "رد شد"

    def test_quotes_grouped_by_topic(self, interviews):
        a = analyze_interviews(interviews)
        assert a.quotes_by_hypothesis["H1"]
        assert all(isinstance(q, str) for q in a.quotes_by_hypothesis["H1"])

    def test_willingness_is_a_percentage(self, interviews):
        a = analyze_interviews(interviews)
        assert 0 <= a.willingness_pct <= 100
        assert a.willing_yes <= a.willing_total

    def test_empty_dataset_raises(self):
        with pytest.raises(ValidationError):
            analyze_interviews({"interviews": []})

    def test_report_marks_synthetic_source(self, interviews):
        report = render_validation_report(analyze_interviews(interviews))
        assert "ساختگی" in report
        assert "Issue #1" in report

    def test_report_marks_real_source_when_not_synthetic(self, interviews):
        real = dict(interviews, synthetic=False)
        report = render_validation_report(analyze_interviews(real))
        assert "میدانی واقعی" in report


class TestAcceptanceAnalysis:
    def test_error_is_measured_against_quote_median(self, acceptance):
        for r in acceptance.projects:
            assert r.quote_median > 0
            assert r.error_pct >= 0

    def test_wide_quote_spread_invalidates_error_measurement(self, acceptance):
        """اختلاف بیش از ۳۰٪ بین مجریان یعنی مبنا بی‌ثبات است."""
        for r in acceptance.projects:
            assert r.valid_for_error == (r.spread_pct <= THRESHOLD_QUOTE_SPREAD)

    def test_sample_exercises_the_invalid_path(self, acceptance):
        """اگر هیچ پروژهٔ نامعتبری نباشد، این قاعده هرگز تست نمی‌شود."""
        assert any(not r.valid_for_error for r in acceptance.projects)

    def test_median_error_excludes_invalid_projects(self, quotes):
        import statistics

        a = analyze_acceptance(quotes)
        valid = [r.error_pct for r in a.projects if r.valid_for_error]
        assert a.median_error == pytest.approx(statistics.median(valid))

    def test_coverage_counts_quotes_not_projects(self, acceptance):
        total = sum(len(r.quotes) for r in acceptance.projects)
        inside = sum(r.in_range_count for r in acceptance.projects)
        assert acceptance.range_coverage_pct == pytest.approx(inside / total * 100)

    def test_coverage_is_not_a_perfect_hundred(self, acceptance):
        """پوشش ۱۰۰٪ یعنی بازه بی‌معنا پهن شده (docs/specs/mvp-scope-lock.md)."""
        assert acceptance.range_coverage_pct < 100

    def test_thresholds_match_the_locked_spec(self):
        assert (THRESHOLD_MEDIAN_ERROR, THRESHOLD_WORST_ERROR) == (25.0, 50.0)
        assert (THRESHOLD_RANGE_COVERAGE, THRESHOLD_QUALITATIVE_PCT) == (60.0, 70.0)

    def test_mock_run_passes_all_four_criteria(self, acceptance):
        assert acceptance.criteria_met == 4, acceptance.failed

    def test_decision_allows_phase_two_when_three_criteria_pass(self, acceptance):
        assert "فاز ۲" in acceptance.decision

    def test_high_error_sends_back_to_price_calibration(self, quotes):
        """اگر خطای میانه از ۴۰٪ بگذرد، اول دیتاست قیمت کالیبره می‌شود."""
        broken = json.loads(json.dumps(quotes))
        for p in broken["projects"]:
            p["quotes_toman"] = [int(q * 0.3) for q in p["quotes_toman"]]
            p["qualitative_ok"] = False
        a = analyze_acceptance(broken)
        assert a.median_error > 40
        assert "Issue #2" in a.decision

    def test_empty_dataset_raises(self):
        with pytest.raises(ValidationError):
            analyze_acceptance({"projects": []})

    def test_report_lists_every_project(self, acceptance):
        report = render_acceptance_report(acceptance)
        for r in acceptance.projects:
            assert r.project_id in report

    def test_report_states_synthetic_limitation(self, acceptance):
        report = render_acceptance_report(acceptance)
        assert "ساختگی" in report
        assert "تصمیم ورود به فاز ۲ را مستند نمی‌کند" in report

    def test_report_names_observed_weaknesses(self, acceptance):
        report = render_acceptance_report(acceptance)
        assert "نقاط ضعف" in report
        worst = max(acceptance.projects, key=lambda r: r.error_pct)
        assert worst.project_id in report


class TestCli:
    def test_writes_both_reports(self, tmp_path):
        assert main(["--out", str(tmp_path)]) == 0
        assert (tmp_path / "validation-report.md").exists()
        assert (tmp_path / "acceptance-report.md").exists()
