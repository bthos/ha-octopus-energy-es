"""Tariff calculation engine for Octopus Energy Spain."""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any

from zoneinfo import ZoneInfo

from ..const import TIMEZONE_MADRID
from .types import (
    FlexiTariffConfig,
    GoTariffConfig,
    RelaxTariffConfig,
    SolarTariffConfig,
    SunClubTariffConfig,
    TariffConfig,
)

_LOGGER = logging.getLogger(__name__)


class TariffCalculator:
    """Calculator for different tariff types."""

    def __init__(self, config: TariffConfig) -> None:
        """Initialize tariff calculator."""
        self._config = config
        self._timezone = ZoneInfo(TIMEZONE_MADRID)

    def calculate_prices(
        self,
        market_prices: list[dict[str, Any]],
        target_date: date | None = None,
    ) -> list[dict[str, Any]]:
        """
        Calculate prices based on tariff configuration.

        Args:
            market_prices: List of market price data with 'start_time' and 'price_per_kwh'
            target_date: Target date for calculation

        Returns:
            List of calculated price data with 'start_time' and 'price_per_kwh'
        """
        if isinstance(self._config, FlexiTariffConfig):
            return self._calculate_flexi(market_prices)

        elif isinstance(self._config, RelaxTariffConfig):
            return self._calculate_relax(market_prices)

        elif isinstance(self._config, SolarTariffConfig):
            return self._calculate_solar(market_prices, target_date)

        elif isinstance(self._config, GoTariffConfig):
            return self._calculate_go(market_prices, target_date)

        elif isinstance(self._config, SunClubTariffConfig):
            return self._calculate_sun_club(market_prices, target_date)

        else:
            _LOGGER.warning("Unknown tariff type: %s", self._config.tariff_type)
            return market_prices

    def _calculate_flexi(
        self, market_prices: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Calculate Flexi prices (direct market price)."""
        # Flexi uses market price directly with 0€/kWh admin cost
        return [
            {
                "start_time": price["start_time"],
                "price_per_kwh": round(price["price_per_kwh"], 6),
            }
            for price in market_prices
        ]

    def _calculate_relax(
        self, market_prices: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Calculate Relax prices (fixed rate)."""
        config: RelaxTariffConfig = self._config  # type: ignore

        return [
            {
                "start_time": price["start_time"],
                "price_per_kwh": round(config.fixed_rate, 6),
            }
            for price in market_prices
        ]

    def _calculate_solar(
        self, market_prices: list[dict[str, Any]], target_date: date | None
    ) -> list[dict[str, Any]]:
        """Calculate Solar prices (time-of-use P1/P2/P3)."""
        config: SolarTariffConfig = self._config  # type: ignore

        if target_date is None:
            target_date = datetime.now(self._timezone).date()

        calculated_prices: list[dict[str, Any]] = []

        for price_data in market_prices:
            start_time_str = price_data["start_time"]
            dt = datetime.fromisoformat(start_time_str)

            # Ensure timezone-aware
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=self._timezone)
            else:
                dt = dt.astimezone(self._timezone)

            hour = dt.hour

            # Determine period
            if hour in config.p1_hours:
                rate = config.p1_rate
            elif hour in config.p2_hours:
                rate = config.p2_rate
            elif hour in config.p3_hours:
                rate = config.p3_rate
            else:
                # Default to P2 if not in any period
                rate = config.p2_rate

            calculated_prices.append(
                {
                    "start_time": start_time_str,
                    "price_per_kwh": round(rate, 6),
                }
            )

        return calculated_prices

    def _calculate_go(
        self, market_prices: list[dict[str, Any]], target_date: date | None
    ) -> list[dict[str, Any]]:
        """Calculate Go prices (EV tariff with P1/P2/P3)."""
        config: GoTariffConfig = self._config  # type: ignore

        if target_date is None:
            target_date = datetime.now(self._timezone).date()

        calculated_prices: list[dict[str, Any]] = []

        for price_data in market_prices:
            start_time_str = price_data["start_time"]
            dt = datetime.fromisoformat(start_time_str)

            # Ensure timezone-aware
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=self._timezone)
            else:
                dt = dt.astimezone(self._timezone)

            hour = dt.hour

            # Determine period
            if hour in config.p1_hours:
                rate = config.p1_rate
            elif hour in config.p2_hours:
                rate = config.p2_rate
            elif hour in config.p3_hours:
                rate = config.p3_rate
            else:
                # Default to P2 if not in any period
                rate = config.p2_rate

            calculated_prices.append(
                {
                    "start_time": start_time_str,
                    "price_per_kwh": round(rate, 6),
                }
            )

        return calculated_prices

    def _calculate_sun_club(
        self, market_prices: list[dict[str, Any]], target_date: date | None
    ) -> list[dict[str, Any]]:
        """Calculate SUN CLUB prices (market price with daylight discount)."""
        config: SunClubTariffConfig = self._config  # type: ignore

        if target_date is None:
            target_date = datetime.now(self._timezone).date()

        calculated_prices: list[dict[str, Any]] = []

        for price_data in market_prices:
            start_time_str = price_data["start_time"]
            dt = datetime.fromisoformat(start_time_str)

            # Ensure timezone-aware
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=self._timezone)
            else:
                dt = dt.astimezone(self._timezone)

            hour = dt.hour
            market_price = price_data["price_per_kwh"]

            # Apply daylight discount
            if config.daylight_start <= hour < config.daylight_end:
                # Check if high solar/low price period (100% discount)
                # This is a simplified check - actual logic may be more complex
                if market_price < 0.05:  # Very low price threshold
                    calculated_price = 0.0
                else:
                    # Apply 45% discount
                    calculated_price = market_price * (1 - config.discount_percentage)
            else:
                calculated_price = market_price

            calculated_prices.append(
                {
                    "start_time": start_time_str,
                    "price_per_kwh": round(calculated_price, 6),
                }
            )

        return calculated_prices

