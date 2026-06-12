from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter

from backend.db import supabase
from backend.schemas import FeeNotificationResponse

router = APIRouter()


@router.get("/{user_id}", response_model=Optional[FeeNotificationResponse])
async def get_fee_notification(user_id: str):
    result = (
        supabase.table("fee_notifications")
        .select("id, message, sent_at")
        .eq("user_id", user_id)
        .is_("read_at", "null")
        .order("sent_at", desc=True)
        .limit(1)
        .maybe_single()
        .execute()
    )
    if not result.data:
        return None
    return FeeNotificationResponse(**result.data)


@router.patch("/{notification_id}/read")
async def mark_notification_read(notification_id: str):
    supabase.table("fee_notifications").update(
        {"read_at": datetime.now(timezone.utc).isoformat()}
    ).eq("id", notification_id).execute()
    return {"ok": True}
