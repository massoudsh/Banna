"""Transparent financing estimates for renovation scenarios (Issue #18)."""

from __future__ import annotations

import math

from app.models.domain import FinancingOption, Scenario


def options_for(
    scenarios: list[Scenario],
    *,
    cash_toman: int,
    installment_months: int,
    annual_rate_pct: float,
) -> list[FinancingOption]:
    """محاسبهٔ اقساط برای سناریوهایی که از نقدینگی کاربر گران‌ترند."""
    monthly_rate = annual_rate_pct / 1200
    options = []
    for scenario in scenarios:
        financed = max(0, scenario.estimate.cost_max_toman - cash_toman)
        if financed == 0:
            continue
        if monthly_rate == 0:
            monthly = math.ceil(financed / installment_months)
        else:
            factor = (1 + monthly_rate) ** installment_months
            monthly = math.ceil(financed * monthly_rate * factor / (factor - 1))
        options.append(
            FinancingOption(
                scenario_kind=scenario.kind,
                cash_contribution_toman=cash_toman,
                financed_amount_toman=financed,
                installment_months=installment_months,
                monthly_payment_toman=monthly,
                total_repayment_toman=monthly * installment_months,
                assumptions=[
                    "مبنای محاسبه سقف بازهٔ سناریو است.",
                    f"نرخ سالانهٔ فرضی: {annual_rate_pct:g}٪.",
                    "این برآورد، پیشنهاد تسهیلات یا تأیید اعتبار نیست.",
                ],
            )
        )
    return options
