from collections import defaultdict
from typing import Optional
import json
import threading
import time

from fastapi import APIRouter, Query
from fastapi.responses import Response

from backend.ai_insights import project_investment_insight
from backend.db import supabase
from backend.deps import not_found
from backend.schemas import FarmDetailResponse, FarmListItem, FarmerSummary
from backend.reputation_engine import build_reputation_profile
from backend.risk_engine import score_project_risk

router = APIRouter()

_cache_lock = threading.Lock()
_cache_bytes: bytes | None = None
_cache_expires: float = 0.0
_CACHE_TTL = 60


def _farmer_context(farmer_id: str) -> tuple[list[dict], list[dict], list[dict]]:
    farms_result = supabase.table("farms").select("*").eq("farmer_id", farmer_id).execute()
    farms = farms_result.data or []
    farm_ids = [farm["id"] for farm in farms]

    investments = []
    if farm_ids:
        investments_result = supabase.table("investments").select("*").in_("farm_id", farm_ids).execute()
        investments = investments_result.data or []

    reviews_result = supabase.table("reviews").select("*").eq("farmer_id", farmer_id).execute()
    return farms, investments, reviews_result.data or []


def _farmer_summary(farmer: dict, reputation: dict) -> FarmerSummary:
    data = dict(farmer)
    data.pop("years_experience", None)
    return FarmerSummary(
        **data,
        reputation_score=reputation.get("reputation_score"),
        project_success_rate=reputation.get("project_success_rate"),
        investor_satisfaction_score=reputation.get("investor_satisfaction_score"),
        years_experience=reputation.get("years_experience"),
        crop_categories=reputation.get("crop_categories") or [],
    )


def _enriched_farm(farm: dict, farmer_data: dict | None) -> tuple[dict, FarmerSummary | None, dict | None]:
    shaped = dict(farm)
    farmer = dict(farmer_data or {})
    reputation = None
    farmer_summary = None

    if farmer and farmer.get("id"):
        farms, investments, reviews = _farmer_context(farmer["id"])
        reputation = build_reputation_profile(farmer, farms, investments, reviews)
        risk = score_project_risk(shaped, reputation)
        shaped.update(risk)
        shaped["ai_insight"] = project_investment_insight(
            {**shaped, "farmer_name": farmer.get("name")},
            reputation,
            risk,
        )
        shaped["current_milestone"] = shaped.get("current_milestone") or "Planning"
        shaped["progress_percent"] = shaped.get("progress_percent") or 0
        shaped["expected_completion_date"] = shaped.get("expected_completion_date") or shaped.get("harvest_date")
        farmer_summary = _farmer_summary(farmer, reputation)

    return shaped, farmer_summary, reputation


def _build_list_items(raw_farms: list[dict]) -> list[FarmListItem]:
    """Build FarmListItem list using ~4 total DB queries regardless of farm count."""
    if not raw_farms:
        return []

    farmer_dicts: dict[str, dict] = {}
    for f in raw_farms:
        farmer_data = f.get("farmers") or {}
        if farmer_data.get("id"):
            farmer_dicts[farmer_data["id"]] = farmer_data

    unique_farmer_ids = list(farmer_dicts.keys())
    if not unique_farmer_ids:
        items = []
        for f in raw_farms:
            farm = dict(f)
            farm.pop("farmers", None)
            items.append(FarmListItem(**farm))
        return items

    # Three bulk queries replacing 3N sequential ones
    all_farmer_farms_res = (
        supabase.table("farms").select("*").in_("farmer_id", unique_farmer_ids).execute()
    )
    all_farmer_farms: list[dict] = all_farmer_farms_res.data or []
    all_farm_ids = [f["id"] for f in all_farmer_farms]

    all_investments: list[dict] = []
    if all_farm_ids:
        inv_res = (
            supabase.table("investments").select("*").in_("farm_id", all_farm_ids).execute()
        )
        all_investments = inv_res.data or []

    reviews_res = (
        supabase.table("reviews").select("*").in_("farmer_id", unique_farmer_ids).execute()
    )
    all_reviews: list[dict] = reviews_res.data or []

    # Group data in memory
    farms_by_farmer: dict[str, list[dict]] = defaultdict(list)
    for f in all_farmer_farms:
        farms_by_farmer[f["farmer_id"]].append(f)

    investments_by_farm: dict[str, list[dict]] = defaultdict(list)
    for inv in all_investments:
        investments_by_farm[inv["farm_id"]].append(inv)

    investments_by_farmer: dict[str, list[dict]] = defaultdict(list)
    for f in all_farmer_farms:
        for inv in investments_by_farm[f["id"]]:
            investments_by_farmer[f["farmer_id"]].append(inv)

    reviews_by_farmer: dict[str, list[dict]] = defaultdict(list)
    for r in all_reviews:
        reviews_by_farmer[r["farmer_id"]].append(r)

    # Build reputation once per unique farmer and cache
    reputation_cache: dict[str, dict] = {}
    for farmer_id, farmer in farmer_dicts.items():
        reputation_cache[farmer_id] = build_reputation_profile(
            farmer,
            farms_by_farmer[farmer_id],
            investments_by_farmer[farmer_id],
            reviews_by_farmer[farmer_id],
        )

    items: list[FarmListItem] = []
    for f in raw_farms:
        farm = dict(f)
        farmer = dict(farm.pop("farmers", None) or {})
        farmer_id = farmer.get("id")

        if farmer_id and farmer_id in reputation_cache:
            reputation = reputation_cache[farmer_id]
            risk = score_project_risk(farm, reputation)
            farm.update(risk)
            farm["current_milestone"] = farm.get("current_milestone") or "Planning"
            farm["progress_percent"] = farm.get("progress_percent") or 0

        items.append(
            FarmListItem(
                **farm,
                farmer_name=farmer.get("name"),
                farmer_rating=farmer.get("rating"),
            )
        )

    return items


@router.get("", response_model=list[FarmListItem])
async def list_farms(
    crop: Optional[str] = Query(None),
    sort: Optional[str] = Query(None),
):
    global _cache_bytes, _cache_expires

    # Return pre-serialized bytes from cache — bypasses Pydantic re-serialization overhead
    if not crop and not sort:
        with _cache_lock:
            if _cache_bytes is not None and time.monotonic() < _cache_expires:
                return Response(content=_cache_bytes, media_type="application/json")

    query = (
        supabase.table("farms")
        .select("*, farmers(id, name, verified, rating, completed_projects, on_time_rate, risk_classification, portrait_url)")
        .eq("status", "active")
    )
    if crop:
        query = query.ilike("crop_type", f"%{crop}%")

    result = query.execute()
    farms = result.data or []

    items = _build_list_items(farms)

    if sort == "roi":
        items.sort(key=lambda x: x.expected_roi, reverse=True)
    if sort == "risk":
        items.sort(key=lambda x: x.risk_score or 0, reverse=True)

    if not crop and not sort:
        serialized = json.dumps([item.model_dump(mode="json") for item in items]).encode()
        with _cache_lock:
            _cache_bytes = serialized
            _cache_expires = time.monotonic() + _CACHE_TTL

    return items


@router.get("/{farm_id}", response_model=FarmDetailResponse)
async def get_farm(farm_id: str):
    result = (
        supabase.table("farms")
        .select("*, farmers(id, name, verified, rating, completed_projects, on_time_rate, risk_classification, portrait_url)")
        .eq("id", farm_id)
        .single()
        .execute()
    )
    if not result.data:
        raise not_found("Farm", farm_id)

    farm = result.data
    farmer_data = farm.pop("farmers", None)
    enriched, farmer, reputation = _enriched_farm(farm, farmer_data)

    return FarmDetailResponse(**enriched, farmer=farmer, reputation=reputation)
