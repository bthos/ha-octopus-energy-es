"""Comparison manager for tariff comparisons."""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from zoneinfo import ZoneInfo

from ..const import DOMAIN, TIMEZONE_MADRID
from ..coordinator import OctopusEnergyESCoordinator
from ..tariff.types import TariffConfig, create_tariff_config
from .calculator import ComparisonCalculator

_LOGGER = logging.getLogger(__name__)


class ComparisonManager:
    """Manager for tariff comparisons."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize comparison manager."""
        self._hass = hass
        self._timezone = ZoneInfo(TIMEZONE_MADRID)
        self._calculator = ComparisonCalculator()

    def get_coordinator(self, entry_id: str) -> OctopusEnergyESCoordinator | None:
        """
        Get coordinator for a given entry_id.
        
        Args:
            entry_id: Config entry ID
            
        Returns:
            Coordinator instance or None if not found
        """
        if DOMAIN not in self._hass.data:
            return None
        
        coordinators = self._hass.data[DOMAIN]
        return coordinators.get(entry_id)

    def get_tariff_config(self, entry_id: str) -> TariffConfig | None:
        """
        Get tariff configuration for a given entry_id.
        
        Args:
            entry_id: Config entry ID
            
        Returns:
            TariffConfig instance or None if not found
        """
        # Get config entry
        entry = self._hass.config_entries.async_get_entry(entry_id)
        if not entry:
            _LOGGER.warning("Config entry %s not found", entry_id)
            return None
        
        # Get merged config (options override data)
        config = {**entry.data, **entry.options}
        
        try:
            return create_tariff_config(config)
        except Exception as err:
            _LOGGER.error("Error creating tariff config for entry %s: %s", entry_id, err)
            return None

    def get_tariff_name(self, entry_id: str) -> str:
        """
        Get tariff name for a given entry_id.
        
        Args:
            entry_id: Config entry ID
            
        Returns:
            Tariff name or entry_id if not found
        """
        entry = self._hass.config_entries.async_get_entry(entry_id)
        if entry:
            return entry.title or entry_id
        return entry_id

    async def get_consumption_data(
        self,
        source_entry_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
        granularity: str = "hourly",
    ) -> list[dict[str, Any]]:
        """
        Get consumption data from source coordinator.
        
        Args:
            source_entry_id: Source config entry ID
            start_date: Start date (optional)
            end_date: End date (optional)
            granularity: Data granularity (hourly/daily/monthly)
            
        Returns:
            List of consumption data
        """
        coordinator = self.get_coordinator(source_entry_id)
        if not coordinator:
            _LOGGER.warning("Source coordinator %s not found", source_entry_id)
            return []
        
        # Get consumption data from coordinator
        if granularity == "hourly":
            consumption_data = coordinator.data.get("consumption_hourly", [])
        elif granularity == "daily":
            consumption_data = coordinator.data.get("consumption_daily", [])
        elif granularity == "monthly":
            consumption_data = coordinator.data.get("consumption_monthly", [])
        else:
            _LOGGER.warning("Unknown granularity: %s", granularity)
            consumption_data = []
        
        # Filter by date range if provided
        if start_date or end_date:
            filtered_data = []
            for item in consumption_data:
                start_time_str = item.get("start_time") or item.get("date")
                if not start_time_str:
                    continue
                
                try:
                    dt = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
                    dt = dt.astimezone(self._timezone)
                    item_date = dt.date()
                    
                    if start_date and item_date < start_date:
                        continue
                    if end_date and item_date > end_date:
                        continue
                    
                    filtered_data.append(item)
                except (ValueError, TypeError):
                    continue
            
            return filtered_data
        
        return consumption_data

    async def get_prices_data(
        self,
        source_entry_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get prices data from source coordinator.
        
        Args:
            source_entry_id: Source config entry ID
            start_date: Start date (optional)
            end_date: End date (optional)
            
        Returns:
            List of price data
        """
        coordinator = self.get_coordinator(source_entry_id)
        if not coordinator:
            _LOGGER.warning("Source coordinator %s not found", source_entry_id)
            return []
        
        # Get prices from coordinator
        today_prices = coordinator.data.get("today_prices", [])
        tomorrow_prices = coordinator.data.get("tomorrow_prices", [])
        
        all_prices = today_prices + tomorrow_prices
        
        # Filter by date range if provided
        if start_date or end_date:
            filtered_prices = []
            for price_item in all_prices:
                start_time_str = price_item.get("start_time")
                if not start_time_str:
                    continue
                
                try:
                    dt = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
                    dt = dt.astimezone(self._timezone)
                    item_date = dt.date()
                    
                    if start_date and item_date < start_date:
                        continue
                    if end_date and item_date > end_date:
                        continue
                    
                    filtered_prices.append(price_item)
                except (ValueError, TypeError):
                    continue
            
            return filtered_prices
        
        return all_prices

    def _get_power_kw_from_coordinator(self, entry_id: str) -> float | None:
        """
        Try to get power_kw from coordinator billing data if available.
        
        Args:
            entry_id: Config entry ID
            
        Returns:
            Power value in kW or None if not available
        """
        coordinator = self.get_coordinator(entry_id)
        if not coordinator:
            return None
        
        # Try to get power from billing data (if available in future API responses)
        billing = coordinator.data.get("billing", {})
        if billing:
            # Check if power is available in billing data
            last_invoice = billing.get("last_invoice")
            if isinstance(last_invoice, dict):
                power_kw = last_invoice.get("power_kw")
                if power_kw is not None:
                    return float(power_kw)
        
        return None

    async def calculate_comparison(
        self,
        tariff_entry_ids: list[str],
        source_entry_id: str | None = None,
        period: str = "daily",
        start_date: date | None = None,
        end_date: date | None = None,
        power_kw: float | None = None,
    ) -> dict[str, Any]:
        """
        Calculate comparison for multiple tariffs.
        
        Args:
            tariff_entry_ids: List of tariff entry IDs to compare
            source_entry_id: Source entry ID for consumption data (defaults to first tariff)
            period: Period type (daily/weekly/monthly/custom)
            start_date: Start date for custom period
            end_date: End date for custom period
            power_kw: Power value in kW (optional)
            
        Returns:
            Dictionary with comparison results
        """
        if not tariff_entry_ids:
            return {
                "period": period,
                "consumption_total": 0.0,
                "tariffs": [],
                "best_tariff": None,
                "savings": None,
            }
        
        # Use first tariff as source if not specified
        if source_entry_id is None:
            source_entry_id = tariff_entry_ids[0]
        
        # Try to get power_kw from coordinator if not provided
        if power_kw is None:
            power_kw = self._get_power_kw_from_coordinator(source_entry_id)
        
        # Calculate date range based on period
        granularity = "hourly"  # Default granularity
        if period == "custom":
            if not start_date or not end_date:
                _LOGGER.warning("Custom period requires start_date and end_date")
                return {
                    "period": period,
                    "consumption_total": 0.0,
                    "tariffs": [],
                    "best_tariff": None,
                    "savings": None,
                }
            # For custom period, determine granularity based on date range
            days_diff = (end_date - start_date).days
            if days_diff <= 7:
                granularity = "hourly"
            elif days_diff <= 30:
                granularity = "daily"
            else:
                granularity = "daily"
        else:
            now = datetime.now(self._timezone).date()
            if period == "daily":
                start_date = now
                end_date = now
                granularity = "hourly"
            elif period == "weekly":
                start_date = now - timedelta(days=7)
                end_date = now
                granularity = "hourly"
            elif period == "monthly":
                start_date = now - timedelta(days=30)
                end_date = now
                granularity = "daily"
            else:
                _LOGGER.warning("Unknown period: %s", period)
                return {
                    "period": period,
                    "consumption_total": 0.0,
                    "tariffs": [],
                    "best_tariff": None,
                    "savings": None,
                }
        
        # Get consumption and prices data
        consumption_data = await self.get_consumption_data(
            source_entry_id, start_date, end_date, granularity
        )
        prices_data = await self.get_prices_data(source_entry_id, start_date, end_date)
        
        if not consumption_data:
            _LOGGER.warning("No consumption data available for comparison")
            return {
                "period": period,
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
                "consumption_total": 0.0,
                "tariffs": [],
                "best_tariff": None,
                "savings": None,
                "error": "No consumption data available",
            }
        
        if not prices_data:
            _LOGGER.warning("No prices data available for comparison")
            return {
                "period": period,
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
                "consumption_total": sum(
                    float(item.get("consumption", item.get("value", 0)))
                    for item in consumption_data
                ),
                "tariffs": [],
                "best_tariff": None,
                "savings": None,
                "error": "No prices data available",
            }
        
        # Get tariff configs
        tariff_configs: dict[str, TariffConfig] = {}
        invalid_entry_ids = []
        for entry_id in tariff_entry_ids:
            config = self.get_tariff_config(entry_id)
            if config:
                tariff_configs[entry_id] = config
            else:
                invalid_entry_ids.append(entry_id)
                _LOGGER.warning("Could not load tariff config for entry_id: %s", entry_id)
        
        if not tariff_configs:
            _LOGGER.warning("No valid tariff configs found")
            return {
                "period": period,
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
                "consumption_total": sum(
                    float(item.get("consumption", item.get("value", 0)))
                    for item in consumption_data
                ),
                "tariffs": [],
                "best_tariff": None,
                "savings": None,
                "error": "No valid tariff configs found",
                "invalid_entry_ids": invalid_entry_ids,
            }
        
        # Calculate comparison
        try:
            result = self._calculator.compare_tariffs(
                tariff_configs,
                consumption_data,
                prices_data,
                power_kw,
                period,
            )
            
            # Add tariff names
            for tariff in result.get("tariffs", []):
                tariff["name"] = self.get_tariff_name(tariff["entry_id"])
            
            # Add dates to result
            result["start_date"] = start_date.isoformat() if start_date else None
            result["end_date"] = end_date.isoformat() if end_date else None
            
            # Add info about invalid entries if any
            if invalid_entry_ids:
                result["invalid_entry_ids"] = invalid_entry_ids
                result["warning"] = f"Some tariff entries could not be loaded: {', '.join(invalid_entry_ids)}"
            
            return result
        except Exception as err:
            _LOGGER.error("Error calculating comparison: %s", err, exc_info=True)
            return {
                "period": period,
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
                "consumption_total": sum(
                    float(item.get("consumption", item.get("value", 0)))
                    for item in consumption_data
                ),
                "tariffs": [],
                "best_tariff": None,
                "savings": None,
                "error": str(err),
            }
