from __future__ import annotations


MILESTONES = [
    "Planning",
    "Land Preparation",
    "Planting",
    "Growing",
    "Harvesting",
    "Distribution",
    "Completed",
]


def milestone_progress_percent(milestone: str) -> int:
    if milestone not in MILESTONES:
        return 0
    if len(MILESTONES) == 1:
        return 100
    return round((MILESTONES.index(milestone) / (len(MILESTONES) - 1)) * 100)


def normalize_progress_payload(payload: dict) -> dict:
    milestone = payload.get("milestone") or payload.get("stage") or "Planning"
    progress_percent = payload.get("progress_percent")
    if progress_percent is None:
        progress_percent = milestone_progress_percent(milestone)
    progress_percent = max(0, min(100, int(progress_percent)))

    return {
        "milestone": milestone,
        "stage": payload.get("stage") or milestone,
        "progress_percent": progress_percent,
        "health": payload.get("health"),
        "weather": payload.get("weather"),
        "photo_url": payload.get("photo_url"),
        "video_url": payload.get("video_url"),
        "document_url": payload.get("document_url"),
        "yield_report": payload.get("yield_report"),
        "expense_report": payload.get("expense_report"),
        "notes": payload.get("notes"),
    }


def build_timeline(farm: dict, updates: list[dict]) -> dict:
    latest = updates[0] if updates else {}
    milestone = latest.get("milestone") or farm.get("current_milestone") or "Planning"
    progress_percent = latest.get("progress_percent")
    if progress_percent is None:
        progress_percent = farm.get("progress_percent")
    if progress_percent is None:
        progress_percent = milestone_progress_percent(milestone)

    completed_milestones = set()
    for update in updates:
        if update.get("milestone"):
            completed_milestones.add(update["milestone"])

    return {
        "start_date": farm.get("created_at"),
        "current_milestone": milestone,
        "expected_completion_date": farm.get("expected_completion_date") or farm.get("harvest_date"),
        "progress_percent": int(progress_percent),
        "latest_update": latest or None,
        "milestones": [
            {
                "label": item,
                "status": "current" if item == milestone else "completed" if item in completed_milestones else "pending",
            }
            for item in MILESTONES
        ],
    }
