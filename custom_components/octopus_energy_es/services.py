"""Services for Octopus Energy España integration."""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.service import SupportsResponse
from zoneinfo import ZoneInfo

from .const import DOMAIN, TIMEZONE_MADRID
from .comparison.manager import ComparisonManager
from .coordinator import OctopusEnergyESCoordinator
from .api.octopus_client import OctopusClientError

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

GET_LAST_DATA_DATE_SCHEMA = vol.Schema(
    {
        vol.Required("entry_id"): cv.string,
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
        """Service to fetch consumption data.
        
        Supports on-demand fetching: if requested date range falls outside cached data,
        makes direct API call to fetch the missing data. Cached data ranges:
        - hourly: last 7 days
        - daily: last 30 days
        - monthly: year-to-date
        """
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
            timezone = ZoneInfo(TIMEZONE_MADRID)
            now = datetime.now(timezone)
            today = now.date()
            
            # Get consumption data from coordinator cache
            if granularity == "hourly":
                consumption_data = coordinator.data.get("consumption_hourly", [])
                # Cached range: last 7 days
                cached_start_date = today - timedelta(days=7)
                cached_end_date = today
            elif granularity == "daily":
                consumption_data = coordinator.data.get("consumption_daily", [])
                # Cached range: last 30 days
                cached_start_date = today - timedelta(days=30)
                cached_end_date = today
            elif granularity == "monthly":
                consumption_data = coordinator.data.get("consumption_monthly", [])
                # Cached range: from start of year
                cached_start_date = date(today.year, 1, 1)
                cached_end_date = today
            else:
                return {
                    "success": False,
                    "error": f"Unknown granularity: {granularity}",
                }
            
            # Determine if on-demand API fetch is needed
            # Check if requested date range falls outside cached data
            needs_api_fetch = False
            api_start_date = None
            api_end_date = None
            
            if start_date or end_date:
                # Determine effective date range (use provided dates or cached range)
                effective_start = start_date if start_date else cached_start_date
                effective_end = end_date if end_date else cached_end_date
                
                # Check if requested range extends before cached data
                if effective_start < cached_start_date:
                    needs_api_fetch = True
                    api_start_date = effective_start
                    # Fetch up to the day before cached data starts, or requested end if earlier
                    api_end_date = min(cached_start_date - timedelta(days=1), effective_end)
                
                # Check if requested range extends after cached data
                if effective_end > cached_end_date:
                    needs_api_fetch = True
                    fetch_start_after_cache = cached_end_date + timedelta(days=1)
                    
                    # If we're already fetching before cache, fetch entire range and deduplicate
                    if api_start_date is not None and api_start_date < cached_start_date:
                        # Range spans both before and after cache - fetch entire range
                        api_start_date = effective_start
                        api_end_date = effective_end
                    else:
                        # Only fetching after cache
                        api_start_date = fetch_start_after_cache
                        api_end_date = effective_end
            
            # Make on-demand API call if needed
            on_demand_data = []
            if needs_api_fetch and coordinator._octopus_client and api_start_date and api_end_date:
                try:
                    _LOGGER.info(
                        "Requested date range falls outside cached data (%s to %s). "
                        "Fetching on-demand from API (%s to %s).",
                        cached_start_date, cached_end_date, api_start_date, api_end_date
                    )
                    on_demand_data = await coordinator._octopus_client.fetch_consumption(
                        start_date=api_start_date,
                        end_date=api_end_date,
                        granularity=granularity
                    )
                    if on_demand_data:
                        _LOGGER.debug(
                            "Fetched %d on-demand consumption measurements (%s to %s)",
                            len(on_demand_data), api_start_date, api_end_date
                        )
                except OctopusClientError as err:
                    _LOGGER.warning(
                        "Error fetching on-demand consumption data: %s. "
                        "Falling back to cached data only.",
                        err
                    )
                    # Continue with cached data only
                except Exception as err:
                    _LOGGER.warning(
                        "Unexpected error fetching on-demand consumption data: %s. "
                        "Falling back to cached data only.",
                        err,
                        exc_info=True
                    )
                    # Continue with cached data only
            
            # Merge cached and on-demand data, deduplicating by start_time/date
            # Use a dict keyed by start_time string to avoid duplicates
            merged_dict: dict[str, dict[str, Any]] = {}
            
            # Add cached data first
            for item in consumption_data:
                start_time_str = item.get("start_time") or item.get("date")
                if start_time_str:
                    # Normalize the time string for use as key
                    normalized_key = start_time_str.replace("Z", "+00:00")
                    merged_dict[normalized_key] = item
            
            # Add on-demand data (will overwrite cached data if duplicate, preferring on-demand)
            for item in on_demand_data:
                start_time_str = item.get("start_time") or item.get("date")
                if start_time_str:
                    # Normalize the time string for use as key
                    normalized_key = start_time_str.replace("Z", "+00:00")
                    merged_dict[normalized_key] = item
            
            # Convert back to list
            all_data = list(merged_dict.values())
            
            # Filter by date range if provided
            if start_date or end_date:
                filtered_data = []
                for item in all_data:
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
            else:
                consumption_data = all_data
            
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
    
    async def get_last_data_date_service(call: ServiceCall) -> dict[str, Any]:
        """Service to get the last available date with consumption data.
        
        Determines the most recent date for which consumption data is available
        in the cached data. This helps avoid requesting data for future dates
        when Octopus Energy API has delays.
        """
        entry_id = call.data.get("entry_id")
        
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
            timezone = ZoneInfo(TIMEZONE_MADRID)
            last_date: date | None = None
            
            # Check all available consumption data sources (hourly, daily, monthly)
            # to find the most recent date
            consumption_sources = [
                ("consumption_hourly", coordinator.data.get("consumption_hourly", [])),
                ("consumption_daily", coordinator.data.get("consumption_daily", [])),
                ("consumption_monthly", coordinator.data.get("consumption_monthly", [])),
            ]
            
            for source_name, consumption_data in consumption_sources:
                if not consumption_data:
                    continue
                
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
                        
                        if last_date is None or item_date > last_date:
                            last_date = item_date
                    except (ValueError, TypeError) as err:
                        _LOGGER.debug(
                            "Error parsing date from %s data: %s",
                            source_name, err
                        )
                        continue
            
            if last_date is None:
                return {
                    "success": False,
                    "error": "No data available",
                }
            
            return {
                "success": True,
                "last_data_date": last_date.isoformat(),
            }
        except Exception as err:
            _LOGGER.error("Error getting last data date: %s", err, exc_info=True)
            return {
                "success": False,
                "error": str(err),
            }
    
    hass.services.async_register(
        DOMAIN,
        "compare_tariffs",
        compare_tariffs_service,
        schema=COMPARE_TARIFFS_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    
    hass.services.async_register(
        DOMAIN,
        "fetch_consumption",
        fetch_consumption_service,
        schema=FETCH_CONSUMPTION_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    
    hass.services.async_register(
        DOMAIN,
        "get_last_data_date",
        get_last_data_date_service,
        schema=GET_LAST_DATA_DATE_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    
    _LOGGER.info("Octopus Energy España services registered")
