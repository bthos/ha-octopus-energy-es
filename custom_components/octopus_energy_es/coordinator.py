"""Data update coordinator for Octopus Energy Spain."""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from zoneinfo import ZoneInfo

from .api.esios_client import ESIOSClient, ESIOSClientError
from .api.omie_client import OMIEClient
from .api.octopus_client import OctopusClient, OctopusClientError
from .api.tariff_scraper import TariffScraper, TariffScraperError
from .const import (
    CONF_ESIOS_TOKEN,
    CONF_PROPERTY_ID,
    DOMAIN,
    MARKET_PUBLISH_HOUR,
    TIMEZONE_MADRID,
    UPDATE_INTERVAL_BILLING,
    UPDATE_INTERVAL_CONSUMPTION,
    UPDATE_INTERVAL_TODAY,
    UPDATE_INTERVAL_TOMORROW,
)
from .tariff.calculator import TariffCalculator
from .tariff.types import create_tariff_config

_LOGGER = logging.getLogger(__name__)


class OctopusEnergyESCoordinator(DataUpdateCoordinator):
    """Coordinator for Octopus Energy Spain data updates."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL_TODAY,
        )

        self._entry = entry
        self._timezone = ZoneInfo(TIMEZONE_MADRID)

        # Initialize API clients
        esios_token = entry.data.get(CONF_ESIOS_TOKEN)
        self._esios_client = ESIOSClient(token=esios_token)

        self._omie_client = OMIEClient()

        email = entry.data[CONF_EMAIL]
        password = entry.data[CONF_PASSWORD]
        property_id = entry.data[CONF_PROPERTY_ID]
        self._octopus_client = OctopusClient(email, password, property_id)

        self._tariff_scraper = TariffScraper()

        # Create tariff calculator
        tariff_config = create_tariff_config(entry.data)
        self._tariff_calculator = TariffCalculator(tariff_config)

        # Data storage
        self._today_prices: list[dict[str, Any]] = []
        self._tomorrow_prices: list[dict[str, Any]] = []
        self._consumption_data: list[dict[str, Any]] = []
        self._billing_data: dict[str, Any] = {}

        # Track last update times
        self._last_tomorrow_update: datetime | None = None

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from APIs."""
        now = datetime.now(self._timezone)
        current_hour = now.hour

        # Update today's prices (hourly)
        try:
            self._today_prices = await self._fetch_and_calculate_prices()
        except Exception as err:
            _LOGGER.warning("Error updating today's prices: %s", err)
            if not self._today_prices:
                raise UpdateFailed(f"Error updating prices: {err}") from err

        # Update tomorrow's prices (daily at 14:00 CET)
        should_update_tomorrow = (
            current_hour >= MARKET_PUBLISH_HOUR
            and (
                self._last_tomorrow_update is None
                or self._last_tomorrow_update.date() < now.date()
            )
        )

        if should_update_tomorrow:
            try:
                tomorrow = now.date() + timedelta(days=1)
                self._tomorrow_prices = await self._fetch_and_calculate_prices(
                    tomorrow
                )
                self._last_tomorrow_update = now
            except Exception as err:
                _LOGGER.warning("Error updating tomorrow's prices: %s", err)
                # Don't fail if tomorrow's prices aren't available yet

        # Update consumption data (every 15 minutes)
        try:
            self._consumption_data = await self._octopus_client.fetch_consumption(
                granularity="hourly"
            )
        except OctopusClientError as err:
            _LOGGER.debug("Error updating consumption: %s", err)
            # Consumption is optional, don't fail

        # Update billing data (daily)
        try:
            self._billing_data = await self._octopus_client.fetch_billing()
        except OctopusClientError as err:
            _LOGGER.debug("Error updating billing: %s", err)
            # Billing is optional, don't fail

        return {
            "today_prices": self._today_prices,
            "tomorrow_prices": self._tomorrow_prices,
            "consumption": self._consumption_data,
            "billing": self._billing_data,
        }

    async def _fetch_and_calculate_prices(
        self, target_date: date | None = None
    ) -> list[dict[str, Any]]:
        """Fetch market prices and calculate tariff prices."""
        market_prices: list[dict[str, Any]] = []

        # Try ESIOS first
        try:
            market_prices = await self._esios_client.fetch_pvpc_prices(target_date)
        except ESIOSClientError as err:
            _LOGGER.warning("ESIOS API error: %s", err)
            # Try OMIE as fallback
            try:
                market_prices = await self._omie_client.fetch_market_prices(
                    target_date
                )
            except Exception as fallback_err:
                _LOGGER.warning("OMIE fallback also failed: %s", fallback_err)
                # If both fail and we have cached data, use it
                if target_date is None and self._today_prices:
                    return self._today_prices
                elif target_date and self._tomorrow_prices:
                    return self._tomorrow_prices
                raise

        if not market_prices:
            # No prices available yet (e.g., tomorrow before 14:00)
            return []

        # Calculate prices based on tariff type
        calculated_prices = self._tariff_calculator.calculate_prices(
            market_prices, target_date
        )

        return calculated_prices

    async def async_config_entry_first_refresh(self) -> None:
        """Refresh data for the first time."""
        await super().async_config_entry_first_refresh()

    async def async_shutdown(self) -> None:
        """Shutdown coordinator and close clients."""
        await self._esios_client.close()
        await self._omie_client.close()
        await self._octopus_client.close()
        await self._tariff_scraper.close()
        await super().async_shutdown()

