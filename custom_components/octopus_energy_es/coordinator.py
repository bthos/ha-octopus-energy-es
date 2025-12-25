"""Data update coordinator for Octopus Energy España."""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from zoneinfo import ZoneInfo

from .api.omie_client import OMIEClient
from .api.octopus_client import OctopusClient, OctopusClientError
from .const import (
    CONF_PROPERTY_ID,
    CONF_PVPC_SENSOR,
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
    """Coordinator for Octopus Energy España data updates."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL_TODAY,
        )

        self._entry = entry
        self._hass = hass
        self._timezone = ZoneInfo(TIMEZONE_MADRID)

        # PVPC sensor entity ID (default to sensor.pvpc)
        self._pvpc_sensor = entry.data.get(CONF_PVPC_SENSOR, "sensor.pvpc")

        self._omie_client = OMIEClient()

        # Octopus API may not be available - credentials are optional
        email = entry.data.get(CONF_EMAIL)
        password = entry.data.get(CONF_PASSWORD)
        property_id = entry.data.get(CONF_PROPERTY_ID, "")
        
        if email and password:
            self._octopus_client = OctopusClient(email, password, property_id)
        else:
            _LOGGER.info("Octopus Energy credentials not provided - using price data only")
            self._octopus_client = None

        # Create tariff calculator
        tariff_config = create_tariff_config(entry.data)
        self._tariff_calculator = TariffCalculator(tariff_config)

        # Data storage
        self._today_prices: list[dict[str, Any]] = []
        self._tomorrow_prices: list[dict[str, Any]] = []
        self._consumption_data: list[dict[str, Any]] = []
        self._billing_data: dict[str, Any] = {}
        self._credits_data: dict[str, Any] = {}
        self._account_data: dict[str, Any] = {}

        # Track last update times
        self._last_tomorrow_update: datetime | None = None

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from APIs."""
        now = datetime.now(self._timezone)
        current_hour = now.hour

        # Update today's prices (hourly)
        try:
            prices = await self._fetch_and_calculate_prices()
            if prices:
                self._today_prices = prices
                _LOGGER.info("Successfully fetched %d price points for today", len(prices))
            elif not self._today_prices:
                # No prices and no cached data - log warning but don't fail completely
                _LOGGER.warning("No price data available and no cached data")
        except Exception as err:
            _LOGGER.error("Error updating today's prices: %s", err, exc_info=True)
            if not self._today_prices:
                # Only fail if we have no cached data at all
                _LOGGER.error("No cached price data available, raising UpdateFailed")
                raise UpdateFailed(f"Error updating prices: {err}") from err
            else:
                _LOGGER.warning("Using cached price data due to update error")

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
        # Note: Octopus Energy España API may not be publicly available
        if self._octopus_client:
            try:
                consumption_result = await self._octopus_client.fetch_consumption(
                    granularity="hourly"
                )
                self._consumption_data = consumption_result or []
                if consumption_result:
                    _LOGGER.debug(
                        "Fetched %d consumption measurements",
                        len(consumption_result)
                    )
                else:
                    _LOGGER.debug("No consumption data returned from API")
            except OctopusClientError as err:
                error_msg = str(err).lower()
                self._consumption_data = []  # Reset on error
                if "not available" in error_msg or "not be publicly" in error_msg:
                    _LOGGER.info(
                        "Octopus Energy España API is not available. "
                        "Consumption data will not be available. "
                        "Price sensors will continue to work using market data."
                    )
                else:
                    _LOGGER.warning(
                        "Error updating consumption data: %s. "
                        "Consumption sensors will show as Unknown.",
                        err
                    )
                # Consumption is optional, don't fail
            except Exception as err:
                self._consumption_data = []  # Reset on unexpected error
                _LOGGER.warning(
                    "Unexpected error updating consumption data: %s. "
                    "Consumption sensors will show as Unknown.",
                    err,
                    exc_info=True
                )

        # Update billing data (daily)
        if self._octopus_client:
            try:
                self._billing_data = await self._octopus_client.fetch_billing()
            except OctopusClientError as err:
                error_msg = str(err).lower()
                if "not available" in error_msg or "not be publicly" in error_msg:
                    _LOGGER.info(
                        "Octopus Energy España API is not available. "
                        "Billing data will not be available. "
                        "Price sensors will continue to work using market data."
                    )
                else:
                    _LOGGER.debug("Error updating billing: %s", err)
                # Billing is optional, don't fail

        # Update credits data (daily)
        if self._octopus_client:
            try:
                self._credits_data = await self._octopus_client.fetch_account_credits()
            except OctopusClientError as err:
                error_msg = str(err).lower()
                if "not available" in error_msg or "not be publicly" in error_msg:
                    _LOGGER.info(
                        "Octopus Energy España API is not available. "
                        "Credits data will not be available. "
                        "Price sensors will continue to work using market data."
                    )
                else:
                    _LOGGER.debug("Error updating credits: %s", err)
                # Credits are optional, don't fail

        # Update account data (daily)
        if self._octopus_client:
            try:
                account_info = await self._octopus_client.fetch_account_info()
                if account_info:
                    # Add tariff from config entry since it's not available from API
                    # Get tariff info from category-based structure
                    pricing_model = self._entry.data.get("pricing_model")
                    time_structure = self._entry.data.get("time_structure")
                    
                    if pricing_model:
                        tariff_display = f"{pricing_model.title()}"
                        if time_structure:
                            tariff_display += f" - {time_structure.replace('_', ' ').title()}"
                        account_info["tariff"] = tariff_display
                    self._account_data = account_info
            except OctopusClientError as err:
                error_msg = str(err).lower()
                if "not available" in error_msg or "not be publicly" in error_msg:
                    _LOGGER.info(
                        "Octopus Energy España API is not available. "
                        "Account data will not be available. "
                        "Price sensors will continue to work using market data."
                    )
                else:
                    _LOGGER.debug("Error updating account info: %s", err)
                # Account info is optional, don't fail

        # Always return a dict, even if empty, so sensors don't fail
        result = {
            "today_prices": self._today_prices or [],
            "tomorrow_prices": self._tomorrow_prices or [],
            "consumption": self._consumption_data or [],
            "billing": self._billing_data or {},
            "credits": self._credits_data or {},
            "account": self._account_data or {},
        }
        
        _LOGGER.debug(
            "Coordinator update complete: %d today prices, %d tomorrow prices",
            len(result["today_prices"]),
            len(result["tomorrow_prices"]),
        )
        
        return result

    async def _fetch_and_calculate_prices(
        self, target_date: date | None = None
    ) -> list[dict[str, Any]]:
        """Fetch market prices from PVPC sensor and calculate tariff prices."""
        market_prices: list[dict[str, Any]] = []

        # Try PVPC sensor first
        try:
            _LOGGER.debug("Fetching prices from PVPC sensor: %s", self._pvpc_sensor)
            pvpc_state = self._hass.states.get(self._pvpc_sensor)
            
            if pvpc_state is None:
                raise ValueError(f"PVPC sensor '{self._pvpc_sensor}' not found. Please ensure the PVPC Hourly Pricing integration is configured.")
            
            # Get price data from sensor attributes
            # PVPC sensor can have either:
            # 1. 'data' attribute with hourly prices array
            # 2. Individual 'Price XXh' attributes (e.g., "Price 00h", "Price 01h", etc.)
            price_data = pvpc_state.attributes.get("data", [])
            
            if price_data:
                # Format 1: Data array format
                # PVPC format: [{"start": "2025-01-15T00:00:00+01:00", "price": 0.12345}, ...]
                for item in price_data:
                    if isinstance(item, dict):
                        start_time = item.get("start") or item.get("start_time")
                        price = item.get("price") or item.get("price_per_kwh")
                        
                        if start_time and price is not None:
                            # Check if this price is for the target date
                            if target_date:
                                try:
                                    price_datetime = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                                    if price_datetime.date() != target_date:
                                        continue
                                except (ValueError, AttributeError):
                                    continue
                            
                            market_prices.append({
                                "start_time": start_time,
                                "price_per_kwh": float(price),
                            })
            else:
                # Format 2: Individual price attributes (price_00h, price_01h, etc.)
                # Get the date for today (or target_date if specified)
                if target_date:
                    price_date = target_date
                else:
                    price_date = datetime.now(self._timezone).date()
                
                # Parse individual hour attributes
                # PVPC sensor uses lowercase with underscore: price_00h, price_01h, etc.
                for hour in range(24):
                    hour_str = f"{hour:02d}"
                    # Try both formats: price_00h (actual) and Price 00h (alternative)
                    price_attr_underscore = f"price_{hour_str}h"
                    price_attr_space = f"Price {hour_str}h"
                    
                    price_value = pvpc_state.attributes.get(price_attr_underscore) or pvpc_state.attributes.get(price_attr_space)
                    
                    if price_value is not None:
                        try:
                            price_float = float(price_value)
                            # Create ISO datetime string for this hour
                            hour_datetime = datetime.combine(
                                price_date,
                                datetime.min.time().replace(hour=hour),
                                self._timezone
                            )
                            start_time = hour_datetime.isoformat()
                            
                            market_prices.append({
                                "start_time": start_time,
                                "price_per_kwh": price_float,
                            })
                        except (ValueError, TypeError):
                            _LOGGER.debug("Invalid price value for %s or %s: %s", price_attr_underscore, price_attr_space, price_value)
                            continue
            
            if not market_prices:
                _LOGGER.warning("PVPC sensor has no price data (checked both 'data' attribute and 'Price XXh' attributes)")
                raise ValueError("PVPC sensor has no price data")
            
            _LOGGER.debug("PVPC sensor returned %d price points", len(market_prices))
            
        except Exception as pvpc_err:
            _LOGGER.warning("PVPC sensor error: %s", pvpc_err)
            # Try OMIE as fallback
            try:
                _LOGGER.debug("Trying OMIE as fallback")
                market_prices = await self._omie_client.fetch_market_prices(
                    target_date
                )
                _LOGGER.debug("OMIE returned %d price points", len(market_prices))
            except Exception as fallback_err:
                _LOGGER.warning("OMIE fallback also failed: %s", fallback_err)
                # If both fail and we have cached data, use it
                if target_date is None and self._today_prices:
                    _LOGGER.info("Using cached today's prices")
                    return self._today_prices
                elif target_date and self._tomorrow_prices:
                    _LOGGER.info("Using cached tomorrow's prices")
                    return self._tomorrow_prices
                _LOGGER.error("No price data available and no cache to fall back to")
                raise

        if not market_prices:
            # No prices available yet (e.g., tomorrow before 14:00)
            _LOGGER.warning("No market prices returned for %s", target_date)
            return []

        # Calculate prices based on tariff type
        calculated_prices = self._tariff_calculator.calculate_prices(
            market_prices, target_date
        )
        _LOGGER.debug("Calculated %d prices for tariff", len(calculated_prices))

        return calculated_prices

    async def async_config_entry_first_refresh(self) -> None:
        """Refresh data for the first time."""
        await super().async_config_entry_first_refresh()

    async def async_shutdown(self) -> None:
        """Shutdown coordinator and close clients."""
        await self._omie_client.close()
        if self._octopus_client:
            await self._octopus_client.close()
        await super().async_shutdown()

