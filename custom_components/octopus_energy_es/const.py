"""Constants for Octopus Energy España integration."""
from __future__ import annotations

from datetime import timedelta

DOMAIN = "octopus_energy_es"

# Configuration keys
CONF_PROPERTY_ID = "property_id"
CONF_PVPC_SENSOR = "pvpc_sensor"

# Tariff category configuration keys
CONF_PRICING_MODEL = "pricing_model"
CONF_TIME_STRUCTURE = "time_structure"
CONF_FIXED_RATE = "fixed_rate"
CONF_P1_RATE = "p1_rate"
CONF_P2_RATE = "p2_rate"
CONF_P3_RATE = "p3_rate"
CONF_POWER_P1_RATE = "power_p1_rate"
CONF_POWER_P2_RATE = "power_p2_rate"
CONF_SOLAR_SURPLUS_RATE = "solar_surplus_rate"
CONF_MANAGEMENT_FEE_MONTHLY = "management_fee_monthly"
CONF_DISCOUNT_START_HOUR = "discount_start_hour"
CONF_DISCOUNT_END_HOUR = "discount_end_hour"
CONF_DISCOUNT_PERCENTAGE = "discount_percentage"

# Period hours configuration (for customization)
CONF_P1_HOURS_WEEKDAYS = "p1_hours_weekdays"
CONF_P2_HOURS_WEEKDAYS = "p2_hours_weekdays"
CONF_P3_HOURS_WEEKDAYS = "p3_hours_weekdays"

# Pricing models
PRICING_MODEL_FIXED = "fixed"
PRICING_MODEL_MARKET = "market"

# Time structures
TIME_STRUCTURE_SINGLE_RATE = "single_rate"
TIME_STRUCTURE_TIME_OF_USE = "time_of_use"


# Update intervals
UPDATE_INTERVAL_TODAY = timedelta(hours=1)
UPDATE_INTERVAL_TOMORROW = timedelta(hours=24)
UPDATE_INTERVAL_CONSUMPTION = timedelta(minutes=15)
UPDATE_INTERVAL_BILLING = timedelta(hours=24)

# Spanish market publishes tomorrow's prices at 14:00 CET
MARKET_PUBLISH_HOUR = 14

# Octopus Energy España uses GraphQL API
# Using the same endpoint as the dashboard for consistency
OCTOPUS_API_BASE_URL = "https://octopusenergy.es/api/graphql/kraken"

# Default timezone
TIMEZONE_MADRID = "Europe/Madrid"

# Sensor attributes
ATTR_DATA = "data"
ATTR_START_TIME = "start_time"
ATTR_PRICE_PER_KWH = "price_per_kwh"
ATTR_UNIT_OF_MEASUREMENT = "€/kWh"

# Default period definitions (P1/P2/P3) - Weekdays only
# Weekends and holidays: All hours are P3 (Valle)
# Based on official Octopus Energy España structure:
# P1 (Punta): laborables 11-14, 19-22
# P2 (Llano): laborables 9-10, 15-18, 23
# P3 (Valle): laborables 0-8, fines de semana y festivos 0-24
DEFAULT_P1_HOURS_WEEKDAYS = [11, 12, 13, 14, 19, 20, 21, 22]  # Peak hours (weekdays)
DEFAULT_P2_HOURS_WEEKDAYS = [9, 10, 15, 16, 17, 18, 23]  # Standard hours (weekdays)
DEFAULT_P3_HOURS_WEEKDAYS = [0, 1, 2, 3, 4, 5, 6, 7, 8]  # Valley hours (weekdays)


# Credit reason codes
CREDIT_REASON_SUN_CLUB = "SUN_CLUB"
CREDIT_REASON_SUN_CLUB_POWER_UP = "SUN_CLUB_POWER_UP"

