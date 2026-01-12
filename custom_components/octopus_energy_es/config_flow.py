"""Config flow for Octopus Energy España integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.data_entry_flow import FlowResult
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import HomeAssistantError
from collections.abc import Mapping

from .const import (
    CONF_DEBUG,
    CONF_DISCOUNT_END_HOUR,
    CONF_DISCOUNT_PERCENTAGE,
    CONF_DISCOUNT_START_HOUR,
    CONF_ELECTRICITY_TAX_RATE,
    CONF_FIXED_RATE,
    CONF_MANAGEMENT_FEE_MONTHLY,
    CONF_NAME,
    CONF_OTHER_CONCEPTS_RATE,
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
    CONF_TARIFF_CONFIG_MODE,
    CONF_TIME_STRUCTURE,
    CONF_VAT_RATE,
    DEFAULT_ELECTRICITY_TAX_RATE,
    DEFAULT_P1_HOURS_WEEKDAYS,
    DEFAULT_P2_HOURS_WEEKDAYS,
    DEFAULT_P3_HOURS_WEEKDAYS,
    DEFAULT_VAT_RATE,
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
        self._auto_configured: bool = False
        self._reauth_entry: ConfigEntry | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        return await self.async_step_octopus_credentials(user_input)

    async def async_step_octopus_credentials(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle Octopus Energy credentials."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate credentials by attempting to authenticate
            try:
                from .api.octopus_client import OctopusClient, OctopusClientError
                
                email = user_input.get(CONF_EMAIL, "").strip()
                password = user_input.get(CONF_PASSWORD, "")
                
                if not email or not password:
                    errors["base"] = "email_password_required"
                    return self.async_show_form(
                        step_id="octopus_credentials",
                        data_schema=vol.Schema(
                            {
                                vol.Required(CONF_EMAIL, default=email): str,
                                vol.Required(CONF_PASSWORD): str,
                            }
                        ),
                        errors=errors,
                    )
                
                # Try to authenticate (property_id not needed for auth)
                # Use a dummy property_id just for authentication
                test_client = OctopusClient(email, password, "dummy")
                try:
                    await test_client._authenticate()
                except OctopusClientError as err:
                    error_msg = str(err).lower()
                    await test_client.close()
                    # Handle authentication errors
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
                        "timeout",
                        "not available", 
                        "not be publicly", 
                        "domain name not found",
                        "cannot connect to host",
                        "name or service not known"
                    ]):
                        errors["base"] = "cannot_connect"
                    else:
                        errors["base"] = "unknown"
                    
                    return self.async_show_form(
                        step_id="octopus_credentials",
                        data_schema=vol.Schema(
                            {
                                vol.Required(CONF_EMAIL, default=email): str,
                                vol.Required(CONF_PASSWORD): str,
                            }
                        ),
                        errors=errors,
                    )
                
                # Try to fetch properties list
                properties = await test_client.fetch_properties()
                await test_client.close()
                
                if properties:
                    # If we found properties, store them and let user select
                    self._data[CONF_EMAIL] = email
                    self._data[CONF_PASSWORD] = password
                    self._properties = properties
                    
                    # Set unique ID based on email to prevent duplicate entries
                    # Only check for duplicates if not in reauth flow
                    if not self._reauth_entry:
                        await self.async_set_unique_id(email.lower().strip())
                        self._abort_if_unique_id_configured()
                    
                    # If only one account, auto-select it
                    if len(properties) == 1:
                        prop = properties[0]
                        # Use account number as property_id
                        self._data[CONF_PROPERTY_ID] = prop.get("number") or prop.get("id") or str(prop)
                        return await self.async_step_tariff_config_mode()
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
                
            except Exception as err:
                _LOGGER.error("Unexpected error validating credentials: %s", err, exc_info=True)
                errors["base"] = "unknown"
                return self.async_show_form(
                    step_id="octopus_credentials",
                    data_schema=vol.Schema(
                        {
                            vol.Required(CONF_EMAIL, default=user_input.get(CONF_EMAIL, "")): str,
                            vol.Required(CONF_PASSWORD): str,
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
            return await self.async_step_tariff_config_mode()

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
                return await self.async_step_tariff_config_mode()
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

    def _map_tariff_info_to_config(self, tariff_info: dict[str, Any]) -> bool:
        """
        Map tariff info from API to config flow parameters.
        
        Args:
            tariff_info: Tariff information dictionary from API
            
        Returns:
            True if all required data was successfully mapped, False otherwise
        """
        try:
            product = tariff_info.get("product", {})
            prices = product.get("prices", {})
            params = product.get("params", {})
            
            # Determine pricing model and time structure
            product_type = params.get("product_type", "").upper()
            
            if product_type == "FIXED":
                self._pricing_model = PRICING_MODEL_FIXED
                self._data[CONF_PRICING_MODEL] = PRICING_MODEL_FIXED
                
                # Check fixed_type from params to determine time structure
                fixed_type = params.get("fixed_type", "")
                variable_term = prices.get("variable_term", [])
                
                # Use fixed_type if available, otherwise fall back to variable_term length
                if fixed_type == "SinglePeriod":
                    self._time_structure = TIME_STRUCTURE_SINGLE_RATE
                    self._data[CONF_TIME_STRUCTURE] = TIME_STRUCTURE_SINGLE_RATE
                    if len(variable_term) >= 1:
                        self._data[CONF_FIXED_RATE] = float(variable_term[0])
                    else:
                        _LOGGER.warning("Invalid variable_term length for SinglePeriod: %d", len(variable_term))
                        return False
                elif fixed_type == "TimeOfUse" or len(variable_term) >= 3:
                    self._time_structure = TIME_STRUCTURE_TIME_OF_USE
                    self._data[CONF_TIME_STRUCTURE] = TIME_STRUCTURE_TIME_OF_USE
                    if len(variable_term) >= 3:
                        self._data[CONF_P1_RATE] = float(variable_term[0])
                        self._data[CONF_P2_RATE] = float(variable_term[1])
                        self._data[CONF_P3_RATE] = float(variable_term[2])
                    else:
                        _LOGGER.warning("Invalid variable_term length for TimeOfUse: %d", len(variable_term))
                        return False
                else:
                    # Fallback: determine by variable_term length
                    if len(variable_term) == 1:
                        self._time_structure = TIME_STRUCTURE_SINGLE_RATE
                        self._data[CONF_TIME_STRUCTURE] = TIME_STRUCTURE_SINGLE_RATE
                        self._data[CONF_FIXED_RATE] = float(variable_term[0])
                    elif len(variable_term) >= 3:
                        self._time_structure = TIME_STRUCTURE_TIME_OF_USE
                        self._data[CONF_TIME_STRUCTURE] = TIME_STRUCTURE_TIME_OF_USE
                        self._data[CONF_P1_RATE] = float(variable_term[0])
                        self._data[CONF_P2_RATE] = float(variable_term[1])
                        self._data[CONF_P3_RATE] = float(variable_term[2])
                    else:
                        _LOGGER.warning("Invalid variable_term length: %d", len(variable_term))
                        return False
                
                # Fixed term (power rates)
                fixed_term = prices.get("fixed_term", [])
                if len(fixed_term) >= 2:
                    self._data[CONF_POWER_P1_RATE] = float(fixed_term[0])
                    self._data[CONF_POWER_P2_RATE] = float(fixed_term[1])
                
                # Solar surplus rate (optional)
                # Track if surplus_rate was provided by API (even if 0) to skip form
                surplus_rate = prices.get("surplus_rate")
                if surplus_rate is not None:
                    surplus_rate_float = float(surplus_rate)
                    # Mark that surplus_rate came from API
                    self._data["_surplus_rate_from_api"] = True
                    # Only set CONF_SOLAR_SURPLUS_RATE if > 0 (for enabling solar features)
                    if surplus_rate_float > 0:
                        self._data[CONF_SOLAR_SURPLUS_RATE] = surplus_rate_float
                    # If = 0, don't set CONF_SOLAR_SURPLUS_RATE (solar features disabled)
                    # but _surplus_rate_from_api flag will skip the form
                    
            elif product_type == "MARKET" or product_type == "":
                # Market pricing or unknown type defaults to market
                self._pricing_model = PRICING_MODEL_MARKET
                self._data[CONF_PRICING_MODEL] = PRICING_MODEL_MARKET
                self._time_structure = TIME_STRUCTURE_SINGLE_RATE
                self._data[CONF_TIME_STRUCTURE] = TIME_STRUCTURE_SINGLE_RATE
            else:
                _LOGGER.warning("Unknown product_type: %s", product_type)
                return False
            
            # Tariff name from product display name
            display_name = product.get("display_name")
            if display_name:
                self._data[CONF_NAME] = display_name
            
            # Store tariff info for sensor
            self._data["_tariff_info"] = tariff_info
            
            # Check if all required fields are present
            pricing_model = self._data.get(CONF_PRICING_MODEL)
            time_structure = self._data.get(CONF_TIME_STRUCTURE)
            
            if pricing_model == PRICING_MODEL_FIXED:
                # For fixed pricing, we need energy rates and power rates
                if time_structure == TIME_STRUCTURE_SINGLE_RATE:
                    has_energy_rate = CONF_FIXED_RATE in self._data
                else:
                    has_energy_rate = (
                        CONF_P1_RATE in self._data and
                        CONF_P2_RATE in self._data and
                        CONF_P3_RATE in self._data
                    )
                has_power_rates = (
                    CONF_POWER_P1_RATE in self._data and
                    CONF_POWER_P2_RATE in self._data
                )
                
                if not has_energy_rate or not has_power_rates:
                    _LOGGER.debug("Missing required fields for fixed pricing: energy_rate=%s, power_rates=%s", 
                                 has_energy_rate, has_power_rates)
                    return False
            else:
                # For market pricing, no required rates (uses PVPC sensor)
                pass
            
            # Set default tax rates if not present
            if CONF_ELECTRICITY_TAX_RATE not in self._data:
                self._data[CONF_ELECTRICITY_TAX_RATE] = DEFAULT_ELECTRICITY_TAX_RATE
            if CONF_VAT_RATE not in self._data:
                self._data[CONF_VAT_RATE] = DEFAULT_VAT_RATE
            
            # Set default PVPC sensor for market pricing
            if pricing_model == PRICING_MODEL_MARKET and CONF_PVPC_SENSOR not in self._data:
                self._data[CONF_PVPC_SENSOR] = "sensor.pvpc"
            
            return True
            
        except Exception as err:
            _LOGGER.error("Error mapping tariff info to config: %s", err, exc_info=True)
            return False

    async def async_step_tariff_config_mode(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle tariff configuration mode selection (auto or manual)."""
        if user_input is not None:
            config_mode = user_input.get(CONF_TARIFF_CONFIG_MODE, "manual")
            self._data[CONF_TARIFF_CONFIG_MODE] = config_mode
            
            if config_mode == "auto":
                # Try to fetch tariff info from API
                try:
                    from .api.octopus_client import OctopusClient, OctopusClientError
                    
                    email = self._data.get(CONF_EMAIL)
                    password = self._data.get(CONF_PASSWORD)
                    property_id = self._data.get(CONF_PROPERTY_ID)
                    
                    if not email or not password:
                        return await self.async_step_pricing_model()
                    
                    client = OctopusClient(email, password, property_id)
                    try:
                        tariff_info = await client.fetch_tariff_info()
                        await client.close()
                        
                        if tariff_info:
                            # Map tariff info to config
                            mapping_success = self._map_tariff_info_to_config(tariff_info)
                            
                            if mapping_success:
                                # All required data mapped successfully
                                self._auto_configured = True
                                # Start from pricing_model to show forms with pre-filled values
                                return await self.async_step_pricing_model()
                            else:
                                # Partial mapping - continue with manual configuration for missing fields
                                _LOGGER.info("Partial tariff info mapping, continuing with manual configuration for missing fields")
                                return await self.async_step_energy_rates()
                        else:
                            # Tariff info not available, fall back to manual
                            _LOGGER.warning("Could not fetch tariff info, falling back to manual configuration")
                            return await self.async_step_pricing_model()
                    except Exception as err:
                        _LOGGER.warning("Error fetching tariff info: %s", err)
                        await client.close()
                        # Fall back to manual configuration
                        return await self.async_step_pricing_model()
                except Exception as err:
                    _LOGGER.error("Error setting up client for tariff info: %s", err)
                    return await self.async_step_pricing_model()
            else:
                # Manual configuration
                return await self.async_step_pricing_model()
        
        return self.async_show_form(
            step_id="tariff_config_mode",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_TARIFF_CONFIG_MODE,
                        default="auto"
                    ): vol.In(
                        {
                            "auto": "Automatic (from Octopus Energy API)",
                            "manual": "Manual (configure manually)",
                        }
                    )
                }
            ),
        )

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
                return await self.async_step_energy_rates()

        # Skip if value came from API (auto-configured)
        if self._auto_configured and CONF_PRICING_MODEL in self._data:
            self._pricing_model = self._data[CONF_PRICING_MODEL]
            if self._pricing_model == PRICING_MODEL_FIXED:
                return await self.async_step_time_structure()
            else:
                # Market pricing - skip time structure step
                self._time_structure = TIME_STRUCTURE_SINGLE_RATE
                self._data[CONF_TIME_STRUCTURE] = self._time_structure
                return await self.async_step_energy_rates()
        
        # Use value from self._data if available (from auto-config)
        pricing_model_default = self._data.get(CONF_PRICING_MODEL, PRICING_MODEL_MARKET)
        
        return self.async_show_form(
            step_id="pricing_model",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PRICING_MODEL, default=pricing_model_default): vol.In(
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
            return await self.async_step_energy_rates()

        # Skip if value came from API (auto-configured)
        if self._auto_configured and CONF_TIME_STRUCTURE in self._data:
            self._time_structure = self._data[CONF_TIME_STRUCTURE]
            return await self.async_step_energy_rates()
        
        # Use value from self._data if available (from auto-config)
        time_structure_default = self._data.get(CONF_TIME_STRUCTURE, TIME_STRUCTURE_SINGLE_RATE)
        
        return self.async_show_form(
            step_id="time_structure",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_TIME_STRUCTURE, default=time_structure_default): vol.In(
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

        # Skip if values came from API (auto-configured)
        if self._auto_configured:
            if pricing_model == PRICING_MODEL_FIXED:
                if time_structure == TIME_STRUCTURE_SINGLE_RATE:
                    if CONF_FIXED_RATE in self._data:
                        return await self.async_step_power_rates()
                elif time_structure == TIME_STRUCTURE_TIME_OF_USE:
                    if (CONF_P1_RATE in self._data and 
                        CONF_P2_RATE in self._data and 
                        CONF_P3_RATE in self._data):
                        return await self.async_step_power_rates()
            else:
                # Market pricing - energy rates are optional, skip if not needed
                return await self.async_step_power_rates()

        schema_dict: dict[str, Any] = {}

        if pricing_model == PRICING_MODEL_FIXED:
            if time_structure == TIME_STRUCTURE_SINGLE_RATE:
                # Use value from self._data if available (from auto-config)
                fixed_rate_default = self._data.get(CONF_FIXED_RATE)
                schema_dict[vol.Required(CONF_FIXED_RATE, default=fixed_rate_default)] = vol.Coerce(float)
            elif time_structure == TIME_STRUCTURE_TIME_OF_USE:
                # Use values from self._data if available (from auto-config)
                p1_rate_default = self._data.get(CONF_P1_RATE)
                p2_rate_default = self._data.get(CONF_P2_RATE)
                p3_rate_default = self._data.get(CONF_P3_RATE)
                schema_dict[vol.Required(CONF_P1_RATE, default=p1_rate_default)] = vol.Coerce(float)
                schema_dict[vol.Required(CONF_P2_RATE, default=p2_rate_default)] = vol.Coerce(float)
                schema_dict[vol.Required(CONF_P3_RATE, default=p3_rate_default)] = vol.Coerce(float)
        else:
            # Market pricing - optional management fee
            management_fee_default = self._data.get(CONF_MANAGEMENT_FEE_MONTHLY)
            schema_dict[vol.Optional(CONF_MANAGEMENT_FEE_MONTHLY, default=management_fee_default)] = vol.Coerce(float)

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
        
        # Skip if values came from API (auto-configured)
        if self._auto_configured and (CONF_POWER_P1_RATE in self._data and CONF_POWER_P2_RATE in self._data):
            return await self.async_step_solar_features()
        
        # Use values from self._data if available (from auto-config)
        power_p1_rate_default = self._data.get(CONF_POWER_P1_RATE)
        power_p2_rate_default = self._data.get(CONF_POWER_P2_RATE)

        return self.async_show_form(
            step_id="power_rates",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_POWER_P1_RATE, default=power_p1_rate_default): vol.Coerce(float),
                    vol.Required(CONF_POWER_P2_RATE, default=power_p2_rate_default): vol.Coerce(float),
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
            else:
                # Remove solar surplus rate if user unchecks has_solar
                self._data.pop(CONF_SOLAR_SURPLUS_RATE, None)
            return await self.async_step_discount_programs()
        
        # Skip if surplus_rate came from API (auto-configured)
        # Check if surplus_rate was provided by API (even if it was 0)
        surplus_rate_from_api = self._data.get("_surplus_rate_from_api", False)
        if self._auto_configured and surplus_rate_from_api:
            # Value came from API, skip form and proceed (whether > 0 or = 0)
            # If > 0, solar features are enabled (CONF_SOLAR_SURPLUS_RATE is set)
            # If = 0, solar features are disabled (CONF_SOLAR_SURPLUS_RATE is not set)
            return await self.async_step_discount_programs()
        
        # Check if surplus_rate is already set (from auto-config) and > 0
        # If yes, automatically set has_solar=True and use the rate
        surplus_rate_value = self._data.get(CONF_SOLAR_SURPLUS_RATE)
        has_solar_default = surplus_rate_value is not None and float(surplus_rate_value) > 0
        solar_surplus_rate_default = self._data.get(CONF_SOLAR_SURPLUS_RATE, 0.04)

        return self.async_show_form(
            step_id="solar_features",
            data_schema=vol.Schema(
                {
                    vol.Required("has_solar", default=has_solar_default): bool,
                    vol.Optional(CONF_SOLAR_SURPLUS_RATE, default=solar_surplus_rate_default): vol.Coerce(float),
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
            else:
                # Remove discount data if user unchecks has_discount
                self._data.pop(CONF_DISCOUNT_START_HOUR, None)
                self._data.pop(CONF_DISCOUNT_END_HOUR, None)
                self._data.pop(CONF_DISCOUNT_PERCENTAGE, None)
            return await self.async_step_other_concepts()
        
        # Always show form for discount programs (this info is not in API)

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

    async def async_step_other_concepts(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle other concepts configuration (optional)."""
        if user_input is not None:
            if user_input.get("has_other_concepts"):
                self._data[CONF_OTHER_CONCEPTS_RATE] = user_input.get(CONF_OTHER_CONCEPTS_RATE, 0.046)
            else:
                # Remove other concepts rate if user unchecks has_other_concepts
                self._data.pop(CONF_OTHER_CONCEPTS_RATE, None)
            return await self.async_step_taxes()
        
        # Always show form for other concepts (this info is not in API)

        return self.async_show_form(
            step_id="other_concepts",
            data_schema=vol.Schema(
                {
                    vol.Required("has_other_concepts", default=True): bool,
                    vol.Optional(CONF_OTHER_CONCEPTS_RATE, default=0.046): vol.Coerce(float),
                }
            ),
        )

    async def async_step_taxes(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle taxes configuration."""
        if user_input is not None:
            self._data[CONF_ELECTRICITY_TAX_RATE] = user_input.get(CONF_ELECTRICITY_TAX_RATE, DEFAULT_ELECTRICITY_TAX_RATE)
            self._data[CONF_VAT_RATE] = user_input.get(CONF_VAT_RATE, DEFAULT_VAT_RATE)
            
            # Check if we need PVPC sensor (only for market pricing)
            pricing_model = self._pricing_model or self._data.get(CONF_PRICING_MODEL, PRICING_MODEL_MARKET)
            if pricing_model == PRICING_MODEL_MARKET:
                return await self.async_step_pvpc_sensor()
            else:
                # Fixed pricing - skip PVPC sensor and go to tariff name
                return await self.async_step_tariff_name()
        
        # Always show form for taxes (user should confirm or adjust default values)
        # Use values from self._data if available (from auto-config or defaults)
        electricity_tax_rate_default = self._data.get(CONF_ELECTRICITY_TAX_RATE, DEFAULT_ELECTRICITY_TAX_RATE)
        vat_rate_default = self._data.get(CONF_VAT_RATE, DEFAULT_VAT_RATE)

        return self.async_show_form(
            step_id="taxes",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_ELECTRICITY_TAX_RATE, default=electricity_tax_rate_default): vol.All(
                        vol.Coerce(float), vol.Range(min=0, max=1)
                    ),
                    vol.Optional(CONF_VAT_RATE, default=vat_rate_default): vol.All(
                        vol.Coerce(float), vol.Range(min=0, max=1)
                    ),
                }
            ),
        )

    async def async_step_pvpc_sensor(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle PVPC sensor selection (only for market pricing)."""
        if user_input is not None:
            pvpc_sensor = user_input.get(CONF_PVPC_SENSOR, "sensor.pvpc")
            self._data[CONF_PVPC_SENSOR] = pvpc_sensor
            return await self.async_step_tariff_name()
        
        # PVPC sensor is set as default, not from API, so always show form
        pvpc_sensor_default = self._data.get(CONF_PVPC_SENSOR, "sensor.pvpc")

        return self.async_show_form(
            step_id="pvpc_sensor",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_PVPC_SENSOR, default=pvpc_sensor_default): str,
                }
            ),
        )

    async def async_step_tariff_name(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle tariff name input."""
        if user_input is not None:
            tariff_name = user_input.get(CONF_NAME, "").strip()
            if tariff_name:
                self._data[CONF_NAME] = tariff_name
            return self._create_entry()

        # Skip if value came from API (auto-configured) - tariff name comes from product.display_name
        tariff_name_default = self._data.get(CONF_NAME, "").strip()
        if self._auto_configured and tariff_name_default:
            # Name came from API, skip form and create entry
            return self._create_entry()
        
        # If not set, generate default name based on pricing model
        if not tariff_name_default:
            pricing_model = self._pricing_model or self._data.get(CONF_PRICING_MODEL, PRICING_MODEL_MARKET)
            time_structure = self._time_structure or self._data.get(CONF_TIME_STRUCTURE, TIME_STRUCTURE_SINGLE_RATE)
            
            if pricing_model == PRICING_MODEL_FIXED:
                if time_structure == TIME_STRUCTURE_SINGLE_RATE:
                    tariff_name_default = "Octopus Relax"
                else:
                    tariff_name_default = "Octopus Solar"
            else:
                tariff_name_default = "Octopus Flexi"

        return self.async_show_form(
            step_id="tariff_name",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME, default=tariff_name_default): str,
                }
            ),
            description_placeholders={
                "name_info": (
                    "Enter a name for this tariff configuration. "
                    "This name will be used to identify this service in Home Assistant."
                ),
            },
        )

    def _create_entry(self) -> FlowResult:
        """Create the config entry."""
        # Use tariff name from config, or generate default if not set
        tariff_name = self._data.get(CONF_NAME, "").strip()
        if not tariff_name:
            # Fallback to generated name if not provided
            pricing_model = self._pricing_model or self._data.get(CONF_PRICING_MODEL, PRICING_MODEL_MARKET)
            model_name = "Fixed" if pricing_model == PRICING_MODEL_FIXED else "Market"
            tariff_name = f"Octopus Energy España - {model_name}"
        
        # Set default PVPC sensor for market pricing if not set
        pricing_model = self._pricing_model or self._data.get(CONF_PRICING_MODEL, PRICING_MODEL_MARKET)
        if pricing_model == PRICING_MODEL_MARKET and CONF_PVPC_SENSOR not in self._data:
            self._data[CONF_PVPC_SENSOR] = "sensor.pvpc"
        
        # Remove temporary flags before saving (keep _tariff_info)
        entry_data = {k: v for k, v in self._data.items() if not k.startswith("_") or k == "_tariff_info"}
        
        # If reauth flow, update existing entry instead of creating new one
        if self._reauth_entry:
            self.hass.config_entries.async_update_entry(
                self._reauth_entry,
                data={**self._reauth_entry.data, **entry_data},
            )
            await self.hass.config_entries.async_reload(self._reauth_entry.entry_id)
            return self.async_abort(reason="reauth_successful")
        
        return self.async_create_entry(
            title=tariff_name,
            data=entry_data,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> FlowResult:
        """Handle reauthentication."""
        self._reauth_entry = self._get_reauth_entry()
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm reauthentication."""
        errors: dict[str, str] = {}
        
        if user_input is None:
            # Pre-fill email from existing entry
            email = self._reauth_entry.data.get(CONF_EMAIL, "") if self._reauth_entry else ""
            return self.async_show_form(
                step_id="reauth_confirm",
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_EMAIL, default=email): str,
                        vol.Required(CONF_PASSWORD): str,
                    }
                ),
                errors=errors,
                description_placeholders={
                    "email": email,
                },
            )
        
        # Validate new credentials
        try:
            from .api.octopus_client import OctopusClient, OctopusClientError
            
            email = user_input.get(CONF_EMAIL, "").strip()
            password = user_input.get(CONF_PASSWORD, "")
            
            if not email or not password:
                errors["base"] = "email_password_required"
                return self.async_show_form(
                    step_id="reauth_confirm",
                    data_schema=vol.Schema(
                        {
                            vol.Required(CONF_EMAIL, default=email): str,
                            vol.Required(CONF_PASSWORD): str,
                        }
                    ),
                    errors=errors,
                )
            
            # Test authentication
            test_client = OctopusClient(email, password, "dummy")
            try:
                await test_client._authenticate()
                # Try to fetch properties to verify access
                properties = await test_client.fetch_properties()
                await test_client.close()
                
                if not properties:
                    errors["base"] = "no_accounts_found"
                    return self.async_show_form(
                        step_id="reauth_confirm",
                        data_schema=vol.Schema(
                            {
                                vol.Required(CONF_EMAIL, default=email): str,
                                vol.Required(CONF_PASSWORD): str,
                            }
                        ),
                        errors=errors,
                    )
                
                # Update credentials in entry data
                self._data[CONF_EMAIL] = email
                self._data[CONF_PASSWORD] = password
                
                # If property_id changed, update it
                if len(properties) == 1:
                    prop = properties[0]
                    self._data[CONF_PROPERTY_ID] = prop.get("number") or prop.get("id") or str(prop)
                elif self._reauth_entry:
                    # Keep existing property_id if multiple accounts
                    self._data[CONF_PROPERTY_ID] = self._reauth_entry.data.get(CONF_PROPERTY_ID)
                
                # For reauth, update entry directly without going through tariff config
                if self._reauth_entry:
                    # Update entry data with new credentials
                    updated_data = {**self._reauth_entry.data}
                    updated_data[CONF_EMAIL] = email
                    updated_data[CONF_PASSWORD] = password
                    if CONF_PROPERTY_ID in self._data:
                        updated_data[CONF_PROPERTY_ID] = self._data[CONF_PROPERTY_ID]
                    
                    self.hass.config_entries.async_update_entry(
                        self._reauth_entry,
                        data=updated_data,
                    )
                    await self.hass.config_entries.async_reload(self._reauth_entry.entry_id)
                    return self.async_abort(reason="reauth_successful")
                
                # Continue with tariff config mode for new entry
                self._properties = properties
                return await self.async_step_tariff_config_mode()
                
            except OctopusClientError as err:
                error_msg = str(err).lower()
                await test_client.close()
                
                if any(phrase in error_msg for phrase in [
                    "401", 
                    "invalid", 
                    "credentials", 
                    "incorrect",
                    "wrong",
                    "please make sure",
                    "please check",
                    "kt-ct-1138"
                ]):
                    errors["base"] = "invalid_auth"
                elif any(phrase in error_msg for phrase in [
                    "cannot_connect", 
                    "connection", 
                    "network", 
                    "timeout",
                    "not available", 
                    "not be publicly", 
                    "domain name not found",
                    "cannot connect to host",
                    "name or service not known"
                ]):
                    errors["base"] = "cannot_connect"
                else:
                    errors["base"] = "unknown"
                
                return self.async_show_form(
                    step_id="reauth_confirm",
                    data_schema=vol.Schema(
                        {
                            vol.Required(CONF_EMAIL, default=email): str,
                            vol.Required(CONF_PASSWORD): str,
                        }
                    ),
                    errors=errors,
                )
                
        except Exception as err:
            _LOGGER.error("Unexpected error during reauthentication: %s", err, exc_info=True)
            errors["base"] = "unknown"
            return self.async_show_form(
                step_id="reauth_confirm",
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_EMAIL, default=user_input.get(CONF_EMAIL, "")): str,
                        vol.Required(CONF_PASSWORD): str,
                    }
                ),
                errors=errors,
            )

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return OctopusEnergyESOptionsFlowHandler(config_entry)


class OctopusEnergyESOptionsFlowHandler(config_entries.OptionsFlowWithConfigEntry):
    """Handle options flow for Octopus Energy España."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        super().__init__(config_entry)
        self._data: dict[str, Any] = {}
        self._pricing_model: str | None = None
        self._time_structure: str | None = None

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        # Load current configuration
        current_data = self.config_entry.data.copy()
        current_options = self.config_entry.options.copy()
        
        # Merge data and options (options take precedence)
        self._data = {**current_data, **current_options}
        
        # Initialize pricing model and time structure from current config
        self._pricing_model = self._data.get(CONF_PRICING_MODEL, PRICING_MODEL_MARKET)
        self._time_structure = self._data.get(CONF_TIME_STRUCTURE, TIME_STRUCTURE_SINGLE_RATE)
        
        return await self.async_step_tariff_name()

    async def async_step_tariff_name(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle tariff name input."""
        if user_input is not None:
            tariff_name = user_input.get(CONF_NAME, "").strip()
            if tariff_name:
                self._data[CONF_NAME] = tariff_name
            return await self.async_step_pricing_model()

        # Use current entry title as default, or generate default name
        current_name = self.config_entry.title
        if not current_name or current_name.startswith("Octopus Energy España"):
            # Generate default name based on pricing model
            pricing_model = self._pricing_model or self._data.get(CONF_PRICING_MODEL, PRICING_MODEL_MARKET)
            time_structure = self._time_structure or self._data.get(CONF_TIME_STRUCTURE, TIME_STRUCTURE_SINGLE_RATE)
            
            if pricing_model == PRICING_MODEL_FIXED:
                if time_structure == TIME_STRUCTURE_SINGLE_RATE:
                    default_name = "Octopus Relax"
                else:
                    default_name = "Octopus Solar"
            else:
                default_name = "Octopus Flexi"
        else:
            default_name = current_name

        return self.async_show_form(
            step_id="tariff_name",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME, default=default_name): str,
                }
            ),
            description_placeholders={
                "name_info": (
                    "Enter a name for this tariff configuration. "
                    "This name will be used to identify this service in Home Assistant."
                ),
            },
        )

    async def async_step_pricing_model(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle pricing model selection."""
        if user_input is not None:
            new_pricing_model = user_input[CONF_PRICING_MODEL]
            old_pricing_model = self._pricing_model
            
            # If switching pricing models, clear incompatible values
            if old_pricing_model and old_pricing_model != new_pricing_model:
                if old_pricing_model == PRICING_MODEL_FIXED:
                    # Switching from Fixed to Market - remove fixed rates
                    self._data.pop(CONF_FIXED_RATE, None)
                    self._data.pop(CONF_P1_RATE, None)
                    self._data.pop(CONF_P2_RATE, None)
                    self._data.pop(CONF_P3_RATE, None)
                else:
                    # Switching from Market to Fixed - remove management fee
                    self._data.pop(CONF_MANAGEMENT_FEE_MONTHLY, None)
            
            self._pricing_model = new_pricing_model
            self._data[CONF_PRICING_MODEL] = self._pricing_model
            
            if self._pricing_model == PRICING_MODEL_FIXED:
                return await self.async_step_time_structure()
            else:
                # Market pricing - skip time structure step
                self._time_structure = TIME_STRUCTURE_SINGLE_RATE
                self._data[CONF_TIME_STRUCTURE] = self._time_structure
                return await self.async_step_energy_rates()

        return self.async_show_form(
            step_id="pricing_model",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_PRICING_MODEL,
                        default=self._pricing_model or PRICING_MODEL_MARKET
                    ): vol.In(
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
            new_time_structure = user_input[CONF_TIME_STRUCTURE]
            old_time_structure = self._time_structure
            
            # If switching time structures, clear incompatible values
            if old_time_structure and old_time_structure != new_time_structure:
                if old_time_structure == TIME_STRUCTURE_SINGLE_RATE:
                    # Switching from Single Rate to Time-of-Use - remove fixed_rate
                    self._data.pop(CONF_FIXED_RATE, None)
                else:
                    # Switching from Time-of-Use to Single Rate - remove P1/P2/P3 rates
                    self._data.pop(CONF_P1_RATE, None)
                    self._data.pop(CONF_P2_RATE, None)
                    self._data.pop(CONF_P3_RATE, None)
            
            self._time_structure = new_time_structure
            self._data[CONF_TIME_STRUCTURE] = self._time_structure
            return await self.async_step_energy_rates()

        return self.async_show_form(
            step_id="time_structure",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_TIME_STRUCTURE,
                        default=self._time_structure or TIME_STRUCTURE_SINGLE_RATE
                    ): vol.In(
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
                schema_dict[vol.Required(
                    CONF_FIXED_RATE,
                    default=self._data.get(CONF_FIXED_RATE)
                )] = vol.Coerce(float)
            elif time_structure == TIME_STRUCTURE_TIME_OF_USE:
                schema_dict[vol.Required(
                    CONF_P1_RATE,
                    default=self._data.get(CONF_P1_RATE)
                )] = vol.Coerce(float)
                schema_dict[vol.Required(
                    CONF_P2_RATE,
                    default=self._data.get(CONF_P2_RATE)
                )] = vol.Coerce(float)
                schema_dict[vol.Required(
                    CONF_P3_RATE,
                    default=self._data.get(CONF_P3_RATE)
                )] = vol.Coerce(float)
        else:
            # Market pricing - optional management fee
            schema_dict[vol.Optional(
                CONF_MANAGEMENT_FEE_MONTHLY,
                default=self._data.get(CONF_MANAGEMENT_FEE_MONTHLY)
            )] = vol.Coerce(float)

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
        
        # Check if data is already filled (from auto-config)
        if (CONF_POWER_P1_RATE in self._data and 
            CONF_POWER_P2_RATE in self._data):
            # Data already filled, skip to next step
            return await self.async_step_solar_features()

        return self.async_show_form(
            step_id="power_rates",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_POWER_P1_RATE,
                        default=self._data.get(CONF_POWER_P1_RATE)
                    ): vol.Coerce(float),
                    vol.Required(
                        CONF_POWER_P2_RATE,
                        default=self._data.get(CONF_POWER_P2_RATE)
                    ): vol.Coerce(float),
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
            else:
                # Remove solar surplus rate if solar is disabled
                self._data.pop(CONF_SOLAR_SURPLUS_RATE, None)
            return await self.async_step_discount_programs()

        has_solar = CONF_SOLAR_SURPLUS_RATE in self._data
        return self.async_show_form(
            step_id="solar_features",
            data_schema=vol.Schema(
                {
                    vol.Required("has_solar", default=has_solar): bool,
                    vol.Optional(
                        CONF_SOLAR_SURPLUS_RATE,
                        default=self._data.get(CONF_SOLAR_SURPLUS_RATE, 0.04)
                    ): vol.Coerce(float),
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
            else:
                # Remove discount settings if discount is disabled
                self._data.pop(CONF_DISCOUNT_START_HOUR, None)
                self._data.pop(CONF_DISCOUNT_END_HOUR, None)
                self._data.pop(CONF_DISCOUNT_PERCENTAGE, None)
            return await self.async_step_other_concepts()

        has_discount = CONF_DISCOUNT_START_HOUR in self._data
        return self.async_show_form(
            step_id="discount_programs",
            data_schema=vol.Schema(
                {
                    vol.Required("has_discount", default=has_discount): bool,
                    vol.Optional(
                        CONF_DISCOUNT_START_HOUR,
                        default=self._data.get(CONF_DISCOUNT_START_HOUR, 12)
                    ): vol.All(
                        vol.Coerce(int), vol.Range(min=0, max=23)
                    ),
                    vol.Optional(
                        CONF_DISCOUNT_END_HOUR,
                        default=self._data.get(CONF_DISCOUNT_END_HOUR, 18)
                    ): vol.All(
                        vol.Coerce(int), vol.Range(min=0, max=23)
                    ),
                    vol.Optional(
                        CONF_DISCOUNT_PERCENTAGE,
                        default=self._data.get(CONF_DISCOUNT_PERCENTAGE, 0.45)
                    ): vol.All(
                        vol.Coerce(float), vol.Range(min=0, max=1)
                    ),
                }
            ),
        )

    async def async_step_other_concepts(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle other concepts configuration (optional)."""
        if user_input is not None:
            if user_input.get("has_other_concepts"):
                self._data[CONF_OTHER_CONCEPTS_RATE] = user_input.get(CONF_OTHER_CONCEPTS_RATE, 0.046)
            else:
                # Remove other concepts rate if disabled
                self._data.pop(CONF_OTHER_CONCEPTS_RATE, None)
            return await self.async_step_taxes()

        has_other_concepts = CONF_OTHER_CONCEPTS_RATE in self._data
        return self.async_show_form(
            step_id="other_concepts",
            data_schema=vol.Schema(
                {
                    vol.Required("has_other_concepts", default=has_other_concepts): bool,
                    vol.Optional(
                        CONF_OTHER_CONCEPTS_RATE,
                        default=self._data.get(CONF_OTHER_CONCEPTS_RATE, 0.046)
                    ): vol.Coerce(float),
                }
            ),
        )

    async def async_step_taxes(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle taxes configuration."""
        if user_input is not None:
            self._data[CONF_ELECTRICITY_TAX_RATE] = user_input.get(CONF_ELECTRICITY_TAX_RATE, DEFAULT_ELECTRICITY_TAX_RATE)
            self._data[CONF_VAT_RATE] = user_input.get(CONF_VAT_RATE, DEFAULT_VAT_RATE)
            
            # Check if we need PVPC sensor (only for market pricing)
            pricing_model = self._pricing_model or self._data.get(CONF_PRICING_MODEL, PRICING_MODEL_MARKET)
            if pricing_model == PRICING_MODEL_MARKET:
                return await self.async_step_pvpc_sensor()
            else:
                # Fixed pricing - skip PVPC sensor and go to integration settings
                return await self.async_step_integration_settings()

        return self.async_show_form(
            step_id="taxes",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_ELECTRICITY_TAX_RATE,
                        default=self._data.get(CONF_ELECTRICITY_TAX_RATE, DEFAULT_ELECTRICITY_TAX_RATE)
                    ): vol.All(
                        vol.Coerce(float), vol.Range(min=0, max=1)
                    ),
                    vol.Optional(
                        CONF_VAT_RATE,
                        default=self._data.get(CONF_VAT_RATE, DEFAULT_VAT_RATE)
                    ): vol.All(
                        vol.Coerce(float), vol.Range(min=0, max=1)
                    ),
                }
            ),
        )

    async def async_step_pvpc_sensor(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle PVPC sensor selection (only for market pricing)."""
        if user_input is not None:
            pvpc_sensor = user_input.get(CONF_PVPC_SENSOR, "sensor.pvpc")
            self._data[CONF_PVPC_SENSOR] = pvpc_sensor
            return await self.async_step_integration_settings()

        return self.async_show_form(
            step_id="pvpc_sensor",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_PVPC_SENSOR,
                        default=self._data.get(CONF_PVPC_SENSOR, "sensor.pvpc")
                    ): str,
                }
            ),
        )

    async def async_step_integration_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle integration settings (debug logging)."""
        if user_input is not None:
            self._data[CONF_DEBUG] = user_input.get(CONF_DEBUG, False)
            return self._save_options()

        return self.async_show_form(
            step_id="integration_settings",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_DEBUG,
                        default=self._data.get(CONF_DEBUG, False)
                    ): bool,
                }
            ),
            description_placeholders={
                "debug_info": (
                    "Enable DEBUG logging for detailed information about "
                    "API calls, price calculations, and data updates. "
                    "Useful for troubleshooting issues."
                ),
            },
        )

    def _save_options(self) -> FlowResult:
        """Save the options."""
        # Separate data that should be in options vs data
        # Credentials and property_id stay in data, everything else goes to options
        options_data = {}
        data_keys_to_keep = {CONF_EMAIL, CONF_PASSWORD, CONF_PROPERTY_ID}
        
        # Get tariff name for title
        tariff_name = self._data.get(CONF_NAME, "").strip()
        if not tariff_name:
            # Use current entry title if name not provided
            tariff_name = self.config_entry.title
        
        # Preserve _tariff_info from current entry if not updated (deep copy to avoid reference issues)
        import copy
        current_tariff_info = None
        if "_tariff_info" not in self._data:
            # Try to get from current entry data or options
            current_tariff_info = self.config_entry.data.get("_tariff_info") or self.config_entry.options.get("_tariff_info")
            if current_tariff_info:
                current_tariff_info = copy.deepcopy(current_tariff_info)
        
        for key, value in self._data.items():
            if key not in data_keys_to_keep:
                # Skip temporary flags (keep _tariff_info)
                if not (key.startswith("_") and key != "_tariff_info"):
                    options_data[key] = value
        
        # Preserve _tariff_info if it wasn't updated
        if current_tariff_info and "_tariff_info" not in options_data:
            options_data["_tariff_info"] = current_tariff_info
        
        return self.async_create_entry(title=tariff_name, data=options_data)
