"""Comparison calculator for tariff cost calculations."""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any

from zoneinfo import ZoneInfo

from ..const import TIMEZONE_MADRID, TIME_STRUCTURE_SINGLE_RATE, TIME_STRUCTURE_TIME_OF_USE
from ..tariff.calculator import TariffCalculator
from ..tariff.types import TariffConfig, create_tariff_config

_LOGGER = logging.getLogger(__name__)


class ComparisonCalculator:
    """Calculator for comparing multiple tariffs."""

    def __init__(self) -> None:
        """Initialize comparison calculator."""
        self._timezone = ZoneInfo(TIMEZONE_MADRID)

    def _parse_datetime_to_madrid(self, dt_str: str) -> datetime | None:
        """Parse datetime string and convert to Madrid timezone."""
        try:
            dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=ZoneInfo("UTC"))
            return dt.astimezone(self._timezone)
        except (ValueError, TypeError) as err:
            _LOGGER.debug("Error parsing datetime '%s': %s", dt_str, err)
            return None

    def _get_period_for_hour(
        self, tariff_config: TariffConfig, hour: int, is_weekday: bool
    ) -> str:
        """Get period (P1/P2/P3) for a given hour."""
        if tariff_config.time_structure != TIME_STRUCTURE_TIME_OF_USE:
            return "SINGLE"
        
        if not is_weekday:
            return "P3"
        
        if hour in tariff_config.p1_hours_weekdays:
            return "P1"
        elif hour in tariff_config.p2_hours_weekdays:
            return "P2"
        elif hour in tariff_config.p3_hours_weekdays:
            return "P3"
        else:
            _LOGGER.warning("Hour %d not in any period definition, defaulting to P2", hour)
            return "P2"

    def calculate_period_breakdown(
        self, tariff_config: TariffConfig, consumption_data: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Calculate consumption breakdown by periods P1/P2/P3.
        
        Args:
            tariff_config: Tariff configuration
            consumption_data: List of consumption items with 'start_time' and 'consumption'
            
        Returns:
            Dictionary with period breakdown:
            - p1_consumption: kWh in P1 period
            - p2_consumption: kWh in P2 period
            - p3_consumption: kWh in P3 period
            - p1_percentage: % of total consumption
            - p2_percentage: % of total consumption
            - p3_percentage: % of total consumption
            - total_consumption: Total consumption in kWh
        """
        p1_total = 0.0
        p2_total = 0.0
        p3_total = 0.0
        
        for item in consumption_data:
            start_time_str = item.get("start_time")
            if not start_time_str:
                continue
            
            dt = self._parse_datetime_to_madrid(start_time_str)
            if not dt:
                continue
            
            consumption = float(item.get("consumption", item.get("value", 0)))
            hour = dt.hour
            is_weekday = dt.weekday() < 5
            
            period = self._get_period_for_hour(tariff_config, hour, is_weekday)
            
            if period == "P1":
                p1_total += consumption
            elif period == "P2":
                p2_total += consumption
            elif period == "P3":
                p3_total += consumption
            # SINGLE rate: distribute evenly or skip (will be handled below)
        
        total_consumption = p1_total + p2_total + p3_total
        
        # For single-rate tariffs, show that all consumption is in one period
        if tariff_config.time_structure == TIME_STRUCTURE_SINGLE_RATE:
            return {
                "p1_consumption": 0.0,
                "p2_consumption": 0.0,
                "p3_consumption": total_consumption,
                "p1_percentage": 0.0,
                "p2_percentage": 0.0,
                "p3_percentage": 100.0 if total_consumption > 0 else 0.0,
                "total_consumption": total_consumption,
            }
        
        # Calculate percentages
        p1_percentage = (p1_total / total_consumption * 100) if total_consumption > 0 else 0.0
        p2_percentage = (p2_total / total_consumption * 100) if total_consumption > 0 else 0.0
        p3_percentage = (p3_total / total_consumption * 100) if total_consumption > 0 else 0.0
        
        return {
            "p1_consumption": round(p1_total, 2),
            "p2_consumption": round(p2_total, 2),
            "p3_consumption": round(p3_total, 2),
            "p1_percentage": round(p1_percentage, 1),
            "p2_percentage": round(p2_percentage, 1),
            "p3_percentage": round(p3_percentage, 1),
            "total_consumption": round(total_consumption, 2),
        }

    def calculate_hourly_costs(
        self,
        tariff_config: TariffConfig,
        hourly_consumption: list[dict[str, Any]],
        hourly_prices: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Calculate hourly costs for a tariff.
        
        Args:
            tariff_config: Tariff configuration
            hourly_consumption: List of hourly consumption data
            hourly_prices: List of hourly price data
            
        Returns:
            List of hourly cost breakdowns
        """
        calculator = TariffCalculator(tariff_config)
        hourly_costs = []
        
        # Create a price lookup by start_time
        price_lookup: dict[str, float] = {}
        for price_data in hourly_prices:
            start_time = price_data.get("start_time")
            if start_time:
                price_lookup[start_time] = price_data.get("price_per_kwh", 0.0)
        
        for consumption_item in hourly_consumption:
            start_time = consumption_item.get("start_time")
            if not start_time:
                continue
            
            consumption = float(consumption_item.get("consumption", consumption_item.get("value", 0)))
            price_per_kwh = price_lookup.get(start_time, 0.0)
            
            # Calculate cost for this hour
            cost = consumption * price_per_kwh
            
            # Get period for visualization
            dt = self._parse_datetime_to_madrid(start_time)
            period = None
            if dt:
                hour = dt.hour
                is_weekday = dt.weekday() < 5
                period = self._get_period_for_hour(tariff_config, hour, is_weekday)
                if period == "SINGLE":
                    period = "P3"  # Use P3 as default for single-rate visualization
            
            hourly_costs.append({
                "hour": start_time,
                "cost": round(cost, 6),
                "consumption": round(consumption, 2),
                "period": period,
            })
        
        return hourly_costs

    def calculate_tariff_cost(
        self,
        tariff_config: TariffConfig,
        consumption_data: list[dict[str, Any]],
        prices_data: list[dict[str, Any]],
        power_kw: float | None = None,
        period: str = "daily",
    ) -> dict[str, Any]:
        """
        Calculate total cost for a tariff over a period.
        
        Args:
            tariff_config: Tariff configuration
            consumption_data: List of consumption data (hourly or daily)
            prices_data: List of price data
            power_kw: Power value in kW (optional)
            period: Period type (daily/weekly/monthly/custom)
            
        Returns:
            Dictionary with cost breakdown
        """
        calculator = TariffCalculator(tariff_config)
        
        # Calculate prices using tariff calculator (applies tariff rules)
        calculated_prices = calculator.calculate_prices(prices_data)
        
        # Create price lookup from calculated prices
        price_lookup: dict[str, float] = {}
        for price_data in calculated_prices:
            start_time = price_data.get("start_time")
            if start_time:
                price_lookup[start_time] = price_data.get("price_per_kwh", 0.0)
        
        # Calculate energy cost
        energy_cost = 0.0
        hourly_breakdown = []
        daily_breakdown = []
        
        # Group consumption by date for daily breakdown
        daily_totals: dict[str, dict[str, float]] = {}
        
        for consumption_item in consumption_data:
            start_time = consumption_item.get("start_time")
            if not start_time:
                continue
            
            consumption = float(consumption_item.get("consumption", consumption_item.get("value", 0)))
            price_per_kwh = price_lookup.get(start_time, 0.0)
            
            # Calculate cost for this period
            cost = consumption * price_per_kwh
            energy_cost += cost
            
            # Add to hourly breakdown
            dt = self._parse_datetime_to_madrid(start_time)
            period_name = None
            if dt:
                hour = dt.hour
                is_weekday = dt.weekday() < 5
                period_name = self._get_period_for_hour(tariff_config, hour, is_weekday)
                if period_name == "SINGLE":
                    period_name = "P3"
            
            hourly_breakdown.append({
                "hour": start_time,
                "cost": round(cost, 6),
                "consumption": round(consumption, 2),
                "period": period_name,
            })
            
            # Group by date for daily breakdown
            if dt:
                date_str = dt.date().isoformat()
                if date_str not in daily_totals:
                    daily_totals[date_str] = {"cost": 0.0, "consumption": 0.0}
                daily_totals[date_str]["cost"] += cost
                daily_totals[date_str]["consumption"] += consumption
        
        # Create daily breakdown
        for date_str, totals in sorted(daily_totals.items()):
            daily_breakdown.append({
                "date": date_str,
                "cost": round(totals["cost"], 2),
                "consumption": round(totals["consumption"], 2),
            })
        
        # Calculate power cost
        power_cost = None
        if power_kw is not None:
            # Calculate average power cost for the period
            # For simplicity, use first date from consumption data
            target_date = None
            if consumption_data:
                first_item = consumption_data[0]
                start_time = first_item.get("start_time")
                if start_time:
                    dt = self._parse_datetime_to_madrid(start_time)
                    if dt:
                        target_date = dt.date()
            
            if target_date:
                power_cost_dict = calculator.calculate_power_cost(power_kw, target_date)
                # Estimate total power cost for the period
                days = len(daily_totals) if daily_totals else 1
                power_cost = power_cost_dict["total_cost"] * days
        
        # Calculate management fee daily
        management_fee_daily = None
        if tariff_config.management_fee_monthly is not None:
            management_fee_daily = tariff_config.management_fee_monthly / 30.0
        
        # Calculate total daily cost
        days = len(daily_totals) if daily_totals else 1
        management_fee_total = (management_fee_daily * days) if management_fee_daily else None
        
        cost_breakdown = calculator.calculate_daily_cost(
            energy_cost=energy_cost,
            power_cost=power_cost,
            management_fee_daily=management_fee_total,
        )
        
        # Calculate period breakdown
        period_breakdown = self.calculate_period_breakdown(tariff_config, consumption_data)
        
        return {
            "total_cost": cost_breakdown["total"],
            "energy_cost": round(energy_cost, 2),
            "power_cost": round(power_cost, 2) if power_cost else 0.0,
            "management_fee": round(management_fee_total, 2) if management_fee_total else 0.0,
            "taxes": round(cost_breakdown["electricity_tax"] + cost_breakdown["vat"], 2),
            "hourly_breakdown": hourly_breakdown,
            "daily_breakdown": daily_breakdown,
            "period_breakdown": period_breakdown,
        }

    def compare_tariffs(
        self,
        tariff_configs: dict[str, TariffConfig],
        consumption_data: list[dict[str, Any]],
        prices_data: list[dict[str, Any]],
        power_kw: float | None = None,
        period: str = "daily",
    ) -> dict[str, Any]:
        """
        Compare multiple tariffs.
        
        Args:
            tariff_configs: Dictionary mapping entry_id to TariffConfig
            consumption_data: List of consumption data
            prices_data: List of price data
            power_kw: Power value in kW (optional)
            period: Period type (daily/weekly/monthly/custom)
            
        Returns:
            Dictionary with comparison results
        """
        results = []
        total_consumption = sum(
            float(item.get("consumption", item.get("value", 0)))
            for item in consumption_data
        )
        
        for entry_id, tariff_config in tariff_configs.items():
            cost_data = self.calculate_tariff_cost(
                tariff_config,
                consumption_data,
                prices_data,
                power_kw,
                period,
            )
            
            # Get tariff name from config (if available)
            tariff_name = f"Tariff {entry_id[:8]}"
            
            results.append({
                "entry_id": entry_id,
                "name": tariff_name,
                "total_cost": cost_data["total_cost"],
                "energy_cost": cost_data["energy_cost"],
                "power_cost": cost_data["power_cost"],
                "management_fee": cost_data["management_fee"],
                "taxes": cost_data["taxes"],
                "hourly_breakdown": cost_data["hourly_breakdown"],
                "daily_breakdown": cost_data["daily_breakdown"],
                "period_breakdown": cost_data["period_breakdown"],
            })
        
        # Find best and worst tariffs
        if results:
            sorted_results = sorted(results, key=lambda x: x["total_cost"])
            best_tariff = sorted_results[0]
            worst_tariff = sorted_results[-1]
            
            savings_amount = worst_tariff["total_cost"] - best_tariff["total_cost"]
            savings_percentage = (
                (savings_amount / worst_tariff["total_cost"] * 100)
                if worst_tariff["total_cost"] > 0
                else 0.0
            )
            
            return {
                "period": period,
                "consumption_total": round(total_consumption, 2),
                "tariffs": results,
                "best_tariff": {
                    "entry_id": best_tariff["entry_id"],
                    "name": best_tariff["name"],
                    "total_cost": best_tariff["total_cost"],
                },
                "savings": {
                    "best_entry_id": best_tariff["entry_id"],
                    "worst_entry_id": worst_tariff["entry_id"],
                    "amount": round(savings_amount, 2),
                    "percentage": round(savings_percentage, 2),
                },
            }
        
        return {
            "period": period,
            "consumption_total": round(total_consumption, 2),
            "tariffs": [],
            "best_tariff": None,
            "savings": None,
        }
