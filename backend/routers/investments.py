from fastapi import APIRouter, HTTPException, Query

from backend.calculations import expected_return_for, investment_financials
from backend.db import supabase
from backend.deps import not_found
from backend.profit_engine import load_fee_rules
from backend.schemas import InvestmentCreate, InvestmentResponse, PortfolioSummary, UserCreate, UserResponse
from backend.serializers import investment_response

router = APIRouter()


@router.post("/users", response_model=UserResponse, status_code=201)
async def create_or_get_user(user: UserCreate):
    existing = supabase.table("users").select("*").eq("email", user.email).execute()
    if existing.data:
        existing_user = existing.data[0]
        if existing_user.get("role") != "investor":
            raise HTTPException(status_code=422, detail="This email is not registered as an investor")
        return UserResponse(**existing_user)

    result = supabase.table("users").insert({
        "name": user.name,
        "email": user.email,
        "role": "investor",
    }).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create user")
    return UserResponse(**result.data[0])


@router.post("", response_model=InvestmentResponse, status_code=201)
async def create_investment(payload: InvestmentCreate):
    user_result = (
        supabase.table("users")
        .select("id, name, email, role")
        .eq("id", payload.user_id)
        .single()
        .execute()
    )
    if not user_result.data:
        raise not_found("User", payload.user_id)
    if user_result.data.get("role") != "investor":
        raise HTTPException(status_code=422, detail="Only investor accounts can invest")

    farm_result = supabase.table("farms").select("*").eq("id", payload.farm_id).single().execute()
    if not farm_result.data:
        raise not_found("Farm", payload.farm_id)

    farm = farm_result.data
    expected_return = expected_return_for(payload.amount, float(farm["expected_roi"]))
    financials = investment_financials(
        payload.amount,
        expected_return,
        expected_roi=float(farm["expected_roi"]),
        funding_volume=float(farm.get("total_funding_goal") or payload.amount),
        rules=load_fee_rules(supabase),
    )

    result = supabase.table("investments").insert({
        "user_id": payload.user_id,
        "farm_id": payload.farm_id,
        "amount": payload.amount,
        "expected_return": expected_return,
        **financials,
        "status": "active",
    }).execute()

    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create investment")

    farmer_result = (
        supabase.table("farmers")
        .select("id, name, rating, verified")
        .eq("id", farm["farmer_id"])
        .single()
        .execute()
    )

    return investment_response(
        result.data[0],
        farm_data=farm,
        farmer_data=farmer_result.data or {},
        user_data=user_result.data,
    )


@router.get("/portfolio", response_model=PortfolioSummary)
async def get_portfolio(user_id: str = Query(...)):
    result = (
        supabase.table("investments")
        .select("*, farms(*, farmers(id, name, rating, verified)), users(id, name, email)")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )

    items: list[InvestmentResponse] = []
    total_invested = 0.0
    total_expected = 0.0
    total_gross_profit = 0.0
    total_platform_fees = 0.0
    total_net_profit = 0.0

    for raw in result.data or []:
        inv = dict(raw)
        farm_data = inv.pop("farms", None) or {}
        user_data = inv.pop("users", None) or {}
        farmer_data = farm_data.pop("farmers", None) or {}
        item = investment_response(inv, farm_data=farm_data, farmer_data=farmer_data, user_data=user_data)
        items.append(item)
        total_invested += item.amount
        total_expected += item.expected_return
        total_gross_profit += item.gross_profit
        total_platform_fees += item.investor_platform_fee
        total_net_profit += item.net_profit

    projected_percent = round(
        ((total_expected - total_invested) / total_invested * 100) if total_invested > 0 else 0,
        1,
    )

    return PortfolioSummary(
        total_invested=round(total_invested, 2),
        expected_returns=round(total_expected, 2),
        total_gross_profit=round(total_gross_profit, 2),
        total_platform_fees=round(total_platform_fees, 2),
        total_net_profit=round(total_net_profit, 2),
        projected_percent=projected_percent,
        investments=items,
    )
