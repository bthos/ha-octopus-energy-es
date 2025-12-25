"""Octopus Energy Spain API client for consumption and billing data."""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any

import aiohttp
from python_graphql_client import GraphqlClient
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
        Authenticate with Octopus Energy Spain GraphQL API and return auth token.

        Uses GraphQL mutation: obtainKrakenToken
        """
        if self._auth_token:
            return self._auth_token

        mutation = """
           mutation obtainKrakenToken($input: ObtainJSONWebTokenInput!) {
              obtainKrakenToken(input: $input) {
                token
              }
            }
        """
        variables = {"input": {"email": self._email, "password": self._password}}

        try:
            client = GraphqlClient(endpoint=OCTOPUS_API_BASE_URL)
            response = await client.execute_async(mutation, variables)

            if "errors" in response:
                error_msg = str(response["errors"])
                _LOGGER.error("GraphQL authentication error: %s", error_msg)
                if "401" in error_msg or "invalid" in error_msg.lower() or "credentials" in error_msg.lower():
                    raise OctopusClientError("Invalid Octopus Energy credentials")
                raise OctopusClientError(f"Authentication failed: {error_msg}")

            if "data" not in response or "obtainKrakenToken" not in response["data"]:
                _LOGGER.error("Unexpected authentication response: %s", response)
                raise OctopusClientError("No auth token received from API")

            self._auth_token = response["data"]["obtainKrakenToken"]["token"]

            if not self._auth_token:
                _LOGGER.error("No auth token in response: %s", response)
                raise OctopusClientError("No auth token received from API")

            _LOGGER.debug("Successfully authenticated with Octopus Energy Spain API")
            return self._auth_token

        except Exception as err:
            if isinstance(err, OctopusClientError):
                raise
            error_msg = str(err)
            if "Domain name not found" in error_msg or "Name or service not known" in error_msg:
                _LOGGER.error(
                    "Octopus Energy Spain API endpoint not found. "
                    "The API may not be publicly available. "
                    "Consumption and billing data will not be available. "
                    "Price data will still work using market data sources."
                )
                raise OctopusClientError(
                    "Octopus Energy Spain API is not available. "
                    "This integration can still provide price data using market sources, "
                    "but consumption and billing data will not be available."
                ) from err
            _LOGGER.error("Network error authenticating: %s", err)
            raise OctopusClientError(f"Error authenticating: {err}") from err

    async def _get_graphql_client(self) -> GraphqlClient:
        """Get GraphQL client with authentication."""
        token = await self._authenticate()
        return GraphqlClient(
            endpoint=OCTOPUS_API_BASE_URL,
            headers={"authorization": token}
        )

    async def fetch_consumption(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        granularity: str = "hourly",
    ) -> list[dict[str, Any]]:
        """
        Fetch consumption data using GraphQL.

        Note: The GraphQL API may not support consumption queries directly.
        This is a placeholder for future implementation.

        Args:
            start_date: Start date for consumption data
            end_date: End date for consumption data
            granularity: 'hourly' or 'daily'

        Returns:
            List of consumption data dictionaries
        """
        # TODO: Implement GraphQL query for consumption data
        # The reference implementation doesn't show consumption queries
        # This may need to be implemented based on available GraphQL schema
        _LOGGER.warning("Consumption data fetching not yet implemented for GraphQL API")
        return []

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

    async def fetch_properties(self) -> list[dict[str, Any]]:
        """
        Fetch list of accounts for the authenticated user using GraphQL.

        Returns:
            List of account dictionaries with 'number' field
        """
        query = """
             query getAccountNames{
                viewer {
                    accounts {
                        ... on Account {
                            number
                        }
                    }
                }
            }
        """

        try:
            client = await self._get_graphql_client()
            response = await client.execute_async(query)

            if "errors" in response:
                _LOGGER.error("GraphQL error fetching accounts: %s", response["errors"])
                return []

            if "data" not in response or "viewer" not in response["data"]:
                _LOGGER.warning("Unexpected response format when fetching accounts")
                return []

            accounts = response["data"]["viewer"]["accounts"]
            # Convert to list of dicts with 'id' field for compatibility
            properties = [{"id": acc["number"], "number": acc["number"]} for acc in accounts]
            
            _LOGGER.debug("Found %d accounts", len(properties))
            return properties

        except Exception as err:
            _LOGGER.error("Error fetching accounts: %s", err)
            return []

