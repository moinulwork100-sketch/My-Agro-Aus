from collections import defaultdict

from fastapi import APIRouter, HTTPException
from backend.db import supabase
from backend.deps import not_found
from backend.schemas import FarmerResponse, FarmerSummary, ReviewCreate, ReviewResponse, InvestmentResponse
from backend.reputation_engine import build_reputation_profile
from backend.serializers import investment_response

router = APIRouter()


def _farmer_history(farmer_id: str) -> tuple[list[dict], list[dict], list[dict]]:
    farms_result = supabase.table("farms").select("*").eq("farmer_id", farmer_id).execute()
    farms = farms_result.data or []
    farm_ids = [farm["id"] for farm in farms]
    investments = []
    if farm_ids:
        inv_result = supabase.table("investments").select("*").in_("farm_id", farm_ids).execute()
        investments = inv_result.data or []
    reviews_result = (
        supabase.table("reviews")
        .select("*")
        .eq("farmer_id", farmer_id)
        .order("created_at", desc=True)
        .execute()
    )
    return farms, investments, reviews_result.data or []


@router.get("", response_model=list[FarmerSummary])
async def list_farmers():
    result = (
        supabase.table("farmers")
        .select("id, name, verified, rating, completed_projects, on_time_rate, risk_classification, portrait_url")
        .order("name")
        .execute()
    )
    farmers = result.data or []
    if not farmers:
        return []

    unique_farmer_ids = [f["id"] for f in farmers]

    # Three bulk queries replacing 3N sequential ones
    all_farms_res = supabase.table("farms").select("*").in_("farmer_id", unique_farmer_ids).execute()
    all_farms: list[dict] = all_farms_res.data or []
    all_farm_ids = [f["id"] for f in all_farms]

    all_investments: list[dict] = []
    if all_farm_ids:
        inv_res = supabase.table("investments").select("*").in_("farm_id", all_farm_ids).execute()
        all_investments = inv_res.data or []

    reviews_res = supabase.table("reviews").select("*").in_("farmer_id", unique_farmer_ids).execute()
    all_reviews: list[dict] = reviews_res.data or []

    # Group in memory
    farms_by_farmer: dict[str, list[dict]] = defaultdict(list)
    for f in all_farms:
        farms_by_farmer[f["farmer_id"]].append(f)

    investments_by_farm: dict[str, list[dict]] = defaultdict(list)
    for inv in all_investments:
        investments_by_farm[inv["farm_id"]].append(inv)

    investments_by_farmer: dict[str, list[dict]] = defaultdict(list)
    for f in all_farms:
        for inv in investments_by_farm[f["id"]]:
            investments_by_farmer[f["farmer_id"]].append(inv)

    reviews_by_farmer: dict[str, list[dict]] = defaultdict(list)
    for r in all_reviews:
        reviews_by_farmer[r["farmer_id"]].append(r)

    items = []
    for farmer in farmers:
        farmer_id = farmer["id"]
        reputation = build_reputation_profile(
            farmer,
            farms_by_farmer[farmer_id],
            investments_by_farmer[farmer_id],
            reviews_by_farmer[farmer_id],
        )
        data = dict(farmer)
        data.pop("years_experience", None)
        items.append(
            FarmerSummary(
                **data,
                reputation_score=reputation.get("reputation_score"),
                project_success_rate=reputation.get("project_success_rate"),
                investor_satisfaction_score=reputation.get("investor_satisfaction_score"),
                years_experience=reputation.get("years_experience"),
                crop_categories=reputation.get("crop_categories") or [],
            )
        )
    return items


@router.get("/{farmer_id}", response_model=FarmerResponse)
async def get_farmer(farmer_id: str):
    result = supabase.table("farmers").select("*").eq("id", farmer_id).single().execute()
    if not result.data:
        raise not_found("Farmer", farmer_id)

    farmer = result.data

    farms, investments, review_rows = _farmer_history(farmer_id)
    reputation = build_reputation_profile(farmer, farms, investments, review_rows)
    reviews = [ReviewResponse(**r) for r in review_rows]

    return FarmerResponse(**farmer, reviews=reviews, reputation=reputation)


@router.post("/{farmer_id}/reviews", response_model=ReviewResponse, status_code=201)
async def create_farmer_review(farmer_id: str, payload: ReviewCreate):
    farmer_result = supabase.table("farmers").select("*").eq("id", farmer_id).single().execute()
    if not farmer_result.data:
        raise not_found("Farmer", farmer_id)

    farms_result = supabase.table("farms").select("id").eq("farmer_id", farmer_id).execute()
    farm_ids = [farm["id"] for farm in (farms_result.data or [])]
    if not farm_ids:
        raise HTTPException(status_code=422, detail="This farmer has no projects to review")

    completed_result = (
        supabase.table("investments")
        .select("id")
        .eq("user_id", payload.user_id)
        .eq("status", "completed")
        .in_("farm_id", farm_ids)
        .execute()
    )
    if not completed_result.data:
        raise HTTPException(status_code=422, detail="Reviews can be submitted after a completed investment")

    existing = (
        supabase.table("reviews")
        .select("id")
        .eq("farmer_id", farmer_id)
        .eq("user_id", payload.user_id)
        .execute()
    )
    if existing.data:
        raise HTTPException(status_code=409, detail="You already reviewed this farmer")

    user_result = supabase.table("users").select("name").eq("id", payload.user_id).single().execute()
    reviewer_name = payload.reviewer_name or (user_result.data or {}).get("name")
    result = supabase.table("reviews").insert({
        "farmer_id": farmer_id,
        "user_id": payload.user_id,
        "rating": payload.rating,
        "comment": payload.comment,
        "reviewer_name": reviewer_name,
    }).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create review")

    reviews_result = supabase.table("reviews").select("rating").eq("farmer_id", farmer_id).execute()
    ratings = [float(review["rating"]) for review in reviews_result.data or []]
    if ratings:
        average_rating = round(sum(ratings) / len(ratings), 1)
        supabase.table("farmers").update({"rating": average_rating}).eq("id", farmer_id).execute()

    return ReviewResponse(**result.data[0])


@router.get("/{farmer_id}/conversations", response_model=list[InvestmentResponse])
async def get_farmer_conversations(farmer_id: str):
    # Get all farms that belong to this farmer
    farms_result = supabase.table("farms").select("id").eq("farmer_id", farmer_id).execute()
    farm_ids = [f["id"] for f in (farms_result.data or [])]
    if not farm_ids:
        return []

    # Get all investments for those farms
    result = (
        supabase.table("investments")
        .select("*, farms(*, farmers(id, name, rating, verified)), users(id, name, email)")
        .in_("farm_id", farm_ids)
        .order("created_at", desc=True)
        .execute()
    )

    items = []
    for raw in (result.data or []):
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
