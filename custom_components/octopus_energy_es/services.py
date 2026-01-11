"""Services for Octopus Energy España integration."""
from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers import config_validation as cv
from zoneinfo import ZoneInfo

from .const import DOMAIN, TIMEZONE_MADRID
from .comparison.manager import ComparisonManager
from .coordinator import OctopusEnergyESCoordinator

_LOGGER = logging.getLogger(__name__)

# Service schemas
COMPARE_TARIFFS_SCHEMA = vol.Schema(
    {
        vol.Required("tariff_entry_ids"): vol.All(cv.ensure_list, [cv.string]),
        vol.Optional("source_entry_id"): cv.string,
        vol.Optional("period", default="daily"): vol.In(["daily", "weekly", "monthly", "custom"]),
        vol.Optional("start_date"): cv.date,
        vol.Optional("end_date"): cv.date,
        vol.Optional("power_kw"): vol.Coerce(float),
    }
)

FETCH_CONSUMPTION_SCHEMA = vol.Schema(
    {
        vol.Required("entry_id"): cv.string,
        vol.Optional("start_date"): cv.date,
        vol.Optional("end_date"): cv.date,
        vol.Optional("granularity", default="hourly"): vol.In(["hourly", "daily", "monthly"]),
        vol.Optional("apply_tariffs"): vol.All(cv.ensure_list, [cv.string]),
    }
)


@callback
async def async_setup_services(hass: HomeAssistant) -> None:
    """Set up services for Octopus Energy España."""
    
    async def compare_tariffs_service(call: ServiceCall) -> dict[str, Any]:
        """Service to compare multiple tariffs."""
        tariff_entry_ids = call.data.get("tariff_entry_ids", [])
        source_entry_id = call.data.get("source_entry_id")
        period = call.data.get("period", "daily")
        start_date = call.data.get("start_date")
        end_date = call.data.get("end_date")
        power_kw = call.data.get("power_kw")
        
        if not tariff_entry_ids:
            _LOGGER.error("No tariff_entry_ids provided")
            return {
                "success": False,
                "error": "No tariff_entry_ids provided",
            }
        
        try:
            manager = ComparisonManager(hass)
            result = await manager.calculate_comparison(
                tariff_entry_ids=tariff_entry_ids,
                source_entry_id=source_entry_id,
                period=period,
                start_date=start_date,
                end_date=end_date,
                power_kw=power_kw,
            )
            
            return {
                "success": True,
                "result": result,
            }
        except Exception as err:
            _LOGGER.error("Error comparing tariffs: %s", err, exc_info=True)
            return {
                "success": False,
                "error": str(err),
            }
    
    async def fetch_consumption_service(call: ServiceCall) -> dict[str, Any]:
        """Service to fetch consumption data."""
        entry_id = call.data.get("entry_id")
        start_date = call.data.get("start_date")
        end_date = call.data.get("end_date")
        granularity = call.data.get("granularity", "hourly")
        apply_tariffs = call.data.get("apply_tariffs")
        
        if DOMAIN not in hass.data:
            return {
                "success": False,
                "error": "Octopus Energy España integration not initialized",
            }
        
        coordinators = hass.data[DOMAIN]
        coordinator: OctopusEnergyESCoordinator | None = coordinators.get(entry_id)
        
        if not coordinator:
            return {
                "success": False,
                "error": f"Config entry {entry_id} not found",
            }
        
        try:
            # Get consumption data from coordinator
            if granularity == "hourly":
                consumption_data = coordinator.data.get("consumption_hourly", [])
            elif granularity == "daily":
                consumption_data = coordinator.data.get("consumption_daily", [])
            elif granularity == "monthly":
                consumption_data = coordinator.data.get("consumption_monthly", [])
            else:
                return {
                    "success": False,
                    "error": f"Unknown granularity: {granularity}",
                }
            
            # Filter by date range if provided
            if start_date or end_date:
                filtered_data = []
                timezone = ZoneInfo(TIMEZONE_MADRID)
                for item in consumption_data:
                    start_time_str = item.get("start_time") or item.get("date")
                    if not start_time_str:
                        continue
                    
                    try:
                        dt = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=ZoneInfo("UTC"))
                        dt = dt.astimezone(timezone)
                        item_date = dt.date()
                        
                        if start_date and item_date < start_date:
                            continue
                        if end_date and item_date > end_date:
                            continue
                        
                        filtered_data.append(item)
                    except (ValueError, TypeError):
                        continue
                
                consumption_data = filtered_data
            
            result: dict[str, Any] = {
                "success": True,
                "consumption_data": consumption_data,
            }
            
            # If apply_tariffs is specified, calculate costs for each tariff
            if apply_tariffs:
                try:
                    manager = ComparisonManager(hass)
                    prices_data = await manager.get_prices_data(entry_id, start_date, end_date)
                    
                    if not prices_data:
                        result["warning"] = "No prices data available for tariff cost calculation"
                    else:
                        tariff_costs = {}
                        for tariff_entry_id in apply_tariffs:
                            tariff_config = manager.get_tariff_config(tariff_entry_id)
                            if tariff_config:
                                from .comparison.calculator import ComparisonCalculator
                                calculator = ComparisonCalculator()
                                cost_data = calculator.calculate_tariff_cost(
                                    tariff_config,
                                    consumption_data,
                                    prices_data,
                                    period=granularity,
                                )
                                tariff_costs[tariff_entry_id] = cost_data
                            else:
                                _LOGGER.warning("Could not load tariff config for entry_id: %s", tariff_entry_id)
                        
                        if tariff_costs:
                            result["tariff_costs"] = tariff_costs
                        else:
                            result["warning"] = "No valid tariff configs found for cost calculation"
                except Exception as err:
                    _LOGGER.error("Error calculating tariff costs: %s", err, exc_info=True)
                    result["warning"] = f"Error calculating tariff costs: {str(err)}"
            
            return result
        except Exception as err:
            _LOGGER.error("Error fetching consumption: %s", err, exc_info=True)
            return {
                "success": False,
                "error": str(err),
            }
    
    hass.services.async_register(
        DOMAIN,
        "compare_tariffs",
        compare_tariffs_service,
        schema=COMPARE_TARIFFS_SCHEMA,
    )
    
    hass.services.async_register(
        DOMAIN,
        "fetch_consumption",
        fetch_consumption_service,
        schema=FETCH_CONSUMPTION_SCHEMA,
    )
    
    _LOGGER.info("Octopus Energy España services registered")
