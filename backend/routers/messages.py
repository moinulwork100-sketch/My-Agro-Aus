from fastapi import APIRouter
from backend.db import supabase
from backend.deps import not_found
from backend.schemas import MessageCreate, MessageResponse

router = APIRouter()


@router.get("/{investment_id}/messages", response_model=list[MessageResponse])
async def get_messages(investment_id: str):
    inv_check = supabase.table("investments").select("id").eq("id", investment_id).execute()
    if not inv_check.data:
        raise not_found("Investment", investment_id)

    result = (
        supabase.table("messages")
        .select("*")
        .eq("investment_id", investment_id)
        .order("created_at")
        .execute()
    )
    return [MessageResponse(**m) for m in (result.data or [])]


@router.post("/{investment_id}/messages", response_model=MessageResponse, status_code=201)
async def send_message(investment_id: str, payload: MessageCreate):
    inv_check = supabase.table("investments").select("id").eq("id", investment_id).execute()
    if not inv_check.data:
        raise not_found("Investment", investment_id)

    result = supabase.table("messages").insert({
        "investment_id": investment_id,
        "sender": payload.sender,
        "body": payload.body,
    }).execute()

    return MessageResponse(**result.data[0])
