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
            # Validate credentials by attempting to authenticate
            try:
                from .api.octopus_client import OctopusClient, OctopusClientError
                
                email = user_input[CONF_EMAIL]
                password = user_input[CONF_PASSWORD]
                property_id = user_input[CONF_PROPERTY_ID]
                
                # Try to authenticate
                test_client = OctopusClient(email, password, property_id)
                await test_client._authenticate()
                await test_client.close()
                
                # Credentials are valid, store them
                self._data.update(user_input)
                return await self.async_step_tariff_config()
                
            except OctopusClientError as err:
                _LOGGER.error("Error validating credentials: %s", err)
                error_msg = str(err).lower()
                if "401" in error_msg or "invalid" in error_msg:
                    errors["base"] = "invalid_auth"
                elif "cannot_connect" in error_msg or "connection" in error_msg or "network" in error_msg:
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
                            vol.Required(CONF_EMAIL, default=user_input.get(CONF_EMAIL, "")): str,
                            vol.Required(CONF_PASSWORD): str,
                            vol.Required(CONF_PROPERTY_ID, default=user_input.get(CONF_PROPERTY_ID, "")): str,
                        }
                    ),
                    errors=errors,
                )

        return self.async_show_form(
            step_id="octopus_credentials",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_EMAIL): str,
                    vol.Required(CONF_PASSWORD): str,
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

