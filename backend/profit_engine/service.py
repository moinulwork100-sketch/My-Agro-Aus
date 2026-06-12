from __future__ import annotations

from backend.config import settings


def _round(value: float) -> float:
    return round(float(value), 2)


def expected_return_for(amount: float, expected_roi: float) -> float:
    return _round(amount * (1 + expected_roi / 100))


def _fee_rate_for_value(rules: list[dict] | None, value: float, fallback: float) -> float:
    if not rules:
        return fallback
    numeric = float(value or 0)
    for rule in rules:
        minimum = rule.get("minimum")
        maximum = rule.get("maximum")
        above_minimum = minimum is None or numeric > float(minimum)
        below_maximum = maximum is None or numeric <= float(maximum)
        if above_minimum and below_maximum:
            return float(rule.get("rate") or fallback)
    return fallback


def investor_fee_rate_for_roi(expected_roi: float, rules: dict | None = None) -> float:
    roi = float(expected_roi or 0)
    rule_rate = _fee_rate_for_value((rules or {}).get("investor"), roi, -1)
    if rule_rate >= 0:
        return rule_rate
    if roi <= 10:
        return settings.investor_low_roi_fee_rate
    if roi <= 15:
        return settings.investor_medium_roi_fee_rate
    return settings.investor_high_roi_fee_rate


def farmer_fee_rate_for_funding(funding_volume: float, rules: dict | None = None) -> float:
    volume = float(funding_volume or 0)
    rule_rate = _fee_rate_for_value((rules or {}).get("farmer"), volume, -1)
    if rule_rate >= 0:
        return rule_rate
    if volume < 10000:
        return settings.farmer_under_10k_fee_rate
    if volume <= 50000:
        return settings.farmer_10k_to_50k_fee_rate
    return settings.farmer_above_50k_fee_rate


def investment_financials(
    amount: float,
    expected_return: float,
    *,
    expected_roi: float = 0,
    funding_volume: float | None = None,
    rules: dict | None = None,
) -> dict[str, float | bool]:
    amount = float(amount or 0)
    expected_return = float(expected_return or amount)
    gross_profit = _round(max(expected_return - amount, 0))
    investor_fee_rate = investor_fee_rate_for_roi(expected_roi, rules=rules)
    farmer_fee_rate = farmer_fee_rate_for_funding(funding_volume if funding_volume is not None else amount, rules=rules)

    loss_protection_applied = gross_profit <= 0
    investor_platform_fee = 0.0 if loss_protection_applied else _round(gross_profit * investor_fee_rate)
    farmer_platform_fee = 0.0 if loss_protection_applied else _round(gross_profit * farmer_fee_rate)
    net_profit = _round(gross_profit - investor_platform_fee)
    farmer_payout = _round(amount - farmer_platform_fee)

    return {
        "gross_profit": gross_profit,
        "investor_fee_rate": investor_fee_rate,
        "investor_platform_fee": investor_platform_fee,
        "net_profit": net_profit,
        "farmer_fee_rate": farmer_fee_rate,
        "farmer_platform_fee": farmer_platform_fee,
        "farmer_payout": farmer_payout,
        "loss_protection_applied": loss_protection_applied,
    }


def fee_rules() -> dict[str, list[dict[str, float | str | None]]]:
    return {
        "investor": [
            {
                "id": "investor_low_roi",
                "label": "Low ROI projects",
                "rate": settings.investor_low_roi_fee_rate,
                "minimum": None,
                "maximum": 10,
            },
            {
                "id": "investor_medium_roi",
                "label": "Medium ROI projects",
                "rate": settings.investor_medium_roi_fee_rate,
                "minimum": 10,
                "maximum": 15,
            },
            {
                "id": "investor_high_roi",
                "label": "High ROI projects",
                "rate": settings.investor_high_roi_fee_rate,
                "minimum": 15,
                "maximum": None,
            },
        ],
        "farmer": [
            {
                "id": "farmer_under_10k",
                "label": "Funding under $10,000",
                "rate": settings.farmer_under_10k_fee_rate,
                "minimum": None,
                "maximum": 10000,
            },
            {
                "id": "farmer_10k_to_50k",
                "label": "Funding $10,000-$50,000",
                "rate": settings.farmer_10k_to_50k_fee_rate,
                "minimum": 10000,
                "maximum": 50000,
            },
            {
                "id": "farmer_above_50k",
                "label": "Funding above $50,000",
                "rate": settings.farmer_above_50k_fee_rate,
                "minimum": 50000,
                "maximum": None,
            },
        ],
    }


def fee_rules_from_rows(rows: list[dict]) -> dict[str, list[dict[str, float | str | None]]]:
    grouped = {"investor": [], "farmer": []}
    for row in sorted(rows, key=lambda item: item.get("sort_order") or 0):
        audience = row.get("audience")
        if audience not in grouped:
            continue
        grouped[audience].append(
            {
                "id": row.get("id"),
                "label": row.get("label"),
                "rate": float(row.get("rate") or 0),
                "minimum": float(row["minimum"]) if row.get("minimum") is not None else None,
                "maximum": float(row["maximum"]) if row.get("maximum") is not None else None,
            }
        )
    defaults = fee_rules()
    return {
        "investor": grouped["investor"] or defaults["investor"],
        "farmer": grouped["farmer"] or defaults["farmer"],
    }
