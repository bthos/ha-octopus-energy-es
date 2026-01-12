"""Test coordinator for Octopus Energy España."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import ConfigEntryAuthFailed

from custom_components.octopus_energy_es.coordinator import (
    OctopusEnergyESCoordinator,
    _is_auth_error,
)
from custom_components.octopus_energy_es.const import DOMAIN, TIMEZONE_MADRID


@pytest.fixture
def mock_entry():
    """Create a mock config entry."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry_id"
    entry.data = {
        "email": "test@example.com",
        "password": "testpassword",
        "property_id": "12345",
    }
    entry.options = {}
    entry.title = "Test Entry"
    return entry


@pytest.fixture
def coordinator(hass: HomeAssistant, mock_entry):
    """Create coordinator instance."""
    with patch("custom_components.octopus_energy_es.coordinator.DataUpdateCoordinator.__init__", lambda self, hass, logger, name, update_interval: None):
        with patch("custom_components.octopus_energy_es.coordinator.OctopusClient"):
            with patch("custom_components.octopus_energy_es.coordinator.TariffCalculator"):
                with patch("custom_components.octopus_energy_es.coordinator.create_tariff_config"):
                    coord = OctopusEnergyESCoordinator(hass, mock_entry)
                    return coord


def test_is_auth_error():
    """Test _is_auth_error helper function."""
    assert _is_auth_error("401 unauthorized") is True
    assert _is_auth_error("Invalid credentials") is True
    assert _is_auth_error("Wrong password") is True
    assert _is_auth_error("kt-ct-1138") is True
    assert _is_auth_error("Connection timeout") is False
    assert _is_auth_error("Network error") is False


async def test_coordinator_init(hass: HomeAssistant, mock_entry):
    """Test coordinator initialization."""
    with patch("custom_components.octopus_energy_es.coordinator.DataUpdateCoordinator.__init__", lambda self, hass, logger, name, update_interval: None):
        with patch("custom_components.octopus_energy_es.coordinator.OctopusClient") as mock_client_class:
            with patch("custom_components.octopus_energy_es.coordinator.TariffCalculator"):
                with patch("custom_components.octopus_energy_es.coordinator.create_tariff_config"):
                    coord = OctopusEnergyESCoordinator(hass, mock_entry)
                    
                    assert coord._entry == mock_entry
                    assert coord._hass == hass
                    assert coord._timezone == ZoneInfo(TIMEZONE_MADRID)
                    assert coord._pvpc_sensor == "sensor.pvpc"
                    assert coord._octopus_client is not None


async def test_coordinator_init_no_credentials(hass: HomeAssistant, mock_entry):
    """Test coordinator initialization without credentials."""
    mock_entry.data = {}
    
    with patch("custom_components.octopus_energy_es.coordinator.DataUpdateCoordinator.__init__", lambda self, hass, logger, name, update_interval: None):
        with patch("custom_components.octopus_energy_es.coordinator.TariffCalculator"):
            with patch("custom_components.octopus_energy_es.coordinator.create_tariff_config"):
                coord = OctopusEnergyESCoordinator(hass, mock_entry)
                
                assert coord._octopus_client is None


async def test_coordinator_auth_error_handling(
    hass: HomeAssistant, coordinator: OctopusEnergyESCoordinator
):
    """Test that authentication errors trigger ConfigEntryAuthFailed."""
    from custom_components.octopus_energy_es.api.octopus_client import OctopusClientError
    
    # Mock OctopusClient to raise auth error
    coordinator._octopus_client = AsyncMock()
    coordinator._octopus_client.fetch_consumption = AsyncMock(
        side_effect=OctopusClientError("Invalid credentials")
    )
    
    # Mock PVPC sensor to return empty
    hass.states = MagicMock()
    hass.states.get = MagicMock(return_value=None)
    
    # Mock _fetch_and_calculate_prices to return empty list
    coordinator._fetch_and_calculate_prices = AsyncMock(return_value=[])
    
    # Should raise ConfigEntryAuthFailed
    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator._async_update_data()


async def test_coordinator_update_success(
    hass: HomeAssistant, coordinator: OctopusEnergyESCoordinator
):
    """Test successful coordinator update."""
    # Mock PVPC sensor
    mock_state = MagicMock()
    mock_state.state = "0.15"
    mock_state.attributes = {}
    hass.states = MagicMock()
    hass.states.get = MagicMock(return_value=mock_state)
    
    # Mock price fetching
    coordinator._fetch_and_calculate_prices = AsyncMock(
        return_value=[
            {
                "start_time": datetime.now(ZoneInfo(TIMEZONE_MADRID)).isoformat(),
                "price_per_kwh": 0.15,
            }
        ]
    )
    
    # Mock Octopus client methods - need to ensure all methods are AsyncMock
    if coordinator._octopus_client:
        # Make sure the client itself is properly mocked
        coordinator._octopus_client = AsyncMock()
        coordinator._octopus_client.fetch_consumption = AsyncMock(return_value=[])
        coordinator._octopus_client.fetch_billing = AsyncMock(return_value={})
        coordinator._octopus_client.fetch_credits = AsyncMock(return_value={})
        coordinator._octopus_client.fetch_account = AsyncMock(return_value={})
        coordinator._octopus_client.fetch_account_credits = AsyncMock(return_value={})
        coordinator._octopus_client.close = AsyncMock()
    
    # Update should succeed
    result = await coordinator._async_update_data()
    
    assert result is not None
    assert isinstance(result, dict)
    assert "today_prices" in result
