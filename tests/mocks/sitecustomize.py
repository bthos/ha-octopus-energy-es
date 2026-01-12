"""Site customization to inject mocks before imports."""
import sys
from unittest.mock import MagicMock

# Import mocks module
try:
    from tests.mocks import homeassistant as ha_mocks
except ImportError:
    # If running from different path, create minimal mocks
    ha_mocks = MagicMock()
    ha_mocks.config_entries = MagicMock()
    ha_mocks.core = MagicMock()
    ha_mocks.data_entry_flow = MagicMock()
    ha_mocks.const = MagicMock()
    ha_mocks.helpers = MagicMock()
    ha_mocks.exceptions = MagicMock()

# Create mock homeassistant module structure
homeassistant_mock = MagicMock()
homeassistant_mock.config_entries = ha_mocks.config_entries
homeassistant_mock.core = ha_mocks.core
homeassistant_mock.data_entry_flow = ha_mocks.data_entry_flow
homeassistant_mock.const = ha_mocks.const
homeassistant_mock.helpers = ha_mocks.helpers
homeassistant_mock.exceptions = ha_mocks.exceptions

# Inject into sys.modules before any imports
sys.modules['homeassistant'] = homeassistant_mock
sys.modules['homeassistant.config_entries'] = homeassistant_mock.config_entries
sys.modules['homeassistant.core'] = homeassistant_mock.core
sys.modules['homeassistant.data_entry_flow'] = homeassistant_mock.data_entry_flow
sys.modules['homeassistant.const'] = homeassistant_mock.const
sys.modules['homeassistant.helpers'] = homeassistant_mock.helpers
sys.modules['homeassistant.helpers.update_coordinator'] = homeassistant_mock.helpers.update_coordinator
sys.modules['homeassistant.exceptions'] = homeassistant_mock.exceptions

# Make constants available as attributes for direct import
homeassistant_mock.const.CONF_EMAIL = "email"
homeassistant_mock.const.CONF_PASSWORD = "password"
