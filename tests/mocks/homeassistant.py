"""Mock homeassistant module for local testing."""
from __future__ import annotations

from enum import Enum
from unittest.mock import MagicMock, AsyncMock
from typing import Any

# Mock Platform enum
class Platform(Enum):
    """Mock Platform enum."""
    SENSOR = "sensor"

# Mock const module
const = MagicMock()
const.Platform = Platform
const.CONF_EMAIL = "email"
const.CONF_PASSWORD = "password"

# Mock config_entries module
class ConfigEntry:
    """Mock ConfigEntry."""
    def __init__(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            setattr(self, key, value)

class ConfigFlow:
    """Mock ConfigFlow base class."""
    def __init_subclass__(cls, domain=None, **kwargs):
        """Mock __init_subclass__ that accepts domain parameter."""
        super().__init_subclass__(**kwargs)
        if domain:
            cls.domain = domain
    
    def async_show_form(self, **kwargs):
        """Mock async_show_form method (synchronous in Home Assistant)."""
        return {"type": "form", **kwargs}
    
    def async_create_entry(self, **kwargs):
        """Mock async_create_entry method (synchronous in Home Assistant)."""
        return {"type": "create_entry", **kwargs}
    
    def async_abort(self, **kwargs):
        """Mock async_abort method (synchronous in Home Assistant)."""
        return {"type": "abort", **kwargs}
    
    async def async_set_unique_id(self, unique_id):
        """Mock async_set_unique_id method."""
        self._unique_id = unique_id
    
    def _abort_if_unique_id_configured(self):
        """Mock _abort_if_unique_id_configured method."""
        pass

class OptionsFlow:
    """Mock OptionsFlow base class."""
    pass

class OptionsFlowWithConfigEntry:
    """Mock OptionsFlowWithConfigEntry base class."""
    pass

SOURCE_USER = "user"

config_entries = MagicMock()
config_entries.ConfigEntry = ConfigEntry
config_entries.ConfigFlow = ConfigFlow
config_entries.OptionsFlow = OptionsFlow
config_entries.OptionsFlowWithConfigEntry = OptionsFlowWithConfigEntry
config_entries.SOURCE_USER = SOURCE_USER

# Mock core module
class HomeAssistant:
    """Mock HomeAssistant class."""
    pass

core = MagicMock()
core.HomeAssistant = HomeAssistant

# Mock data_entry_flow module
class FlowResultType:
    """Mock FlowResultType enum."""
    FORM = "form"
    ABORT = "abort"
    CREATE_ENTRY = "create_entry"

data_entry_flow = MagicMock()
data_entry_flow.FlowResultType = FlowResultType

# Mock helpers module
class DataUpdateCoordinator:
    """Mock DataUpdateCoordinator."""
    pass

class UpdateFailed(Exception):
    """Mock UpdateFailed exception."""
    pass

update_coordinator = MagicMock()
update_coordinator.DataUpdateCoordinator = DataUpdateCoordinator
update_coordinator.UpdateFailed = UpdateFailed

helpers = MagicMock()
helpers.update_coordinator = update_coordinator

# Mock exceptions module
exceptions = MagicMock()
exceptions.ConfigEntryAuthFailed = Exception
exceptions.ConfigEntryNotReady = Exception
exceptions.HomeAssistantError = Exception
