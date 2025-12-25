"""Tariff calculation engine for Octopus Energy España."""
from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

from zoneinfo import ZoneInfo

from ..const import (
    PRICING_MODEL_FIXED,
    PRICING_MODEL_MARKET,
    TIME_STRUCTURE_SINGLE_RATE,
    TIME_STRUCTURE_TIME_OF_USE,
    TIMEZONE_MADRID,
)
from .types import TariffConfig

_LOGGER = logging.getLogger(__name__)


class TariffCalculator:
    """Calculator for different tariff types."""

    def __init__(self, config: TariffConfig) -> None:
        """Initialize tariff calculator."""
        self._config = config
        self._timezone = ZoneInfo(TIMEZONE_MADRID)

    def _is_weekday(self, dt: datetime) -> bool:
        """Check if datetime is a weekday (Monday-Friday)."""
        return dt.weekday() < 5  # 0-4 are Monday-Friday

    def _get_period_for_hour(
        self, hour: int, is_weekday: bool
    ) -> tuple[str, float | None]:
        """
        Get the period (P1/P2/P3) and rate for a given hour.
        
        Args:
            hour: Hour of day (0-23)
            is_weekday: Whether this is a weekday
            
        Returns:
            Tuple of (period_name, rate) or (None, None) if not applicable
        """
        if self._config.time_structure != TIME_STRUCTURE_TIME_OF_USE:
            # Single rate - no period logic needed
            return ("SINGLE", None)
        
        # Time-of-use: Check weekday vs weekend
        if not is_weekday:
            # Weekends/holidays: All hours are P3 (Valle)
            return ("P3", self._config.p3_rate)
        
        # Weekdays: Use period definitions
        if hour in self._config.p1_hours_weekdays:
            return ("P1", self._config.p1_rate)
        elif hour in self._config.p2_hours_weekdays:
            return ("P2", self._config.p2_rate)
        elif hour in self._config.p3_hours_weekdays:
            return ("P3", self._config.p3_rate)
        else:
            # Should not happen if validation is correct, but default to P2
            _LOGGER.warning(
                "Hour %d not in any period definition, defaulting to P2", hour
            )
            return ("P2", self._config.p2_rate)

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
        if self._config.pricing_model == PRICING_MODEL_MARKET:
            return self._calculate_market(market_prices, target_date)
        elif self._config.pricing_model == PRICING_MODEL_FIXED:
            return self._calculate_fixed(market_prices, target_date)
        else:
            _LOGGER.warning(
                "Unknown pricing model: %s", self._config.pricing_model
            )
            return market_prices

    def _calculate_market(
        self, market_prices: list[dict[str, Any]], target_date: date | None
    ) -> list[dict[str, Any]]:
        """Calculate prices for market-based pricing model."""
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

            market_price = price_data["price_per_kwh"]
            hour = dt.hour

            # Apply discount if configured
            if (
                self._config.discount_start_hour is not None
                and self._config.discount_end_hour is not None
                and self._config.discount_percentage is not None
            ):
                if (
                    self._config.discount_start_hour
                    <= hour
                    < self._config.discount_end_hour
                ):
                    calculated_price = market_price * (
                        1 - self._config.discount_percentage
                    )
                else:
                    calculated_price = market_price
            else:
                calculated_price = market_price

            calculated_prices.append(
                {
                    "start_time": start_time_str,
                    "price_per_kwh": round(calculated_price, 6),
                }
            )

        return calculated_prices

    def _calculate_fixed(
        self, market_prices: list[dict[str, Any]], target_date: date | None
    ) -> list[dict[str, Any]]:
        """Calculate prices for fixed pricing model."""
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
            is_weekday = self._is_weekday(dt)

            if self._config.time_structure == TIME_STRUCTURE_SINGLE_RATE:
                # Single rate: Use fixed_rate
                if self._config.fixed_rate is not None:
                    rate = self._config.fixed_rate
                else:
                    _LOGGER.warning(
                        "Fixed rate not configured for single-rate tariff"
                    )
                    rate = 0.0
            else:
                # Time-of-use: Determine period
                period, period_rate = self._get_period_for_hour(hour, is_weekday)
                if period_rate is not None:
                    rate = period_rate
                else:
                    _LOGGER.warning(
                        "Period rate not found for hour %d, period %s", hour, period
                    )
                    rate = 0.0

            calculated_prices.append(
                {
                    "start_time": start_time_str,
                    "price_per_kwh": round(rate, 6),
                }
            )

        return calculated_prices

    def calculate_power_cost(
        self,
        power_kw: float,
        target_date: date | None = None,
    ) -> dict[str, float]:
        """
        Calculate power (potencia) cost for a given power value.
        
        Args:
            power_kw: Power value in kW
            target_date: Target date for calculation
            
        Returns:
            Dictionary with 'p1_cost', 'p2_cost', 'total_cost' in €/day
        """
        if self._config.power_p1_rate is None or self._config.power_p2_rate is None:
            _LOGGER.warning("Power rates not configured")
            return {"p1_cost": 0.0, "p2_cost": 0.0, "total_cost": 0.0}
        
        if target_date is None:
            target_date = datetime.now(self._timezone).date()
        
        # Power rates use P1/P2 structure (not P1/P2/P3 like energy)
        # P1 (Punta): Same hours as energy P1
        # P2 (Valle): Combines energy P2 + P3 hours
        
        # Count hours in each period for the day
        p1_hours = 0
        p2_hours = 0
        
        dt_start = datetime.combine(target_date, datetime.min.time()).replace(
            tzinfo=self._timezone
        )
        
        for hour in range(24):
            dt = dt_start.replace(hour=hour)
            is_weekday = self._is_weekday(dt)
            
            if not is_weekday:
                # Weekends/holidays: All hours are P2 (Valle)
                p2_hours += 1
            else:
                # Weekdays: Check period
                if hour in self._config.p1_hours_weekdays:
                    p1_hours += 1
                else:
                    # P2 or P3 both count as P2 for power rates
                    p2_hours += 1
        
        # Calculate costs (rates are in €/kW/day)
        p1_cost = (power_kw * self._config.power_p1_rate * p1_hours) / 24
        p2_cost = (power_kw * self._config.power_p2_rate * p2_hours) / 24
        total_cost = p1_cost + p2_cost
        
        return {
            "p1_cost": round(p1_cost, 6),
            "p2_cost": round(p2_cost, 6),
            "total_cost": round(total_cost, 6),
        }
