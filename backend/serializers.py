from __future__ import annotations

from backend.calculations import ensure_financial_fields
from backend.schemas import FarmListItem, InvestmentResponse, InvestorSummary


def farm_list_item(farm_data: dict | None, farmer_data: dict | None = None) -> FarmListItem | None:
    if not farm_data:
        return None
    farmer = farmer_data or {}
    return FarmListItem(
        **farm_data,
        farmer_name=farmer.get("name"),
        farmer_rating=farmer.get("rating"),
    )


def investment_response(
    investment_data: dict,
    farm_data: dict | None = None,
    farmer_data: dict | None = None,
    user_data: dict | None = None,
) -> InvestmentResponse:
    row = ensure_financial_fields(dict(investment_data), farm_data=farm_data)
    user = None
    if user_data:
        user = InvestorSummary(
            id=user_data["id"],
            name=user_data["name"],
            email=user_data.get("email"),
        )

    return InvestmentResponse(
        **row,
        farm=farm_list_item(farm_data, farmer_data),
        user=user,
    )
