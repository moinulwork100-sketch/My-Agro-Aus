from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.db import supabase
from backend.profit_engine import load_fee_rules, save_fee_rules
from backend.routers import admin as admin_router
from backend.routers import auth, dashboards, farms, farmers, investments, notifications as notifications_router, progress, messages
from backend.schemas import PlatformConfigResponse, PlatformConfigUpdate

app = FastAPI(title="MyAgro API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(farms.router, prefix="/api/farms", tags=["farms"])
app.include_router(farmers.router, prefix="/api/farmers", tags=["farmers"])
app.include_router(investments.router, prefix="/api/investments", tags=["investments"])
app.include_router(progress.router, prefix="/api/farms", tags=["progress"])
app.include_router(messages.router, prefix="/api/investments", tags=["messages"])
app.include_router(dashboards.router, prefix="/api/dashboards", tags=["dashboards"])
app.include_router(admin_router.router, prefix="/api/admin", tags=["admin"])
app.include_router(notifications_router.router, prefix="/api/notifications", tags=["notifications"])


@app.get("/api")
async def health():
    return {"status": "ok", "service": "MyAgro API"}


@app.get("/api/config", response_model=PlatformConfigResponse)
async def platform_config():
    rules = load_fee_rules(supabase)
    return PlatformConfigResponse(
        investor_fee_rate=settings.investor_fee_rate,
        farmer_fee_rate=settings.farmer_fee_rate,
        investor_fee_tiers=rules["investor"],
        farmer_fee_tiers=rules["farmer"],
    )


@app.post("/api/config/fee-rules", response_model=PlatformConfigResponse)
async def update_platform_fee_rules(payload: PlatformConfigUpdate):
    from fastapi import HTTPException

    admin = supabase.table("users").select("id, role").eq("id", payload.admin_id).maybe_single().execute()
    if not admin or not admin.data or admin.data.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")

    rules = save_fee_rules(
        supabase,
        {
            "investor": [rule.model_dump() for rule in payload.investor_fee_tiers],
            "farmer": [rule.model_dump() for rule in payload.farmer_fee_tiers],
        },
    )
    return PlatformConfigResponse(
        investor_fee_rate=settings.investor_fee_rate,
        farmer_fee_rate=settings.farmer_fee_rate,
        investor_fee_tiers=rules["investor"],
        farmer_fee_tiers=rules["farmer"],
    )
