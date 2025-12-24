"""Constants for Octopus Energy Spain integration."""
from __future__ import annotations

from datetime import timedelta

DOMAIN = "octopus_energy_es"

# Configuration keys
CONF_TARIFF_TYPE = "tariff_type"
CONF_PROPERTY_ID = "property_id"
CONF_ESIOS_TOKEN = "esios_token"
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

# API endpoints
ESIOS_API_BASE_URL = "https://api.esios.ree.es"
ESIOS_API_INDICATOR_PVPC = 1001  # PVPC hourly prices

OCTOPUS_API_BASE_URL = "https://api.octopusenergy.es"

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

