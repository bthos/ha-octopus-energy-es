"""Config flow for Octopus Energy España integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_DISCOUNT_START_HOUR,
    CONF_DISCOUNT_END_HOUR,
    CONF_DISCOUNT_PERCENTAGE,
    CONF_FIXED_RATE,
    CONF_MANAGEMENT_FEE_MONTHLY,
    CONF_P1_HOURS_WEEKDAYS,
    CONF_P1_RATE,
    CONF_P2_HOURS_WEEKDAYS,
    CONF_P2_RATE,
    CONF_P3_HOURS_WEEKDAYS,
    CONF_P3_RATE,
    CONF_POWER_P1_RATE,
    CONF_POWER_P2_RATE,
    CONF_PRICING_MODEL,
    CONF_PVPC_SENSOR,
    CONF_PROPERTY_ID,
    CONF_SOLAR_SURPLUS_RATE,
    CONF_TIME_STRUCTURE,
    DEFAULT_P1_HOURS_WEEKDAYS,
    DEFAULT_P2_HOURS_WEEKDAYS,
    DEFAULT_P3_HOURS_WEEKDAYS,
    DOMAIN,
    PRICING_MODEL_FIXED,
    PRICING_MODEL_MARKET,
    TIME_STRUCTURE_SINGLE_RATE,
    TIME_STRUCTURE_TIME_OF_USE,
)

_LOGGER = logging.getLogger(__name__)


class OctopusEnergyESConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Octopus Energy España."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._data: dict[str, Any] = {}
        self._pricing_model: str | None = None
        self._time_structure: str | None = None
        self._properties: list[dict[str, Any]] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        return await self.async_step_pricing_model(user_input)

    async def async_step_pricing_model(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle pricing model selection."""
        if user_input is not None:
            self._pricing_model = user_input[CONF_PRICING_MODEL]
            self._data[CONF_PRICING_MODEL] = self._pricing_model
            
            if self._pricing_model == PRICING_MODEL_FIXED:
                return await self.async_step_time_structure()
            else:
                # Market pricing - skip time structure step
                self._time_structure = TIME_STRUCTURE_SINGLE_RATE
                self._data[CONF_TIME_STRUCTURE] = self._time_structure
                return await self.async_step_octopus_credentials()

        return self.async_show_form(
            step_id="pricing_model",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PRICING_MODEL): vol.In(
                        {
                            PRICING_MODEL_FIXED: "Fixed (Fixed rates for 12 months)",
                            PRICING_MODEL_MARKET: "Market (Variable market-based pricing)",
                        }
                    )
                }
            ),
        )

    async def async_step_time_structure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle time structure selection (for Fixed pricing)."""
        if user_input is not None:
            self._time_structure = user_input[CONF_TIME_STRUCTURE]
            self._data[CONF_TIME_STRUCTURE] = self._time_structure
            return await self.async_step_octopus_credentials()

        return self.async_show_form(
            step_id="time_structure",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_TIME_STRUCTURE): vol.In(
                        {
                            TIME_STRUCTURE_SINGLE_RATE: "Single Rate (Same price 24h)",
                            TIME_STRUCTURE_TIME_OF_USE: "Time-of-Use (P1/P2/P3 periods)",
                        }
                    )
                }
            ),
            description_placeholders={
                "period_info": (
                    "P1 (Punta): 11-14, 19-22 weekdays\n"
                    "P2 (Llano): 9-10, 15-18, 23 weekdays\n"
                    "P3 (Valle): 0-8 weekdays, all hours weekends/holidays"
                ),
            },
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
                return await self.async_step_energy_rates()
            # Validate credentials by attempting to authenticate
            try:
                from .api.octopus_client import OctopusClient, OctopusClientError
                
                email = user_input.get(CONF_EMAIL, "")
                password = user_input.get(CONF_PASSWORD, "")
                
                if not email or not password:
                    # No credentials provided - skip to energy rates
                    return await self.async_step_energy_rates()
                
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
                            "Octopus Energy España API is not publicly available. "
                            "The integration will work for price data only. "
                            "Consumption and billing features will not be available."
                        )
                        # Store credentials anyway - user might want to use them later
                        # or the API might become available
                        self._data[CONF_EMAIL] = email
                        self._data[CONF_PASSWORD] = password
                        await test_client.close()
                        return await self.async_step_energy_rates()
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
                        return await self.async_step_energy_rates()
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
                        "Octopus Energy España API is not publicly available. "
                        "The integration will work for price data only. "
                        "Consumption and billing features will not be available."
                    )
                    # Store credentials if provided
                    if user_input.get(CONF_EMAIL) and user_input.get(CONF_PASSWORD):
                        self._data[CONF_EMAIL] = user_input[CONF_EMAIL]
                        self._data[CONF_PASSWORD] = user_input[CONF_PASSWORD]
                    return await self.async_step_energy_rates()
                
                # Other authentication errors - provide user-friendly messages
                _LOGGER.error("Error validating credentials: %s", err)
                # Check for invalid credentials errors (including GraphQL validation errors)
                if any(phrase in error_msg for phrase in [
                    "401", 
                    "invalid", 
                    "credentials", 
                    "incorrect",
                    "wrong",
                    "please make sure",
                    "please check",
                    "kt-ct-1138"  # GraphQL error code for invalid credentials
                ]):
                    errors["base"] = "invalid_auth"
                elif any(phrase in error_msg for phrase in [
                    "cannot_connect", 
                    "connection", 
                    "network", 
                    "timeout"
                ]):
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
            return await self.async_step_energy_rates()

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
                return await self.async_step_energy_rates()
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

    async def async_step_energy_rates(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle energy rates configuration."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_power_rates()

        pricing_model = self._pricing_model or self._data.get(CONF_PRICING_MODEL, PRICING_MODEL_MARKET)
        time_structure = self._time_structure or self._data.get(CONF_TIME_STRUCTURE, TIME_STRUCTURE_SINGLE_RATE)

        schema_dict: dict[str, Any] = {}

        if pricing_model == PRICING_MODEL_FIXED:
            if time_structure == TIME_STRUCTURE_SINGLE_RATE:
                schema_dict[vol.Required(CONF_FIXED_RATE)] = vol.Coerce(float)
            elif time_structure == TIME_STRUCTURE_TIME_OF_USE:
                schema_dict[vol.Required(CONF_P1_RATE)] = vol.Coerce(float)
                schema_dict[vol.Required(CONF_P2_RATE)] = vol.Coerce(float)
                schema_dict[vol.Required(CONF_P3_RATE)] = vol.Coerce(float)
        else:
            # Market pricing - optional management fee
            schema_dict[vol.Optional(CONF_MANAGEMENT_FEE_MONTHLY)] = vol.Coerce(float)

        return self.async_show_form(
            step_id="energy_rates",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
        )

    async def async_step_power_rates(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle power rates configuration (always required)."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_solar_features()

        return self.async_show_form(
            step_id="power_rates",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_POWER_P1_RATE): vol.Coerce(float),
                    vol.Required(CONF_POWER_P2_RATE): vol.Coerce(float),
                }
            ),
            description_placeholders={
                "power_info": (
                    "Power rates (Potencia) are always time-of-use:\n"
                    "P1 (Punta): Same hours as energy P1\n"
                    "P2 (Valle): Combines energy P2 + P3 hours"
                ),
            },
            errors=errors,
        )

    async def async_step_solar_features(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle solar features configuration (optional)."""
        if user_input is not None:
            if user_input.get("has_solar"):
                self._data[CONF_SOLAR_SURPLUS_RATE] = user_input.get(CONF_SOLAR_SURPLUS_RATE, 0.04)
            return await self.async_step_discount_programs()

        return self.async_show_form(
            step_id="solar_features",
            data_schema=vol.Schema(
                {
                    vol.Required("has_solar", default=False): bool,
                    vol.Optional(CONF_SOLAR_SURPLUS_RATE, default=0.04): vol.Coerce(float),
                }
            ),
            description_placeholders={
                "solar_info": (
                    "Solar surplus rate: Compensation rate for surplus energy (€/kWh).\n"
                    "Solar Wallet balance is retrieved from API automatically."
                ),
            },
        )

    async def async_step_discount_programs(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle discount programs configuration (optional)."""
        if user_input is not None:
            if user_input.get("has_discount"):
                self._data[CONF_DISCOUNT_START_HOUR] = user_input.get(CONF_DISCOUNT_START_HOUR)
                self._data[CONF_DISCOUNT_END_HOUR] = user_input.get(CONF_DISCOUNT_END_HOUR)
                self._data[CONF_DISCOUNT_PERCENTAGE] = user_input.get(CONF_DISCOUNT_PERCENTAGE, 0.45)
            return await self.async_step_pvpc_sensor()

        return self.async_show_form(
            step_id="discount_programs",
            data_schema=vol.Schema(
                {
                    vol.Required("has_discount", default=False): bool,
                    vol.Optional(CONF_DISCOUNT_START_HOUR, default=12): vol.All(
                        vol.Coerce(int), vol.Range(min=0, max=23)
                    ),
                    vol.Optional(CONF_DISCOUNT_END_HOUR, default=18): vol.All(
                        vol.Coerce(int), vol.Range(min=0, max=23)
                    ),
                    vol.Optional(CONF_DISCOUNT_PERCENTAGE, default=0.45): vol.All(
                        vol.Coerce(float), vol.Range(min=0, max=1)
                    ),
                }
            ),
        )

    async def async_step_pvpc_sensor(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle PVPC sensor selection."""
        if user_input is not None:
            pvpc_sensor = user_input.get(CONF_PVPC_SENSOR, "sensor.pvpc")
            self._data[CONF_PVPC_SENSOR] = pvpc_sensor
            
            # Generate title based on pricing model
            pricing_model = self._pricing_model or self._data.get(CONF_PRICING_MODEL, PRICING_MODEL_MARKET)
            model_name = "Fixed" if pricing_model == PRICING_MODEL_FIXED else "Market"
            
            return self.async_create_entry(
                title=f"Octopus Energy España - {model_name}",
                data=self._data,
            )

        return self.async_show_form(
            step_id="pvpc_sensor",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_PVPC_SENSOR, default="sensor.pvpc"): str,
                }
            ),
        )

