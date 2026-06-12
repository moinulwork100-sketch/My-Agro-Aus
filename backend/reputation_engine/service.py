from __future__ import annotations

from backend.calculations import ensure_financial_fields


def _round(value: float, digits: int = 2) -> float:
    return round(float(value), digits)


def _avg(values: list[float], default: float = 0) -> float:
    cleaned = [float(value) for value in values if value is not None]
    if not cleaned:
        return default
    return sum(cleaned) / len(cleaned)


def _status_completed(value: str | None) -> bool:
    return (value or "").lower() == "completed"


def build_reputation_profile(
    farmer: dict,
    farms: list[dict] | None = None,
    investments: list[dict] | None = None,
    reviews: list[dict] | None = None,
) -> dict:
    farms = farms or []
    investments = investments or []
    reviews = reviews or []

    completed_from_farms = sum(1 for farm in farms if _status_completed(farm.get("status")))
    completed_projects = max(int(farmer.get("completed_projects") or 0), completed_from_farms)
    active_projects = sum(1 for farm in farms if (farm.get("status") or "").lower() == "active")
    funded_projects = sum(1 for farm in farms if int(farm.get("funded_percent") or 0) >= 100)
    failed_projects = sum(1 for farm in farms if (farm.get("status") or "").lower() in {"failed", "defaulted"})

    shaped_investments = []
    for investment in investments:
        farm = next((item for item in farms if item.get("id") == investment.get("farm_id")), None)
        shaped_investments.append(ensure_financial_fields(dict(investment), farm_data=farm))

    total_investment_received = sum(float(item.get("amount") or 0) for item in shaped_investments)
    total_profit_generated = sum(float(item.get("gross_profit") or 0) for item in shaped_investments)

    review_scores = [float(review.get("rating")) for review in reviews if review.get("rating") is not None]
    stored_rating = float(farmer.get("rating") or 0)
    investor_satisfaction_score = _avg(review_scores, stored_rating)
    overall_rating = investor_satisfaction_score or stored_rating

    success_values = [float(farm.get("success_rate")) for farm in farms if farm.get("success_rate") is not None]
    if success_values:
        project_success_rate = _round(_avg(success_values), 1)
    else:
        total_history = completed_projects + failed_projects
        project_success_rate = _round((completed_projects / total_history) * 100 if total_history else 0, 1)

    on_time_completion_rate = _round(float(farmer.get("on_time_rate") or 0), 1)
    crop_categories = sorted({farm.get("crop_type") for farm in farms if farm.get("crop_type")})
    years_experience = int(farmer.get("years_experience") or max(1, round(completed_projects / 2)))
    verification_status = "Verified" if farmer.get("verified") else "Pending Verification"

    performance = []
    for farm in farms:
        farm_investments = [item for item in shaped_investments if item.get("farm_id") == farm.get("id")]
        raised = sum(float(item.get("amount") or 0) for item in farm_investments)
        profit = sum(float(item.get("gross_profit") or 0) for item in farm_investments)
        performance.append(
            {
                "farm_id": farm.get("id"),
                "name": farm.get("name"),
                "crop_type": farm.get("crop_type"),
                "status": farm.get("status"),
                "success_rate": farm.get("success_rate"),
                "funded_percent": farm.get("funded_percent"),
                "total_raised": _round(raised),
                "profit_generated": _round(profit),
                "completed_on_time": _status_completed(farm.get("status")) and on_time_completion_rate >= 80,
            }
        )

    reputation_score = (
        min(overall_rating / 5 * 100, 100) * 0.35
        + project_success_rate * 0.30
        + min(completed_projects / 25 * 100, 100) * 0.20
        + on_time_completion_rate * 0.15
    )

    return {
        "overall_rating": _round(overall_rating, 1),
        "reputation_score": _round(reputation_score, 1),
        "total_completed_projects": completed_projects,
        "total_active_projects": active_projects,
        "total_funded_projects": funded_projects,
        "total_investment_received": _round(total_investment_received),
        "total_profit_generated": _round(total_profit_generated),
        "project_success_rate": project_success_rate,
        "on_time_completion_rate": on_time_completion_rate,
        "investor_satisfaction_score": _round(investor_satisfaction_score, 1),
        "years_experience": years_experience,
        "crop_categories": crop_categories,
        "verification_status": verification_status,
        "failed_projects": failed_projects,
        "historical_project_performance": performance,
    }
