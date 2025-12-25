"""Sensor entities for Octopus Energy España integration."""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.components.sensor import (
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

PRICE_SENSOR_DESCRIPTION = SensorEntityDescription(
    key="price",
    name="Octopus Energy España Price",
    native_unit_of_measurement="€/kWh",
    state_class=SensorStateClass.MEASUREMENT,
)

CURRENT_PRICE_SENSOR_DESCRIPTION = SensorEntityDescription(
    key="current_price",
    name="Octopus Energy España Current Price",
    native_unit_of_measurement="€/kWh",
    state_class=SensorStateClass.MEASUREMENT,
)

MIN_PRICE_SENSOR_DESCRIPTION = SensorEntityDescription(
    key="min_price",
    name="Octopus Energy España Min Price",
    native_unit_of_measurement="€/kWh",
    state_class=SensorStateClass.MEASUREMENT,
)

MAX_PRICE_SENSOR_DESCRIPTION = SensorEntityDescription(
    key="max_price",
    name="Octopus Energy España Max Price",
    native_unit_of_measurement="€/kWh",
    state_class=SensorStateClass.MEASUREMENT,
)

CHEAPEST_HOUR_SENSOR_DESCRIPTION = SensorEntityDescription(
    key="cheapest_hour",
    name="Octopus Energy España Cheapest Hour",
    icon="mdi:clock-outline",
)

DAILY_CONSUMPTION_SENSOR_DESCRIPTION = SensorEntityDescription(
    key="daily_consumption",
    name="Octopus Energy España Daily Consumption",
    native_unit_of_measurement="kWh",
    state_class=SensorStateClass.TOTAL_INCREASING,
    icon="mdi:lightning-bolt",
)

HOURLY_CONSUMPTION_SENSOR_DESCRIPTION = SensorEntityDescription(
    key="hourly_consumption",
    name="Octopus Energy España Hourly Consumption",
    native_unit_of_measurement="kWh",
    state_class=SensorStateClass.MEASUREMENT,
    icon="mdi:lightning-bolt",
)

MONTHLY_CONSUMPTION_SENSOR_DESCRIPTION = SensorEntityDescription(
    key="monthly_consumption",
    name="Octopus Energy España Monthly Consumption",
    native_unit_of_measurement="kWh",
    state_class=SensorStateClass.TOTAL_INCREASING,
    icon="mdi:lightning-bolt",
)

WEEKLY_CONSUMPTION_SENSOR_DESCRIPTION = SensorEntityDescription(
    key="weekly_consumption",
    name="Octopus Energy España Weekly Consumption",
    native_unit_of_measurement="kWh",
    state_class=SensorStateClass.TOTAL_INCREASING,
    icon="mdi:lightning-bolt",
)

YEARLY_CONSUMPTION_SENSOR_DESCRIPTION = SensorEntityDescription(
    key="yearly_consumption",
    name="Octopus Energy España Yearly Consumption",
    native_unit_of_measurement="kWh",
    state_class=SensorStateClass.TOTAL_INCREASING,
    icon="mdi:lightning-bolt",
)

DAILY_COST_SENSOR_DESCRIPTION = SensorEntityDescription(
    key="daily_cost",
    name="Octopus Energy España Daily Cost",
    native_unit_of_measurement="€",
    state_class=SensorStateClass.TOTAL_INCREASING,
    icon="mdi:currency-eur",
)

LAST_INVOICE_SENSOR_DESCRIPTION = SensorEntityDescription(
    key="last_invoice",
    name="Octopus Energy España Last Invoice",
    native_unit_of_measurement="€",
    state_class=SensorStateClass.TOTAL_INCREASING,
    icon="mdi:receipt",
)

BILLING_PERIOD_SENSOR_DESCRIPTION = SensorEntityDescription(
    key="billing_period",
    name="Octopus Energy España Billing Period",
    icon="mdi:calendar-range",
)

CREDITS_SENSOR_DESCRIPTION = SensorEntityDescription(
    key="credits",
    name="Octopus Energy España Credits",
    native_unit_of_measurement="€",
    state_class=SensorStateClass.TOTAL_INCREASING,
    icon="mdi:currency-eur",
)

CREDITS_ESTIMATED_SENSOR_DESCRIPTION = SensorEntityDescription(
    key="credits_estimated",
    name="Octopus Energy España Credits Estimated",
    native_unit_of_measurement="€",
    state_class=SensorStateClass.TOTAL_INCREASING,
    icon="mdi:currency-eur",
)

ACCOUNT_SENSOR_DESCRIPTION = SensorEntityDescription(
    key="account",
    name="Octopus Energy España Account",
    icon="mdi:account",
)

NEXT_INVOICE_ESTIMATED_SENSOR_DESCRIPTION = SensorEntityDescription(
    key="next_invoice_estimated",
    name="Octopus Energy España Next Invoice Estimated",
    native_unit_of_measurement="€",
    state_class=SensorStateClass.TOTAL_INCREASING,
    icon="mdi:receipt-text",
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
        OctopusEnergyESHourlyConsumptionSensor(
            coordinator, HOURLY_CONSUMPTION_SENSOR_DESCRIPTION
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



class OctopusEnergyESPriceSensor(OctopusEnergyESSensor):
    """Main price sensor with data array for price-timeline-card."""

    @property
    def native_value(self) -> float | None:
        """Return the average price for current day."""
        if not self.coordinator.data:
            _LOGGER.debug("Coordinator data is None or empty")
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

    @property
    def native_value(self) -> float | None:
        """Return daily consumption (today's if available, otherwise most recent available)."""
        data = self.coordinator.data
        consumption = data.get("consumption", [])

        if not consumption:
            self._consumption_date = None
            self._is_today = False
            self._data_available_until = None
            return None

        # Group consumption by date and calculate daily totals
        daily_totals: dict[date, float] = {}
        all_dates: list[date] = []
        
        now = datetime.now(ZoneInfo(TIMEZONE_MADRID))
        today = now.date()

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

        if not daily_totals:
            self._consumption_date = None
            self._is_today = False
            self._data_available_until = None
            return None

        # Find the most recent date with data
        all_dates.sort(reverse=True)
        self._data_available_until = all_dates[0]

        # Try today first, then fall back to most recent available date
        if today in daily_totals:
            self._consumption_date = today
            self._is_today = True
            return round(daily_totals[today], 3)
        else:
            # Use the most recent available date
            most_recent_date = all_dates[0]
            self._consumption_date = most_recent_date
            self._is_today = False
            return round(daily_totals[most_recent_date], 3)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        attrs: dict[str, Any] = {}
        
        if self._consumption_date:
            attrs["consumption_date"] = self._consumption_date.isoformat()
        attrs["is_today"] = self._is_today
        
        if self._data_available_until:
            attrs["data_available_until"] = self._data_available_until.isoformat()
        
        return attrs


class OctopusEnergyESHourlyConsumptionSensor(OctopusEnergyESSensor):
    """Hourly consumption sensor."""

    def __init__(self, coordinator: OctopusEnergyESCoordinator, description: SensorEntityDescription) -> None:
        """Initialize the hourly consumption sensor."""
        super().__init__(coordinator, description)
        self._consumption_datetime: datetime | None = None
        self._is_current_hour: bool = False
        self._data_available_until: datetime | None = None

    @property
    def native_value(self) -> float | None:
        """Return hourly consumption (current hour's if available, otherwise most recent available)."""
        data = self.coordinator.data
        consumption = data.get("consumption", [])

        if not consumption:
            self._consumption_datetime = None
            self._is_current_hour = False
            self._data_available_until = None
            return None

        # Group consumption by hour and calculate hourly totals
        hourly_totals: dict[datetime, float] = {}
        all_hours: list[datetime] = []

        now = datetime.now(ZoneInfo(TIMEZONE_MADRID))
        current_hour = now.replace(minute=0, second=0, microsecond=0)

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

        if not hourly_totals:
            self._consumption_datetime = None
            self._is_current_hour = False
            self._data_available_until = None
            return None

        # Find the most recent hour with data
        all_hours.sort(reverse=True)
        self._data_available_until = all_hours[0]

        # Try current hour first, then fall back to most recent available hour
        if current_hour in hourly_totals:
            self._consumption_datetime = current_hour
            self._is_current_hour = True
            return round(hourly_totals[current_hour], 3)
        else:
            # Use the most recent available hour
            most_recent_hour = all_hours[0]
            self._consumption_datetime = most_recent_hour
            self._is_current_hour = False
            return round(hourly_totals[most_recent_hour], 3)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        attrs: dict[str, Any] = {}

        if self._consumption_datetime:
            attrs["consumption_datetime"] = self._consumption_datetime.isoformat()
        attrs["is_current_hour"] = self._is_current_hour

        if self._data_available_until:
            attrs["data_available_until"] = self._data_available_until.isoformat()

        return attrs


class OctopusEnergyESMonthlyConsumptionSensor(OctopusEnergyESSensor):
    """Monthly consumption sensor."""

    def __init__(self, coordinator: OctopusEnergyESCoordinator, description: SensorEntityDescription) -> None:
        """Initialize the monthly consumption sensor."""
        super().__init__(coordinator, description)
        self._consumption_month: tuple[int, int] | None = None  # (year, month)
        self._is_current_month: bool = False
        self._data_available_until: tuple[int, int] | None = None  # (year, month)

    @property
    def native_value(self) -> float | None:
        """Return monthly consumption (current month's if available, otherwise most recent available)."""
        data = self.coordinator.data
        consumption = data.get("consumption", [])

        if not consumption:
            self._consumption_month = None
            self._is_current_month = False
            self._data_available_until = None
            return None

        # Group consumption by month and calculate monthly totals
        monthly_totals: dict[tuple[int, int], float] = {}
        all_months: list[tuple[int, int]] = []

        now = datetime.now(ZoneInfo(TIMEZONE_MADRID))
        current_month = now.month
        current_year = now.year

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

        if not monthly_totals:
            self._consumption_month = None
            self._is_current_month = False
            self._data_available_until = None
            return None

        # Find the most recent month with data
        all_months.sort(reverse=True)
        self._data_available_until = all_months[0]

        # Try current month first, then fall back to most recent available month
        current_month_key = (current_year, current_month)
        if current_month_key in monthly_totals:
            self._consumption_month = current_month_key
            self._is_current_month = True
            return round(monthly_totals[current_month_key], 3)
        else:
            # Use the most recent available month
            most_recent_month = all_months[0]
            self._consumption_month = most_recent_month
            self._is_current_month = False
            return round(monthly_totals[most_recent_month], 3)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        attrs: dict[str, Any] = {}

        if self._consumption_month:
            year, month = self._consumption_month
            attrs["consumption_month"] = f"{year:04d}-{month:02d}"
        attrs["is_current_month"] = self._is_current_month

        if self._data_available_until:
            year, month = self._data_available_until
            attrs["data_available_until"] = f"{year:04d}-{month:02d}"

        return attrs


class OctopusEnergyESWeeklyConsumptionSensor(OctopusEnergyESSensor):
    """Weekly consumption sensor."""

    def __init__(self, coordinator: OctopusEnergyESCoordinator, description: SensorEntityDescription) -> None:
        """Initialize the weekly consumption sensor."""
        super().__init__(coordinator, description)
        self._consumption_week_start: date | None = None
        self._consumption_week_end: date | None = None
        self._is_current_week: bool = False
        self._data_available_until: date | None = None

    @property
    def native_value(self) -> float | None:
        """Return weekly consumption (current week's if available, otherwise most recent available 7-day period)."""
        data = self.coordinator.data
        consumption = data.get("consumption", [])

        if not consumption:
            self._consumption_week_start = None
            self._consumption_week_end = None
            self._is_current_week = False
            self._data_available_until = None
            return None

        now = datetime.now(ZoneInfo(TIMEZONE_MADRID))
        today = now.date()
        
        # Calculate current week (last 7 days from today)
        current_week_end = today
        current_week_start = current_week_end - timedelta(days=6)

        # Group consumption by date and calculate daily totals
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

        if not daily_totals:
            self._consumption_week_start = None
            self._consumption_week_end = None
            self._is_current_week = False
            self._data_available_until = None
            return None

        # Find the most recent date with data
        all_dates.sort(reverse=True)
        self._data_available_until = all_dates[0]

        # Try current week first
        current_week_total = 0.0
        has_current_week_data = False
        for check_date in (current_week_start + timedelta(days=i) for i in range(7)):
            if check_date in daily_totals:
                current_week_total += daily_totals[check_date]
                has_current_week_data = True

        if has_current_week_data and current_week_total > 0:
            self._consumption_week_start = current_week_start
            self._consumption_week_end = current_week_end
            self._is_current_week = True
            return round(current_week_total, 3)

        # Fall back to most recent 7-day period with data
        # Find the most recent date with data and sum 7 days ending on that date
        most_recent_date = all_dates[0]
        most_recent_week_end = most_recent_date
        most_recent_week_start = most_recent_week_end - timedelta(days=6)

        most_recent_week_total = 0.0
        for check_date in (most_recent_week_start + timedelta(days=i) for i in range(7)):
            if check_date in daily_totals:
                most_recent_week_total += daily_totals[check_date]

        if most_recent_week_total > 0:
            self._consumption_week_start = most_recent_week_start
            self._consumption_week_end = most_recent_week_end
            self._is_current_week = False
            return round(most_recent_week_total, 3)

        # No valid week found
        self._consumption_week_start = None
        self._consumption_week_end = None
        self._is_current_week = False
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        attrs: dict[str, Any] = {}

        if self._consumption_week_start:
            attrs["consumption_week_start"] = self._consumption_week_start.isoformat()
        if self._consumption_week_end:
            attrs["consumption_week_end"] = self._consumption_week_end.isoformat()
        attrs["is_current_week"] = self._is_current_week

        if self._data_available_until:
            attrs["data_available_until"] = self._data_available_until.isoformat()

        return attrs


class OctopusEnergyESYearlyConsumptionSensor(OctopusEnergyESSensor):
    """Yearly consumption sensor."""

    def __init__(self, coordinator: OctopusEnergyESCoordinator, description: SensorEntityDescription) -> None:
        """Initialize the yearly consumption sensor."""
        super().__init__(coordinator, description)
        self._consumption_year: int | None = None
        self._is_current_year: bool = False
        self._data_available_until: int | None = None

    @property
    def native_value(self) -> float | None:
        """Return yearly consumption (current year's if available, otherwise most recent available)."""
        data = self.coordinator.data
        consumption = data.get("consumption", [])

        if not consumption:
            self._consumption_year = None
            self._is_current_year = False
            self._data_available_until = None
            return None

        # Group consumption by year and calculate yearly totals
        yearly_totals: dict[int, float] = {}
        all_years: list[int] = []

        now = datetime.now(ZoneInfo(TIMEZONE_MADRID))
        current_year = now.year

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

        if not yearly_totals:
            self._consumption_year = None
            self._is_current_year = False
            self._data_available_until = None
            return None

        # Find the most recent year with data
        all_years.sort(reverse=True)
        self._data_available_until = all_years[0]

        # Try current year first, then fall back to most recent available year
        if current_year in yearly_totals:
            self._consumption_year = current_year
            self._is_current_year = True
            return round(yearly_totals[current_year], 3)
        else:
            # Use the most recent available year
            most_recent_year = all_years[0]
            self._consumption_year = most_recent_year
            self._is_current_year = False
            return round(yearly_totals[most_recent_year], 3)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        attrs: dict[str, Any] = {}

        if self._consumption_year:
            attrs["consumption_year"] = f"{self._consumption_year:04d}"
        attrs["is_current_year"] = self._is_current_year

        if self._data_available_until:
            attrs["data_available_until"] = f"{self._data_available_until:04d}"

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
        data = self.coordinator.data
        prices = data.get("today_prices", [])
        consumption = data.get("consumption", [])

        if not prices or not consumption:
            self._cost_date = None
            self._is_today = False
            self._data_available_until = None
            return None

        # Group consumption by date and calculate daily totals
        daily_totals: dict[date, float] = {}
        all_dates: list[date] = []
        
        now = datetime.now(ZoneInfo(TIMEZONE_MADRID))
        today = now.date()

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

        if not daily_totals:
            self._cost_date = None
            self._is_today = False
            self._data_available_until = None
            return None

        # Find the most recent date with data
        all_dates.sort(reverse=True)
        self._data_available_until = all_dates[0]

        # Try today first, then fall back to most recent available date
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
        """Calculate energy cost for a specific day using DailyCostSensor logic."""
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
        energy_cost = 0.0
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
            # Calculate daily total consumption
            daily_consumption = sum(hourly_consumption.values())
            
            # Get prices for the target date
            daily_prices: list[float] = []
            for price in prices:
                price_dt_madrid = _parse_datetime_to_madrid(price.get("start_time", ""))
                if price_dt_madrid and price_dt_madrid.date() == target_date:
                    daily_prices.append(price.get("price_per_kwh", 0))

            if daily_prices:
                # Calculate average price for the day
                avg_price = sum(daily_prices) / len(daily_prices)
                energy_cost = daily_consumption * avg_price

        return energy_cost

    @property
    def native_value(self) -> float | None:
        """Return estimated next invoice amount."""
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


class OctopusEnergyESCreditsSensor(OctopusEnergyESSensor):
    """Credits sensor (shows last month's credits as Octopus calculates them post factum)."""

    @property
    def native_value(self) -> float | None:
        """Return credits (last month's credits)."""
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

        return round(total_estimated_credits, 2) if total_estimated_credits > 0 else None

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

