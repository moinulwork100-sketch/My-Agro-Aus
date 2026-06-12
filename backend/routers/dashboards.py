from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime

from fastapi import APIRouter, HTTPException, Query

from backend.config import settings
from backend.db import supabase
from backend.deps import not_found
from backend.reputation_engine import build_reputation_profile
from backend.risk_engine import score_project_risk
from backend.schemas import (
    AdminAnalytics,
    AdminDashboardResponse,
    AdminTotals,
    ChartDatum,
    FarmerDashboardResponse,
    FarmerProjectSummary,
    FarmerResponse,
    InvestorDashboardResponse,
    InvestmentResponse,
    PortfolioSummary,
    UserResponse,
)
from backend.serializers import farm_list_item, investment_response

router = APIRouter()


def _month_label(value: str | date | datetime | None) -> str:
    if not value:
        return "Unknown"
    if isinstance(value, datetime):
        return value.strftime("%b %Y")
    if isinstance(value, date):
        return value.strftime("%b %Y")
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return "Unknown"
    return parsed.strftime("%b %Y")


def _round(value: float) -> float:
    return round(float(value), 2)


def _top_chart(counter: Counter, limit: int = 5, id_lookup: dict | None = None) -> list[ChartDatum]:
    return [
        ChartDatum(label=label, value=_round(value), id=(id_lookup or {}).get(label))
        for label, value in counter.most_common(limit)
    ]


def _shape_investments(rows: list[dict]) -> list[InvestmentResponse]:
    items: list[InvestmentResponse] = []
    for raw in rows:
        inv = dict(raw)
        farm_data = inv.pop("farms", None) or {}
        user_data = inv.pop("users", None) or {}
        farmer_data = farm_data.pop("farmers", None) or {}
        items.append(
            investment_response(
                inv,
                farm_data=farm_data,
                farmer_data=farmer_data,
                user_data=user_data,
            )
        )
    return items


def _group_reviews(rows: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        if row.get("farmer_id"):
            grouped[row["farmer_id"]].append(row)
    return grouped


def _farmer_reputation(
    farmer: dict,
    farms: list[dict],
    investments: list[dict],
    reviews: list[dict],
) -> dict:
    farm_ids = {farm.get("id") for farm in farms}
    farmer_investments = [item for item in investments if item.get("farm_id") in farm_ids]
    return build_reputation_profile(farmer, farms, farmer_investments, reviews)


def _portfolio_from_items(items: list[InvestmentResponse]) -> PortfolioSummary:
    total_invested = sum(item.amount for item in items)
    total_expected = sum(item.expected_return for item in items)
    total_gross_profit = sum(item.gross_profit for item in items)
    total_platform_fees = sum(item.investor_platform_fee for item in items)
    total_net_profit = sum(item.net_profit for item in items)
    projected_percent = round(
        ((total_expected - total_invested) / total_invested * 100) if total_invested else 0,
        1,
    )
    return PortfolioSummary(
        total_invested=_round(total_invested),
        expected_returns=_round(total_expected),
        total_gross_profit=_round(total_gross_profit),
        total_platform_fees=_round(total_platform_fees),
        total_net_profit=_round(total_net_profit),
        projected_percent=projected_percent,
        investments=items,
    )


def _require_admin(admin_id: str) -> UserResponse:
    result = supabase.table("users").select("*").eq("id", admin_id).single().execute()
    if not result.data:
        raise not_found("Admin", admin_id)
    user = UserResponse(**result.data)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return user


@router.get("/investor/{user_id}", response_model=InvestorDashboardResponse)
async def investor_dashboard(user_id: str):
    user_result = supabase.table("users").select("*").eq("id", user_id).single().execute()
    if not user_result.data:
        raise not_found("User", user_id)
    user = UserResponse(**user_result.data)
    if user.role != "investor":
        raise HTTPException(status_code=422, detail="Investor account required")

    result = (
        supabase.table("investments")
        .select("*, farms(*, farmers(id, name, rating, verified)), users(id, name, email)")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )
    items = _shape_investments(result.data or [])
    portfolio = _portfolio_from_items(items)

    all_result = (
        supabase.table("investments")
        .select("amount, farms(crop_type, farmers(name))")
        .execute()
    )
    farmer_totals: Counter = Counter()
    crop_totals: Counter = Counter()
    for inv in all_result.data or []:
        amount = float(inv.get("amount") or 0)
        farm = inv.get("farms") or {}
        farmer = farm.get("farmers") or {}
        if farmer.get("name"):
            farmer_totals[farmer["name"]] += amount
        if farm.get("crop_type"):
            crop_totals[farm["crop_type"]] += amount

    most_farmer = _top_chart(farmer_totals, 1)
    most_crop = _top_chart(crop_totals, 1)
    return InvestorDashboardResponse(
        user=user,
        portfolio=portfolio,
        most_invested_farmer=most_farmer[0] if most_farmer else None,
        most_invested_crop=most_crop[0] if most_crop else None,
        platform_fee_rate=settings.investor_fee_rate,
    )


@router.get("/farmer/{farmer_id}", response_model=FarmerDashboardResponse)
async def farmer_dashboard(farmer_id: str):
    farmer_result = supabase.table("farmers").select("*").eq("id", farmer_id).single().execute()
    if not farmer_result.data:
        raise not_found("Farmer", farmer_id)
    reviews_result = supabase.table("reviews").select("*").eq("farmer_id", farmer_id).execute()

    farms_result = (
        supabase.table("farms")
        .select("*, farmers(id, name, verified, rating, completed_projects, on_time_rate, risk_classification, portrait_url)")
        .eq("farmer_id", farmer_id)
        .order("created_at", desc=True)
        .execute()
    )

    farm_ids = [farm["id"] for farm in farms_result.data or []]
    investments_by_farm: dict[str, list[InvestmentResponse]] = defaultdict(list)
    if farm_ids:
        inv_result = (
            supabase.table("investments")
            .select("*, farms(*, farmers(id, name, rating, verified)), users(id, name, email)")
            .in_("farm_id", farm_ids)
            .order("created_at", desc=True)
            .execute()
        )
        for item in _shape_investments(inv_result.data or []):
            investments_by_farm[item.farm_id].append(item)

    raw_investments = []
    for project_investments in investments_by_farm.values():
        raw_investments.extend(item.model_dump() for item in project_investments)
    reputation = build_reputation_profile(
        farmer_result.data,
        farms_result.data or [],
        raw_investments,
        reviews_result.data or [],
    )
    farmer = FarmerResponse(**farmer_result.data, reputation=reputation)

    projects: list[FarmerProjectSummary] = []
    investor_counter: Counter = Counter()
    total_raised = 0.0
    total_farmer_fees = 0.0
    net_farmer_payout = 0.0

    for raw_farm in farms_result.data or []:
        farm = dict(raw_farm)
        farmer_data = farm.pop("farmers", None) or {}
        risk = score_project_risk(farm, reputation)
        farm.update(risk)
        farm_item = farm_list_item(farm, farmer_data)
        project_investments = investments_by_farm.get(farm["id"], [])
        raised = sum(inv.amount for inv in project_investments)
        farmer_fee = sum(inv.farmer_platform_fee for inv in project_investments)
        payout = sum(inv.farmer_payout for inv in project_investments)
        farmer_profit = sum(inv.gross_profit for inv in project_investments)
        for inv in project_investments:
            if inv.user:
                investor_counter[inv.user.name] += inv.amount

        total_raised += raised
        total_farmer_fees += farmer_fee
        net_farmer_payout += payout
        projects.append(
            FarmerProjectSummary(
                farm=farm_item,
                investments=project_investments,
                total_raised=_round(raised),
                farmer_platform_fee=_round(farmer_fee),
                net_farmer_payout=_round(payout),
                expected_farmer_profit=_round(farmer_profit),
                funding_progress=float(farm_item.funded_percent or 0),
                status=farm_item.status,
                progress_percent=farm_item.progress_percent,
                current_milestone=farm_item.current_milestone,
                risk_score=farm_item.risk_score,
                risk_level=farm_item.risk_level,
            )
        )

    return FarmerDashboardResponse(
        farmer=farmer,
        projects=projects,
        total_raised=_round(total_raised),
        total_farmer_fees=_round(total_farmer_fees),
        net_farmer_payout=_round(net_farmer_payout),
        most_active_investors=_top_chart(investor_counter),
        platform_fee_rate=settings.farmer_fee_rate,
    )


@router.get("/admin", response_model=AdminDashboardResponse)
async def admin_dashboard(admin_id: str = Query(...)):
    _require_admin(admin_id)

    users_result = supabase.table("users").select("*").order("created_at", desc=True).execute()
    farmers_result = supabase.table("farmers").select("*").order("created_at", desc=True).execute()
    farms_result = (
        supabase.table("farms")
        .select("*, farmers(id, name, verified, rating, completed_projects, on_time_rate, risk_classification, portrait_url)")
        .order("created_at", desc=True)
        .execute()
    )
    investments_result = (
        supabase.table("investments")
        .select("*, farms(*, farmers(id, name, rating, verified)), users(id, name, email)")
        .order("created_at", desc=True)
        .execute()
    )
    reviews_result = supabase.table("reviews").select("*").execute()

    users = [UserResponse(**user) for user in users_result.data or []]
    raw_farms: list[dict] = []
    farms_by_farmer: dict[str, list[dict]] = defaultdict(list)
    farmer_lookup = {farmer["id"]: farmer for farmer in farmers_result.data or []}
    for raw_farm in farms_result.data or []:
        farm = dict(raw_farm)
        farm.pop("farmers", None)
        raw_farms.append(farm)
        if farm.get("farmer_id"):
            farms_by_farmer[farm["farmer_id"]].append(farm)

    review_lookup = _group_reviews(reviews_result.data or [])
    raw_investments = []
    for row in investments_result.data or []:
        inv = dict(row)
        inv.pop("farms", None)
        inv.pop("users", None)
        raw_investments.append(inv)

    reputation_lookup: dict[str, dict] = {}
    for farmer in farmers_result.data or []:
        reputation_lookup[farmer["id"]] = _farmer_reputation(
            farmer,
            farms_by_farmer.get(farmer["id"], []),
            raw_investments,
            review_lookup.get(farmer["id"], []),
        )

    risk_distribution: Counter = Counter()
    risk_score_by_month: dict[str, list[int]] = defaultdict(list)
    projects = []
    for raw_farm in farms_result.data or []:
        farm = dict(raw_farm)
        farmer_data = farm.pop("farmers", None) or {}
        reputation = reputation_lookup.get(farm.get("farmer_id")) or build_reputation_profile(farmer_data, [farm], [], [])
        risk = score_project_risk(farm, reputation)
        farm.update(risk)
        risk_distribution[risk["risk_level"]] += 1
        risk_score_by_month[_month_label(farm.get("created_at"))].append(risk["risk_score"])
        item = farm_list_item(farm, farmer_data)
        if item:
            projects.append(item)

    investments = _shape_investments(investments_result.data or [])
    total_investment_volume = sum(inv.amount for inv in investments)
    total_farmer_payouts = sum(inv.farmer_payout for inv in investments)
    total_investor_profit = sum(inv.net_profit for inv in investments)
    total_farmer_profit = sum(max(inv.gross_profit - inv.farmer_platform_fee, 0) for inv in investments)
    total_platform_commission = sum(
        inv.investor_platform_fee + inv.farmer_platform_fee for inv in investments
    )

    revenue_by_month: Counter = Counter()
    profit_by_month: Counter = Counter()
    farmer_totals: Counter = Counter()
    crop_totals: Counter = Counter()
    investor_frequency: Counter = Counter()

    farmer_name_to_id = {f.get("name"): f.get("id") for f in farmers_result.data or []}
    user_name_to_id = {u.name: u.id for u in users}
    project_name_to_id = {p.name: p.id for p in projects}

    for inv in investments:
        month = _month_label(inv.created_at.isoformat() if inv.created_at else None)
        revenue_by_month[month] += inv.investor_platform_fee + inv.farmer_platform_fee
        profit_by_month[month] += inv.net_profit
        if inv.farm:
            crop_totals[inv.farm.crop_type] += inv.amount
            if inv.farm.farmer_name:
                farmer_totals[inv.farm.farmer_name] += inv.amount
        if inv.user:
            investor_frequency[inv.user.name] += 1

    month_order = list(revenue_by_month.keys())
    farmer_rankings = sorted(
        [
            ChartDatum(
                id=farmer.get("id"),
                label=farmer.get("name") or "Farmer",
                value=_round(reputation_lookup.get(farmer["id"], {}).get("reputation_score") or 0),
                sublabel=f"{reputation_lookup.get(farmer['id'], {}).get('overall_rating', 0):.1f}/5 rating",
            )
            for farmer in farmers_result.data or []
        ],
        key=lambda item: item.value,
        reverse=True,
    )

    analytics = AdminAnalytics(
        revenue_by_month=[ChartDatum(label=month, value=_round(revenue_by_month[month])) for month in month_order],
        growth_over_time=[
            {
                "label": month,
                "revenue": _round(revenue_by_month[month]),
                "profit": _round(profit_by_month[month]),
            }
            for month in month_order
        ],
        revenue_breakdown=[
            ChartDatum(label="Revenue", value=_round(total_investment_volume)),
            ChartDatum(label="Costs", value=_round(total_farmer_payouts)),
            ChartDatum(label="Profit", value=_round(total_platform_commission)),
        ],
        most_invested_farmers=_top_chart(farmer_totals, id_lookup=farmer_name_to_id),
        most_invested_crops=_top_chart(crop_totals),
        most_frequent_investors=_top_chart(investor_frequency, id_lookup=user_name_to_id),
        risk_distribution=[
            ChartDatum(label="Low Risk", value=risk_distribution["LOW"]),
            ChartDatum(label="Medium Risk", value=risk_distribution["MEDIUM"]),
            ChartDatum(label="High Risk", value=risk_distribution["HIGH"]),
        ],
        top_performing_farmers=farmer_rankings[:5],
        lowest_performing_farmers=list(reversed(farmer_rankings[-5:])),
        project_success_rates=[
            ChartDatum(id=project.id, label=project.name, value=float(project.success_rate or 0), sublabel=project.risk_level)
            for project in projects
        ],
        risk_trends_over_time=[
            ChartDatum(label=month, value=_round(sum(scores) / len(scores)))
            for month, scores in risk_score_by_month.items()
        ],
    )

    totals = AdminTotals(
        total_platform_commission=_round(total_platform_commission),
        total_investment_volume=_round(total_investment_volume),
        total_farmer_payouts=_round(total_farmer_payouts),
        total_investor_profit=_round(total_investor_profit),
        active_projects=sum(1 for project in projects if project.status == "active"),
        completed_projects=sum(1 for project in projects if project.status == "completed"),
        user_count=len(users),
        farmer_count=len(farmers_result.data or []),
        low_risk_projects=risk_distribution["LOW"],
        medium_risk_projects=risk_distribution["MEDIUM"],
        high_risk_projects=risk_distribution["HIGH"],
        average_farmer_rating=_round(
            sum(float(rep.get("overall_rating") or 0) for rep in reputation_lookup.values()) / len(reputation_lookup)
            if reputation_lookup
            else 0
        ),
        platform_revenue=_round(total_platform_commission),
        total_farmer_profit=_round(total_farmer_profit),
        profit_sharing_revenue=_round(total_platform_commission),
    )

    return AdminDashboardResponse(
        totals=totals,
        users=users,
        projects=projects,
        investments=investments,
        analytics=analytics,
    )
