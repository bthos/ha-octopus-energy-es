"""Tariff type definitions and data structures."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..const import (
    CONF_DAYLIGHT_END,
    CONF_DAYLIGHT_START,
    CONF_DISCOUNT_PERCENTAGE,
    CONF_FIXED_RATE,
    CONF_P1_RATE,
    CONF_P2_RATE,
    CONF_P3_RATE,
    CONF_SOLAR_SURPLUS_RATE,
    DEFAULT_P1_HOURS,
    DEFAULT_P2_HOURS,
    DEFAULT_P3_HOURS,
    TARIFF_TYPE_FLEXI,
    TARIFF_TYPE_GO,
    TARIFF_TYPE_RELAX,
    TARIFF_TYPE_SOLAR,
    TARIFF_TYPE_SUN_CLUB,
)


@dataclass
class TariffConfig:
    """Base tariff configuration."""

    tariff_type: str


@dataclass
class FlexiTariffConfig(TariffConfig):
    """Octopus Flexi tariff configuration (variable market price)."""

    tariff_type: str = TARIFF_TYPE_FLEXI


@dataclass
class RelaxTariffConfig(TariffConfig):
    """Octopus Relax tariff configuration (fixed price)."""

    tariff_type: str = TARIFF_TYPE_RELAX
    fixed_rate: float = 0.0


@dataclass
class SolarTariffConfig(TariffConfig):
    """Octopus Solar tariff configuration (time-of-use)."""

    tariff_type: str = TARIFF_TYPE_SOLAR
    p1_rate: float = 0.0
    p2_rate: float = 0.0
    p3_rate: float = 0.0
    solar_surplus_rate: float = 0.04
    p1_hours: list[int] = None
    p2_hours: list[int] = None
    p3_hours: list[int] = None

    def __post_init__(self) -> None:
        """Set default period hours if not provided."""
        if self.p1_hours is None:
            self.p1_hours = DEFAULT_P1_HOURS.copy()
        if self.p2_hours is None:
            self.p2_hours = DEFAULT_P2_HOURS.copy()
        if self.p3_hours is None:
            self.p3_hours = DEFAULT_P3_HOURS.copy()


@dataclass
class GoTariffConfig(TariffConfig):
    """Octopus Go tariff configuration (EV tariff)."""

    tariff_type: str = TARIFF_TYPE_GO
    p1_rate: float = 0.0
    p2_rate: float = 0.0
    p3_rate: float = 0.0
    p1_hours: list[int] = None
    p2_hours: list[int] = None
    p3_hours: list[int] = None

    def __post_init__(self) -> None:
        """Set default period hours if not provided."""
        if self.p1_hours is None:
            self.p1_hours = DEFAULT_P1_HOURS.copy()
        if self.p2_hours is None:
            self.p2_hours = DEFAULT_P2_HOURS.copy()
        if self.p3_hours is None:
            self.p3_hours = DEFAULT_P3_HOURS.copy()


@dataclass
class SunClubTariffConfig(TariffConfig):
    """SUN CLUB tariff configuration (daylight discount)."""

    tariff_type: str = TARIFF_TYPE_SUN_CLUB
    daylight_start: int = 12
    daylight_end: int = 18
    discount_percentage: float = 0.45


def create_tariff_config(config_data: dict[str, Any]) -> TariffConfig:
    """
    Create appropriate tariff config from configuration data.

    Args:
        config_data: Configuration dictionary from config entry

    Returns:
        Appropriate TariffConfig instance
    """
    tariff_type = config_data.get("tariff_type", TARIFF_TYPE_FLEXI)

    if tariff_type == TARIFF_TYPE_FLEXI:
        return FlexiTariffConfig()

    elif tariff_type == TARIFF_TYPE_RELAX:
        return RelaxTariffConfig(
            fixed_rate=config_data.get(CONF_FIXED_RATE, 0.0),
        )

    elif tariff_type == TARIFF_TYPE_SOLAR:
        return SolarTariffConfig(
            p1_rate=config_data.get(CONF_P1_RATE, 0.0),
            p2_rate=config_data.get(CONF_P2_RATE, 0.0),
            p3_rate=config_data.get(CONF_P3_RATE, 0.0),
            solar_surplus_rate=config_data.get(CONF_SOLAR_SURPLUS_RATE, 0.04),
        )

    elif tariff_type == TARIFF_TYPE_GO:
        return GoTariffConfig(
            p1_rate=config_data.get(CONF_P1_RATE, 0.0),
            p2_rate=config_data.get(CONF_P2_RATE, 0.0),
            p3_rate=config_data.get(CONF_P3_RATE, 0.0),
        )

    elif tariff_type == TARIFF_TYPE_SUN_CLUB:
        return SunClubTariffConfig(
            daylight_start=config_data.get(CONF_DAYLIGHT_START, 12),
            daylight_end=config_data.get(CONF_DAYLIGHT_END, 18),
            discount_percentage=config_data.get(CONF_DISCOUNT_PERCENTAGE, 0.45),
        )

    else:
        # Default to Flexi
        return FlexiTariffConfig()

