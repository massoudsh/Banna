from app.engines.financing import options_for
from app.pipeline import run


def test_financing_uses_scenario_max_and_explicit_assumptions():
    result = run(description="آشپزخانه و حمام بازسازی کامل", total_area_m2=80)
    options = options_for(result.scenarios, cash_toman=100_000_000, installment_months=12, annual_rate_pct=0)

    assert options
    standard = next(option for option in options if option.scenario_kind.value == "standard")
    assert standard.total_repayment_toman >= standard.financed_amount_toman
    assert standard.total_repayment_toman - standard.financed_amount_toman < standard.installment_months
    assert any("پیشنهاد تسهیلات" in assumption for assumption in standard.assumptions)
