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
from .api.tariff_scraper import TariffScraper, TariffScraperError
from .const import (
    CONF_PROPERTY_ID,
    CONF_PVPC_SENSOR,
    CONF_TARIFF_TYPE,
    DOMAIN,
    HISTORICAL_RANGE_1_YEAR,
    HISTORICAL_RANGE_2_YEARS,
    HISTORICAL_RANGE_ALL_AVAILABLE,
    HISTORICAL_RANGE_CUSTOM,
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

        self._tariff_scraper = TariffScraper()

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
        self._historical_data: list[dict[str, Any]] = []
        self._historical_credits_data: list[dict[str, Any]] = []

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
                    tariff_type = self._entry.data.get(CONF_TARIFF_TYPE)
                    if tariff_type:
                        account_info["tariff"] = tariff_type
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

        # Merge historical data with recent consumption data
        merged_consumption = self._merge_consumption_data(
            self._consumption_data or [],
            self._historical_data or []
        )
        
        # Merge historical credits with recent credits data
        merged_credits = self._merge_credits_data(
            self._credits_data or {},
            self._historical_credits_data or []
        )
        
        # Always return a dict, even if empty, so sensors don't fail
        result = {
            "today_prices": self._today_prices or [],
            "tomorrow_prices": self._tomorrow_prices or [],
            "consumption": merged_consumption,
            "billing": self._billing_data or {},
            "credits": merged_credits,
            "account": self._account_data or {},
        }
        
        _LOGGER.debug(
            "Coordinator update complete: %d today prices, %d tomorrow prices",
            len(result["today_prices"]),
            len(result["tomorrow_prices"]),
        )
        
        return result

    async def async_load_historical_data(
        self, start_date: date | None = None, end_date: date | None = None
    ) -> list[dict[str, Any]]:
        """
        Load historical consumption data for the specified date range.
        
        Args:
            start_date: Start date for historical data. If None, uses config entry settings.
            end_date: End date for historical data. If None, defaults to today.
            
        Returns:
            List of consumption measurements
        """
        if not self._octopus_client:
            _LOGGER.warning("Cannot load historical data: Octopus Energy client not available")
            return []
        
        # Determine date range from config entry if not provided
        if start_date is None or end_date is None:
            entry_data = self._entry.data
            historical_range = entry_data.get("historical_data_range")
            
            if not end_date:
                end_date = date.today()
            
            if not start_date:
                if historical_range == HISTORICAL_RANGE_1_YEAR:
                    start_date = end_date - timedelta(days=365)
                elif historical_range == HISTORICAL_RANGE_2_YEARS:
                    start_date = end_date - timedelta(days=730)
                elif historical_range == HISTORICAL_RANGE_CUSTOM:
                    start_date_str = entry_data.get("historical_data_start_date")
                    if start_date_str:
                        try:
                            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                        except ValueError:
                            _LOGGER.error("Invalid start_date format: %s", start_date_str)
                            return []
                    else:
                        _LOGGER.error("Custom date range selected but no start_date provided")
                        return []
                elif historical_range == HISTORICAL_RANGE_ALL_AVAILABLE:
                    # For "all available", we'll try to fetch from a reasonable start date
                    # The API will return what's available
                    start_date = end_date - timedelta(days=365 * 2)  # Start with 2 years, API will limit
                else:
                    # Default to 1 year if not specified
                    start_date = end_date - timedelta(days=365)
        
        _LOGGER.info(
            "Loading historical consumption data: %s to %s",
            start_date.isoformat(),
            end_date.isoformat()
        )
        
        try:
            # Fetch consumption data with chunking support
            consumption_data = await self._octopus_client.fetch_consumption(
                start_date=start_date,
                end_date=end_date,
                granularity="hourly",
                use_property_query=True,
            )
            
            _LOGGER.info(
                "Successfully loaded %d historical consumption measurements",
                len(consumption_data)
            )
            
            return consumption_data
        except OctopusClientError as err:
            _LOGGER.error("Error loading historical data: %s", err)
            return []
        except Exception as err:
            _LOGGER.error("Unexpected error loading historical data: %s", err, exc_info=True)
            return []

    def _merge_consumption_data(
        self, recent_consumption: list[dict[str, Any]], historical_consumption: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Merge recent and historical consumption data, removing duplicates.
        
        Args:
            recent_consumption: List of recent consumption measurements
            historical_consumption: List of historical consumption measurements
            
        Returns:
            Merged list of consumption measurements, sorted chronologically
        """
        if not historical_consumption:
            return recent_consumption or []
        
        # Create a dict keyed by start_time for deduplication
        merged_dict: dict[str, dict[str, Any]] = {}
        
        # First add historical data
        for item in historical_consumption:
            if isinstance(item, dict):
                start_time = item.get("start_time") or item.get("date")
                if start_time:
                    merged_dict[start_time] = item
        
        # Then add recent data (will overwrite historical if same start_time)
        for item in recent_consumption or []:
            if isinstance(item, dict):
                start_time = item.get("start_time") or item.get("date")
                if start_time:
                    merged_dict[start_time] = item
        
        # Convert back to list and sort by start_time
        merged_list = list(merged_dict.values())
        merged_list.sort(key=lambda x: x.get("start_time") or x.get("date") or "")
        
        return merged_list

    def _merge_credits_data(
        self, recent_credits: dict[str, Any], historical_credits: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Merge recent and historical credits data, removing duplicates.
        
        Args:
            recent_credits: Dict with recent credits structure (from API)
            historical_credits: List of historical credit records
            
        Returns:
            Merged credits dict with all credits combined
        """
        if not historical_credits:
            return recent_credits or {}
        
        # Extract credits list from recent_credits structure
        recent_credits_list = recent_credits.get("credits", []) if isinstance(recent_credits, dict) else []
        
        # Create a dict keyed by credit ID for deduplication
        merged_credits_dict: dict[str, dict[str, Any]] = {}
        
        # First add historical credits
        for credit in historical_credits:
            if isinstance(credit, dict):
                credit_id = credit.get("id")
                if credit_id:
                    merged_credits_dict[credit_id] = credit
                else:
                    # Fallback: use createdAt as key if no ID
                    created_at = credit.get("createdAt")
                    if created_at:
                        merged_credits_dict[created_at] = credit
        
        # Then add recent credits (will overwrite historical if same ID)
        for credit in recent_credits_list:
            if isinstance(credit, dict):
                credit_id = credit.get("id")
                if credit_id:
                    merged_credits_dict[credit_id] = credit
                else:
                    # Fallback: use createdAt as key if no ID
                    created_at = credit.get("createdAt")
                    if created_at:
                        merged_credits_dict[created_at] = credit
        
        # Convert back to list
        merged_credits_list = list(merged_credits_dict.values())
        
        # Recalculate totals with merged credits
        # Group by reason code
        credits_by_reason_code: dict[str, list[dict[str, Any]]] = {}
        for credit in merged_credits_list:
            reason_code = credit.get("reasonCode", "UNKNOWN")
            if reason_code not in credits_by_reason_code:
                credits_by_reason_code[reason_code] = []
            credits_by_reason_code[reason_code].append(credit)
        
        # Calculate totals by reason code
        totals_by_reason_code: dict[str, float] = {}
        for reason_code, credits_list in credits_by_reason_code.items():
            totals_by_reason_code[reason_code] = sum(
                float(c.get("amount", 0)) / 100 for c in credits_list
            )
        
        # Calculate date-based totals
        now = datetime.now(self._timezone)
        current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_month_start = (current_month_start - timedelta(days=1)).replace(day=1)
        last_month_end = current_month_start - timedelta(seconds=1)
        
        total_current_month = 0.0
        total_last_month = 0.0
        total_all = 0.0
        
        for credit in merged_credits_list:
            amount = float(credit.get("amount", 0)) / 100  # Convert cents to euros
            created_at_str = credit.get("createdAt")
            
            total_all += amount
            
            if created_at_str:
                try:
                    created_at = datetime.fromisoformat(
                        created_at_str.replace("Z", "+00:00")
                    ).astimezone(self._timezone)
                    
                    if created_at >= current_month_start:
                        total_current_month += amount
                    elif last_month_start <= created_at <= last_month_end:
                        total_last_month += amount
                except (ValueError, AttributeError) as err:
                    _LOGGER.debug("Error parsing credit date %s: %s", created_at_str, err)
        
        # For backward compatibility, calculate SUN_CLUB specific totals
        from .const import CREDIT_REASON_SUN_CLUB, CREDIT_REASON_SUN_CLUB_POWER_UP
        
        sun_club_total = totals_by_reason_code.get(CREDIT_REASON_SUN_CLUB, 0.0)
        sun_club_power_up_total = 0.0
        for reason_code, total in totals_by_reason_code.items():
            if reason_code.startswith(CREDIT_REASON_SUN_CLUB_POWER_UP):
                sun_club_power_up_total += total
        
        return {
            "credits": merged_credits_list,
            "by_reason_code": credits_by_reason_code,
            "totals_by_reason_code": {
                code: round(total, 2) for code, total in totals_by_reason_code.items()
            },
            "totals": {
                "sun_club": round(sun_club_total, 2),  # Backward compatibility
                "sun_club_power_up": round(sun_club_power_up_total, 2),  # Backward compatibility
                "current_month": round(total_current_month, 2),
                "last_month": round(total_last_month, 2),
                "total": round(total_all, 2),
            },
        }

    async def async_load_historical_credits(
        self, start_date: date | None = None, end_date: date | None = None
    ) -> list[dict[str, Any]]:
        """
        Load historical credits data for the specified date range.
        
        Args:
            start_date: Start date for historical credits. If None, uses config entry settings.
            end_date: End date for historical credits. If None, defaults to today.
            
        Returns:
            List of credit records
        """
        if not self._octopus_client:
            _LOGGER.warning("Cannot load historical credits: Octopus Energy client not available")
            return []
        
        # Determine date range from config entry if not provided
        if start_date is None or end_date is None:
            entry_data = self._entry.data
            historical_range = entry_data.get("historical_data_range")
            
            if not end_date:
                end_date = date.today()
            
            if not start_date:
                if historical_range == HISTORICAL_RANGE_1_YEAR:
                    start_date = end_date - timedelta(days=365)
                elif historical_range == HISTORICAL_RANGE_2_YEARS:
                    start_date = end_date - timedelta(days=730)
                elif historical_range == HISTORICAL_RANGE_CUSTOM:
                    start_date_str = entry_data.get("historical_data_start_date")
                    if start_date_str:
                        try:
                            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                        except ValueError:
                            _LOGGER.error("Invalid start_date format: %s", start_date_str)
                            return []
                    else:
                        _LOGGER.error("Custom date range selected but no start_date provided")
                        return []
                elif historical_range == HISTORICAL_RANGE_ALL_AVAILABLE:
                    # For "all available", we'll try to fetch from a reasonable start date
                    start_date = end_date - timedelta(days=365 * 2)  # Start with 2 years
                else:
                    # Default to 1 year if not specified
                    start_date = end_date - timedelta(days=365)
        
        _LOGGER.info(
            "Loading historical credits data: %s to %s",
            start_date.isoformat(),
            end_date.isoformat()
        )
        
        try:
            # Fetch credits data with date range
            # fetch_account_credits uses from_date parameter (ISO string)
            credits_data = await self._octopus_client.fetch_account_credits(
                from_date=start_date.isoformat()
            )
            
            if not credits_data or not credits_data.get("credits"):
                _LOGGER.warning("No historical credits data returned from API")
                return []
            
            credits_list = credits_data.get("credits", [])
            
            # Filter credits to the specified date range
            filtered_credits = []
            for credit in credits_list:
                created_at_str = credit.get("createdAt")
                if created_at_str:
                    try:
                        created_at_dt = datetime.fromisoformat(
                            created_at_str.replace("Z", "+00:00")
                        ).astimezone(self._timezone)
                        created_at_date = created_at_dt.date()
                        
                        if start_date <= created_at_date <= end_date:
                            filtered_credits.append(credit)
                    except (ValueError, AttributeError):
                        # Include credit if date parsing fails (better to include than exclude)
                        filtered_credits.append(credit)
                else:
                    # Include credit if no date (better to include than exclude)
                    filtered_credits.append(credit)
            
            _LOGGER.info(
                "Successfully loaded %d historical credit records",
                len(filtered_credits)
            )
            
            return filtered_credits
        except OctopusClientError as err:
            _LOGGER.error("Error loading historical credits: %s", err)
            return []
        except Exception as err:
            _LOGGER.error("Unexpected error loading historical credits: %s", err, exc_info=True)
            return []

    def get_historical_data_range(self) -> dict[str, Any] | None:
        """
        Get the date range and count of available historical consumption data.
        
        Returns:
            Dict with 'start_date', 'end_date', and 'count' keys, or None if no historical data
        """
        if not self._historical_data:
            return None
        
        try:
            # Find earliest and latest dates from historical data
            dates: list[date] = []
            for item in self._historical_data:
                if isinstance(item, dict):
                    start_time_str = item.get("start_time") or item.get("date")
                    if start_time_str:
                        try:
                            dt = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
                            if dt.tzinfo is None:
                                dt = dt.replace(tzinfo=ZoneInfo("UTC"))
                            dt_madrid = dt.astimezone(self._timezone)
                            dates.append(dt_madrid.date())
                        except (ValueError, TypeError):
                            continue
            
            if not dates:
                return None
            
            dates.sort()
            return {
                "start_date": dates[0].isoformat(),
                "end_date": dates[-1].isoformat(),
                "count": len(self._historical_data),
            }
        except Exception as err:
            _LOGGER.debug("Error getting historical data range: %s", err)
            return None

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
        await self._tariff_scraper.close()
        await super().async_shutdown()

