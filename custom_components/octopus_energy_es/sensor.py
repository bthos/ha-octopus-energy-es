"""Sensor entities for Octopus Energy España integration."""
from __future__ import annotations

import logging
from datetime import datetime
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

DAILY_COST_SENSOR_DESCRIPTION = SensorEntityDescription(
    key="daily_cost",
    name="Octopus Energy España Daily Cost",
    native_unit_of_measurement="€",
    state_class=SensorStateClass.TOTAL_INCREASING,
    icon="mdi:currency-eur",
)

CURRENT_BILL_SENSOR_DESCRIPTION = SensorEntityDescription(
    key="current_bill",
    name="Octopus Energy España Current Bill",
    native_unit_of_measurement="€",
    state_class=SensorStateClass.TOTAL_INCREASING,
    icon="mdi:receipt",
)

MONTHLY_BILL_SENSOR_DESCRIPTION = SensorEntityDescription(
    key="monthly_bill",
    name="Octopus Energy España Monthly Bill",
    native_unit_of_measurement="€",
    state_class=SensorStateClass.TOTAL_INCREASING,
    icon="mdi:receipt",
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
        OctopusEnergyESDailyCostSensor(coordinator, DAILY_COST_SENSOR_DESCRIPTION),
        OctopusEnergyESCurrentBillSensor(coordinator, CURRENT_BILL_SENSOR_DESCRIPTION),
        OctopusEnergyESMonthlyBillSensor(coordinator, MONTHLY_BILL_SENSOR_DESCRIPTION),
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
        prices = data.get("today_prices", [])

        # Format data for price-timeline-card compatibility
        price_data = [
            {
                ATTR_START_TIME: price["start_time"],
                ATTR_PRICE_PER_KWH: price["price_per_kwh"],
            }
            for price in prices
        ]

        return {
            ATTR_DATA: price_data,
            ATTR_UNIT_OF_MEASUREMENT: "€/kWh",
        }


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

    @property
    def native_value(self) -> float | None:
        """Return daily consumption."""
        data = self.coordinator.data
        consumption = data.get("consumption", [])

        if not consumption:
            return None

        # Sum consumption for today
        today = datetime.now(ZoneInfo(TIMEZONE_MADRID)).date()
        total = 0.0

        for item in consumption:
            # Parse consumption item (format may vary)
            if isinstance(item, dict):
                item_date_str = item.get("date") or item.get("start_time")
                if item_date_str:
                    try:
                        item_date = datetime.fromisoformat(item_date_str).date()
                        if item_date == today:
                            total += float(item.get("consumption", item.get("value", 0)))
                    except (ValueError, TypeError):
                        continue

        return round(total, 3) if total > 0 else None


class OctopusEnergyESHourlyConsumptionSensor(OctopusEnergyESSensor):
    """Hourly consumption sensor."""

    @property
    def native_value(self) -> float | None:
        """Return current hour consumption."""
        data = self.coordinator.data
        consumption = data.get("consumption", [])

        if not consumption:
            return None

        now = datetime.now(ZoneInfo(TIMEZONE_MADRID))
        current_hour = now.replace(minute=0, second=0, microsecond=0)

        for item in consumption:
            if isinstance(item, dict):
                item_time_str = item.get("start_time") or item.get("datetime")
                if item_time_str:
                    try:
                        item_time = datetime.fromisoformat(item_time_str)
                        if item_time.replace(minute=0, second=0, microsecond=0) == current_hour:
                            return float(item.get("consumption", item.get("value", 0)))
                    except (ValueError, TypeError):
                        continue

        return None


class OctopusEnergyESMonthlyConsumptionSensor(OctopusEnergyESSensor):
    """Monthly consumption sensor."""

    @property
    def native_value(self) -> float | None:
        """Return monthly consumption."""
        data = self.coordinator.data
        consumption = data.get("consumption", [])

        if not consumption:
            return None

        now = datetime.now(ZoneInfo(TIMEZONE_MADRID))
        current_month = now.month
        current_year = now.year

        total = 0.0

        for item in consumption:
            if isinstance(item, dict):
                item_date_str = item.get("date") or item.get("start_time")
                if item_date_str:
                    try:
                        item_date = datetime.fromisoformat(item_date_str)
                        if item_date.month == current_month and item_date.year == current_year:
                            total += float(item.get("consumption", item.get("value", 0)))
                    except (ValueError, TypeError):
                        continue

        return round(total, 3) if total > 0 else None


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
                item_date_str = item.get("date") or item.get("start_time")
                if item_date_str:
                    try:
                        item_date = datetime.fromisoformat(item_date_str).date()
                        if item_date == today:
                            item_time = datetime.fromisoformat(item_date_str)
                            hour = item_time.hour

                            # Find matching price
                            for price in prices:
                                price_time = datetime.fromisoformat(price["start_time"])
                                if price_time.hour == hour:
                                    consumption_value = float(
                                        item.get("consumption", item.get("value", 0))
                                    )
                                    total_cost += consumption_value * price["price_per_kwh"]
                                    break
                    except (ValueError, TypeError):
                        continue

        return round(total_cost, 2) if total_cost > 0 else None


class OctopusEnergyESCurrentBillSensor(OctopusEnergyESSensor):
    """Current bill sensor."""

    @property
    def native_value(self) -> float | None:
        """Return current bill amount."""
        data = self.coordinator.data
        billing = data.get("billing", {})

        if not billing:
            return None

        # Extract current bill from billing data
        return billing.get("current_bill") or billing.get("amount")


class OctopusEnergyESMonthlyBillSensor(OctopusEnergyESSensor):
    """Monthly bill sensor."""

    @property
    def native_value(self) -> float | None:
        """Return monthly bill amount."""
        data = self.coordinator.data
        billing = data.get("billing", {})

        if not billing:
            return None

        return billing.get("monthly_bill") or billing.get("month_amount")


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

