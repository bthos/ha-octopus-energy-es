"""Octopus Energy España integration for Home Assistant."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady

from .const import CONF_DEBUG, DOMAIN
from .coordinator import OctopusEnergyESCoordinator
from .services import async_setup_services

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

# Frontend resource is now in separate plugin repository


def _setup_logging(entry: ConfigEntry) -> None:
    """Set up logging level based on configuration."""
    # Get merged config (options override data)
    config = {**entry.data, **entry.options}
    debug_enabled = config.get(CONF_DEBUG, False)
    
    # Set logging level for all module loggers
    log_level = logging.DEBUG if debug_enabled else logging.INFO
    
    # Update loggers for all modules in this integration
    logger_names = [
        "custom_components.octopus_energy_es",
        "custom_components.octopus_energy_es.coordinator",
        "custom_components.octopus_energy_es.sensor",
        "custom_components.octopus_energy_es.config_flow",
        "custom_components.octopus_energy_es.api.octopus_client",
        "custom_components.octopus_energy_es.tariff.calculator",
        "custom_components.octopus_energy_es.comparison.manager",
        "custom_components.octopus_energy_es.comparison.calculator",
        "custom_components.octopus_energy_es.services",
    ]
    
    for logger_name in logger_names:
        logger = logging.getLogger(logger_name)
        logger.setLevel(log_level)


# Frontend card is now a separate plugin - no notification needed


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Octopus Energy España from a config entry."""
    # Set up logging level based on configuration
    _setup_logging(entry)
    
    # Set up services (only once)
    if DOMAIN not in hass.data:
        await async_setup_services(hass)
    
    coordinator = OctopusEnergyESCoordinator(hass, entry)
    
    # Try to refresh data, but handle errors appropriately
    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryAuthFailed:
        # Authentication failed - trigger reauth flow
        raise
    except Exception as err:
        # For other errors, check if it's a temporary issue
        error_msg = str(err).lower()
        if any(phrase in error_msg for phrase in [
            "cannot_connect",
            "connection",
            "network",
            "timeout",
            "not available",
            "not be publicly",
            "domain name not found",
            "cannot connect to host",
            "name or service not known"
        ]):
            # Temporary connection issue - raise ConfigEntryNotReady
            raise ConfigEntryNotReady(f"Connection error: {err}") from err
        else:
            # Log error but continue setup - data will be fetched on next update
            _LOGGER.warning("Initial data refresh failed, will retry: %s", err)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Listen for options updates
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when options are updated."""
    # Update logging level before reload
    _setup_logging(entry)
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok

