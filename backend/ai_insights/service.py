from __future__ import annotations


def _investor_fit(risk_level: str) -> str:
    if risk_level == "LOW":
        return "suitable for conservative investors"
    if risk_level == "MEDIUM":
        return "better suited to investors comfortable with balanced risk"
    return "best reserved for investors seeking higher-risk, higher-return exposure"


def project_investment_insight(farm: dict, reputation: dict, risk: dict) -> str:
    farmer_name = farm.get("farmer_name") or farm.get("name") or "This farmer"
    completed = reputation.get("total_completed_projects") or 0
    success_rate = reputation.get("project_success_rate") or farm.get("success_rate") or 0
    rating = reputation.get("overall_rating") or 0
    active_projects = reputation.get("total_active_projects") or 0
    risk_level = risk.get("risk_level") or "MEDIUM"
    risk_score = risk.get("risk_score") or 0

    return (
        f"{farmer_name} has completed {completed} projects with a {success_rate:.0f}% success rate "
        f"and maintains a {rating:.1f}-star investor rating. Based on historical performance, "
        f"current active project load ({active_projects}), and the project funding profile, this project "
        f"is considered {risk_level} RISK ({risk_score}/100) and is {_investor_fit(risk_level)}."
    )
