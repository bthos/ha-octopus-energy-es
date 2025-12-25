"""Tariff type definitions and data structures."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..const import (
    CONF_DISCOUNT_START_HOUR,
    CONF_DISCOUNT_END_HOUR,
    CONF_DISCOUNT_PERCENTAGE,
    CONF_FIXED_RATE,
    CONF_MANAGEMENT_FEE_MONTHLY,
    CONF_P1_HOURS_WEEKDAYS,
    CONF_P1_RATE,
    CONF_P2_HOURS_WEEKDAYS,
    CONF_P2_RATE,
    CONF_P3_HOURS_WEEKDAYS,
    CONF_P3_RATE,
    CONF_POWER_P1_RATE,
    CONF_POWER_P2_RATE,
    CONF_PRICING_MODEL,
    CONF_SOLAR_SURPLUS_RATE,
    CONF_TIME_STRUCTURE,
    DEFAULT_P1_HOURS_WEEKDAYS,
    DEFAULT_P2_HOURS_WEEKDAYS,
    DEFAULT_P3_HOURS_WEEKDAYS,
    PRICING_MODEL_FIXED,
    PRICING_MODEL_MARKET,
    TIME_STRUCTURE_SINGLE_RATE,
    TIME_STRUCTURE_TIME_OF_USE,
)


@dataclass
class TariffConfig:
    """Unified tariff configuration based on categories."""

    # Core categories
    pricing_model: str  # "fixed" or "market"
    time_structure: str  # "single_rate" or "time_of_use"

    # Energy Rates
    fixed_rate: float | None = None
    p1_rate: float | None = None
    p2_rate: float | None = None
    p3_rate: float | None = None

    # Period Hours (for time-of-use, weekdays only)
    # Weekends/holidays: All hours are P3 (handled in calculator logic)
    p1_hours_weekdays: list[int] = field(default_factory=lambda: DEFAULT_P1_HOURS_WEEKDAYS.copy())
    p2_hours_weekdays: list[int] = field(default_factory=lambda: DEFAULT_P2_HOURS_WEEKDAYS.copy())
    p3_hours_weekdays: list[int] = field(default_factory=lambda: DEFAULT_P3_HOURS_WEEKDAYS.copy())

    # Power Rates (Potencia) - Always time-of-use with P1/P2 structure
    power_p1_rate: float | None = None  # €/kW/day (Punta period)
    power_p2_rate: float | None = None  # €/kW/day (Valle period = P2 + P3)

    # Solar Features
    solar_surplus_rate: float | None = None  # Compensation rate for surplus energy (€/kWh)
    # Note: Solar Wallet balance is retrieved from API, not configured here

    # Management Fees
    management_fee_monthly: float | None = None  # €/month

    # Discount Programs
    discount_start_hour: int | None = None  # 0-23
    discount_end_hour: int | None = None  # 0-23
    discount_percentage: float | None = None  # 0-1 (0-100%)

    def __post_init__(self) -> None:
        """Validate configuration."""
        if self.pricing_model not in (PRICING_MODEL_FIXED, PRICING_MODEL_MARKET):
            raise ValueError(f"Invalid pricing_model: {self.pricing_model}")

        if self.time_structure not in (TIME_STRUCTURE_SINGLE_RATE, TIME_STRUCTURE_TIME_OF_USE):
            raise ValueError(f"Invalid time_structure: {self.time_structure}")

        # Validate period hours cover all 24 hours for weekdays
        all_hours = set(self.p1_hours_weekdays + self.p2_hours_weekdays + self.p3_hours_weekdays)
        if all_hours != set(range(24)):
            missing = set(range(24)) - all_hours
            raise ValueError(f"Period hours don't cover all 24 hours. Missing: {missing}")

        # Validate discount hours if discount is enabled
        if self.discount_percentage is not None:
            if self.discount_start_hour is None or self.discount_end_hour is None:
                raise ValueError("discount_start_hour and discount_end_hour required when discount_percentage is set")
            if not (0 <= self.discount_start_hour <= 23 and 0 <= self.discount_end_hour <= 23):
                raise ValueError("discount hours must be between 0 and 23")
            if not (0 <= self.discount_percentage <= 1):
                raise ValueError("discount_percentage must be between 0 and 1")


def create_tariff_config(config_data: dict[str, Any]) -> TariffConfig:
    """
    Create tariff config from configuration data.

    Args:
        config_data: Configuration dictionary from config entry

    Returns:
        TariffConfig instance
    """
    return TariffConfig(
        pricing_model=config_data.get(CONF_PRICING_MODEL, PRICING_MODEL_MARKET),
        time_structure=config_data.get(CONF_TIME_STRUCTURE, TIME_STRUCTURE_SINGLE_RATE),
        fixed_rate=config_data.get(CONF_FIXED_RATE),
        p1_rate=config_data.get(CONF_P1_RATE),
        p2_rate=config_data.get(CONF_P2_RATE),
        p3_rate=config_data.get(CONF_P3_RATE),
        p1_hours_weekdays=config_data.get(
            CONF_P1_HOURS_WEEKDAYS, DEFAULT_P1_HOURS_WEEKDAYS.copy()
        ),
        p2_hours_weekdays=config_data.get(
            CONF_P2_HOURS_WEEKDAYS, DEFAULT_P2_HOURS_WEEKDAYS.copy()
        ),
        p3_hours_weekdays=config_data.get(
            CONF_P3_HOURS_WEEKDAYS, DEFAULT_P3_HOURS_WEEKDAYS.copy()
        ),
        power_p1_rate=config_data.get(CONF_POWER_P1_RATE),
        power_p2_rate=config_data.get(CONF_POWER_P2_RATE),
        solar_surplus_rate=config_data.get(CONF_SOLAR_SURPLUS_RATE),
        management_fee_monthly=config_data.get(CONF_MANAGEMENT_FEE_MONTHLY),
        discount_start_hour=config_data.get(CONF_DISCOUNT_START_HOUR),
        discount_end_hour=config_data.get(CONF_DISCOUNT_END_HOUR),
        discount_percentage=config_data.get(CONF_DISCOUNT_PERCENTAGE),
    )
