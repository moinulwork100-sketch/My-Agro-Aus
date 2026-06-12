from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException

from backend.db import supabase
from backend.deps import not_found
from backend.schemas import (
    AdminLogin,
    AuthSession,
    EmailVerificationRequest,
    EmailVerificationResend,
    EmailVerificationResponse,
    FarmerLogin,
    FarmerOnboardingRegister,
    FarmerRegister,
    InvestorRegister,
    LoginCredentials,
    PasswordResetConfirm,
    PasswordResetRequest,
    PasswordResetResponse,
    ProfileUpdate,
    UserCreate,
)

router = APIRouter()

RESET_TOKEN_MINUTES = 30
EMAIL_TOKEN_HOURS = 24
PROFILE_COMPLETION_THRESHOLD = 75


def _has_value(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (list, tuple, set)):
        return len(value) > 0
    if isinstance(value, str):
        return bool(value.strip())
    return value is not None


def _completion(requirements: list[tuple[str, object]]) -> tuple[int, list[str]]:
    if not requirements:
        return 100, []
    missing = [label for label, value in requirements if not _has_value(value)]
    completed = len(requirements) - len(missing)
    return round((completed / len(requirements)) * 100), missing


def _list_value(value) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, tuple):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return []


def _load_farmer(farmer_id: str | None) -> dict | None:
    if not farmer_id:
        return None
    try:
        result = supabase.table("farmers").select("*").eq("id", farmer_id).execute()
    except Exception:
        return None
    return result.data[0] if result.data else None


def _farmer_photo(farmer: dict | None) -> str | None:
    if not farmer:
        return None
    return farmer.get("profile_photo_url") or farmer.get("portrait_url")


def _profile_completion(user: dict, farmer: dict | None = None) -> tuple[int, list[str]]:
    email_verified = True if "email_verified" not in user else bool(user.get("email_verified"))
    common = [
        ("Full Name", user.get("name")),
        ("Email Address", user.get("email")),
        ("Phone Number", user.get("phone")),
        ("Country", user.get("country") or user.get("location")),
    ]
    if user.get("role") == "farmer":
        requirements = common + [
            ("Farm Name", farmer.get("farm_name") if farmer else None),
            ("Farm Location", farmer.get("farm_location") if farmer else None),
            ("Farming Experience", farmer.get("years_experience") if farmer else None),
            ("Farm Size", farmer.get("farm_size") if farmer else None),
            ("Crop Categories", _list_value(farmer.get("crop_categories")) if farmer else []),
            ("Farm Description", farmer.get("bio") if farmer else None),
            ("Upload Profile Photo", _farmer_photo(farmer)),
            ("Verify Email", email_verified),
        ]
        return _completion(requirements)

    if user.get("role") == "investor":
        requirements = common + [
            ("Investor Type", user.get("investor_type")),
            ("Investment Interests", _list_value(user.get("investment_interests"))),
            ("Risk Tolerance", user.get("risk_tolerance")),
            ("Preferred Crops", _list_value(user.get("preferred_crops"))),
            ("Preferred Investment Size", user.get("preferred_investment_size")),
            ("Verify Email", email_verified),
        ]
        return _completion(requirements)

    return 100, []


def _session_from_user(
    user: dict,
    *,
    remember_me: bool = False,
    email_verification_token: str | None = None,
) -> AuthSession:
    farmer = _load_farmer(user.get("farmer_id")) if user.get("role") == "farmer" else None
    profile_completion, missing = _profile_completion(user, farmer)
    email_verified = True if "email_verified" not in user else bool(user.get("email_verified"))
    session_hours = 24 * 30 if remember_me else 8
    return AuthSession(
        id=user["id"],
        name=user["name"],
        email=user["email"],
        role=user.get("role", "investor"),
        farmer_id=user.get("farmer_id"),
        phone=user.get("phone"),
        location=user.get("location"),
        country=user.get("country") or user.get("location"),
        email_verified=email_verified,
        profile_completion=profile_completion,
        profile_minimum_met=profile_completion >= PROFILE_COMPLETION_THRESHOLD,
        missing_profile_items=missing,
        investor_type=user.get("investor_type"),
        investment_interests=_list_value(user.get("investment_interests")),
        risk_tolerance=user.get("risk_tolerance"),
        preferred_crops=_list_value(user.get("preferred_crops")),
        preferred_investment_size=user.get("preferred_investment_size"),
        kyc_status=user.get("kyc_status"),
        government_id_verification=user.get("government_id_verification"),
        bank_verification=user.get("bank_verification"),
        farm_name=farmer.get("farm_name") if farmer else None,
        farm_location=farmer.get("farm_location") if farmer else None,
        farming_experience_years=farmer.get("years_experience") if farmer else None,
        farm_size=farmer.get("farm_size") if farmer else None,
        crop_categories=_list_value(farmer.get("crop_categories")) if farmer else [],
        farm_description=farmer.get("bio") if farmer else None,
        profile_photo_url=_farmer_photo(farmer) or user.get("profile_photo_url"),
        land_ownership_verification=farmer.get("land_ownership_verification") if farmer else None,
        farm_inspection_verification=farmer.get("farm_inspection_verification") if farmer else None,
        banking_verification=farmer.get("banking_verification") if farmer else None,
        email_verification_token=email_verification_token,
        session_expires_at=datetime.now(timezone.utc) + timedelta(hours=session_hours),
        created_at=user.get("created_at"),
    )


def _password_hash(password: str) -> str:
    salt = os.urandom(16).hex()
    iterations = 260000
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations).hex()
    return f"pbkdf2_sha256${iterations}${salt}${digest}"


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _verify_password(password: str, stored_hash: str | None, *, legacy_email: str | None = None) -> bool:
    if stored_hash:
        try:
            algorithm, iterations, salt, expected = stored_hash.split("$", 3)
            if algorithm != "pbkdf2_sha256":
                return False
            digest = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                salt.encode("utf-8"),
                int(iterations),
            ).hex()
            return hmac.compare_digest(digest, expected)
        except (TypeError, ValueError):
            return False

    # Compatibility for existing seeded/dev users before password_hash existed.
    return bool(legacy_email and hmac.compare_digest(password, legacy_email))


def _find_user_by_email(email: str) -> dict:
    result = supabase.table("users").select("*").eq("email", email).execute()
    if not result.data:
        raise not_found("Account", email)
    return result.data[0]


def _find_user_by_id(user_id: str) -> dict:
    result = supabase.table("users").select("*").eq("id", user_id).execute()
    if not result.data:
        raise not_found("Account", user_id)
    return result.data[0]


def _ensure_email_available(email: str) -> None:
    result = supabase.table("users").select("id").eq("email", email).execute()
    if result.data:
        raise HTTPException(status_code=409, detail="An account with this email already exists")


def _authenticate_email_password(email: str, password: str) -> dict:
    email = email.strip().lower()
    if not email or not password:
        raise HTTPException(status_code=422, detail="Email and password are required")
    user = _find_user_by_email(email)
    if not _verify_password(password, user.get("password_hash"), legacy_email=user.get("email")):
        raise HTTPException(status_code=403, detail="Invalid email or password")
    return user


def _insert_user(values: dict) -> dict:
    password = values.pop("password", None)
    insert_values = dict(values)
    if password:
        insert_values["password_hash"] = _password_hash(password)

    try:
        result = supabase.table("users").insert(insert_values).execute()
    except Exception:
        # Older dev databases may not have password_hash until schema.sql is applied.
        insert_values.pop("password_hash", None)
        result = supabase.table("users").insert(insert_values).execute()

    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create user account")
    return result.data[0]


def _create_email_verification_token(user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=EMAIL_TOKEN_HOURS)).isoformat()
    try:
        supabase.table("email_verification_tokens").insert(
            {
                "user_id": user_id,
                "token_hash": _token_hash(token),
                "expires_at": expires_at,
                "used_at": None,
            }
        ).execute()
    except Exception:
        raise HTTPException(status_code=500, detail="Email verification storage is not configured")
    return token


@router.post("/login", response_model=AuthSession)
async def login(payload: LoginCredentials):
    user = _authenticate_email_password(payload.email, payload.password)
    return _session_from_user(user, remember_me=payload.remember_me)


@router.post("/register/investor", response_model=AuthSession, status_code=201)
async def register_investor(payload: InvestorRegister):
    email = payload.email.strip().lower()
    _ensure_email_available(email)
    user = _insert_user(
        {
            "name": payload.name.strip(),
            "email": email,
            "phone": payload.phone.strip(),
            "country": payload.country.strip(),
            "location": payload.country.strip(),
            "role": "investor",
            "password": payload.password,
            "email_verified": False,
            "investor_type": payload.investor_type,
            "investment_interests": payload.investment_interests,
            "risk_tolerance": payload.risk_tolerance,
            "preferred_crops": payload.preferred_crops,
            "preferred_investment_size": payload.preferred_investment_size,
            "kyc_status": payload.kyc_status,
            "government_id_verification": payload.government_id_verification,
            "bank_verification": payload.bank_verification,
        }
    )
    token = _create_email_verification_token(user["id"])
    return _session_from_user(user, remember_me=payload.remember_me, email_verification_token=token)


@router.post("/register/farmer", response_model=AuthSession, status_code=201)
async def register_farmer_onboarding(payload: FarmerOnboardingRegister):
    email = payload.email.strip().lower()
    _ensure_email_available(email)

    farmer_values = {
        "name": payload.name.strip(),
        "email": email,
        "verified": False,
        "rating": 0,
        "completed_projects": 0,
        "on_time_rate": 0,
        "years_experience": payload.farming_experience_years,
        "risk_classification": "PENDING",
        "bio": payload.farm_description.strip(),
        "portrait_url": payload.profile_photo_url,
        "farm_name": payload.farm_name.strip(),
        "farm_location": payload.farm_location.strip(),
        "farm_size": payload.farm_size.strip(),
        "crop_categories": payload.crop_categories,
        "land_ownership_verification": payload.land_ownership_verification,
        "government_id_verification": payload.government_id_verification,
        "farm_inspection_verification": payload.farm_inspection_verification,
        "banking_verification": payload.banking_verification,
    }
    farmer_result = supabase.table("farmers").insert(farmer_values).execute()
    if not farmer_result.data:
        raise HTTPException(status_code=500, detail="Failed to create farmer profile")
    farmer = farmer_result.data[0]

    user = _insert_user(
        {
            "name": payload.name.strip(),
            "email": email,
            "phone": payload.phone.strip(),
            "country": payload.country.strip(),
            "location": payload.country.strip(),
            "role": "farmer",
            "farmer_id": farmer["id"],
            "password": payload.password,
            "email_verified": False,
        }
    )
    token = _create_email_verification_token(user["id"])
    return _session_from_user(user, remember_me=payload.remember_me, email_verification_token=token)


@router.post("/email/resend", response_model=EmailVerificationResponse)
async def resend_email_verification(payload: EmailVerificationResend):
    user = _find_user_by_id(payload.user_id)
    if bool(user.get("email_verified")):
        return EmailVerificationResponse(message="Email is already verified.")
    token = _create_email_verification_token(user["id"])
    return EmailVerificationResponse(message="Verification email has been sent.", verification_token=token)


@router.post("/email/verify", response_model=AuthSession)
async def verify_email(payload: EmailVerificationRequest):
    token_hash = _token_hash(payload.token)
    result = (
        supabase.table("email_verification_tokens")
        .select("*")
        .eq("token_hash", token_hash)
        .is_("used_at", "null")
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=403, detail="Invalid or expired verification token")

    verification_row = result.data[0]
    expires_at = datetime.fromisoformat(str(verification_row["expires_at"]).replace("Z", "+00:00"))
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=403, detail="Invalid or expired verification token")

    try:
        supabase.table("users").update(
            {
                "email_verified": True,
                "email_verified_at": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("id", verification_row["user_id"]).execute()
        supabase.table("email_verification_tokens").update(
            {"used_at": datetime.now(timezone.utc).isoformat()}
        ).eq("id", verification_row["id"]).execute()
    except Exception:
        raise HTTPException(status_code=500, detail="Email verification storage is not configured")

    user = _find_user_by_id(verification_row["user_id"])
    return _session_from_user(user)


@router.patch("/profile/{user_id}", response_model=AuthSession)
async def update_profile(user_id: str, payload: ProfileUpdate):
    user = _find_user_by_id(user_id)
    values = payload.model_dump(exclude_unset=True)

    user_updates = {}
    for key in ("phone", "country", "investor_type", "investment_interests", "risk_tolerance", "preferred_crops", "preferred_investment_size", "profile_photo_url"):
        if key in values:
            user_updates[key] = values[key]
    if "country" in user_updates:
        user_updates["location"] = user_updates["country"]

    if user_updates:
        result = supabase.table("users").update(user_updates).eq("id", user_id).execute()
        if result.data:
            user = result.data[0]
        else:
            user = _find_user_by_id(user_id)

    if user.get("role") == "farmer":
        farmer_updates = {}
        farmer_map = {
            "farm_name": "farm_name",
            "farm_location": "farm_location",
            "farming_experience_years": "years_experience",
            "farm_size": "farm_size",
            "crop_categories": "crop_categories",
            "farm_description": "bio",
            "profile_photo_url": "portrait_url",
        }
        for payload_key, db_key in farmer_map.items():
            if payload_key in values:
                farmer_updates[db_key] = values[payload_key]
        if farmer_updates:
            if not user.get("farmer_id"):
                raise HTTPException(status_code=422, detail="Farmer profile is not linked to this account")
            supabase.table("farmers").update(farmer_updates).eq("id", user["farmer_id"]).execute()

    return _session_from_user(_find_user_by_id(user_id))


@router.post("/investor", response_model=AuthSession, status_code=201)
async def investor_login(payload: UserCreate):
    password = payload.password or payload.email
    try:
        user = _authenticate_email_password(payload.email, password)
    except HTTPException as exc:
        if exc.status_code != 404 or not payload.name:
            raise
        user = _insert_user(
            {
                "name": payload.name,
                "email": payload.email.strip().lower(),
                "role": "investor",
                "password": password,
            }
        )
    if user.get("role") != "investor":
        raise HTTPException(status_code=422, detail="This email is not registered as an investor")
    return _session_from_user(user, remember_me=payload.remember_me)


@router.post("/farmer/register", response_model=AuthSession, status_code=201)
async def farmer_register(payload: FarmerRegister):
    existing_user = supabase.table("users").select("*").eq("email", payload.email).execute()
    if existing_user.data:
        user = existing_user.data[0]
        if user.get("role") != "farmer":
            raise HTTPException(status_code=422, detail="This email is already registered with another role")
        if payload.password and not _verify_password(payload.password, user.get("password_hash"), legacy_email=user.get("email")):
            raise HTTPException(status_code=403, detail="Invalid email or password")
        return _session_from_user(user)

    try:
        existing_farmer = supabase.table("farmers").select("*").eq("email", payload.email).execute()
        farmer = existing_farmer.data[0] if existing_farmer.data else None
    except Exception:
        farmer = None

    if not farmer:
        farmer_values = {
            "name": payload.name,
            "email": payload.email,
            "verified": False,
            "rating": 0,
            "completed_projects": 0,
            "on_time_rate": 0,
            "risk_classification": "PENDING",
            "bio": "New MyAgro farmer profile pending verification.",
        }
        try:
            farmer_result = supabase.table("farmers").insert(farmer_values).execute()
        except Exception:
            farmer_values.pop("email", None)
            farmer_result = supabase.table("farmers").insert(farmer_values).execute()
        if not farmer_result.data:
            raise HTTPException(status_code=500, detail="Failed to create farmer profile")
        farmer = farmer_result.data[0]

    user = _insert_user(
        {
            "name": payload.name,
            "email": payload.email.strip().lower(),
            "phone": payload.phone,
            "location": payload.location,
            "role": "farmer",
            "farmer_id": farmer["id"],
            "password": payload.password or payload.email,
        }
    )
    return _session_from_user(user)


@router.post("/farmer/login", response_model=AuthSession)
async def farmer_login(payload: FarmerLogin):
    email = payload.email or payload.identifier or ""
    user = _authenticate_email_password(email, payload.password)
    if user.get("role") != "farmer":
        raise HTTPException(status_code=422, detail="This email is not registered as a farmer")
    return _session_from_user(user, remember_me=payload.remember_me)


@router.post("/admin/login", response_model=AuthSession)
async def admin_login(payload: AdminLogin):
    email = payload.email or ""
    password = payload.password or payload.access_code or ""
    user = _authenticate_email_password(email, password)
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return _session_from_user(user)


@router.post("/password/forgot", response_model=PasswordResetResponse)
async def forgot_password(payload: PasswordResetRequest):
    email = payload.email.strip().lower()
    # Do not reveal whether an email exists.
    message = "If an account exists for this email, a password reset link has been sent."
    try:
        user = _find_user_by_email(email)
    except HTTPException:
        return PasswordResetResponse(message=message)

    token = secrets.token_urlsafe(32)
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=RESET_TOKEN_MINUTES)).isoformat()
    try:
        supabase.table("password_reset_tokens").insert(
            {
                "user_id": user["id"],
                "token_hash": _token_hash(token),
                "expires_at": expires_at,
                "used_at": None,
            }
        ).execute()
    except Exception:
        return PasswordResetResponse(message=message)

    # In production this token is sent by email. Returning it in dev keeps the MVP testable.
    return PasswordResetResponse(message=message, reset_token=token)


@router.post("/password/reset", response_model=PasswordResetResponse)
async def reset_password(payload: PasswordResetConfirm):
    token_hash = _token_hash(payload.token)
    result = (
        supabase.table("password_reset_tokens")
        .select("*")
        .eq("token_hash", token_hash)
        .is_("used_at", "null")
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=403, detail="Invalid or expired reset token")

    reset_row = result.data[0]
    expires_at = datetime.fromisoformat(str(reset_row["expires_at"]).replace("Z", "+00:00"))
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=403, detail="Invalid or expired reset token")

    try:
        supabase.table("users").update({"password_hash": _password_hash(payload.password)}).eq("id", reset_row["user_id"]).execute()
        supabase.table("password_reset_tokens").update({"used_at": datetime.now(timezone.utc).isoformat()}).eq("id", reset_row["id"]).execute()
    except Exception:
        raise HTTPException(status_code=500, detail="Password reset storage is not configured")

    return PasswordResetResponse(message="Password has been reset.")
