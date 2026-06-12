from fastapi import APIRouter, HTTPException
from backend.db import supabase
from backend.deps import not_found
from backend.farmer_progress import build_timeline, normalize_progress_payload
from backend.schemas import ProgressCreate, ProgressResponse, ProjectTimelineResponse

router = APIRouter()


@router.get("/{farm_id}/progress", response_model=list[ProgressResponse])
async def get_farm_progress(farm_id: str):
    farm_check = supabase.table("farms").select("id").eq("id", farm_id).execute()
    if not farm_check.data:
        raise not_found("Farm", farm_id)

    result = (
        supabase.table("progress_updates")
        .select("*")
        .eq("farm_id", farm_id)
        .order("created_at", desc=True)
        .execute()
    )
    return [ProgressResponse(**p) for p in (result.data or [])]


@router.get("/{farm_id}/timeline", response_model=ProjectTimelineResponse)
async def get_farm_timeline(farm_id: str):
    farm_check = supabase.table("farms").select("*").eq("id", farm_id).single().execute()
    if not farm_check.data:
        raise not_found("Farm", farm_id)

    result = (
        supabase.table("progress_updates")
        .select("*")
        .eq("farm_id", farm_id)
        .order("created_at", desc=True)
        .execute()
    )
    return ProjectTimelineResponse(**build_timeline(farm_check.data, result.data or []))


@router.post("/{farm_id}/progress", response_model=ProgressResponse, status_code=201)
async def create_farm_progress(farm_id: str, payload: ProgressCreate):
    farm_check = supabase.table("farms").select("*").eq("id", farm_id).single().execute()
    if not farm_check.data:
        raise not_found("Farm", farm_id)
    farm = farm_check.data
    if farm.get("farmer_id") != payload.farmer_id:
        raise HTTPException(status_code=403, detail="Only the project farmer can update progress")

    update_payload = normalize_progress_payload(payload.model_dump())
    result = supabase.table("progress_updates").insert({
        "farm_id": farm_id,
        **update_payload,
    }).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create progress update")

    farm_update = {
        "current_milestone": update_payload["milestone"],
        "progress_percent": update_payload["progress_percent"],
    }
    if update_payload["milestone"] == "Completed":
        farm_update["status"] = "completed"
        farm_update["funded_percent"] = 100
    supabase.table("farms").update(farm_update).eq("id", farm_id).execute()

    return ProgressResponse(**result.data[0])
