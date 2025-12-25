"""Config flow for Octopus Energy Spain integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_ESIOS_TOKEN,
    CONF_PROPERTY_ID,
    CONF_TARIFF_TYPE,
    DEFAULT_P1_HOURS,
    DEFAULT_P2_HOURS,
    DEFAULT_P3_HOURS,
    DOMAIN,
    SUN_CLUB_DAYLIGHT_END,
    SUN_CLUB_DAYLIGHT_START,
    TARIFF_TYPE_FLEXI,
    TARIFF_TYPE_GO,
    TARIFF_TYPE_RELAX,
    TARIFF_TYPE_SOLAR,
    TARIFF_TYPE_SUN_CLUB,
    TARIFF_TYPES,
)

_LOGGER = logging.getLogger(__name__)


class OctopusEnergyESConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Octopus Energy Spain."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._data: dict[str, Any] = {}
        self._tariff_type: str | None = None
        self._properties: list[dict[str, Any]] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        return await self.async_step_tariff_type(user_input)

    async def async_step_tariff_type(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle tariff type selection."""
        if user_input is not None:
            self._tariff_type = user_input[CONF_TARIFF_TYPE]
            self._data[CONF_TARIFF_TYPE] = self._tariff_type
            return await self.async_step_octopus_credentials()

        return self.async_show_form(
            step_id="tariff_type",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_TARIFF_TYPE): vol.In(
                        {
                            TARIFF_TYPE_FLEXI: "Octopus Flexi (Variable Market Price)",
                            TARIFF_TYPE_RELAX: "Octopus Relax (Fixed Price)",
                            TARIFF_TYPE_SOLAR: "Octopus Solar (Time-of-Use)",
                            TARIFF_TYPE_GO: "Octopus Go (EV Tariff)",
                            TARIFF_TYPE_SUN_CLUB: "SUN CLUB (Daylight Discount)",
                        }
                    )
                }
            ),
        )

    async def async_step_octopus_credentials(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle Octopus Energy credentials."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # If user skipped credentials (API not available), allow it
            if not user_input.get(CONF_EMAIL) and not user_input.get(CONF_PASSWORD):
                # User can skip if they only want price data
                _LOGGER.info("Skipping Octopus Energy credentials - using price data only")
                return await self.async_step_tariff_config()
            # Validate credentials by attempting to authenticate
            try:
                from .api.octopus_client import OctopusClient, OctopusClientError
                
                email = user_input.get(CONF_EMAIL, "")
                password = user_input.get(CONF_PASSWORD, "")
                
                if not email or not password:
                    # No credentials provided - skip to tariff config
                    return await self.async_step_tariff_config()
                
                # Try to authenticate (property_id not needed for auth)
                # Use a dummy property_id just for authentication
                test_client = OctopusClient(email, password, "dummy")
                try:
                    await test_client._authenticate()
                except OctopusClientError as err:
                    error_msg = str(err).lower()
                    # Check for API not available errors
                    if any(phrase in error_msg for phrase in [
                        "not available", 
                        "not be publicly", 
                        "domain name not found",
                        "cannot connect to host",
                        "name or service not known"
                    ]):
                        # API doesn't exist - this is OK, we can still use price data
                        _LOGGER.warning(
                            "Octopus Energy Spain API is not publicly available. "
                            "The integration will work for price data only. "
                            "Consumption and billing features will not be available."
                        )
                        # Store credentials anyway - user might want to use them later
                        # or the API might become available
                        self._data[CONF_EMAIL] = email
                        self._data[CONF_PASSWORD] = password
                        await test_client.close()
                        return await self.async_step_tariff_config()
                    else:
                        # Other authentication error - re-raise
                        await test_client.close()
                        raise
                
                # Try to fetch properties list
                properties = await test_client.fetch_properties()
                await test_client.close()
                
                if properties:
                    # If we found properties, store them and let user select
                    self._data[CONF_EMAIL] = email
                    self._data[CONF_PASSWORD] = password
                    self._properties = properties
                    
                    # If only one account, auto-select it
                    if len(properties) == 1:
                        prop = properties[0]
                        # Use account number as property_id
                        self._data[CONF_PROPERTY_ID] = prop.get("number") or prop.get("id") or str(prop)
                        return await self.async_step_tariff_config()
                    else:
                        # Multiple accounts - show selection step
                        return await self.async_step_select_property()
                else:
                    # Couldn't fetch accounts - this is an error
                    # Account should always be available after successful authentication
                    _LOGGER.error("Authentication succeeded but no accounts found. This may indicate an account access issue.")
                    # Store credentials and show manual entry as fallback
                    self._data[CONF_EMAIL] = email
                    self._data[CONF_PASSWORD] = password
                    return await self.async_step_manual_account()
                
            except OctopusClientError as err:
                error_msg = str(err).lower()
                # Check if this is an API not available error
                if any(phrase in error_msg for phrase in [
                    "not available", 
                    "not be publicly", 
                    "domain name not found",
                    "cannot connect to host",
                    "name or service not known"
                ]):
                    # API doesn't exist - allow user to proceed with price data only
                    _LOGGER.warning(
                        "Octopus Energy Spain API is not publicly available. "
                        "The integration will work for price data only. "
                        "Consumption and billing features will not be available."
                    )
                    # Store credentials if provided
                    if user_input.get(CONF_EMAIL) and user_input.get(CONF_PASSWORD):
                        self._data[CONF_EMAIL] = user_input[CONF_EMAIL]
                        self._data[CONF_PASSWORD] = user_input[CONF_PASSWORD]
                    return await self.async_step_tariff_config()
                
                # Other authentication errors - provide user-friendly messages
                _LOGGER.error("Error validating credentials: %s", err)
                if "401" in error_msg or "invalid" in error_msg or "credentials" in error_msg:
                    errors["base"] = "invalid_auth"
                elif "cannot_connect" in error_msg or "connection" in error_msg or "network" in error_msg or "timeout" in error_msg:
                    errors["base"] = "cannot_connect"
                else:
                    errors["base"] = "unknown"
            except Exception as err:
                _LOGGER.error("Unexpected error validating credentials: %s", err, exc_info=True)
                errors["base"] = "unknown"
            
            # If there are errors, show the form again
            if errors:
                return self.async_show_form(
                    step_id="octopus_credentials",
                    data_schema=vol.Schema(
                        {
                            vol.Optional(CONF_EMAIL, default=user_input.get(CONF_EMAIL, "")): str,
                            vol.Optional(CONF_PASSWORD): str,
                        }
                    ),
                    errors=errors,
                )

        return self.async_show_form(
            step_id="octopus_credentials",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_EMAIL): str,
                    vol.Optional(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    async def async_step_select_property(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle account selection when multiple accounts are available."""
        if user_input is not None:
            self._data[CONF_PROPERTY_ID] = user_input[CONF_PROPERTY_ID]
            return await self.async_step_tariff_config()

        # Build options dict from accounts
        property_options = {}
        for prop in self._properties:
            # Use account number as ID
            prop_id = prop.get("number") or prop.get("id") or str(prop)
            prop_name = prop.get("name") or prop.get("address") or prop.get("description") or f"Account {prop_id}"
            property_options[prop_id] = prop_name

        return self.async_show_form(
            step_id="select_property",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PROPERTY_ID): vol.In(property_options),
                }
            ),
        )

    async def async_step_manual_account(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle manual account entry as fallback when auto-detection fails."""
        errors: dict[str, str] = {}

        if user_input is not None:
            account_number = user_input.get(CONF_PROPERTY_ID, "").strip()
            if account_number:
                self._data[CONF_PROPERTY_ID] = account_number
                return await self.async_step_tariff_config()
            else:
                errors["base"] = "account_number_required"

        return self.async_show_form(
            step_id="manual_account",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PROPERTY_ID): str,
                }
            ),
            errors=errors,
        )

    async def async_step_tariff_config(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle tariff-specific configuration."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_esios_token()

        tariff_type = self._tariff_type or self._data.get(CONF_TARIFF_TYPE)

        if tariff_type == TARIFF_TYPE_FLEXI:
            # No configuration needed for Flexi
            return await self.async_step_esios_token()

        schema_dict: dict[str, Any] = {}

        if tariff_type == TARIFF_TYPE_RELAX:
            schema_dict[vol.Required("fixed_rate")] = vol.Coerce(float)

        elif tariff_type == TARIFF_TYPE_SOLAR:
            schema_dict[vol.Required("p1_rate")] = vol.Coerce(float)
            schema_dict[vol.Required("p2_rate")] = vol.Coerce(float)
            schema_dict[vol.Required("p3_rate")] = vol.Coerce(float)
            schema_dict[vol.Optional("solar_surplus_rate", default=0.04)] = vol.Coerce(
                float
            )

        elif tariff_type == TARIFF_TYPE_GO:
            schema_dict[vol.Required("p1_rate")] = vol.Coerce(float)
            schema_dict[vol.Required("p2_rate")] = vol.Coerce(float)
            schema_dict[vol.Required("p3_rate")] = vol.Coerce(float)

        elif tariff_type == TARIFF_TYPE_SUN_CLUB:
            schema_dict[vol.Optional("daylight_start", default=SUN_CLUB_DAYLIGHT_START)] = (
                vol.All(vol.Coerce(int), vol.Range(min=0, max=23))
            )
            schema_dict[vol.Optional("daylight_end", default=SUN_CLUB_DAYLIGHT_END)] = (
                vol.All(vol.Coerce(int), vol.Range(min=0, max=23))
            )
            schema_dict[vol.Optional("discount_percentage", default=0.45)] = vol.All(
                vol.Coerce(float), vol.Range(min=0, max=1)
            )

        return self.async_show_form(
            step_id="tariff_config",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
        )

    async def async_step_esios_token(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle ESIOS API token (optional)."""
        if user_input is not None:
            if token := user_input.get(CONF_ESIOS_TOKEN):
                self._data[CONF_ESIOS_TOKEN] = token
            
            # Get tariff type for title
            tariff_type = self._tariff_type or self._data.get(CONF_TARIFF_TYPE, "Unknown")
            tariff_name = tariff_type.replace("_", " ").title() if tariff_type else "Unknown"
            
            return self.async_create_entry(
                title=f"Octopus Energy Spain - {tariff_name}",
                data=self._data,
            )

        return self.async_show_form(
            step_id="esios_token",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_ESIOS_TOKEN): str,
                }
            ),
        )

