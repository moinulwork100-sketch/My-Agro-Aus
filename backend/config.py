from __future__ import annotations

import os
from dataclasses import dataclass


def _rate_from_env(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be a decimal rate such as 0.10") from exc
    if value < 0 or value > 1:
        raise RuntimeError(f"{name} must be between 0 and 1")
    return value


def _rate_with_fallback(name: str, fallback_name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is not None and raw.strip() != "":
        return _rate_from_env(name, default)
    return _rate_from_env(fallback_name, default)


def _cors_origins() -> list[str]:
    raw = os.environ.get("CORS_ORIGINS", "*")
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


@dataclass(frozen=True)
class Settings:
    investor_low_roi_fee_rate: float = _rate_with_fallback(
        "MYAGRO_INVESTOR_LOW_ROI_FEE_RATE",
        "MYAGRO_INVESTOR_FEE_RATE",
        0.10,
    )
    investor_medium_roi_fee_rate: float = _rate_from_env("MYAGRO_INVESTOR_MEDIUM_ROI_FEE_RATE", 0.15)
    investor_high_roi_fee_rate: float = _rate_from_env("MYAGRO_INVESTOR_HIGH_ROI_FEE_RATE", 0.25)
    farmer_under_10k_fee_rate: float = _rate_with_fallback(
        "MYAGRO_FARMER_UNDER_10K_FEE_RATE",
        "MYAGRO_FARMER_FEE_RATE",
        0.05,
    )
    farmer_10k_to_50k_fee_rate: float = _rate_from_env("MYAGRO_FARMER_10K_TO_50K_FEE_RATE", 0.10)
    farmer_above_50k_fee_rate: float = _rate_from_env("MYAGRO_FARMER_ABOVE_50K_FEE_RATE", 0.15)
    cors_origins: list[str] = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "cors_origins", _cors_origins())
        object.__setattr__(self, "investor_fee_rate", self.investor_low_roi_fee_rate)
        object.__setattr__(self, "farmer_fee_rate", self.farmer_under_10k_fee_rate)


settings = Settings()
