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

SUN_CLUB_TOTAL_SAVINGS_SENSOR_DESCRIPTION = SensorEntityDescription(
    key="sun_club_total_savings",
    name="Octopus Energy España SUN CLUB Total Savings",
    native_unit_of_measurement="€",
    state_class=SensorStateClass.TOTAL_INCREASING,
    icon="mdi:currency-eur",
)

SUN_CLUB_CURRENT_MONTH_SAVINGS_SENSOR_DESCRIPTION = SensorEntityDescription(
    key="sun_club_current_month_savings",
    name="Octopus Energy España SUN CLUB Current Month Savings",
    native_unit_of_measurement="€",
    state_class=SensorStateClass.TOTAL_INCREASING,
    icon="mdi:currency-eur",
)

SUN_CLUB_LAST_MONTH_SAVINGS_SENSOR_DESCRIPTION = SensorEntityDescription(
    key="sun_club_last_month_savings",
    name="Octopus Energy España SUN CLUB Last Month Savings",
    native_unit_of_measurement="€",
    state_class=SensorStateClass.TOTAL_INCREASING,
    icon="mdi:currency-eur",
)

SUN_CLUB_REGULAR_SAVINGS_SENSOR_DESCRIPTION = SensorEntityDescription(
    key="sun_club_regular_savings",
    name="Octopus Energy España SUN CLUB Regular Savings",
    native_unit_of_measurement="€",
    state_class=SensorStateClass.TOTAL_INCREASING,
    icon="mdi:currency-eur",
)

SUN_CLUB_POWER_UP_SAVINGS_SENSOR_DESCRIPTION = SensorEntityDescription(
    key="sun_club_power_up_savings",
    name="Octopus Energy España SUN CLUB Power-Up Savings",
    native_unit_of_measurement="€",
    state_class=SensorStateClass.TOTAL_INCREASING,
    icon="mdi:currency-eur",
)

ACCOUNT_SENSOR_DESCRIPTION = SensorEntityDescription(
    key="account",
    name="Octopus Energy España Account",
    icon="mdi:account",
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
        OctopusEnergyESBillingPeriodSensor(coordinator, BILLING_PERIOD_SENSOR_DESCRIPTION),
        OctopusEnergyESSunClubTotalSavingsSensor(
            coordinator, SUN_CLUB_TOTAL_SAVINGS_SENSOR_DESCRIPTION
        ),
        OctopusEnergyESSunClubCurrentMonthSavingsSensor(
            coordinator, SUN_CLUB_CURRENT_MONTH_SAVINGS_SENSOR_DESCRIPTION
        ),
        OctopusEnergyESSunClubLastMonthSavingsSensor(
            coordinator, SUN_CLUB_LAST_MONTH_SAVINGS_SENSOR_DESCRIPTION
        ),
        OctopusEnergyESSunClubRegularSavingsSensor(
            coordinator, SUN_CLUB_REGULAR_SAVINGS_SENSOR_DESCRIPTION
        ),
        OctopusEnergyESSunClubPowerUpSavingsSensor(
            coordinator, SUN_CLUB_POWER_UP_SAVINGS_SENSOR_DESCRIPTION
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
            "manufacturer": "Octopus Energy",
            "model": coordinator._entry.data.get("tariff_type", "Unknown"),
        }

    def _get_historical_data_attributes(self) -> dict[str, Any]:
        """Get historical data availability attributes."""
        attrs: dict[str, Any] = {}
        
        # Get historical data range from coordinator
        historical_range = self.coordinator.get_historical_data_range()
        if historical_range:
            attrs["historical_data_start_date"] = historical_range["start_date"]
            attrs["historical_data_end_date"] = historical_range["end_date"]
            attrs["historical_data_count"] = historical_range["count"]
        
        # Get total data count (recent + historical)
        data = self.coordinator.data
        consumption = data.get("consumption", [])
        if consumption:
            attrs["total_data_count"] = len(consumption)
        
        return attrs


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
        
        # Add historical data attributes
        attrs.update(self._get_historical_data_attributes())
        
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

        # Add historical data attributes
        attrs.update(self._get_historical_data_attributes())

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

        # Add historical data attributes
        attrs.update(self._get_historical_data_attributes())

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

        # Add historical data attributes
        attrs.update(self._get_historical_data_attributes())

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

        # Add historical data attributes
        attrs.update(self._get_historical_data_attributes())

        return attrs


class OctopusEnergyESDailyCostSensor(OctopusEnergyESSensor):
    """Daily cost sensor."""

    @property
    def native_value(self) -> float | None:
        """Return daily cost."""
        data = self.coordinator.data
        prices = data.get("today_prices", [])
        consumption = data.get("consumption", [])

        if not prices or not consumption:
            return None

        today = datetime.now(ZoneInfo(TIMEZONE_MADRID)).date()
        total_cost = 0.0

        # Match consumption with prices
        for item in consumption:
            if isinstance(item, dict):
                item_time_str = item.get("start_time") or item.get("date")
                if item_time_str:
                    item_dt_madrid = _parse_datetime_to_madrid(item_time_str)
                    if item_dt_madrid and item_dt_madrid.date() == today:
                        hour = item_dt_madrid.hour
                        # Find matching price
                        for price in prices:
                            price_dt_madrid = _parse_datetime_to_madrid(price["start_time"])
                            if price_dt_madrid and price_dt_madrid.hour == hour:
                                consumption_value = float(
                                    item.get("consumption", item.get("value", 0))
                                )
                                total_cost += consumption_value * price["price_per_kwh"]
                                break

        return round(total_cost, 2) if total_cost > 0 else None


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


class OctopusEnergyESSunClubTotalSavingsSensor(OctopusEnergyESSensor):
    """SUN CLUB total savings sensor."""

    @property
    def native_value(self) -> float | None:
        """Return total SUN CLUB savings."""
        data = self.coordinator.data
        credits = data.get("credits", {})

        if not credits:
            return None

        totals = credits.get("totals", {})
        return totals.get("total")


class OctopusEnergyESSunClubCurrentMonthSavingsSensor(OctopusEnergyESSensor):
    """SUN CLUB current month savings sensor."""

    @property
    def native_value(self) -> float | None:
        """Return current month SUN CLUB savings."""
        data = self.coordinator.data
        credits = data.get("credits", {})

        if not credits:
            return None

        totals = credits.get("totals", {})
        return totals.get("current_month")


class OctopusEnergyESSunClubLastMonthSavingsSensor(OctopusEnergyESSensor):
    """SUN CLUB last month savings sensor."""

    @property
    def native_value(self) -> float | None:
        """Return last month SUN CLUB savings."""
        data = self.coordinator.data
        credits = data.get("credits", {})

        if not credits:
            return None

        totals = credits.get("totals", {})
        return totals.get("last_month")


class OctopusEnergyESSunClubRegularSavingsSensor(OctopusEnergyESSensor):
    """SUN CLUB regular savings sensor."""

    @property
    def native_value(self) -> float | None:
        """Return regular SUN CLUB savings (daylight hours discount)."""
        data = self.coordinator.data
        credits = data.get("credits", {})

        if not credits:
            return None

        totals = credits.get("totals", {})
        return totals.get("sun_club")


class OctopusEnergyESSunClubPowerUpSavingsSensor(OctopusEnergyESSensor):
    """SUN CLUB power-up savings sensor."""

    @property
    def native_value(self) -> float | None:
        """Return SUN CLUB power-up savings."""
        data = self.coordinator.data
        credits = data.get("credits", {})

        if not credits:
            return None

        totals = credits.get("totals", {})
        return totals.get("sun_club_power_up")


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

