"""Sensor entities for Octopus Energy España integration."""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from zoneinfo import ZoneInfo

from .const import (
    ATTR_DATA,
    ATTR_PRICE_PER_KWH,
    ATTR_START_TIME,
    ATTR_UNIT_OF_MEASUREMENT,
    CONF_DISCOUNT_END_HOUR,
    CONF_DISCOUNT_PERCENTAGE,
    CONF_DISCOUNT_START_HOUR,
    CONF_MANAGEMENT_FEE_MONTHLY,
    CONF_OTHER_CONCEPTS_RATE,
    DOMAIN,
    PRICING_MODEL_FIXED,
    PRICING_MODEL_MARKET,
    TIMEZONE_MADRID,
)
from .coordinator import OctopusEnergyESCoordinator

_LOGGER = logging.getLogger(__name__)


def _parse_datetime_to_madrid(dt_str: str) -> datetime | None:
    """
    Parse a datetime string and convert it to Madrid timezone.
    
    Args:
        dt_str: ISO datetime string (may include 'Z' for UTC)
        
    Returns:
        Datetime object in Madrid timezone, or None if parsing fails
    """
    try:
        # Parse datetime and convert to Madrid timezone
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            # If no timezone, assume UTC
            dt = dt.replace(tzinfo=ZoneInfo("UTC"))
        # Convert to Madrid timezone
        return dt.astimezone(ZoneInfo(TIMEZONE_MADRID))
    except (ValueError, TypeError) as err:
        _LOGGER.debug("Error parsing datetime '%s': %s", dt_str, err)
        return None


def _group_consumption_by_date(
    consumption: list[dict[str, Any]]
) -> tuple[dict[date, float], list[date]]:
    """
    Group consumption data by date and calculate daily totals.
    
    Args:
        consumption: List of consumption items with 'start_time' or 'date' and 'consumption' or 'value'
        
    Returns:
        Tuple of (daily_totals dict, sorted list of dates)
    """
    daily_totals: dict[date, float] = {}
    all_dates: list[date] = []
    
    for item in consumption:
        if isinstance(item, dict):
            item_time_str = item.get("start_time") or item.get("date")
            if item_time_str:
                item_dt_madrid = _parse_datetime_to_madrid(item_time_str)
                if item_dt_madrid:
                    item_date = item_dt_madrid.date()
                    if item_date not in daily_totals:
                        daily_totals[item_date] = 0.0
                        all_dates.append(item_date)
                    daily_totals[item_date] += float(item.get("consumption", item.get("value", 0)))
    
    all_dates.sort(reverse=True)
    return daily_totals, all_dates


def _group_consumption_by_hour(
    consumption: list[dict[str, Any]]
) -> tuple[dict[datetime, float], list[datetime]]:
    """
    Group consumption data by hour and calculate hourly totals.
    
    Args:
        consumption: List of consumption items with 'start_time' or 'datetime' and 'consumption' or 'value'
        
    Returns:
        Tuple of (hourly_totals dict, sorted list of hours)
    """
    hourly_totals: dict[datetime, float] = {}
    all_hours: list[datetime] = []
    
    for item in consumption:
        if isinstance(item, dict):
            item_time_str = item.get("start_time") or item.get("datetime")
            if item_time_str:
                item_dt_madrid = _parse_datetime_to_madrid(item_time_str)
                if item_dt_madrid:
                    item_hour = item_dt_madrid.replace(minute=0, second=0, microsecond=0)
                    if item_hour not in hourly_totals:
                        hourly_totals[item_hour] = 0.0
                        all_hours.append(item_hour)
                    hourly_totals[item_hour] += float(item.get("consumption", item.get("value", 0)))
    
    all_hours.sort(reverse=True)
    return hourly_totals, all_hours


def _group_consumption_by_month(
    consumption: list[dict[str, Any]]
) -> tuple[dict[tuple[int, int], float], list[tuple[int, int]]]:
    """
    Group consumption data by month and calculate monthly totals.
    
    Args:
        consumption: List of consumption items with 'start_time' or 'date' and 'consumption' or 'value'
        
    Returns:
        Tuple of (monthly_totals dict keyed by (year, month), sorted list of month keys)
    """
    monthly_totals: dict[tuple[int, int], float] = {}
    all_months: list[tuple[int, int]] = []
    
    for item in consumption:
        if isinstance(item, dict):
            item_time_str = item.get("start_time") or item.get("date")
            if item_time_str:
                item_dt_madrid = _parse_datetime_to_madrid(item_time_str)
                if item_dt_madrid:
                    month_key = (item_dt_madrid.year, item_dt_madrid.month)
                    if month_key not in monthly_totals:
                        monthly_totals[month_key] = 0.0
                        all_months.append(month_key)
                    monthly_totals[month_key] += float(item.get("consumption", item.get("value", 0)))
    
    all_months.sort(reverse=True)
    return monthly_totals, all_months


def _group_consumption_by_year(
    consumption: list[dict[str, Any]]
) -> tuple[dict[int, float], list[int]]:
    """
    Group consumption data by year and calculate yearly totals.
    
    Args:
        consumption: List of consumption items with 'start_time' or 'date' and 'consumption' or 'value'
        
    Returns:
        Tuple of (yearly_totals dict, sorted list of years)
    """
    yearly_totals: dict[int, float] = {}
    all_years: list[int] = []
    
    for item in consumption:
        if isinstance(item, dict):
            item_time_str = item.get("start_time") or item.get("date")
            if item_time_str:
                item_dt_madrid = _parse_datetime_to_madrid(item_time_str)
                if item_dt_madrid:
                    year = item_dt_madrid.year
                    if year not in yearly_totals:
                        yearly_totals[year] = 0.0
                        all_years.append(year)
                    yearly_totals[year] += float(item.get("consumption", item.get("value", 0)))
    
    all_years.sort(reverse=True)
    return yearly_totals, all_years


def _calculate_last_reset_for_date(target_date: date) -> str:
    """Calculate last_reset datetime for a given date (start of day at midnight)."""
    day_start = datetime.combine(target_date, datetime.min.time(), tzinfo=ZoneInfo(TIMEZONE_MADRID))
    return day_start.isoformat()


def _calculate_last_reset_for_datetime(target_datetime: datetime) -> str:
    """Calculate last_reset datetime for a given datetime (the datetime itself)."""
    return target_datetime.isoformat()


def _calculate_last_reset_for_month(year: int, month: int) -> str:
    """Calculate last_reset datetime for a given month (start of month, 1st day at midnight)."""
    month_start = datetime(year, month, 1, tzinfo=ZoneInfo(TIMEZONE_MADRID))
    return month_start.isoformat()


def _calculate_last_reset_for_year(year: int) -> str:
    """Calculate last_reset datetime for a given year (January 1st at midnight)."""
    year_start = datetime(year, 1, 1, tzinfo=ZoneInfo(TIMEZONE_MADRID))
    return year_start.isoformat()

PRICE_SENSOR_DESCRIPTION = SensorEntityDescription(
    key="octopus_energy_es_average_price",
    name="Average Price (24h)",
    native_unit_of_measurement="€/kWh",
    state_class=SensorStateClass.MEASUREMENT,
    icon="mdi:chart-timeline-variant",
    suggested_display_precision=4,
)

CURRENT_PRICE_SENSOR_DESCRIPTION = SensorEntityDescription(
    key="octopus_energy_es_current_price",
    name="Current Price",
    native_unit_of_measurement="€/kWh",
    state_class=SensorStateClass.MEASUREMENT,
    icon="mdi:currency-eur",
    suggested_display_precision=4,
)

MIN_PRICE_SENSOR_DESCRIPTION = SensorEntityDescription(
    key="octopus_energy_es_min_price",
    name="Min Price",
    native_unit_of_measurement="€/kWh",
    state_class=SensorStateClass.MEASUREMENT,
    icon="mdi:trending-down",
    suggested_display_precision=4,
)

MAX_PRICE_SENSOR_DESCRIPTION = SensorEntityDescription(
    key="octopus_energy_es_max_price",
    name="Max Price",
    native_unit_of_measurement="€/kWh",
    state_class=SensorStateClass.MEASUREMENT,
    icon="mdi:trending-up",
    suggested_display_precision=4,
)

CHEAPEST_HOUR_SENSOR_DESCRIPTION = SensorEntityDescription(
    key="octopus_energy_es_cheapest_hour",
    name="Cheapest Hour",
    icon="mdi:clock-outline",
)

DAILY_CONSUMPTION_SENSOR_DESCRIPTION = SensorEntityDescription(
    key="octopus_energy_es_daily_consumption",
    name="Daily Consumption",
    native_unit_of_measurement="kWh",
    device_class=SensorDeviceClass.ENERGY,
    state_class=SensorStateClass.TOTAL,
    icon="mdi:lightning-bolt",
    suggested_display_precision=3,
)


MONTHLY_CONSUMPTION_SENSOR_DESCRIPTION = SensorEntityDescription(
    key="octopus_energy_es_monthly_consumption",
    name="Monthly Consumption",
    native_unit_of_measurement="kWh",
    device_class=SensorDeviceClass.ENERGY,
    state_class=SensorStateClass.TOTAL,
    icon="mdi:lightning-bolt",
    suggested_display_precision=3,
)

WEEKLY_CONSUMPTION_SENSOR_DESCRIPTION = SensorEntityDescription(
    key="octopus_energy_es_weekly_consumption",
    name="Weekly Consumption",
    native_unit_of_measurement="kWh",
    device_class=SensorDeviceClass.ENERGY,
    state_class=SensorStateClass.TOTAL,
    icon="mdi:lightning-bolt",
    suggested_display_precision=3,
)

YEARLY_CONSUMPTION_SENSOR_DESCRIPTION = SensorEntityDescription(
    key="octopus_energy_es_yearly_consumption",
    name="Yearly Consumption",
    native_unit_of_measurement="kWh",
    device_class=SensorDeviceClass.ENERGY,
    state_class=SensorStateClass.TOTAL,
    icon="mdi:lightning-bolt",
    suggested_display_precision=3,
)

DAILY_COST_SENSOR_DESCRIPTION = SensorEntityDescription(
    key="octopus_energy_es_daily_cost",
    name="Daily Cost",
    native_unit_of_measurement="€",
    state_class=SensorStateClass.TOTAL_INCREASING,
    icon="mdi:cash",
    suggested_display_precision=2,
)

LAST_INVOICE_SENSOR_DESCRIPTION = SensorEntityDescription(
    key="octopus_energy_es_last_invoice",
    name="Last Invoice",
    native_unit_of_measurement="€",
    state_class=SensorStateClass.TOTAL_INCREASING,
    icon="mdi:invoice-text-outline",
    suggested_display_precision=2,
)

BILLING_PERIOD_SENSOR_DESCRIPTION = SensorEntityDescription(
    key="octopus_energy_es_billing_period",
    name="Billing Period",
    icon="mdi:calendar-range",
)

CREDITS_SENSOR_DESCRIPTION = SensorEntityDescription(
    key="octopus_energy_es_credits",
    name="Credits",
    native_unit_of_measurement="€",
    state_class=SensorStateClass.TOTAL_INCREASING,
    icon="mdi:piggy-bank-outline",
    suggested_display_precision=2,
)

CREDITS_ESTIMATED_SENSOR_DESCRIPTION = SensorEntityDescription(
    key="octopus_energy_es_credits_estimated",
    name="Credits (Estimated)",
    native_unit_of_measurement="€",
    state_class=SensorStateClass.TOTAL_INCREASING,
    icon="mdi:piggy-bank-outline",
    suggested_display_precision=2,
)

ACCOUNT_SENSOR_DESCRIPTION = SensorEntityDescription(
    key="octopus_energy_es_account",
    name="Account",
    icon="mdi:account",
)

NEXT_INVOICE_ESTIMATED_SENSOR_DESCRIPTION = SensorEntityDescription(
    key="octopus_energy_es_next_invoice_estimated",
    name="Next Invoice (Estimated)",
    native_unit_of_measurement="€",
    state_class=SensorStateClass.TOTAL_INCREASING,
    icon="mdi:invoice-text-clock-outline",
    suggested_display_precision=2,
)

SOLAR_WALLET_SENSOR_DESCRIPTION = SensorEntityDescription(
    key="octopus_energy_es_solar_wallet",
    name="Solar Wallet",
    native_unit_of_measurement="€",
    state_class=SensorStateClass.TOTAL,
    icon="mdi:wallet-bifold-outline",
    suggested_display_precision=2,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Octopus Energy España sensors."""
    coordinator: OctopusEnergyESCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = [
        OctopusEnergyESPriceSensor(coordinator, PRICE_SENSOR_DESCRIPTION),
        OctopusEnergyESCurrentPriceSensor(coordinator, CURRENT_PRICE_SENSOR_DESCRIPTION),
        OctopusEnergyESMinPriceSensor(coordinator, MIN_PRICE_SENSOR_DESCRIPTION),
        OctopusEnergyESMaxPriceSensor(coordinator, MAX_PRICE_SENSOR_DESCRIPTION),
        OctopusEnergyESCheapestHourSensor(coordinator, CHEAPEST_HOUR_SENSOR_DESCRIPTION),
        OctopusEnergyESDailyConsumptionSensor(
            coordinator, DAILY_CONSUMPTION_SENSOR_DESCRIPTION
        ),
        OctopusEnergyESMonthlyConsumptionSensor(
            coordinator, MONTHLY_CONSUMPTION_SENSOR_DESCRIPTION
        ),
        OctopusEnergyESWeeklyConsumptionSensor(
            coordinator, WEEKLY_CONSUMPTION_SENSOR_DESCRIPTION
        ),
        OctopusEnergyESYearlyConsumptionSensor(
            coordinator, YEARLY_CONSUMPTION_SENSOR_DESCRIPTION
        ),
        OctopusEnergyESDailyCostSensor(coordinator, DAILY_COST_SENSOR_DESCRIPTION),
        OctopusEnergyESLastInvoiceSensor(coordinator, LAST_INVOICE_SENSOR_DESCRIPTION),
        OctopusEnergyESNextInvoiceEstimatedSensor(coordinator, NEXT_INVOICE_ESTIMATED_SENSOR_DESCRIPTION),
        OctopusEnergyESBillingPeriodSensor(coordinator, BILLING_PERIOD_SENSOR_DESCRIPTION),
        OctopusEnergyESCreditsSensor(
            coordinator, CREDITS_SENSOR_DESCRIPTION
        ),
        OctopusEnergyESCreditsEstimatedSensor(
            coordinator, CREDITS_ESTIMATED_SENSOR_DESCRIPTION
        ),
        OctopusEnergyESSolarWalletSensor(coordinator, SOLAR_WALLET_SENSOR_DESCRIPTION),
        OctopusEnergyESAccountSensor(coordinator, ACCOUNT_SENSOR_DESCRIPTION),
    ]

    async_add_entities(entities)


class OctopusEnergyESSensor(CoordinatorEntity, SensorEntity):
    """Base sensor for Octopus Energy España."""

    def __init__(
        self,
        coordinator: OctopusEnergyESCoordinator,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator._entry.entry_id}_{description.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator._entry.entry_id)},
            "name": "Octopus Energy España",
            "manufacturer": "Octopus Energy España",
            "model": coordinator._entry.data.get("pricing_model", "Unknown"),
        }

    @property
    def _has_data(self) -> bool:
        """Check if coordinator has data available."""
        # Check if coordinator.data exists and is a dict
        if self.coordinator.data is None:
            return False
        if not isinstance(self.coordinator.data, dict):
            return False
        # Allow using data if coordinator has successfully updated at least once
        # This ensures sensors can access data even if the last update failed
        if self.coordinator.last_update_success:
            return True
        # If last update failed, check if there's actual non-empty data available
        # (for cases where cached data exists from a previous successful update)
        data = self.coordinator.data
        # Check if any of the main data sources have actual data (not empty lists/dicts)
        has_prices = bool(data.get("today_prices") or data.get("tomorrow_prices"))
        has_consumption = bool(data.get("consumption"))
        has_billing = bool(data.get("billing") and isinstance(data.get("billing"), dict) and data.get("billing"))
        has_credits = bool(data.get("credits") and isinstance(data.get("credits"), dict) and data.get("credits"))
        has_account = bool(data.get("account") and isinstance(data.get("account"), dict) and data.get("account"))
        
        if has_prices or has_consumption or has_billing or has_credits or has_account:
            return True
        return False



class OctopusEnergyESPriceSensor(OctopusEnergyESSensor):
    """Main price sensor with data array for price-timeline-card."""

    @property
    def native_value(self) -> float | None:
        """Return the average price for current day."""
        if not self._has_data:
            return None
            
        data = self.coordinator.data
        prices = data.get("today_prices", [])

        if not prices:
            _LOGGER.debug("No price data in coordinator")
            return None

        total = sum(price["price_per_kwh"] for price in prices)
        return round(total / len(prices), 6)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        data = self.coordinator.data
        today_prices = data.get("today_prices", [])
        tomorrow_prices = data.get("tomorrow_prices", [])
        
        # Combine today and tomorrow prices for data attribute (ha_epex_spot format)
        all_prices = today_prices + tomorrow_prices
        
        # Format data for price-timeline-card compatibility (ha_epex_spot format)
        price_data = [
            {
                "start_time": price["start_time"],
                "price_per_kwh": price["price_per_kwh"],
            }
            for price in all_prices
        ]
        
        # Separate today and tomorrow prices (ha_epex_spot format)
        today_data = [
            {
                "start_time": price["start_time"],
                "price_per_kwh": price["price_per_kwh"],
            }
            for price in today_prices
        ]
        
        tomorrow_data = [
            {
                "start_time": price["start_time"],
                "price_per_kwh": price["price_per_kwh"],
            }
            for price in tomorrow_prices
        ]
        
        # Add individual hour attributes (price_00h, price_01h, etc.) for today
        hour_attributes = {}
        for price in today_prices:
            try:
                price_dt = datetime.fromisoformat(price["start_time"].replace("Z", "+00:00"))
                if price_dt.tzinfo is None:
                    price_dt = price_dt.replace(tzinfo=ZoneInfo("UTC"))
                price_dt_madrid = price_dt.astimezone(ZoneInfo(TIMEZONE_MADRID))
                hour = price_dt_madrid.hour
                hour_attributes[f"price_{hour:02d}h"] = price["price_per_kwh"]
            except (ValueError, TypeError):
                continue
        
        attributes = {
            "data": price_data,  # All prices (today + tomorrow)
            "today": today_data,  # Today's prices only
            "tomorrow": tomorrow_data,  # Tomorrow's prices only
            "unit_of_measurement": "€/kWh",
        }
        
        # Add individual hour attributes
        attributes.update(hour_attributes)
        
        return attributes


class OctopusEnergyESCurrentPriceSensor(OctopusEnergyESSensor):
    """Current price sensor."""

    @property
    def native_value(self) -> float | None:
        """Return the current price."""
        if not self._has_data:
            return None
            
        data = self.coordinator.data
        prices = data.get("today_prices", [])

        if not prices:
            return None

        now = datetime.now(ZoneInfo(TIMEZONE_MADRID))
        current_hour = now.replace(minute=0, second=0, microsecond=0)

        # Find price for current hour
        for price in prices:
            price_time = datetime.fromisoformat(price["start_time"])
            if price_time.replace(tzinfo=None) == current_hour.replace(tzinfo=None):
                return price["price_per_kwh"]

        return None


class OctopusEnergyESMinPriceSensor(OctopusEnergyESSensor):
    """Minimum price sensor."""

    @property
    def native_value(self) -> float | None:
        """Return the minimum price."""
        if not self._has_data:
            return None
            
        data = self.coordinator.data
        prices = data.get("today_prices", [])

        if not prices:
            return None

        return min(price["price_per_kwh"] for price in prices)


class OctopusEnergyESMaxPriceSensor(OctopusEnergyESSensor):
    """Maximum price sensor."""

    @property
    def native_value(self) -> float | None:
        """Return the maximum price."""
        if not self._has_data:
            return None
            
        data = self.coordinator.data
        prices = data.get("today_prices", [])

        if not prices:
            return None

        return max(price["price_per_kwh"] for price in prices)


class OctopusEnergyESCheapestHourSensor(OctopusEnergyESSensor):
    """Cheapest hour sensor."""

    @property
    def native_value(self) -> str | None:
        """Return the cheapest hour."""
        if not self._has_data:
            return None
            
        data = self.coordinator.data
        prices = data.get("today_prices", [])

        if not prices:
            return None

        cheapest = min(prices, key=lambda x: x["price_per_kwh"])
        dt = datetime.fromisoformat(cheapest["start_time"])
        return dt.strftime("%H:00")


class OctopusEnergyESDailyConsumptionSensor(OctopusEnergyESSensor):
    """Daily consumption sensor."""

    def __init__(self, coordinator: OctopusEnergyESCoordinator, description: SensorEntityDescription) -> None:
        """Initialize the daily consumption sensor."""
        super().__init__(coordinator, description)
        self._consumption_date: date | None = None
        self._is_today: bool = False
        self._data_available_until: date | None = None
        self._hourly_breakdown: dict[str, float] = {}

    @property
    def native_value(self) -> float | None:
        """Return daily consumption (today's if available, otherwise most recent available)."""
        if not self._has_data:
            return None
            
        data = self.coordinator.data
        consumption = data.get("consumption", [])

        if not consumption:
            self._consumption_date = None
            self._is_today = False
            self._data_available_until = None
            self._hourly_breakdown = {}
            return None

        # Group consumption by date and by hour
        daily_totals, all_dates = _group_consumption_by_date(consumption)
        hourly_totals, all_hours = _group_consumption_by_hour(consumption)

        if not daily_totals:
            self._consumption_date = None
            self._is_today = False
            self._data_available_until = None
            self._hourly_breakdown = {}
            return None

        # Find the most recent date with data
        self._data_available_until = all_dates[0] if all_dates else None

        # Try today first, then fall back to most recent available date
        now = datetime.now(ZoneInfo(TIMEZONE_MADRID))
        today = now.date()
        
        target_date = today if today in daily_totals else (all_dates[0] if all_dates else None)
        
        if target_date:
            # Calculate hourly breakdown for the target date
            hourly_breakdown: dict[str, float] = {}
            target_date_start = datetime.combine(target_date, datetime.min.time(), tzinfo=ZoneInfo(TIMEZONE_MADRID))
            
            for hour_num in range(24):
                hour_dt = target_date_start + timedelta(hours=hour_num)
                hour_key = f"hour_{hour_num:02d}"
                
                if hour_dt in hourly_totals:
                    hourly_breakdown[hour_key] = round(hourly_totals[hour_dt], 3)
                else:
                    hourly_breakdown[hour_key] = 0.0
            
            self._hourly_breakdown = hourly_breakdown
            
            if target_date == today:
                self._consumption_date = today
                self._is_today = True
                return round(daily_totals[today], 3)
            else:
                self._consumption_date = target_date
                self._is_today = False
                return round(daily_totals[target_date], 3)
        
        self._consumption_date = None
        self._is_today = False
        self._hourly_breakdown = {}
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        attrs: dict[str, Any] = {}
        
        if self._consumption_date:
            attrs["consumption_date"] = self._consumption_date.isoformat()
            attrs["last_reset"] = _calculate_last_reset_for_date(self._consumption_date)
        attrs["is_today"] = self._is_today
        
        if self._data_available_until:
            attrs["data_available_until"] = self._data_available_until.isoformat()
        
        # Add individual hour attributes
        if self._hourly_breakdown:
            for hour_key, value in self._hourly_breakdown.items():
                attrs[hour_key] = value
        
        return attrs


class OctopusEnergyESMonthlyConsumptionSensor(OctopusEnergyESSensor):
    """Monthly consumption sensor (updates weekly to show cumulative monthly consumption)."""

    def __init__(self, coordinator: OctopusEnergyESCoordinator, description: SensorEntityDescription) -> None:
        """Initialize the monthly consumption sensor."""
        super().__init__(coordinator, description)
        self._consumption_month: tuple[int, int] | None = None  # (year, month)
        self._is_current_month: bool = False
        self._data_available_until: tuple[int, int] | None = None  # (year, month)
        self._last_monthly_update: date | None = None  # Last week start date when state was updated
        self._cumulative_monthly_total: float = 0.0
        self._weekly_breakdown: dict[str, float] = {}

    def _get_week_start(self, target_date: date) -> date:
        """Get the start date of the week containing target_date (Monday = 0)."""
        # Get Monday of the week
        days_since_monday = target_date.weekday()
        return target_date - timedelta(days=days_since_monday)

    @property
    def native_value(self) -> float | None:
        """Return cumulative monthly consumption up to current week (updates weekly)."""
        if not self._has_data:
            return None
            
        data = self.coordinator.data
        consumption = data.get("consumption", [])

        if not consumption:
            self._consumption_month = None
            self._is_current_month = False
            self._data_available_until = None
            self._cumulative_monthly_total = 0.0
            self._weekly_breakdown = {}
            return None

        now = datetime.now(ZoneInfo(TIMEZONE_MADRID))
        today = now.date()
        current_month = now.month
        current_year = now.year
        current_month_key = (current_year, current_month)
        
        # Get current week start
        current_week_start = self._get_week_start(today)

        # Group consumption by date to calculate weekly totals
        daily_totals, all_dates = _group_consumption_by_date(consumption)

        if not daily_totals:
            self._consumption_month = None
            self._is_current_month = False
            self._data_available_until = None
            self._cumulative_monthly_total = 0.0
            self._weekly_breakdown = {}
            return None

        # Find the most recent month with data
        monthly_totals, all_months = _group_consumption_by_month(consumption)
        self._data_available_until = all_months[0] if all_months else None

        # Check if we should update (only if week has changed or first run)
        should_update = (
            self._last_monthly_update is None or
            self._last_monthly_update != current_week_start
        )

        if not should_update:
            # Return cached cumulative total if week hasn't changed
            return round(self._cumulative_monthly_total, 3)

        # Calculate cumulative monthly consumption up to current week
        # Sum all days in current month up to today, grouped by week
        cumulative_total = 0.0
        weekly_breakdown: dict[str, float] = {}
        month_start = date(current_year, current_month, 1)
        
        # Calculate weekly totals for current month
        for check_date in (month_start + timedelta(days=i) for i in range((today - month_start).days + 1)):
            if check_date <= today and check_date in daily_totals:
                day_value = daily_totals[check_date]
                cumulative_total += day_value
                
                # Determine which week of the month this day belongs to (1-5)
                week_start = self._get_week_start(check_date)
                days_since_month_start = (week_start - month_start).days
                week_num = (days_since_month_start // 7) + 1
                week_key = f"week_{week_num}"
                
                if week_key not in weekly_breakdown:
                    weekly_breakdown[week_key] = 0.0
                weekly_breakdown[week_key] += day_value

        # If current month has no data, fall back to most recent available month
        if cumulative_total == 0.0 and all_months:
            most_recent_month = all_months[0]
            most_recent_year, most_recent_month_num = most_recent_month
            month_start = date(most_recent_year, most_recent_month_num, 1)
            
            # Get last day of that month
            if most_recent_month_num == 12:
                month_end = date(most_recent_year + 1, 1, 1) - timedelta(days=1)
            else:
                month_end = date(most_recent_year, most_recent_month_num + 1, 1) - timedelta(days=1)
            
            # Sum all days in that month, grouped by week
            for check_date in (month_start + timedelta(days=i) for i in range((month_end - month_start).days + 1)):
                if check_date in daily_totals:
                    day_value = daily_totals[check_date]
                    cumulative_total += day_value
                    
                    # Determine which week of the month this day belongs to
                    week_start = self._get_week_start(check_date)
                    days_since_month_start = (week_start - month_start).days
                    week_num = (days_since_month_start // 7) + 1
                    week_key = f"week_{week_num}"
                    
                    if week_key not in weekly_breakdown:
                        weekly_breakdown[week_key] = 0.0
                    weekly_breakdown[week_key] += day_value
            
            self._consumption_month = most_recent_month
            self._is_current_month = False
        else:
            self._consumption_month = current_month_key
            self._is_current_month = True

        # Round weekly breakdown values
        weekly_breakdown = {k: round(v, 3) for k, v in weekly_breakdown.items()}

        # Update tracking
        self._last_monthly_update = current_week_start
        self._cumulative_monthly_total = cumulative_total
        self._weekly_breakdown = weekly_breakdown

        return round(cumulative_total, 3)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        attrs: dict[str, Any] = {}

        if self._consumption_month:
            year, month = self._consumption_month
            attrs["consumption_month"] = f"{year:04d}-{month:02d}"
            attrs["last_reset"] = _calculate_last_reset_for_month(year, month)
        attrs["is_current_month"] = self._is_current_month

        if self._data_available_until:
            year, month = self._data_available_until
            attrs["data_available_until"] = f"{year:04d}-{month:02d}"

        if self._last_monthly_update:
            attrs["last_update_week"] = self._last_monthly_update.isoformat()
            # Calculate current week number in month (1-5)
            if self._consumption_month:
                year, month_num = self._consumption_month
                month_start = date(year, month_num, 1)
                week_start = self._get_week_start(self._last_monthly_update)
                # Calculate which week of the month this is
                days_since_month_start = (week_start - month_start).days
                current_week = (days_since_month_start // 7) + 1
                attrs["current_week"] = current_week

        # Add individual week attributes
        if self._weekly_breakdown:
            for week_key, value in self._weekly_breakdown.items():
                attrs[week_key] = value

        return attrs


class OctopusEnergyESWeeklyConsumptionSensor(OctopusEnergyESSensor):
    """Weekly consumption sensor (updates daily to show cumulative weekly consumption)."""

    def __init__(self, coordinator: OctopusEnergyESCoordinator, description: SensorEntityDescription) -> None:
        """Initialize the weekly consumption sensor."""
        super().__init__(coordinator, description)
        self._consumption_week_start: date | None = None
        self._consumption_week_end: date | None = None
        self._is_current_week: bool = False
        self._data_available_until: date | None = None
        self._last_weekly_update: date | None = None  # Last day when state was updated
        self._cumulative_weekly_total: float = 0.0
        self._daily_breakdown: dict[str, float] = {}

    @property
    def native_value(self) -> float | None:
        """Return cumulative weekly consumption up to current day (updates daily)."""
        if not self._has_data:
            return None
            
        data = self.coordinator.data
        consumption = data.get("consumption", [])

        if not consumption:
            self._consumption_week_start = None
            self._consumption_week_end = None
            self._is_current_week = False
            self._data_available_until = None
            self._cumulative_weekly_total = 0.0
            self._daily_breakdown = {}
            return None

        now = datetime.now(ZoneInfo(TIMEZONE_MADRID))
        today = now.date()
        
        # Calculate current week (last 7 days from today)
        current_week_end = today
        current_week_start = current_week_end - timedelta(days=6)

        # Group consumption by date
        daily_totals, all_dates = _group_consumption_by_date(consumption)

        if not daily_totals:
            self._consumption_week_start = None
            self._consumption_week_end = None
            self._is_current_week = False
            self._data_available_until = None
            self._cumulative_weekly_total = 0.0
            self._daily_breakdown = {}
            return None

        # Find the most recent date with data
        self._data_available_until = all_dates[0] if all_dates else None

        # Check if we should update (only if day has changed or first run)
        should_update = (
            self._last_weekly_update is None or
            self._last_weekly_update != today
        )

        if not should_update:
            # Return cached cumulative total if day hasn't changed
            return round(self._cumulative_weekly_total, 3)

        # Calculate cumulative weekly consumption up to current day
        # Sum all days in current week up to today
        cumulative_total = 0.0
        has_current_week_data = False
        daily_breakdown: dict[str, float] = {}
        day_names = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        
        for i, check_date in enumerate((current_week_start + timedelta(days=j) for j in range(7))):
            if check_date <= today and check_date in daily_totals:
                day_value = daily_totals[check_date]
                cumulative_total += day_value
                daily_breakdown[day_names[i]] = round(day_value, 3)
                has_current_week_data = True

        if has_current_week_data and cumulative_total > 0:
            self._consumption_week_start = current_week_start
            self._consumption_week_end = current_week_end
            self._is_current_week = True
        else:
            # Fall back to most recent 7-day period with data
            most_recent_date = all_dates[0]
            most_recent_week_end = most_recent_date
            most_recent_week_start = most_recent_week_end - timedelta(days=6)

            cumulative_total = 0.0
            daily_breakdown = {}
            for i, check_date in enumerate((most_recent_week_start + timedelta(days=j) for j in range(7))):
                if check_date in daily_totals:
                    day_value = daily_totals[check_date]
                    cumulative_total += day_value
                    daily_breakdown[day_names[i]] = round(day_value, 3)

            if cumulative_total > 0:
                self._consumption_week_start = most_recent_week_start
                self._consumption_week_end = most_recent_week_end
                self._is_current_week = False
            else:
                # No valid week found
                self._consumption_week_start = None
                self._consumption_week_end = None
                self._is_current_week = False
                self._cumulative_weekly_total = 0.0
                self._daily_breakdown = {}
                return None

        # Update tracking
        self._last_weekly_update = today
        self._cumulative_weekly_total = cumulative_total
        self._daily_breakdown = daily_breakdown

        return round(cumulative_total, 3)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        attrs: dict[str, Any] = {}

        if self._consumption_week_start:
            attrs["consumption_week_start"] = self._consumption_week_start.isoformat()
            attrs["last_reset"] = _calculate_last_reset_for_date(self._consumption_week_start)
        if self._consumption_week_end:
            attrs["consumption_week_end"] = self._consumption_week_end.isoformat()
        attrs["is_current_week"] = self._is_current_week

        if self._data_available_until:
            attrs["data_available_until"] = self._data_available_until.isoformat()

        if self._last_weekly_update:
            attrs["last_update_day"] = self._last_weekly_update.isoformat()
            # Calculate current day number in week (1-7, Monday=1)
            if self._consumption_week_start:
                days_since_week_start = (self._last_weekly_update - self._consumption_week_start).days
                current_day = days_since_week_start + 1
                attrs["current_day"] = current_day

        # Add individual day attributes
        if self._daily_breakdown:
            for day_name, value in self._daily_breakdown.items():
                attrs[day_name] = value

        return attrs


class OctopusEnergyESYearlyConsumptionSensor(OctopusEnergyESSensor):
    """Yearly consumption sensor (updates monthly to show cumulative yearly consumption)."""

    def __init__(self, coordinator: OctopusEnergyESCoordinator, description: SensorEntityDescription) -> None:
        """Initialize the yearly consumption sensor."""
        super().__init__(coordinator, description)
        self._consumption_year: int | None = None
        self._is_current_year: bool = False
        self._data_available_until: int | None = None
        self._last_yearly_update: tuple[int, int] | None = None  # (year, month)
        self._monthly_breakdown: dict[str, float] = {}
        self._cumulative_yearly_total: float = 0.0

    @property
    def native_value(self) -> float | None:
        """Return cumulative yearly consumption up to current month (updates monthly)."""
        if not self._has_data:
            return None
            
        data = self.coordinator.data
        consumption = data.get("consumption", [])

        if not consumption:
            self._consumption_year = None
            self._is_current_year = False
            self._data_available_until = None
            self._monthly_breakdown = {}
            self._cumulative_yearly_total = 0.0
            return None

        now = datetime.now(ZoneInfo(TIMEZONE_MADRID))
        current_year = now.year
        current_month = now.month
        current_month_key = (current_year, current_month)

        # Group consumption by month to get monthly breakdown
        monthly_totals, all_months = _group_consumption_by_month(consumption)

        if not monthly_totals:
            self._consumption_year = None
            self._is_current_year = False
            self._data_available_until = None
            self._monthly_breakdown = {}
            self._cumulative_yearly_total = 0.0
            return None

        # Find the most recent month with data
        if all_months:
            most_recent_month = all_months[0]
            self._data_available_until = most_recent_month[0]  # year
        else:
            self._data_available_until = None

        # Calculate cumulative yearly consumption up to current month
        cumulative_total = 0.0
        monthly_breakdown: dict[str, float] = {}
        month_names = [
            "january", "february", "march", "april", "may", "june",
            "july", "august", "september", "october", "november", "december"
        ]

        # Sum all months in current year up to current month
        for month_num in range(1, current_month + 1):
            month_key = (current_year, month_num)
            if month_key in monthly_totals:
                month_value = monthly_totals[month_key]
                cumulative_total += month_value
                monthly_breakdown[month_names[month_num - 1]] = round(month_value, 3)

        # Determine which year to display
        display_year = current_year
        display_month_key = current_month_key
        is_current = True

        # If current year has no data, fall back to most recent available year
        if cumulative_total == 0.0:
            most_recent_year = all_months[0][0] if all_months else current_year
            if most_recent_year != current_year:
                # For previous years, show full year total (all 12 months)
                display_year = most_recent_year
                # Use the last month of that year for tracking
                most_recent_month = all_months[0][1] if all_months else 12
                display_month_key = (most_recent_year, most_recent_month)
                is_current = False
                
                for month_num in range(1, 13):
                    month_key = (most_recent_year, month_num)
                    if month_key in monthly_totals:
                        month_value = monthly_totals[month_key]
                        cumulative_total += month_value
                        monthly_breakdown[month_names[month_num - 1]] = round(month_value, 3)

        # Check if we should update (only if month has changed or first run)
        should_update = (
            self._last_yearly_update is None or
            self._last_yearly_update != display_month_key
        )

        if not should_update:
            # Return cached cumulative total if month hasn't changed
            return round(self._cumulative_yearly_total, 3)

        # Update tracking
        self._consumption_year = display_year
        self._is_current_year = is_current
        self._last_yearly_update = display_month_key
        self._monthly_breakdown = monthly_breakdown
        self._cumulative_yearly_total = cumulative_total

        return round(cumulative_total, 3)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes with monthly breakdown."""
        attrs: dict[str, Any] = {}

        if self._consumption_year:
            attrs["consumption_year"] = f"{self._consumption_year:04d}"
            attrs["last_reset"] = _calculate_last_reset_for_year(self._consumption_year)
        attrs["is_current_year"] = self._is_current_year

        if self._data_available_until:
            attrs["data_available_until"] = f"{self._data_available_until:04d}"

        # Add monthly breakdown
        if self._last_yearly_update:
            year, month = self._last_yearly_update
            attrs["current_month"] = month
            attrs["last_update_month"] = month

        if self._monthly_breakdown:
            # Add individual month attributes
            for month_name, value in self._monthly_breakdown.items():
                attrs[month_name] = value

        return attrs


class OctopusEnergyESDailyCostSensor(OctopusEnergyESSensor):
    """Daily cost sensor."""

    def __init__(self, coordinator: OctopusEnergyESCoordinator, description: SensorEntityDescription) -> None:
        """Initialize the daily cost sensor."""
        super().__init__(coordinator, description)
        self._cost_date: date | None = None
        self._is_today: bool = False
        self._data_available_until: date | None = None
        self._cost_breakdown: dict[str, float] | None = None

    @property
    def native_value(self) -> float | None:
        """Return daily cost (today's if available, otherwise most recent available)."""
        if not self._has_data:
            return None
            
        data = self.coordinator.data
        prices = data.get("today_prices", [])
        consumption = data.get("consumption", [])

        if not prices or not consumption:
            self._cost_date = None
            self._is_today = False
            self._data_available_until = None
            return None

        # Group consumption by date
        daily_totals, all_dates = _group_consumption_by_date(consumption)

        if not daily_totals:
            self._cost_date = None
            self._is_today = False
            self._data_available_until = None
            return None

        # Find the most recent date with data
        self._data_available_until = all_dates[0] if all_dates else None

        # Try today first, then fall back to most recent available date
        now = datetime.now(ZoneInfo(TIMEZONE_MADRID))
        today = now.date()
        target_date = today if today in daily_totals else all_dates[0]
        self._cost_date = target_date
        self._is_today = (target_date == today)

        # Calculate energy cost for the target date
        # Match hourly consumption with hourly prices for accurate cost calculation
        energy_cost = 0.0
        
        # Group consumption by hour for the target date
        hourly_consumption: dict[int, float] = {}
        for item in consumption:
            if isinstance(item, dict):
                item_time_str = item.get("start_time") or item.get("date")
                if item_time_str:
                    item_dt_madrid = _parse_datetime_to_madrid(item_time_str)
                    if item_dt_madrid and item_dt_madrid.date() == target_date:
                        hour = item_dt_madrid.hour
                        if hour not in hourly_consumption:
                            hourly_consumption[hour] = 0.0
                        hourly_consumption[hour] += float(item.get("consumption", item.get("value", 0)))

        # Match hourly consumption with hourly prices
        matched_hours = 0
        for hour, consumption_value in hourly_consumption.items():
            # Find matching price for this hour
            for price in prices:
                price_dt_madrid = _parse_datetime_to_madrid(price.get("start_time", ""))
                if price_dt_madrid and price_dt_madrid.date() == target_date and price_dt_madrid.hour == hour:
                    energy_cost += consumption_value * price.get("price_per_kwh", 0)
                    matched_hours += 1
                    break

        # If we couldn't match hourly consumption with hourly prices,
        # fall back to using daily total consumption and average price
        if matched_hours == 0:
            # Get daily consumption for target date (should exist since we selected it from daily_totals)
            daily_consumption = daily_totals.get(target_date, 0.0)
            
            # Get prices for the target date
            daily_prices: list[float] = []
            for price in prices:
                price_dt_madrid = _parse_datetime_to_madrid(price.get("start_time", ""))
                if price_dt_madrid and price_dt_madrid.date() == target_date:
                    daily_prices.append(price.get("price_per_kwh", 0))

            # If no prices for target date, use average of all available prices as fallback
            if not daily_prices:
                # Use all available prices as fallback
                all_available_prices = [p.get("price_per_kwh", 0) for p in prices if p.get("price_per_kwh") is not None]
                if all_available_prices:
                    avg_price = sum(all_available_prices) / len(all_available_prices)
                    energy_cost = daily_consumption * avg_price
                else:
                    # No prices available at all, return None
                    self._cost_breakdown = None
                    return None
            else:
                # Calculate average price for the day
                avg_price = sum(daily_prices) / len(daily_prices)
                # Calculate energy cost
                energy_cost = daily_consumption * avg_price

        # Calculate power cost (if power rates are configured)
        # Note: Power value should be provided by user if not available via API
        power_cost = None
        entry = self.coordinator._entry
        power_kw = entry.data.get("power_kw")  # User-provided power value
        if power_kw is not None:
            tariff_calculator = self.coordinator._tariff_calculator
            power_cost_dict = tariff_calculator.calculate_power_cost(float(power_kw), target_date)
            power_cost = power_cost_dict.get("total_cost", 0.0)

        # Calculate management fee daily (convert monthly to daily)
        management_fee_daily = None
        management_fee_monthly = entry.data.get(CONF_MANAGEMENT_FEE_MONTHLY)
        if management_fee_monthly is not None:
            # Approximate: monthly fee / average days per month
            management_fee_daily = float(management_fee_monthly) / 30.0

        # Calculate total cost with taxes and other concepts
        tariff_calculator = self.coordinator._tariff_calculator
        cost_breakdown = tariff_calculator.calculate_daily_cost(
            energy_cost=energy_cost,
            power_cost=power_cost,
            management_fee_daily=management_fee_daily,
            target_date=target_date,
        )
        
        self._cost_breakdown = cost_breakdown
        return cost_breakdown.get("total")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        attrs: dict[str, Any] = {}
        
        if self._cost_date:
            attrs["cost_date"] = self._cost_date.isoformat()
        attrs["is_today"] = self._is_today
        
        if self._data_available_until:
            attrs["data_available_until"] = self._data_available_until.isoformat()
        
        # Add cost breakdown if available
        if self._cost_breakdown:
            attrs["base_cost"] = round(self._cost_breakdown.get("base", 0), 2)
            attrs["other_concepts_cost"] = round(self._cost_breakdown.get("other_concepts", 0), 2)
            attrs["electricity_tax"] = round(self._cost_breakdown.get("electricity_tax", 0), 2)
            attrs["vat"] = round(self._cost_breakdown.get("vat", 0), 2)
            attrs["total_cost"] = round(self._cost_breakdown.get("total", 0), 2)
        
        return attrs


class OctopusEnergyESLastInvoiceSensor(OctopusEnergyESSensor):
    """Last invoice sensor."""

    @property
    def native_value(self) -> float | None:
        """Return last invoice amount."""
        if not self._has_data:
            return None
            
        data = self.coordinator.data
        billing = data.get("billing", {})

        if not billing:
            return None

        last_invoice = billing.get("last_invoice")
        if isinstance(last_invoice, dict):
            amount = last_invoice.get("amount")
            if amount is not None:
                # Amount might be in cents, convert to euros
                return float(amount) / 100 if amount > 1000 else float(amount)
            return None

        # Fallback for old format
        invoices = billing.get("invoices", [])
        if invoices and len(invoices) > 0:
            return invoices[0].get("amount")

        return None


class OctopusEnergyESNextInvoiceEstimatedSensor(OctopusEnergyESSensor):
    """Next invoice estimated sensor."""

    def __init__(self, coordinator: OctopusEnergyESCoordinator, description: SensorEntityDescription) -> None:
        """Initialize the next invoice estimated sensor."""
        super().__init__(coordinator, description)
        self._estimated_breakdown: dict[str, float] | None = None
        self._period_start: date | None = None
        self._period_end: date | None = None
        self._days_elapsed: int = 0
        self._days_remaining: int = 0

    def _calculate_daily_energy_cost(
        self, target_date: date, consumption: list[dict[str, Any]], prices: list[dict[str, Any]]
    ) -> float:
        """Calculate energy cost for a specific day using tariff calculator."""
        # Group consumption by hour for the target date
        hourly_consumption: dict[int, float] = {}
        daily_consumption = 0.0
        
        for item in consumption:
            if isinstance(item, dict):
                item_time_str = item.get("start_time") or item.get("date")
                if item_time_str:
                    item_dt_madrid = _parse_datetime_to_madrid(item_time_str)
                    if item_dt_madrid and item_dt_madrid.date() == target_date:
                        hour = item_dt_madrid.hour
                        consumption_value = float(item.get("consumption", item.get("value", 0)))
                        if hour not in hourly_consumption:
                            hourly_consumption[hour] = 0.0
                        hourly_consumption[hour] += consumption_value
                        daily_consumption += consumption_value

        if daily_consumption == 0.0:
            return 0.0

        # Get tariff configuration
        entry = self.coordinator._entry
        tariff_calculator = self.coordinator._tariff_calculator
        pricing_model = entry.data.get("pricing_model", PRICING_MODEL_MARKET)
        
        # For fixed tariffs, calculate using fixed rates
        if pricing_model == PRICING_MODEL_FIXED:
            energy_cost = 0.0
            target_dt = datetime.combine(target_date, datetime.min.time(), tzinfo=ZoneInfo(TIMEZONE_MADRID))
            is_weekday = target_dt.weekday() < 5
            
            for hour, consumption_value in hourly_consumption.items():
                # Get rate for this hour using tariff calculator logic
                period, period_rate = tariff_calculator._get_period_for_hour(hour, is_weekday)
                if period_rate is not None:
                    energy_cost += consumption_value * period_rate
                else:
                    # Fallback to fixed_rate if available
                    if tariff_calculator._config.fixed_rate is not None:
                        energy_cost += consumption_value * tariff_calculator._config.fixed_rate
            
            return energy_cost
        
        # For market tariffs, try to match with prices for the target date
        # First, try to find prices for the exact target date
        day_prices: list[dict[str, Any]] = []
        for price in prices:
            price_dt_madrid = _parse_datetime_to_madrid(price.get("start_time", ""))
            if price_dt_madrid and price_dt_madrid.date() == target_date:
                day_prices.append(price)
        
        # If we have prices for the target date, use them
        if day_prices:
            energy_cost = 0.0
            matched_hours = 0
            for hour, consumption_value in hourly_consumption.items():
                # Find matching price for this hour
                for price in day_prices:
                    price_dt_madrid = _parse_datetime_to_madrid(price.get("start_time", ""))
                    if price_dt_madrid and price_dt_madrid.hour == hour:
                        # Apply tariff calculator to get final price (with discounts, etc.)
                        calculated_prices = tariff_calculator.calculate_prices([price], target_date)
                        if calculated_prices:
                            energy_cost += consumption_value * calculated_prices[0].get("price_per_kwh", 0)
                            matched_hours += 1
                            break
            
            # If we matched some hours, return the cost
            if matched_hours > 0:
                return energy_cost
        
        # Fallback: Use average price from available prices (today's prices as estimate)
        # This is not ideal but better than returning 0
        if prices:
            # Calculate average price from today's prices (as estimate for past dates)
            avg_price = sum(p.get("price_per_kwh", 0) for p in prices) / len(prices)
            # Apply tariff calculator to get final price
            sample_price = {"start_time": datetime.combine(target_date, datetime.min.time()).isoformat(), "price_per_kwh": avg_price}
            calculated_prices = tariff_calculator.calculate_prices([sample_price], target_date)
            if calculated_prices:
                estimated_price = calculated_prices[0].get("price_per_kwh", avg_price)
                return daily_consumption * estimated_price
        
        # Last resort: return 0 if no prices available
        return 0.0

    @property
    def native_value(self) -> float | None:
        """Return estimated next invoice amount."""
        if not self._has_data:
            return None
            
        data = self.coordinator.data
        billing = data.get("billing", {})
        consumption = data.get("consumption", [])
        prices = data.get("today_prices", [])
        tomorrow_prices = data.get("tomorrow_prices", [])

        # Reset state
        self._estimated_breakdown = None
        self._period_start = None
        self._period_end = None
        self._days_elapsed = 0
        self._days_remaining = 0

        # Check if we have required data
        if not billing or not consumption or not prices:
            return None

        last_invoice = billing.get("last_invoice")
        if not last_invoice or not isinstance(last_invoice, dict):
            return None

        # Calculate next billing period
        start_str = last_invoice.get("start")
        end_str = last_invoice.get("end")

        if not start_str or not end_str:
            return None

        try:
            # Parse dates (they are ISO format date strings like "2025-01-15" from isoformat())
            # Use date.fromisoformat() for ISO date strings, or datetime.fromisoformat() for datetime strings
            if "T" in start_str or "+" in start_str or "Z" in start_str:
                # It's a datetime string
                last_start = datetime.fromisoformat(start_str.replace("Z", "+00:00")).date()
            else:
                # It's a plain date string (YYYY-MM-DD)
                last_start = date.fromisoformat(start_str)
            
            if "T" in end_str or "+" in end_str or "Z" in end_str:
                # It's a datetime string
                last_end = datetime.fromisoformat(end_str.replace("Z", "+00:00")).date()
            else:
                # It's a plain date string (YYYY-MM-DD)
                last_end = date.fromisoformat(end_str)
        except (ValueError, AttributeError, TypeError) as e:
            _LOGGER.debug("Error parsing invoice dates: %s (start=%s, end=%s)", e, start_str, end_str)
            return None

        # Calculate next period
        period_duration = (last_end - last_start).days + 1
        next_start = last_end + timedelta(days=1)
        next_end = next_start + timedelta(days=period_duration - 1)

        # Handle month boundaries - if next_end goes beyond month end, adjust
        if next_end.month != next_start.month:
            # Get last day of next_start's month
            if next_start.month == 12:
                last_day = datetime(next_start.year + 1, 1, 1).date() - timedelta(days=1)
            else:
                last_day = datetime(next_start.year, next_start.month + 1, 1).date() - timedelta(days=1)
            next_end = last_day

        self._period_start = next_start
        self._period_end = next_end

        now = datetime.now(ZoneInfo(TIMEZONE_MADRID))
        today = now.date()

        # Check if we're in the billing period
        if today < next_start:
            # We're before the period starts, return None
            return None

        # Calculate days elapsed and remaining
        if today > next_end:
            # Period has ended, use full period
            days_elapsed = period_duration
            days_remaining = 0
        else:
            days_elapsed = (today - next_start).days + 1
            days_remaining = (next_end - today).days

        self._days_elapsed = days_elapsed
        self._days_remaining = days_remaining

        # Calculate actual energy costs for days elapsed
        actual_energy_cost = 0.0
        total_consumption_so_far = 0.0

        for day_offset in range(days_elapsed):
            check_date = next_start + timedelta(days=day_offset)
            if check_date > today:
                break

            # Calculate energy cost for this day
            day_cost = self._calculate_daily_energy_cost(check_date, consumption, prices)
            actual_energy_cost += day_cost

            # Sum consumption for average calculation
            for item in consumption:
                if isinstance(item, dict):
                    item_time_str = item.get("start_time") or item.get("date")
                    if item_time_str:
                        item_dt_madrid = _parse_datetime_to_madrid(item_time_str)
                        if item_dt_madrid and item_dt_madrid.date() == check_date:
                            total_consumption_so_far += float(item.get("consumption", item.get("value", 0)))

        # Calculate average daily consumption
        if days_elapsed > 0:
            avg_daily_consumption = total_consumption_so_far / days_elapsed
        else:
            # No days elapsed, use last month's average if available
            # For now, return None if no data
            return None

        # Project future energy costs for remaining days
        projected_energy_cost = 0.0
        all_prices = prices + tomorrow_prices

        for day_offset in range(days_remaining):
            check_date = today + timedelta(days=day_offset + 1)
            if check_date > next_end:
                break

            # Get prices for this day (use today's prices, tomorrow's, or repeat pattern)
            day_prices: list[float] = []
            for price in all_prices:
                price_dt_madrid = _parse_datetime_to_madrid(price.get("start_time", ""))
                if price_dt_madrid and price_dt_madrid.date() == check_date:
                    day_prices.append(price.get("price_per_kwh", 0))

            # If no prices for this specific day, use average of available prices
            if not day_prices:
                if prices:
                    day_prices = [p.get("price_per_kwh", 0) for p in prices if p.get("price_per_kwh") is not None]
                elif tomorrow_prices:
                    day_prices = [p.get("price_per_kwh", 0) for p in tomorrow_prices if p.get("price_per_kwh") is not None]

            if day_prices:
                avg_price = sum(day_prices) / len(day_prices)
                projected_energy_cost += avg_daily_consumption * avg_price

        # Calculate power costs for full period
        entry = self.coordinator._entry
        power_kw = entry.data.get("power_kw")
        power_cost_total = 0.0
        if power_kw is not None:
            tariff_calculator = self.coordinator._tariff_calculator
            for day_offset in range(period_duration):
                check_date = next_start + timedelta(days=day_offset)
                power_cost_dict = tariff_calculator.calculate_power_cost(float(power_kw), check_date)
                power_cost_total += power_cost_dict.get("total_cost", 0.0)

        # Get management fee (already monthly)
        management_fee = 0.0
        management_fee_monthly = entry.data.get(CONF_MANAGEMENT_FEE_MONTHLY)
        if management_fee_monthly is not None:
            management_fee = float(management_fee_monthly)

        # Calculate other concepts for full period
        other_concepts = 0.0
        other_concepts_rate = entry.data.get(CONF_OTHER_CONCEPTS_RATE)
        if other_concepts_rate is not None:
            other_concepts = float(other_concepts_rate) * period_duration

        # Calculate base total (before taxes)
        base_total = actual_energy_cost + projected_energy_cost + power_cost_total + management_fee + other_concepts

        # Apply taxes
        tariff_calculator = self.coordinator._tariff_calculator
        tariff_config = tariff_calculator._config
        electricity_tax = base_total * tariff_config.electricity_tax_rate
        vat_base = base_total + electricity_tax
        vat = vat_base * tariff_config.vat_rate
        total = base_total + electricity_tax + vat

        # Store breakdown
        self._estimated_breakdown = {
            "actual_energy_cost": round(actual_energy_cost, 2),
            "projected_energy_cost": round(projected_energy_cost, 2),
            "power_cost": round(power_cost_total, 2),
            "management_fee": round(management_fee, 2),
            "other_concepts": round(other_concepts, 2),
            "base_total": round(base_total, 2),
            "electricity_tax": round(electricity_tax, 2),
            "vat": round(vat, 2),
            "total": round(total, 2),
        }

        return total

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        attrs: dict[str, Any] = {}

        if self._period_start:
            attrs["period_start"] = self._period_start.isoformat()
        if self._period_end:
            attrs["period_end"] = self._period_end.isoformat()
        attrs["days_elapsed"] = self._days_elapsed
        attrs["days_remaining"] = self._days_remaining

        if self._estimated_breakdown:
            attrs["actual_energy_cost"] = self._estimated_breakdown.get("actual_energy_cost", 0)
            attrs["projected_energy_cost"] = self._estimated_breakdown.get("projected_energy_cost", 0)
            attrs["power_cost"] = self._estimated_breakdown.get("power_cost", 0)
            attrs["management_fee"] = self._estimated_breakdown.get("management_fee", 0)
            attrs["other_concepts"] = self._estimated_breakdown.get("other_concepts", 0)
            attrs["base_total"] = self._estimated_breakdown.get("base_total", 0)
            attrs["electricity_tax"] = self._estimated_breakdown.get("electricity_tax", 0)
            attrs["vat"] = self._estimated_breakdown.get("vat", 0)
            attrs["total"] = self._estimated_breakdown.get("total", 0)

        return attrs


class OctopusEnergyESBillingPeriodSensor(OctopusEnergyESSensor):
    """Billing period sensor."""

    @property
    def native_value(self) -> str | None:
        """Return billing period as string."""
        if not self._has_data:
            return None
            
        data = self.coordinator.data
        billing = data.get("billing", {})

        if not billing:
            return None

        last_invoice = billing.get("last_invoice")
        if not last_invoice:
            return None

        start = last_invoice.get("start")
        end = last_invoice.get("end")

        if start and end:
            return f"{start} to {end}"

        return None


class OctopusEnergyESSolarWalletSensor(OctopusEnergyESSensor):
    """Solar Wallet sensor."""

    @property
    def native_value(self) -> float | None:
        """Return Solar Wallet balance."""
        if not self._has_data:
            return None
            
        data = self.coordinator.data
        billing = data.get("billing", {})

        if not billing:
            return None

        solar_wallet = billing.get("solar_wallet")
        if solar_wallet is not None:
            # Balance is already in euros (converted from cents in API client)
            balance = float(solar_wallet)
            # Return 0.0 if balance is 0 to avoid showing "Unknown"
            return balance if balance != 0.0 else 0.0

        return None


class OctopusEnergyESCreditsSensor(OctopusEnergyESSensor):
    """Credits sensor (shows last month's credits as Octopus calculates them post factum)."""

    @property
    def native_value(self) -> float | None:
        """Return credits (last month's credits)."""
        if not self._has_data:
            return None
            
        data = self.coordinator.data
        credits = data.get("credits", {})

        if not credits:
            return None

        totals = credits.get("totals", {})
        return totals.get("current_month")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes with breakdown by reason code."""
        attrs: dict[str, Any] = {}
        data = self.coordinator.data
        credits = data.get("credits", {})

        if credits:
            by_reason_code = credits.get("by_reason_code", {})
            if by_reason_code:
                # Calculate current month totals by reason code
                from datetime import datetime
                from zoneinfo import ZoneInfo
                from .const import TIMEZONE_MADRID
                
                now = datetime.now(ZoneInfo(TIMEZONE_MADRID))
                current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                
                current_month_by_reason: dict[str, float] = {}
                for reason_code, credit_list in by_reason_code.items():
                    month_total = 0.0
                    for credit in credit_list:
                        created_at_str = credit.get("createdAt")
                        if created_at_str:
                            try:
                                created_at = datetime.fromisoformat(
                                    created_at_str.replace("Z", "+00:00")
                                ).astimezone(ZoneInfo(TIMEZONE_MADRID))
                                if created_at >= current_month_start:
                                    # Amount is in cents, convert to euros
                                    amount = float(credit.get("amount", 0)) / 100
                                    month_total += amount
                            except (ValueError, TypeError):
                                pass
                    if month_total > 0:
                        current_month_by_reason[reason_code] = round(month_total, 2)
                
                if current_month_by_reason:
                    attrs["credits_by_reason_code"] = current_month_by_reason
                    attrs["reason_codes"] = list(current_month_by_reason.keys())
            
            # Backward compatibility: show SUN_CLUB specific totals if available
            totals = credits.get("totals", {})
            if totals.get("sun_club"):
                attrs["sun_club"] = totals.get("sun_club")
            if totals.get("sun_club_power_up"):
                attrs["sun_club_power_up"] = totals.get("sun_club_power_up")

        return attrs


class OctopusEnergyESCreditsEstimatedSensor(OctopusEnergyESSensor):
    """Estimated credits sensor (calculates future credits based on consumption during discounted hours)."""

    @property
    def native_value(self) -> float | None:
        """Return estimated credits for current month based on consumption during discount hours."""
        if not self._has_data:
            return None
            
        data = self.coordinator.data
        consumption = data.get("consumption", [])
        prices = data.get("today_prices", [])

        if not consumption or not prices:
            return None

        # Get discount configuration from entry
        entry = self.coordinator._entry
        discount_start_hour = entry.data.get(CONF_DISCOUNT_START_HOUR)
        discount_end_hour = entry.data.get(CONF_DISCOUNT_END_HOUR)
        discount_percentage = entry.data.get(CONF_DISCOUNT_PERCENTAGE)

        # If no discount configured, return None
        if (
            discount_start_hour is None
            or discount_end_hour is None
            or discount_percentage is None
        ):
            return None

        # Calculate estimated credits for current month
        now = datetime.now(ZoneInfo(TIMEZONE_MADRID))
        current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        total_estimated_credits = 0.0

        # Process consumption data
        for item in consumption:
            if isinstance(item, dict):
                item_time_str = item.get("start_time") or item.get("date")
                if item_time_str:
                    item_dt_madrid = _parse_datetime_to_madrid(item_time_str)
                    if item_dt_madrid and item_dt_madrid >= current_month_start:
                        hour = item_dt_madrid.hour
                        
                        # Check if this hour is within discount period
                        if discount_start_hour <= hour < discount_end_hour:
                            consumption_value = float(
                                item.get("consumption", item.get("value", 0))
                            )
                            
                            # Find matching price for this hour
                            for price in prices:
                                price_dt_madrid = _parse_datetime_to_madrid(
                                    price.get("start_time", "")
                                )
                                if (
                                    price_dt_madrid
                                    and price_dt_madrid.date() == item_dt_madrid.date()
                                    and price_dt_madrid.hour == hour
                                ):
                                    price_per_kwh = price.get("price_per_kwh", 0)
                                    # Calculate credit: consumption * price * discount_percentage
                                    credit = consumption_value * price_per_kwh * discount_percentage
                                    total_estimated_credits += credit
                                    break

        return round(total_estimated_credits, 2) if total_estimated_credits > 0 else 0.0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes with breakdown by reason code for current month."""
        attrs: dict[str, Any] = {}
        data = self.coordinator.data
        credits = data.get("credits", {})

        if credits:
            by_reason_code = credits.get("by_reason_code", {})
            if by_reason_code:
                # Calculate current month totals by reason code
                from datetime import datetime
                from zoneinfo import ZoneInfo
                from .const import TIMEZONE_MADRID
                
                now = datetime.now(ZoneInfo(TIMEZONE_MADRID))
                current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                
                current_month_by_reason: dict[str, float] = {}
                for reason_code, credit_list in by_reason_code.items():
                    month_total = 0.0
                    for credit in credit_list:
                        created_at_str = credit.get("createdAt")
                        if created_at_str:
                            try:
                                created_at = datetime.fromisoformat(
                                    created_at_str.replace("Z", "+00:00")
                                ).astimezone(ZoneInfo(TIMEZONE_MADRID))
                                if created_at >= current_month_start:
                                    amount = float(credit.get("amount", 0)) / 100
                                    month_total += amount
                            except (ValueError, AttributeError):
                                pass
                    if month_total > 0:
                        current_month_by_reason[reason_code] = round(month_total, 2)
                
                if current_month_by_reason:
                    attrs["credits_by_reason_code"] = current_month_by_reason

        return attrs


class OctopusEnergyESAccountSensor(OctopusEnergyESSensor):
    """Account information sensor."""

    @property
    def native_value(self) -> str | None:
        """Return account ID."""
        if not self._has_data:
            return None
            
        data = self.coordinator.data
        account = data.get("account", {})
        
        if not account:
            return None
        
        return account.get("account_id")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return account attributes."""
        data = self.coordinator.data
        account = data.get("account", {})
        
        if not account:
            return {}
        
        return {
            "name": account.get("name"),
            "email": account.get("email"),
            "mobile": account.get("mobile"),
            "address": account.get("address"),
            "tariff": account.get("tariff"),
            "cups": account.get("cups"),
        }

