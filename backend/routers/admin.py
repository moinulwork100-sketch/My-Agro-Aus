from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from fastapi import APIRouter, Query

from backend.db import supabase
from backend.routers.dashboards import _require_admin
from backend.schemas import (
    FeeNotifyPayload,
    FeeSettlePayload,
    OutstandingFeeInvestment,
    OutstandingFeeUser,
    OutstandingFeesResponse,
)

router = APIRouter()

_DEFAULT_MESSAGE = (
    "MyAgro notice: you have an outstanding platform fee from a completed investment. "
    "Please contact support to settle your balance."
)


def _parse_dt(value) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


@router.get("/outstanding-fees", response_model=OutstandingFeesResponse)
async def outstanding_fees(admin_id: str = Query(...)):
    _require_admin(admin_id)

    inv_result = (
        supabase.table("investments")
        .select(
            "id, user_id, investor_platform_fee, farmer_platform_fee, created_at,"
            "farms(id, name, farmer_id, farmers(id, name)),"
            "users(id, name, email)"
        )
        .eq("status", "completed")
        .execute()
    )
    investments = inv_result.data or []

    settled_result = supabase.table("fee_settlements").select("investment_id, fee_type").execute()
    settled = {(row["investment_id"], row["fee_type"]) for row in settled_result.data or []}

    notif_result = (
        supabase.table("fee_notifications")
        .select("user_id, sent_at")
        .order("sent_at", desc=True)
        .execute()
    )
    last_notified: dict[str, datetime] = {}
    for row in notif_result.data or []:
        uid = row["user_id"]
        if uid not in last_notified:
            last_notified[uid] = _parse_dt(row["sent_at"])

    farmer_users_result = (
        supabase.table("users")
        .select("id, name, email, farmer_id")
        .eq("role", "farmer")
        .execute()
    )
    farmer_user_by_farmer_id: dict[str, dict] = {
        row["farmer_id"]: row
        for row in farmer_users_result.data or []
        if row.get("farmer_id")
    }

    investor_bucket: dict[str, dict] = {}
    farmer_bucket: dict[str, dict] = {}

    for inv in investments:
        inv_id = inv["id"]
        investor_user = inv.get("users") or {}
        farm = inv.get("farms") or {}
        farm_name = farm.get("name", "Unknown Farm")
        farmer_fk_id = farm.get("farmer_id")
        completed_at = _parse_dt(inv.get("created_at"))

        inv_fee = float(inv.get("investor_platform_fee") or 0)
        if inv_fee > 0 and (inv_id, "investor") not in settled:
            uid = investor_user.get("id")
            if uid:
                if uid not in investor_bucket:
                    investor_bucket[uid] = {
                        "user_id": uid,
                        "name": investor_user.get("name", ""),
                        "email": investor_user.get("email", ""),
                        "role": "investor",
                        "farmer_id": None,
                        "farm_name": None,
                        "total_outstanding": 0.0,
                        "investments": [],
                    }
                investor_bucket[uid]["total_outstanding"] += inv_fee
                investor_bucket[uid]["investments"].append(
                    OutstandingFeeInvestment(
                        investment_id=inv_id,
                        farm_name=farm_name,
                        fee_type="investor",
                        amount=inv_fee,
                        completed_at=completed_at,
                    )
                )

        farmer_fee = float(inv.get("farmer_platform_fee") or 0)
        if farmer_fee > 0 and (inv_id, "farmer") not in settled and farmer_fk_id:
            farmer_user = farmer_user_by_farmer_id.get(farmer_fk_id)
            if farmer_user:
                fuid = farmer_user["id"]
                if fuid not in farmer_bucket:
                    farmer_bucket[fuid] = {
                        "user_id": fuid,
                        "name": farmer_user.get("name", ""),
                        "email": farmer_user.get("email", ""),
                        "role": "farmer",
                        "farmer_id": farmer_fk_id,
                        "farm_name": farm_name,
                        "total_outstanding": 0.0,
                        "investments": [],
                    }
                farmer_bucket[fuid]["total_outstanding"] += farmer_fee
                farmer_bucket[fuid]["investments"].append(
                    OutstandingFeeInvestment(
                        investment_id=inv_id,
                        farm_name=farm_name,
                        fee_type="farmer",
                        amount=farmer_fee,
                        completed_at=completed_at,
                    )
                )

    def _build(entry: dict) -> OutstandingFeeUser:
        uid = entry["user_id"]
        return OutstandingFeeUser(
            user_id=uid,
            name=entry["name"],
            email=entry["email"],
            role=entry["role"],
            farmer_id=entry.get("farmer_id"),
            farm_name=entry.get("farm_name"),
            total_outstanding=round(entry["total_outstanding"], 2),
            investment_count=len(entry["investments"]),
            last_notified_at=last_notified.get(uid),
            investments=entry["investments"],
        )

    investors = [_build(v) for v in investor_bucket.values()]
    farmers = [_build(v) for v in farmer_bucket.values()]
    total_inv = round(sum(u.total_outstanding for u in investors), 2)
    total_far = round(sum(u.total_outstanding for u in farmers), 2)

    return OutstandingFeesResponse(
        investors=investors,
        farmers=farmers,
        total_investor_outstanding=total_inv,
        total_farmer_outstanding=total_far,
        grand_total=round(total_inv + total_far, 2),
    )


@router.post("/outstanding-fees/notify")
async def notify_fee_users(payload: FeeNotifyPayload):
    _require_admin(payload.admin_id)
    message = payload.message or _DEFAULT_MESSAGE
    rows = [
        {"user_id": uid, "admin_id": payload.admin_id, "message": message}
        for uid in payload.user_ids
    ]
    if rows:
        supabase.table("fee_notifications").insert(rows).execute()
    return {"notified": payload.user_ids, "count": len(payload.user_ids)}


@router.post("/outstanding-fees/settle")
async def settle_fees(payload: FeeSettlePayload):
    _require_admin(payload.admin_id)
    rows = [
        {
            "investment_id": item.investment_id,
            "user_id": item.user_id,
            "fee_type": item.fee_type,
            "amount": item.amount,
            "settled_by": payload.admin_id,
            "notes": item.notes,
        }
        for item in payload.settlements
    ]
    if rows:
        supabase.table("fee_settlements").insert(rows).execute()
    return {"settled": len(payload.settlements)}
