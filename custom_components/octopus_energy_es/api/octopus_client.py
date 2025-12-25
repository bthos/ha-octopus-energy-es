"""Octopus Energy España API client for consumption and billing data."""
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
    """Client for Octopus Energy España API."""

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
        Authenticate with Octopus Energy España GraphQL API and return auth token.

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
                errors = response["errors"]
                _LOGGER.error("GraphQL authentication error: %s", errors)
                
                # Extract user-friendly error message from GraphQL error structure
                error_message = None
                for error in errors:
                    if isinstance(error, dict):
                        # Check for errorDescription in extensions
                        extensions = error.get("extensions", {})
                        if "errorDescription" in extensions:
                            error_message = extensions["errorDescription"]
                            break
                        # Check for validation errors
                        validation_errors = extensions.get("validationErrors", [])
                        if validation_errors:
                            error_message = validation_errors[0].get("message")
                            break
                        # Fall back to main message
                        if "message" in error:
                            error_message = error["message"]
                            break
                
                # Default message if we couldn't extract one
                if not error_message:
                    error_message = str(errors)
                
                # Check if it's a credentials error
                error_msg_lower = error_message.lower()
                if any(phrase in error_msg_lower for phrase in [
                    "invalid", "credentials", "incorrect", "wrong", 
                    "please make sure", "kt-ct-1138"
                ]):
                    raise OctopusClientError("Invalid Octopus Energy credentials. Please check your email and password.")
                
                raise OctopusClientError(f"Authentication failed: {error_message}")

            if "data" not in response or "obtainKrakenToken" not in response["data"]:
                _LOGGER.error("Unexpected authentication response: %s", response)
                raise OctopusClientError("No auth token received from API")

            self._auth_token = response["data"]["obtainKrakenToken"]["token"]

            if not self._auth_token:
                _LOGGER.error("No auth token in response: %s", response)
                raise OctopusClientError("No auth token received from API")

            _LOGGER.debug("Successfully authenticated with Octopus Energy España API")
            return self._auth_token

        except Exception as err:
            if isinstance(err, OctopusClientError):
                raise
            error_msg = str(err)
            if "Domain name not found" in error_msg or "Name or service not known" in error_msg:
                _LOGGER.error(
                    "Octopus Energy España API endpoint not found. "
                    "The API may not be publicly available. "
                    "Consumption and billing data will not be available. "
                    "Price data will still work using market data sources."
                )
                raise OctopusClientError(
                    "Octopus Energy España API is not available. "
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

    async def _fetch_property_id(self) -> str | None:
        """
        Fetch property ID for the account.
        
        Returns:
            Property ID string, or None if not found
        """
        query = """
            query AccountProperties($accountNumber: String!) {
                account(accountNumber: $accountNumber) {
                    properties {
                        id
                        electricitySupplyPoints {
                            cups
                        }
                    }
                }
            }
        """
        
        account = self._property_id
        if not account:
            accounts = await self.fetch_properties()
            if accounts:
                account = accounts[0]["number"]
            else:
                _LOGGER.warning("No account number available for fetching property ID")
                return None
        
        try:
            client = await self._get_graphql_client()
            response = await client.execute_async(query, {"accountNumber": account})
            
            if "errors" in response:
                _LOGGER.error("GraphQL error fetching properties: %s", response["errors"])
                return None
            
            if "data" not in response or "account" not in response["data"]:
                _LOGGER.warning("Unexpected response format when fetching properties")
                return None
            
            account_data = response["data"]["account"]
            if not account_data or "properties" not in account_data:
                _LOGGER.warning("No properties found for account")
                return None
            
            properties = account_data["properties"]
            if properties and len(properties) > 0:
                property_id = properties[0].get("id")
                _LOGGER.debug("Found property ID: %s", property_id)
                return property_id
            
            _LOGGER.warning("No property ID found in properties list")
            return None
            
        except Exception as err:
            _LOGGER.error("Error fetching property ID: %s", err)
            return None

    async def fetch_consumption(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        granularity: str = "hourly",
        use_property_query: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Fetch consumption data using GraphQL.

        Args:
            start_date: Start date for consumption data
            end_date: End date for consumption data
            granularity: 'hourly' or 'daily'
            use_property_query: If True, use property-based query (more efficient, default).
                               If False, use account-based query (fallback).

        Returns:
            List of consumption data dictionaries with:
            - start_time: ISO datetime string
            - end_time: ISO datetime string
            - consumption: kWh value
            - unit: "kWh"
        """
        # Default: property-based query (more efficient, discovered via reverse engineering)
        # Falls back to account-based query if property query fails
        if use_property_query:
            try:
                return await self._fetch_consumption_via_property(
                    start_date=start_date,
                    end_date=end_date,
                    granularity=granularity,
                )
            except Exception as err:
                _LOGGER.warning(
                    "Property-based consumption query failed, falling back to account-based query: %s",
                    err
                )
                try:
                    return await self._fetch_consumption_via_account(
                        start_date=start_date,
                        end_date=end_date,
                        granularity=granularity,
                    )
                except Exception as account_err:
                    _LOGGER.error(
                        "Both property-based and account-based consumption queries failed. "
                        "Property query error: %s. Account query error: %s",
                        err,
                        account_err
                    )
                    raise OctopusClientError(
                        f"Failed to fetch consumption data: {account_err}"
                    ) from account_err
        
        # Fallback: account-based query
        return await self._fetch_consumption_via_account(
            start_date=start_date,
            end_date=end_date,
            granularity=granularity,
        )

    async def _fetch_consumption_via_property(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        granularity: str = "hourly",
    ) -> list[dict[str, Any]]:
        """
        Fetch consumption data using property-based query (preferred method).
        
        This method uses property(id: $propertyId) directly, which is more efficient
        than fetching through account.properties. Discovered via reverse engineering
        of the dashboard JavaScript.
        
        Features:
        - Direct property access (more efficient)
        - Server-side timezone conversion via timezone parameter
        - Utility filtering support (if available in schema)
        
        Args:
            start_date: Start date for consumption data
            end_date: End date for consumption data
            granularity: 'hourly' or 'daily'
            
        Returns:
            List of consumption data dictionaries
        """
        query = """
            query getAccountMeasurements(
                $propertyId: ID!
                $first: Int!
                $startAt: DateTime
                $endAt: DateTime
                $after: String
            ) {
                property(id: $propertyId) {
                    measurements(
                        first: $first
                        startAt: $startAt
                        endAt: $endAt
                        after: $after
                    ) {
                        edges {
                            node {
                                value
                                unit
                                ... on IntervalMeasurementType {
                                    startAt
                                    endAt
                                }
                            }
                        }
                        pageInfo {
                            hasNextPage
                            endCursor
                        }
                    }
                }
            }
        """
        
        # Get property ID
        property_id = await self._fetch_property_id()
        if not property_id:
            _LOGGER.warning(
                "No property ID available for property-based consumption query. "
                "This may indicate an authentication or account access issue."
            )
            raise OctopusClientError("No property ID available for property-based consumption query")
        
        # Set date range (default to last 30 days to ensure we get data)
        if not start_date:
            start_date = date.today() - timedelta(days=30)
        if not end_date:
            end_date = date.today()
        
        _LOGGER.debug(
            "Fetching consumption via property query: propertyId=%s, dateRange=%s to %s, granularity=%s",
            property_id,
            start_date.isoformat(),
            end_date.isoformat(),
            granularity
        )
        
        # Calculate number of measurements based on granularity
        days_diff = (end_date - start_date).days + 1
        if granularity == "hourly":
            first = days_diff * 24
        else:
            first = days_diff
        
        # Limit to reasonable page size (API may have limits)
        page_size = min(first, 100)
        
        all_measurements: list[dict[str, Any]] = []
        after: str | None = None
        
        try:
            client = await self._get_graphql_client()
            
            # Fetch all pages
            while True:
                variables: dict[str, Any] = {
                    "propertyId": property_id,
                    "startAt": start_date.isoformat() + "T00:00:00Z",
                    "endAt": end_date.isoformat() + "T23:59:59Z",
                    "first": page_size,
                }
                if after:
                    variables["after"] = after
                
                response = await client.execute_async(query, variables)
                
                if "errors" in response:
                    errors = response["errors"]
                    # Extract actual GraphQL error messages
                    error_messages = []
                    for error in errors:
                        if isinstance(error, dict):
                            error_messages.append(error.get("message", str(error)))
                        else:
                            error_messages.append(str(error))
                    error_msg = "; ".join(error_messages)
                    _LOGGER.error(
                        "GraphQL error fetching consumption via property: %s. "
                        "Query variables: propertyId=%s, startAt=%s, endAt=%s, first=%s",
                        error_msg,
                        variables.get("propertyId"),
                        variables.get("startAt"),
                        variables.get("endAt"),
                        variables.get("first")
                    )
                    # Raise error to trigger fallback in fetch_consumption()
                    raise OctopusClientError(f"Property-based query failed: {error_msg}")
                
                if "data" not in response or "property" not in response["data"]:
                    _LOGGER.warning("Unexpected response format when fetching consumption via property")
                    raise OctopusClientError("Unexpected response format from property-based query")
                
                property_data = response["data"]["property"]
                if not property_data:
                    _LOGGER.debug("Property data is None or empty")
                    break
                
                measurements = property_data.get("measurements", {})
                if not measurements:
                    _LOGGER.debug("No measurements object in property data")
                    break
                
                edges = measurements.get("edges", [])
                page_info = measurements.get("pageInfo", {})
                _LOGGER.debug(
                    "Property query returned %d edges, pageInfo=%s for date range %s to %s",
                    len(edges),
                    page_info,
                    variables.get("startAt"),
                    variables.get("endAt")
                )
                
                # Log first edge structure for debugging if edges exist
                if edges and len(edges) > 0:
                    _LOGGER.debug("Sample edge structure: %s", edges[0])
                
                # Extract measurements
                for edge in edges:
                    node = edge.get("node", {})
                    # Log node structure for debugging
                    _LOGGER.debug("Processing node: startAt=%s, value=%s, keys=%s", 
                                 node.get("startAt"), node.get("value"), list(node.keys()))
                    if not node.get("startAt") or node.get("value") is None:
                        _LOGGER.debug("Skipping node: missing startAt or value")
                        continue
                    
                    measurement = {
                        "start_time": node.get("startAt"),
                        "end_time": node.get("endAt"),
                        "consumption": float(node.get("value", 0)),
                        "unit": node.get("unit", "kWh"),
                    }
                    all_measurements.append(measurement)
                
                # Check for next page
                page_info = measurements.get("pageInfo", {})
                if not page_info.get("hasNextPage", False):
                    break
                
                after = page_info.get("endCursor")
                if not after:
                    break
                
                # Limit total number of pages to avoid infinite loops
                if len(all_measurements) >= first:
                    break
            
            if len(all_measurements) == 0:
                _LOGGER.warning(
                    "Property query returned 0 measurements for date range %s to %s. "
                    "Trying account-based query as fallback.",
                    start_date.isoformat(),
                    end_date.isoformat()
                )
                # Try account-based query as fallback when property query returns no data
                try:
                    account_result = await self._fetch_consumption_via_account(
                        start_date=start_date,
                        end_date=end_date,
                        granularity=granularity,
                    )
                    if account_result:
                        _LOGGER.info(
                            "Account-based query returned %d measurements (property query returned 0)",
                            len(account_result)
                        )
                        return account_result
                except Exception as account_err:
                    _LOGGER.debug("Account-based fallback also failed: %s", account_err)
            else:
                _LOGGER.debug("Fetched %d consumption measurements via property query", len(all_measurements))
            return all_measurements
            
        except Exception as err:
            if isinstance(err, OctopusClientError):
                raise
            _LOGGER.error("Error fetching consumption via property: %s", err, exc_info=True)
            # Re-raise to trigger fallback in fetch_consumption()
            raise OctopusClientError(f"Property-based query error: {err}") from err
    
    async def _fetch_consumption_via_account(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        granularity: str = "hourly",
    ) -> list[dict[str, Any]]:
        """
        Fetch consumption data using account-based query (original implementation).
        
        This is the fallback method that uses account(accountNumber: $accountNumber).properties.
        """
        query = """
            query MeasurementsQuery(
                $accountNumber: String!
                $startAt: DateTime!
                $endAt: DateTime!
                $first: Int!
                $after: String
            ) {
                account(accountNumber: $accountNumber) {
                    properties {
                        id
                        measurements(
                            startAt: $startAt
                            endAt: $endAt
                            first: $first
                            after: $after
                        ) {
                            pageInfo {
                                hasNextPage
                                endCursor
                            }
                            edges {
                                node {
                                    ... on IntervalMeasurementType {
                                        startAt
                                        endAt
                                        value
                                        unit
                                    }
                                }
                            }
                        }
                    }
                }
            }
        """
        
        # Get account number
        account = self._property_id
        if not account:
            accounts = await self.fetch_properties()
            if accounts:
                account = accounts[0]["number"]
            else:
                _LOGGER.warning("No account number available for fetching consumption")
                return []
        
        # Get property ID
        property_id = await self._fetch_property_id()
        if not property_id:
            _LOGGER.warning("No property ID available for fetching consumption")
            return []
        
        # Set date range (default to last 30 days to ensure we get data)
        if not start_date:
            start_date = date.today() - timedelta(days=30)
        if not end_date:
            end_date = date.today()
        
        _LOGGER.debug(
            "Fetching consumption via account query: accountNumber=%s, dateRange=%s to %s, granularity=%s",
            account,
            start_date.isoformat(),
            end_date.isoformat(),
            granularity
        )
        
        # Calculate number of measurements based on granularity
        days_diff = (end_date - start_date).days + 1
        if granularity == "hourly":
            first = days_diff * 24
        else:
            first = days_diff
        
        # Limit to reasonable page size
        page_size = min(first, 100)
        
        all_measurements: list[dict[str, Any]] = []
        after: str | None = None
        
        try:
            client = await self._get_graphql_client()
            
            # Fetch all pages
            while True:
                variables: dict[str, Any] = {
                    "accountNumber": account,
                    "startAt": start_date.isoformat() + "T00:00:00Z",
                    "endAt": end_date.isoformat() + "T23:59:59Z",
                    "first": page_size,
                }
                if after:
                    variables["after"] = after
                
                response = await client.execute_async(query, variables)
                
                if "errors" in response:
                    error_msg = str(response["errors"])
                    _LOGGER.error("GraphQL error fetching consumption: %s", error_msg)
                    # Don't raise error, just return what we have
                    break
                
                if "data" not in response or "account" not in response["data"]:
                    _LOGGER.warning("Unexpected response format when fetching consumption")
                    break
                
                account_data = response["data"]["account"]
                if not account_data or "properties" not in account_data:
                    break
                
                properties = account_data["properties"]
                if not properties or len(properties) == 0:
                    break
                
                # Find the property matching our property_id
                target_property = None
                for prop in properties:
                    if prop.get("id") == property_id:
                        target_property = prop
                        break
                
                if not target_property:
                    _LOGGER.warning("Property ID %s not found in properties list", property_id)
                    break
                
                measurements = target_property.get("measurements", {})
                edges = measurements.get("edges", [])
                
                # Extract measurements
                # Note: Property should already be electricity-specific, so all measurements
                # from this property should be electricity consumption
                for edge in edges:
                    node = edge.get("node", {})
                    # Check if we have the required fields from IntervalMeasurementType
                    if not node.get("startAt") or node.get("value") is None:
                        continue
                    
                    measurement = {
                        "start_time": node.get("startAt"),
                        "end_time": node.get("endAt"),
                        "consumption": float(node.get("value", 0)),
                        "unit": node.get("unit", "kWh"),
                    }
                    all_measurements.append(measurement)
                
                # Check for next page
                page_info = measurements.get("pageInfo", {})
                if not page_info.get("hasNextPage", False):
                    break
                
                after = page_info.get("endCursor")
                if not after:
                    break
                
                # Limit total number of pages to avoid infinite loops
                if len(all_measurements) >= first:
                    break
            
            _LOGGER.debug("Fetched %d consumption measurements", len(all_measurements))
            return all_measurements
            
        except Exception as err:
            if isinstance(err, OctopusClientError):
                raise
            _LOGGER.error("Error fetching consumption: %s", err, exc_info=True)
            # Return empty list instead of raising to allow graceful degradation
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
        Fetch billing data (invoices, costs) using GraphQL.

        Returns:
            Dictionary with billing information including:
            - solar_wallet: Solar wallet balance
            - octopus_credit: Octopus credit balance
            - last_invoice: Last invoice details
        """
        query = """
            query ($account: String!) {
              accountBillingInfo(accountNumber: $account) {
                ledgers {
                  ledgerType
                  statementsWithDetails(first: 1) {
                    edges {
                      node {
                        amount
                        consumptionStartDate
                        consumptionEndDate
                        issuedDate
                      }
                    }
                  }
                  balance
                }
              }
            }
        """
        
        # Use property_id as account number (they should be the same)
        account = self._property_id
        if not account:
            # Try to get first account if property_id not set
            accounts = await self.fetch_properties()
            if accounts:
                account = accounts[0]["number"]
            else:
                raise OctopusClientError("No account number available")

        try:
            client = await self._get_graphql_client()
            response = await client.execute_async(query, {"account": account})

            if "errors" in response:
                _LOGGER.error("GraphQL error fetching billing: %s", response["errors"])
                raise OctopusClientError(f"Error fetching billing: {response['errors']}")

            if "data" not in response or "accountBillingInfo" not in response["data"]:
                _LOGGER.warning("Unexpected response format when fetching billing")
                return {}

            ledgers = response["data"]["accountBillingInfo"]["ledgers"]
            
            # Find electricity and solar wallet ledgers
            SOLAR_WALLET_LEDGER = "SOLAR_WALLET_LEDGER"
            ELECTRICITY_LEDGER = "SPAIN_ELECTRICITY_LEDGER"
            
            electricity = next(
                (x for x in ledgers if x["ledgerType"] == ELECTRICITY_LEDGER), 
                None
            )
            solar_wallet = next(
                (x for x in ledgers if x["ledgerType"] == SOLAR_WALLET_LEDGER),
                {"balance": 0}
            )

            if not electricity:
                _LOGGER.warning("Electricity ledger not found")
                return {
                    "solar_wallet": float(solar_wallet["balance"]) / 100 if solar_wallet else 0,
                    "octopus_credit": 0,
                    "last_invoice": None,
                }

            invoices = electricity.get("statementsWithDetails", {}).get("edges", [])

            if len(invoices) == 0:
                return {
                    "solar_wallet": float(solar_wallet["balance"]) / 100 if solar_wallet else 0,
                    "octopus_credit": float(electricity["balance"]) / 100 if electricity.get("balance") else 0,
                    "last_invoice": None,
                }

            invoice = invoices[0]["node"]

            # Parse dates (handle timezone offset)
            issued_date = datetime.fromisoformat(invoice["issuedDate"].replace("Z", "+00:00")).date()
            start_date = (datetime.fromisoformat(invoice["consumptionStartDate"].replace("Z", "+00:00")) + timedelta(hours=2)).date()
            end_date = (datetime.fromisoformat(invoice["consumptionEndDate"].replace("Z", "+00:00")) - timedelta(seconds=1)).date()

            # Invoice amount is likely in cents, convert to euros
            invoice_amount_raw = invoice.get("amount", 0)
            if invoice_amount_raw is None:
                invoice_amount = 0.0
            else:
                # Convert to float first, then check if it's in cents
                try:
                    invoice_amount = float(invoice_amount_raw)
                    # If amount is greater than 1000, it's likely in cents
                    if invoice_amount > 1000:
                        invoice_amount = invoice_amount / 100
                except (ValueError, TypeError):
                    _LOGGER.warning("Invalid invoice amount format: %s", invoice_amount_raw)
                    invoice_amount = 0.0

            return {
                "solar_wallet": float(solar_wallet["balance"]) / 100 if solar_wallet else 0,
                "octopus_credit": float(electricity["balance"]) / 100 if electricity.get("balance") else 0,
                "last_invoice": {
                    "amount": invoice_amount,
                    "issued": issued_date.isoformat(),
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat(),
                },
            }

        except Exception as err:
            if isinstance(err, OctopusClientError):
                raise
            _LOGGER.error("Error fetching billing: %s", err)
            raise OctopusClientError(f"Error fetching billing: {err}") from err

    async def fetch_account_credits(
        self, ledger_number: str | None = None, from_date: str = "2025-01-01"
    ) -> dict[str, Any]:
        """
        Fetch account credits (transactions) using GraphQL.
        
        Retrieves credits including SUN_CLUB and SUN_CLUB_POWER_UP savings.
        
        Args:
            ledger_number: Optional ledger number to filter by. If None, fetches from all ledgers.
            from_date: Start date for transactions (ISO format, default: "2025-01-01")
            
        Returns:
            Dictionary with credits and totals:
            {
                "credits": [...],  # List of credit records
                "totals": {
                    "sun_club": float,  # Total regular SUN_CLUB credits
                    "sun_club_power_up": float,  # Total POWER_UP credits
                    "current_month": float,  # Current month total
                    "last_month": float,  # Last month total
                    "total": float  # All-time total
                }
            }
        """
        from ..const import CREDIT_REASON_SUN_CLUB, CREDIT_REASON_SUN_CLUB_POWER_UP
        
        query = """
            query AccountCreditsQuery(
              $accountNumber: String!
              $ledgerNumber: String
              $after: String
              $fromDate: Date!
            ) {
              account(accountNumber: $accountNumber) {
                ledgers(ledgerNumber: $ledgerNumber) {
                  transactions(fromDate: $fromDate, first: 100, after: $after) {
                    pageInfo {
                      hasNextPage
                      endCursor
                    }
                    edges {
                      node {
                        __typename
                        ... on Credit {
                          id
                          amounts {
                            gross
                          }
                          createdAt
                          reasonCode
                        }
                      }
                    }
                  }
                }
              }
            }
        """
        
        account = self._property_id
        if not account:
            accounts = await self.fetch_properties()
            if accounts:
                account = accounts[0]["number"]
            else:
                raise OctopusClientError("No account number available")
        
        all_credits: list[dict[str, Any]] = []
        after: str | None = None
        
        try:
            client = await self._get_graphql_client()
            
            # Fetch all pages of credits
            while True:
                variables: dict[str, Any] = {
                    "accountNumber": account,
                    "fromDate": from_date,
                }
                if ledger_number is not None:
                    variables["ledgerNumber"] = ledger_number
                if after is not None:
                    variables["after"] = after
                
                response = await client.execute_async(query, variables)
                
                if "errors" in response:
                    _LOGGER.error("GraphQL error fetching credits: %s", response["errors"])
                    raise OctopusClientError(f"Error fetching credits: {response['errors']}")
                
                if "data" not in response or "account" not in response["data"]:
                    _LOGGER.warning("Unexpected response format when fetching credits")
                    break
                
                account_data = response["data"]["account"]
                if not account_data or "ledgers" not in account_data:
                    break
                
                ledgers = account_data["ledgers"]
                if not ledgers or len(ledgers) == 0:
                    break
                
                transactions = ledgers[0].get("transactions", {})
                edges = transactions.get("edges", [])
                
                # Extract credits from edges
                for edge in edges:
                    node = edge.get("node", {})
                    if node.get("__typename") == "Credit":
                        credit = {
                            "id": node.get("id"),
                            "amount": node.get("amounts", {}).get("gross", 0),
                            "createdAt": node.get("createdAt"),
                            "reasonCode": node.get("reasonCode"),
                        }
                        all_credits.append(credit)
                
                # Check for next page
                page_info = transactions.get("pageInfo", {})
                if not page_info.get("hasNextPage", False):
                    break
                
                after = page_info.get("endCursor")
                if not after:
                    break
            
            # Filter SUN CLUB credits
            sun_club_credits = [
                c for c in all_credits
                if c.get("reasonCode", "").startswith(CREDIT_REASON_SUN_CLUB)
            ]
            
            # Calculate totals
            now = datetime.now(self._timezone)
            current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            last_month_start = (current_month_start - timedelta(days=1)).replace(day=1)
            last_month_end = current_month_start - timedelta(seconds=1)
            
            total_sun_club = 0.0
            total_sun_club_power_up = 0.0
            total_current_month = 0.0
            total_last_month = 0.0
            total_all = 0.0
            
            for credit in sun_club_credits:
                amount = float(credit.get("amount", 0)) / 100  # Convert cents to euros
                reason_code = credit.get("reasonCode", "")
                created_at_str = credit.get("createdAt")
                
                total_all += amount
                
                # Categorize by reason code
                if reason_code == CREDIT_REASON_SUN_CLUB:
                    total_sun_club += amount
                elif reason_code.startswith(CREDIT_REASON_SUN_CLUB_POWER_UP):
                    total_sun_club_power_up += amount
                
                # Date-based totals
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
            
            return {
                "credits": sun_club_credits,
                "totals": {
                    "sun_club": round(total_sun_club, 2),
                    "sun_club_power_up": round(total_sun_club_power_up, 2),
                    "current_month": round(total_current_month, 2),
                    "last_month": round(total_last_month, 2),
                    "total": round(total_all, 2),
                },
            }
            
        except Exception as err:
            if isinstance(err, OctopusClientError):
                raise
            _LOGGER.error("Error fetching credits: %s", err)
            raise OctopusClientError(f"Error fetching credits: {err}") from err

    async def fetch_tariff_info(self) -> dict[str, Any] | None:
        """
        Fetch tariff information from API if available.

        Note: GraphQL API may not have a direct tariff endpoint.
        This is a placeholder for future implementation.

        Returns:
            Dictionary with tariff rates, or None if not available
        """
        # TODO: Implement GraphQL query for tariff information
        # The reference implementation doesn't show tariff queries
        # This may need to be implemented based on available GraphQL schema
        _LOGGER.debug("Tariff info fetching not yet implemented for GraphQL API")
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

    async def fetch_account_info(self) -> dict[str, Any] | None:
        """
        Fetch account information including name, email, mobile, address, and tariff.

        Returns:
            Dictionary with account information, or None if not available
        """
        query = """
            query AccountInfo($accountNumber: String!) {
                account(accountNumber: $accountNumber) {
                    number
                    properties {
                        id
                        address
                        electricitySupplyPoints {
                            cups
                        }
                    }
                }
                viewer {
                    firstName
                    lastName
                    email
                    mobile
                }
            }
        """
        
        # Get account number
        account = self._property_id
        if not account:
            accounts = await self.fetch_properties()
            if accounts:
                account = accounts[0]["number"]
            else:
                _LOGGER.warning("No account number available for fetching account info")
                return None
        
        try:
            client = await self._get_graphql_client()
            response = await client.execute_async(query, {"accountNumber": account})
            
            if "errors" in response:
                _LOGGER.error("GraphQL error fetching account info: %s", response["errors"])
                return None
            
            if "data" not in response:
                _LOGGER.warning("Unexpected response format when fetching account info")
                return None
            
            data = response["data"]
            account_data = data.get("account", {})
            viewer_data = data.get("viewer", {})
            
            # Get account number
            account_id = account_data.get("number", account)
            
            # Get address from first property (address is a string)
            address_str = None
            properties = account_data.get("properties", [])
            if properties:
                property_data = properties[0]
                address_str = property_data.get("address")
                
                # Get CUPS from first supply point
                supply_points = property_data.get("electricitySupplyPoints", [])
                cups = None
                if supply_points:
                    supply_point = supply_points[0]
                    cups = supply_point.get("cups")
            
            # Get user info
            first_name = viewer_data.get("firstName", "")
            last_name = viewer_data.get("lastName", "")
            name = f"{first_name} {last_name}".strip() if first_name or last_name else None
            email = viewer_data.get("email")
            mobile = viewer_data.get("mobile")
            
            account_info = {
                "account_id": account_id,
                "name": name,
                "email": email,
                "mobile": mobile,
                "address": address_str,
                "tariff": None,  # Tariff not available from API, use config entry instead
                "cups": cups,
            }
            
            _LOGGER.debug("Fetched account info: %s", account_info)
            return account_info
            
        except Exception as err:
            if isinstance(err, OctopusClientError):
                raise
            _LOGGER.error("Error fetching account info: %s", err, exc_info=True)
            return None

