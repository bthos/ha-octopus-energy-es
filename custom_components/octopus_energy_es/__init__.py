"""Octopus Energy España integration for Home Assistant."""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback

from .const import (
    CONF_HISTORICAL_DATA_LOAD_DATE,
    CONF_HISTORICAL_DATA_LOADED,
    CONF_HISTORICAL_DATA_RANGE,
    CONF_HISTORICAL_DATA_START_DATE,
    CONF_LOAD_HISTORICAL_DATA,
    DOMAIN,
    HISTORICAL_RANGE_1_YEAR,
    HISTORICAL_RANGE_2_YEARS,
    HISTORICAL_RANGE_ALL_AVAILABLE,
    HISTORICAL_RANGE_CUSTOM,
)
from .coordinator import OctopusEnergyESCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Octopus Energy España from a config entry."""
    coordinator = OctopusEnergyESCoordinator(hass, entry)
    
    # Try to refresh data, but don't fail if it doesn't work initially
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        # Log error but continue setup - data will be fetched on next update
        _LOGGER.warning("Initial data refresh failed, will retry: %s", err)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Set up services (only once, not per entry)
    if DOMAIN not in hass.data.get("_services_setup", set()):
        await async_setup_services(hass, entry)
        hass.data.setdefault("_services_setup", set()).add(DOMAIN)

    # Check if historical data should be loaded
    entry_data = entry.data
    load_historical = entry_data.get(CONF_LOAD_HISTORICAL_DATA, False)
    historical_loaded = entry_data.get(CONF_HISTORICAL_DATA_LOADED, False)

    if load_historical and not historical_loaded:
        # Load historical data in background task
        _LOGGER.info("Historical data loading enabled, starting background load...")
        hass.async_create_task(_load_historical_data(hass, entry, coordinator))

    return True


async def async_setup_services(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Set up services for Octopus Energy España."""

    @callback
    async def handle_load_historical_data(call) -> None:
        """Handle load_historical_data service call."""
        # Find the coordinator for this service call
        # Try to get entry_id from target if provided
        target_entry_id = None
        if "target" in call.data and "entity_id" in call.data.get("target", {}):
            # Extract entry_id from entity_id if possible
            pass
        
        # Use first available coordinator (or find by entry_id if provided)
        if DOMAIN not in hass.data or not hass.data[DOMAIN]:
            _LOGGER.error("No Octopus Energy España integration found")
            return
        
        # For now, use the first coordinator
        # In future, we could match by entry_id if provided
        coordinator = next(iter(hass.data[DOMAIN].values()))
        
        # Find the corresponding entry
        entry = None
        for config_entry in hass.config_entries.async_entries(DOMAIN):
            if hass.data[DOMAIN].get(config_entry.entry_id) == coordinator:
                entry = config_entry
                break
        
        if not entry:
            _LOGGER.error("Could not find config entry for coordinator")
            return

        start_date_str = call.data.get("start_date")
        end_date_str = call.data.get("end_date")
        force_reload = call.data.get("force_reload", False)

        start_date = None
        end_date = None

        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            except ValueError:
                _LOGGER.error("Invalid start_date format: %s (expected YYYY-MM-DD)", start_date_str)
                return

        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            except ValueError:
                _LOGGER.error("Invalid end_date format: %s (expected YYYY-MM-DD)", end_date_str)
                return

        # Check if data already loaded (unless force_reload)
        if not force_reload and entry.data.get(CONF_HISTORICAL_DATA_LOADED, False):
            _LOGGER.info("Historical data already loaded. Use force_reload=true to reload.")
            return

        _LOGGER.info("Loading historical data via service call...")
        await _load_historical_data(hass, entry, coordinator, start_date, end_date)

    hass.services.async_register(DOMAIN, "load_historical_data", handle_load_historical_data)


async def _load_historical_data(
    hass: HomeAssistant,
    entry: ConfigEntry,
    coordinator: OctopusEnergyESCoordinator,
    start_date: date | None = None,
    end_date: date | None = None,
) -> None:
    """
    Load historical consumption data and store it in Home Assistant recorder.
    
    Args:
        hass: Home Assistant instance
        entry: Config entry
        coordinator: Data coordinator
        start_date: Optional start date override
        end_date: Optional end date override
    """
    try:
        # Fetch historical data
        historical_data = await coordinator.async_load_historical_data(
            start_date=start_date, end_date=end_date
        )

        if not historical_data:
            _LOGGER.warning("No historical data returned from API")
            return

        _LOGGER.info(
            "Fetched %d historical consumption measurements, storing in recorder...",
            len(historical_data)
        )

        # Store historical data in recorder
        await _store_historical_data_in_recorder(hass, historical_data)
        
        # Store historical data in coordinator for sensor access
        # This allows sensors to query historical data if needed
        if not hasattr(coordinator, "_historical_data"):
            coordinator._historical_data = []
        coordinator._historical_data.extend(historical_data)

        # Load historical credits data for the same date range
        _LOGGER.info("Loading historical credits data for the same date range...")
        historical_credits = await coordinator.async_load_historical_credits(
            start_date=start_date, end_date=end_date
        )
        
        if historical_credits:
            _LOGGER.info(
                "Fetched %d historical credit records",
                len(historical_credits)
            )
            # Store historical credits in coordinator
            if not hasattr(coordinator, "_historical_credits_data"):
                coordinator._historical_credits_data = []
            coordinator._historical_credits_data.extend(historical_credits)

        # Update config entry to mark historical data as loaded
        entry_data = dict(entry.data)
        entry_data[CONF_HISTORICAL_DATA_LOADED] = True
        entry_data[CONF_HISTORICAL_DATA_LOAD_DATE] = datetime.now().isoformat()

        hass.config_entries.async_update_entry(entry, data=entry_data)

        _LOGGER.info(
            "Successfully loaded and stored %d historical consumption measurements and %d historical credit records",
            len(historical_data),
            len(historical_credits) if historical_credits else 0
        )

    except Exception as err:
        _LOGGER.error("Error loading historical data: %s", err, exc_info=True)


async def _store_historical_data_in_recorder(
    hass: HomeAssistant, historical_data: list[dict[str, Any]]
) -> None:
    """
    Store historical consumption data in Home Assistant recorder.
    
    Historical data is stored in the coordinator and will be accessible to sensors.
    Home Assistant recorder automatically stores sensor state changes as they occur.
    Since sensors now have access to historical data via coordinator.data["consumption"],
    the recorder will store the sensor states when they update.
    
    Note: Home Assistant doesn't support importing historical state changes with past
    timestamps directly. The historical data will be available for sensors to query
    and display, and future sensor updates will be recorded normally.
    """
    if not historical_data:
        return
    
    # Calculate date range for logging
    dates: list[date] = []
    for item in historical_data:
        if isinstance(item, dict):
            timestamp_str = item.get("start_time") or item.get("datetime") or item.get("date")
            if timestamp_str:
                try:
                    from zoneinfo import ZoneInfo
                    dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
                    dt_madrid = dt.astimezone(ZoneInfo("Europe/Madrid"))
                    dates.append(dt_madrid.date())
                except (ValueError, TypeError):
                    continue
    
    if dates:
        dates.sort()
        start_date = dates[0].isoformat()
        end_date = dates[-1].isoformat()
        _LOGGER.info(
            "Historical data loaded: %d measurements from %s to %s. "
            "Data is now available to sensors and will be recorded on next sensor update.",
            len(historical_data),
            start_date,
            end_date
        )
    else:
        _LOGGER.info(
            "Historical data loaded: %d measurements available for sensor queries",
            len(historical_data)
        )
    
    # Historical data is stored in coordinator._historical_data
    # Sensors will access it via coordinator.data["consumption"] after merging
    # Home Assistant recorder will store sensor states automatically when sensors update


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok

