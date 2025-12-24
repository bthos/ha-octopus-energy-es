"""ESIOS API client for fetching PVPC prices."""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any

import aiohttp
from zoneinfo import ZoneInfo

from ..const import ESIOS_API_BASE_URL, ESIOS_API_INDICATOR_PVPC, TIMEZONE_MADRID

_LOGGER = logging.getLogger(__name__)


class ESIOSClientError(Exception):
    """Exception raised for ESIOS API errors."""


class ESIOSClient:
    """Client for ESIOS API."""

    def __init__(self, token: str | None = None) -> None:
        """Initialize ESIOS client."""
        self._token = token
        self._session: aiohttp.ClientSession | None = None
        self._timezone = ZoneInfo(TIMEZONE_MADRID)

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        """Close the session."""
        if self._session:
            await self._session.close()
            self._session = None

    async def fetch_pvpc_prices(
        self, target_date: date | None = None
    ) -> list[dict[str, Any]]:
        """
        Fetch PVPC prices for a specific date.

        Args:
            target_date: Date to fetch prices for. If None, fetches today's prices.

        Returns:
            List of price data dictionaries with 'start_time' and 'price_per_kwh' keys.
        """
        if target_date is None:
            target_date = datetime.now(self._timezone).date()

        # ESIOS API expects dates in format YYYY-MM-DD
        date_str = target_date.isoformat()

        # Build URL
        url = f"{ESIOS_API_BASE_URL}/indicators/{ESIOS_API_INDICATOR_PVPC}"
        params = {
            "start_date": date_str,
            "end_date": date_str,
        }

        headers: dict[str, str] = {
            "Accept": "application/json; application/vnd.esios-api-v1+json",
            "Content-Type": "application/json",
        }

        if self._token:
            headers["x-api-key"] = self._token

        session = await self._get_session()

        try:
            async with session.get(url, params=params, headers=headers) as response:
                if response.status == 401:
                    raise ESIOSClientError("Invalid ESIOS API token")
                if response.status == 404:
                    # Data not yet available (e.g., tomorrow's prices before 14:00)
                    _LOGGER.debug(
                        "PVPC prices not yet available for %s", target_date.isoformat()
                    )
                    return []
                if response.status == 403:
                    _LOGGER.warning("ESIOS API access forbidden. Token may be required or invalid")
                    # Try without token if we had one, or suggest getting a token
                    if self._token:
                        raise ESIOSClientError("ESIOS API access forbidden. Token may be invalid.")
                    else:
                        raise ESIOSClientError("ESIOS API requires a token. Please get one from consultasios@ree.es")
                response.raise_for_status()

                data = await response.json()
                _LOGGER.debug("ESIOS API response: %s", data)

                # Parse ESIOS response format
                prices = self._parse_esios_response(data, target_date)
                
                if not prices:
                    _LOGGER.warning("No prices parsed from ESIOS response for %s", target_date.isoformat())

                return prices

        except aiohttp.ClientError as err:
            _LOGGER.error("ESIOS API client error: %s", err)
            raise ESIOSClientError(f"Error fetching ESIOS data: {err}") from err

    def _parse_esios_response(
        self, data: dict[str, Any], target_date: date
    ) -> list[dict[str, Any]]:
        """
        Parse ESIOS API response into our format.

        ESIOS response format can be:
        {
            "indicator": {
                "id": 1001,
                "name": "PVPC",
                "values": [
                    {
                        "datetime": "2025-01-15T00:00:00.000+01:00",
                        "value": 123.45,  # Price in €/MWh
                        ...
                    },
                    ...
                ]
            }
        }
        Or:
        {
            "indicator": {
                "id": 1001,
                ...
            },
            "values": [
                {
                    "datetime": "2025-01-15T00:00:00.000+01:00",
                    "value": 123.45,
                    ...
                }
            ]
        }
        """
        prices: list[dict[str, Any]] = []

        # Try different response formats
        values = None
        if "indicator" in data:
            if "values" in data["indicator"]:
                values = data["indicator"]["values"]
            elif isinstance(data["indicator"], dict) and "values" in data:
                values = data["values"]
        elif "values" in data:
            values = data["values"]

        if not values:
            _LOGGER.warning("Unexpected ESIOS response format: %s", data.keys())
            _LOGGER.debug("Full ESIOS response: %s", data)
            return prices

        for value_item in values:
            try:
                # Parse datetime
                dt_str = value_item.get("datetime", "")
                if not dt_str:
                    continue

                # Parse datetime string (ISO 8601 format)
                dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))

                # Ensure timezone-aware
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=self._timezone)
                else:
                    dt = dt.astimezone(self._timezone)

                # Get price value (in €/MWh)
                price_mwh = float(value_item.get("value", 0))

                # Convert to €/kWh
                price_kwh = price_mwh / 1000.0

                prices.append(
                    {
                        "start_time": dt.isoformat(),
                        "price_per_kwh": round(price_kwh, 6),
                    }
                )

            except (ValueError, KeyError, TypeError) as err:
                _LOGGER.warning("Error parsing ESIOS value: %s", err)
                continue

        # Sort by start_time
        prices.sort(key=lambda x: x["start_time"])

        return prices

    async def fetch_today_prices(self) -> list[dict[str, Any]]:
        """Fetch today's PVPC prices."""
        return await self.fetch_pvpc_prices()

    async def fetch_tomorrow_prices(self) -> list[dict[str, Any]]:
        """Fetch tomorrow's PVPC prices."""
        tomorrow = datetime.now(self._timezone).date() + timedelta(days=1)
        return await self.fetch_pvpc_prices(tomorrow)

