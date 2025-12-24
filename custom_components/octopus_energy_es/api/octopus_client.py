"""Octopus Energy Spain API client for consumption and billing data."""
from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

import aiohttp
from zoneinfo import ZoneInfo

from ..const import OCTOPUS_API_BASE_URL, TIMEZONE_MADRID

_LOGGER = logging.getLogger(__name__)


class OctopusClientError(Exception):
    """Exception raised for Octopus Energy API errors."""


class OctopusClient:
    """Client for Octopus Energy Spain API."""

    def __init__(self, email: str, password: str, property_id: str) -> None:
        """Initialize Octopus Energy client."""
        self._email = email
        self._password = password
        self._property_id = property_id
        self._session: aiohttp.ClientSession | None = None
        self._auth_token: str | None = None
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

    async def _authenticate(self) -> str:
        """
        Authenticate with Octopus Energy API and return auth token.

        Reference: octopus-spain-monitor implementation
        """
        if self._auth_token:
            return self._auth_token

        session = await self._get_session()
        url = f"{OCTOPUS_API_BASE_URL}/auth/login"

        try:
            async with session.post(
                url,
                json={"email": self._email, "password": self._password},
            ) as response:
                if response.status == 401:
                    raise OctopusClientError("Invalid Octopus Energy credentials")
                if response.status == 404:
                    raise OctopusClientError("Octopus Energy API endpoint not found. API may have changed.")
                response.raise_for_status()

                data = await response.json()
                _LOGGER.debug("Octopus API auth response: %s", data)
                
                self._auth_token = data.get("token") or data.get("access_token") or data.get("accessToken")

                if not self._auth_token:
                    _LOGGER.error("No auth token in response: %s", data)
                    raise OctopusClientError("No auth token received from API")

                return self._auth_token

        except aiohttp.ClientError as err:
            _LOGGER.error("Network error authenticating: %s", err)
            raise OctopusClientError(f"Error authenticating: {err}") from err

    async def _get_headers(self) -> dict[str, str]:
        """Get request headers with authentication."""
        token = await self._authenticate()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    async def fetch_consumption(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        granularity: str = "hourly",
    ) -> list[dict[str, Any]]:
        """
        Fetch consumption data.

        Args:
            start_date: Start date for consumption data
            end_date: End date for consumption data
            granularity: 'hourly' or 'daily'

        Returns:
            List of consumption data dictionaries
        """
        if start_date is None:
            start_date = datetime.now(self._timezone).date()
        if end_date is None:
            end_date = start_date

        session = await self._get_session()
        headers = await self._get_headers()

        url = f"{OCTOPUS_API_BASE_URL}/consumption"
        params = {
            "property_id": self._property_id,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "granularity": granularity,
        }

        try:
            async with session.get(url, params=params, headers=headers) as response:
                if response.status == 401:
                    # Token might be expired, try to re-authenticate
                    self._auth_token = None
                    headers = await self._get_headers()
                    async with session.get(
                        url, params=params, headers=headers
                    ) as retry_response:
                        retry_response.raise_for_status()
                        data = await retry_response.json()
                else:
                    response.raise_for_status()
                    data = await response.json()

                return self._parse_consumption_response(data)

        except aiohttp.ClientError as err:
            raise OctopusClientError(f"Error fetching consumption: {err}") from err

    def _parse_consumption_response(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """Parse consumption API response."""
        consumption_data: list[dict[str, Any]] = []

        # Parse response format from Octopus Energy API
        # Format may vary, this is a generic parser
        if isinstance(data, list):
            consumption_data = data
        elif isinstance(data, dict):
            if "results" in data:
                consumption_data = data["results"]
            elif "data" in data:
                consumption_data = data["data"]
            elif "consumption" in data:
                consumption_data = data["consumption"]

        return consumption_data

    async def fetch_billing(self) -> dict[str, Any]:
        """
        Fetch billing data (invoices, costs).

        Returns:
            Dictionary with billing information
        """
        session = await self._get_session()
        headers = await self._get_headers()

        url = f"{OCTOPUS_API_BASE_URL}/billing"
        params = {"property_id": self._property_id}

        try:
            async with session.get(url, params=params, headers=headers) as response:
                if response.status == 401:
                    self._auth_token = None
                    headers = await self._get_headers()
                    async with session.get(
                        url, params=params, headers=headers
                    ) as retry_response:
                        retry_response.raise_for_status()
                        return await retry_response.json()
                else:
                    response.raise_for_status()
                    return await response.json()

        except aiohttp.ClientError as err:
            raise OctopusClientError(f"Error fetching billing: {err}") from err

    async def fetch_tariff_info(self) -> dict[str, Any] | None:
        """
        Fetch tariff information from API if available.

        Returns:
            Dictionary with tariff rates, or None if not available
        """
        session = await self._get_session()
        headers = await self._get_headers()

        url = f"{OCTOPUS_API_BASE_URL}/tariff"
        params = {"property_id": self._property_id}

        try:
            async with session.get(url, params=params, headers=headers) as response:
                if response.status == 404:
                    # Tariff endpoint might not exist
                    return None
                if response.status == 401:
                    self._auth_token = None
                    headers = await self._get_headers()
                    async with session.get(
                        url, params=params, headers=headers
                    ) as retry_response:
                        if retry_response.status == 404:
                            return None
                        retry_response.raise_for_status()
                        return await retry_response.json()
                else:
                    response.raise_for_status()
                    return await response.json()

        except aiohttp.ClientError as err:
            _LOGGER.debug("Error fetching tariff info: %s", err)
            return None

