"""Test configuration and fixtures."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture
def mock_octopus_client():
    """Mock OctopusClient."""
    with patch(
        "custom_components.octopus_energy_es.api.octopus_client.OctopusClient"
    ) as mock_client:
        client_instance = AsyncMock()
        mock_client.return_value = client_instance
        yield client_instance
