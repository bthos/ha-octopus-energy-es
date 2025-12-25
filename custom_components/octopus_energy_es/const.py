"""Constants for Octopus Energy España integration."""
from __future__ import annotations

from datetime import timedelta

DOMAIN = "octopus_energy_es"

# Configuration keys
CONF_TARIFF_TYPE = "tariff_type"
CONF_PROPERTY_ID = "property_id"
CONF_PVPC_SENSOR = "pvpc_sensor"
CONF_FIXED_RATE = "fixed_rate"
CONF_P1_RATE = "p1_rate"
CONF_P2_RATE = "p2_rate"
CONF_P3_RATE = "p3_rate"
CONF_SOLAR_SURPLUS_RATE = "solar_surplus_rate"
CONF_DAYLIGHT_START = "daylight_start"
CONF_DAYLIGHT_END = "daylight_end"
CONF_DISCOUNT_PERCENTAGE = "discount_percentage"

# Tariff types
TARIFF_TYPE_FLEXI = "flexi"
TARIFF_TYPE_RELAX = "relax"
TARIFF_TYPE_SOLAR = "solar"
TARIFF_TYPE_GO = "go"
TARIFF_TYPE_SUN_CLUB = "sun_club"

TARIFF_TYPES = [
    TARIFF_TYPE_FLEXI,
    TARIFF_TYPE_RELAX,
    TARIFF_TYPE_SOLAR,
    TARIFF_TYPE_GO,
    TARIFF_TYPE_SUN_CLUB,
]

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

# Default period definitions (P1/P2/P3)
DEFAULT_P1_HOURS = [10, 11, 12, 13, 18, 19, 20, 21]  # Peak hours
DEFAULT_P2_HOURS = [8, 9, 14, 15, 16, 17, 22, 23]  # Standard hours
DEFAULT_P3_HOURS = [0, 1, 2, 3, 4, 5, 6, 7]  # Valley hours

# SUN CLUB daylight hours
SUN_CLUB_DAYLIGHT_START = 12
SUN_CLUB_DAYLIGHT_END = 18
SUN_CLUB_DISCOUNT = 0.45  # 45% discount

# Credit reason codes
CREDIT_REASON_SUN_CLUB = "SUN_CLUB"
CREDIT_REASON_SUN_CLUB_POWER_UP = "SUN_CLUB_POWER_UP"

# Historical data configuration
CONF_LOAD_HISTORICAL_DATA = "load_historical_data"
CONF_HISTORICAL_DATA_RANGE = "historical_data_range"
CONF_HISTORICAL_DATA_START_DATE = "historical_data_start_date"
CONF_HISTORICAL_DATA_LOADED = "historical_data_loaded"
CONF_HISTORICAL_DATA_LOAD_DATE = "historical_data_load_date"

# Historical data range options
HISTORICAL_RANGE_1_YEAR = "1_year"
HISTORICAL_RANGE_2_YEARS = "2_years"
HISTORICAL_RANGE_ALL_AVAILABLE = "all_available"
HISTORICAL_RANGE_CUSTOM = "custom"

HISTORICAL_RANGE_OPTIONS = [
    HISTORICAL_RANGE_1_YEAR,
    HISTORICAL_RANGE_2_YEARS,
    HISTORICAL_RANGE_ALL_AVAILABLE,
    HISTORICAL_RANGE_CUSTOM,
]

# Default chunk size for historical data fetching (days)
DEFAULT_HISTORICAL_CHUNK_SIZE_DAYS = 90

