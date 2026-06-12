from __future__ import annotations

from backend.profit_engine.service import expected_return_for, investment_financials


def ensure_financial_fields(row: dict, farm_data: dict | None = None) -> dict:
    amount = float(row.get("amount") or 0)
    expected_return = float(row.get("expected_return") or amount)
    farm = farm_data or {}
    financials = investment_financials(
        amount,
        expected_return,
        expected_roi=float(farm.get("expected_roi") or row.get("expected_roi") or 0),
        funding_volume=float(farm.get("total_funding_goal") or amount),
    )
    should_refresh_dynamic_fields = (
        financials["gross_profit"] > 0
        and (
            float(row.get("investor_fee_rate") or 0) == 0
            or float(row.get("farmer_fee_rate") or 0) == 0
        )
    )
    should_apply_loss_protection = bool(financials["loss_protection_applied"])
    for key, value in financials.items():
        if row.get(key) is None or should_refresh_dynamic_fields or should_apply_loss_protection:
            row[key] = value
    return row
