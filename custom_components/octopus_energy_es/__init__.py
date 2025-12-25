"""Octopus Energy España integration for Home Assistant."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import OctopusEnergyESCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Octopus Energy España from a config entry."""
    coordinator = OctopusEnergyESCoordinator(hass, entry)
    
    # Try to refresh data, but don't fail if it doesn't work initially
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        # Log error but continue setup - data will be fetched on next update
        import logging
        _LOGGER = logging.getLogger(__name__)
        _LOGGER.warning("Initial data refresh failed, will retry: %s", err)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok

