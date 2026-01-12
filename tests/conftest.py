"""Test configuration and fixtures."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def pytest_configure(config):
    """Configure pytest and inject mocks before any imports."""
    # Inject mocks early, before any homeassistant imports
    if 'homeassistant' not in sys.modules:
        try:
            # Try to import real homeassistant first
            import homeassistant  # noqa: F401
        except ImportError:
            # Inject mocks for local testing
            tests_dir = Path(__file__).parent
            mocks_dir = tests_dir / "mocks"
            if mocks_dir.exists():
                # Add tests directory to path
                if str(tests_dir) not in sys.path:
                    sys.path.insert(0, str(tests_dir))
                try:
                    # Import sitecustomize which injects mocks
                    import mocks.sitecustomize  # noqa: F401
                except ImportError:
                    pass


# Try to determine if we have real homeassistant
try:
    HAS_HOMEASSISTANT = 'homeassistant' in sys.modules and hasattr(sys.modules.get('homeassistant'), '__version__')
except Exception:
    HAS_HOMEASSISTANT = False

# pytest-homeassistant-custom-component is required for CI but optional for local testing
if HAS_HOMEASSISTANT:
    try:
        pytest_plugins = "pytest_homeassistant_custom_component"
    except ImportError:
        pass


@pytest.fixture
def mock_octopus_client():
    """Mock OctopusClient."""
    with patch(
        "custom_components.octopus_energy_es.api.octopus_client.OctopusClient"
    ) as mock_client:
        client_instance = AsyncMock()
        mock_client.return_value = client_instance
        yield client_instance


@pytest.fixture
def hass():
    """Mock Home Assistant instance for local testing."""
    from homeassistant.core import HomeAssistant
    
    hass_mock = MagicMock(spec=HomeAssistant)
    hass_mock.config_entries = MagicMock()
    hass_mock.config_entries.async_entries = AsyncMock(return_value=[])
    hass_mock.config_entries.async_update_entry = AsyncMock()
    hass_mock.config_entries.async_reload = AsyncMock()
    hass_mock.config_entries._entries = {}
    return hass_mock
