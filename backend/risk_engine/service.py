from __future__ import annotations

from datetime import date, datetime


CROP_RISK_ADJUSTMENTS = {
    "corn": 2,
    "wheat": 2,
    "rice": -1,
    "organic rice": -2,
    "livestock": 1,
    "potato": -3,
}


def _clamp(value: float, low: float = 0, high: float = 100) -> float:
    return max(low, min(high, value))


def _round(value: float, digits: int = 1) -> float:
    return round(float(value), digits)


def _parse_date(value) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _active_load_score(active_projects: int) -> float:
    if active_projects <= 1:
        return 100
    if active_projects == 2:
        return 90
    if active_projects == 3:
        return 75
    if active_projects == 4:
        return 60
    return max(30, 100 - active_projects * 12)


def _funding_adjustment(funding_goal: float) -> float:
    if funding_goal <= 0:
        return 0
    if funding_goal <= 10000:
        return 2
    if funding_goal <= 50000:
        return 1
    if funding_goal <= 250000:
        return 0
    if funding_goal <= 500000:
        return -2
    return -5


def _seasonal_adjustment(farm: dict) -> float:
    harvest_date = _parse_date(farm.get("harvest_date"))
    if not harvest_date:
        return 0
    crop = (farm.get("crop_type") or "").lower()
    month = harvest_date.month
    if crop in {"corn", "wheat"} and month in {9, 10, 11}:
        return 2
    if "rice" in crop and month in {11, 12, 1}:
        return 1
    if crop == "potato" and month in {8, 9, 10}:
        return 1
    return -1


def _level(score: float) -> str:
    if score >= 75:
        return "LOW"
    if score >= 55:
        return "MEDIUM"
    return "HIGH"


def score_project_risk(farm: dict, reputation: dict) -> dict:
    rating = float(reputation.get("overall_rating") or 0)
    completed_projects = int(reputation.get("total_completed_projects") or 0)
    success_rate = float(reputation.get("project_success_rate") or farm.get("success_rate") or 0)
    investor_rating = float(reputation.get("investor_satisfaction_score") or rating)
    active_projects = int(reputation.get("total_active_projects") or 0)
    failed_projects = int(reputation.get("failed_projects") or 0)

    factor_scores = {
        "farmer_reputation": _clamp(rating / 5 * 100),
        "success_rate": _clamp(success_rate),
        "project_completion_history": _clamp(completed_projects / 25 * 100),
        "investor_ratings": _clamp(investor_rating / 5 * 100),
        "active_project_load": _active_load_score(active_projects),
    }
    weighted_score = (
        factor_scores["farmer_reputation"] * 0.30
        + factor_scores["success_rate"] * 0.25
        + factor_scores["project_completion_history"] * 0.20
        + factor_scores["investor_ratings"] * 0.15
        + factor_scores["active_project_load"] * 0.10
    )

    crop_key = (farm.get("crop_type") or "").lower()
    crop_adjustment = CROP_RISK_ADJUSTMENTS.get(crop_key, 0)
    funding_goal = float(farm.get("total_funding_goal") or 0)
    funding_adjustment = _funding_adjustment(funding_goal)
    seasonal_adjustment = _seasonal_adjustment(farm)
    verification_adjustment = 3 if reputation.get("verification_status") == "Verified" else -3
    failure_adjustment = -min(failed_projects * 8, 24)

    score = _clamp(
        weighted_score
        + crop_adjustment
        + funding_adjustment
        + seasonal_adjustment
        + verification_adjustment
        + failure_adjustment
    )
    level = _level(score)

    reasons = [
        f"Farmer completed {completed_projects} projects.",
        f"{rating:.1f}-star investor reputation.",
        f"{success_rate:.0f}% historical success rate.",
        f"{active_projects} active project{'s' if active_projects != 1 else ''} currently.",
    ]
    if failed_projects:
        reasons.append(f"{failed_projects} failed or defaulted project{'s' if failed_projects != 1 else ''} in history.")
    else:
        reasons.append("No failed or defaulted projects recorded.")
    if crop_adjustment < 0:
        reasons.append(f"{farm.get('crop_type')} carries above-average crop execution risk.")
    if funding_adjustment < 0:
        reasons.append("Large funding goal increases delivery and oversight risk.")

    summary = (
        f"{level} RISK ({round(score)}/100): based on farmer reputation, success history, "
        "completion record, investor ratings, and active project load."
    )

    return {
        "risk_score": int(round(score)),
        "risk_level": level,
        "risk_reasoning_summary": summary,
        "risk_reasons": reasons,
        "risk_factors": {key: _round(value) for key, value in factor_scores.items()},
    }
