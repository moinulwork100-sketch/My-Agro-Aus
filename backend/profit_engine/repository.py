from __future__ import annotations

from backend.profit_engine.service import fee_rules, fee_rules_from_rows


def load_fee_rules(client) -> dict[str, list[dict]]:
    try:
        result = (
            client.table("platform_fee_rules")
            .select("*")
            .order("sort_order")
            .execute()
        )
    except Exception:
        return fee_rules()
    rows = result.data or []
    if not rows:
        return fee_rules()
    return fee_rules_from_rows(rows)


def save_fee_rules(client, rules: dict[str, list[dict]]) -> dict[str, list[dict]]:
    rows = []
    sort_order = 0
    for audience in ("investor", "farmer"):
        for rule in rules.get(audience, []):
            sort_order += 1
            rows.append(
                {
                    "id": rule.get("id") or f"{audience}_{sort_order}",
                    "audience": audience,
                    "label": rule["label"],
                    "rate": rule["rate"],
                    "minimum": rule.get("minimum"),
                    "maximum": rule.get("maximum"),
                    "sort_order": sort_order,
                }
            )
    if rows:
        try:
            client.table("platform_fee_rules").upsert(rows).execute()
        except Exception as exc:
            from fastapi import HTTPException
            raise HTTPException(status_code=500, detail="Failed to save fee rules") from exc
    return load_fee_rules(client)
