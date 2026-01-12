# 🐙 Octopus Energy España - Home Assistant Integration

[![HACS Validation](https://img.shields.io/github/actions/workflow/status/bthos/ha-octopus-energy-es/validate.yml?branch=main&label=HACS&logo=github)](https://github.com/bthos/ha-octopus-energy-es/actions/workflows/validate.yml)

Home Assistant custom component for Octopus Energy España, providing electricity price sensors, consumption tracking, and billing data integration.

## 💝 Support the Developer

**Love this integration?** Help support its development by joining Octopus Energy España!

When you sign up using the button below, **you'll receive 50€ credit** on your second electricity bill, and **the integration developer will also receive 50€** - a win-win that helps keep this project maintained and improved! 🎉

<div align="center">

[![Join Octopus Energy España - Get 50€](https://img.shields.io/badge/Join%20Octopus%20Energy-Get%2050€%20Credit-FF6B35?style=for-the-badge&logo=octopusdeploy&logoColor=white)](https://share.octopusenergy.es/graceful-banana-618)

</div>

✨ **100% renewable energy** • 📊 **Transparent pricing** • ⭐ **4.8/5 customer rating** • 🔓 **No permanence**

*La energía de la buena se comparte* - Your support helps make this integration better for everyone! 🌟

<div align="center">

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=bthos&repository=ha-octopus-energy-es&category=integration)

</div>

## ✨ Features

### 📊 Multiple Tariff Support
Supports all Octopus Energy España tariff types:
- **⚡ Octopus Flexi**: Variable market price (0€/kWh admin cost)
- **🔒 Octopus Relax**: Fixed price 24/7
- **☀️ Octopus Solar**: Time-of-use tariff with P1/P2/P3 periods
- **🚗 Octopus Go**: EV tariff with optimized periods
- **🌞 SUN CLUB**: Daylight discount tariff (45% discount during sunny hours)

### 💰 Price Sensors
- Main price sensor with data array compatible with `price-timeline-card` and `ha_epex_spot` format
- Current, min, max price sensors
- Cheapest hour sensor
- Individual hour attributes (`price_00h`, `price_01h`, etc.)
- Separate `today` and `tomorrow` price arrays

### 📈 Consumption Tracking
- Daily, weekly, monthly, and yearly consumption sensors
- Daily cost calculation
- Hourly breakdown attributes on daily consumption sensor (`hour_00` through `hour_23`)
- Shows latest available data when current period data isn't yet processed

### 🧾 Billing Integration
- Last invoice sensor
- Billing period tracking
- Account information sensor with CUPS, address, and tariff details
- Credits sensor (shows last month's credits as Octopus calculates them postfactum)
- Estimated credits sensor (calculates future credits based on consumption during discount hours)

### 🔌 Data Sources
- **Octopus Energy API**: For consumption and billing data (requires credentials)
- **PVPC Hourly Pricing integration**: ([pvpc_hourly_pricing](https://www.home-assistant.io/integrations/pvpc_hourly_pricing/)) for market prices (required for market-based tariffs)

### 🔄 Tariff Comparison Services
- Compare multiple tariffs side-by-side
- Calculate costs based on your actual consumption patterns
- Visual breakdown by P1/P2/P3 periods
- Identify the most economical tariff
- Calculate potential savings
- Available via Home Assistant services

> **ℹ️ Note**: 
> - Octopus Energy España uses a GraphQL API at `https://octopusenergy.es/api/graphql/kraken`. The integration connects to this API for consumption, billing, and account data.
> - **PVPC Hourly Pricing integration is required only for market-based tariffs.** For fixed tariffs, you can configure rates manually without PVPC.
> - **Octopus Energy credentials (email/password) are required** to access consumption and billing data.
> - **For Lovelace card visualization**, install the separate [Octopus Energy España Consumption Card](https://github.com/bthos/ha-octopus-energy-es-card) plugin.

## 📦 Installation

### Prerequisites

**For market-based tariffs:**
- **⚠️ The [PVPC Hourly Pricing integration](https://www.home-assistant.io/integrations/pvpc_hourly_pricing/) must be configured first.**
  1. Go to **Settings → Devices & Services → Add Integration**
  2. Search for **"Spain electricity hourly pricing (PVPC)"** and configure it
  3. Note the sensor entity ID (default is `sensor.pvpc`)

**For all tariffs:**
- **Octopus Energy España account credentials (email and password) are required** to access consumption and billing data.

### 🎯 HACS (Recommended)

1. Open **HACS** in Home Assistant
2. Go to **Integrations**
3. Click the **three dots menu → Custom repositories**
4. Add this repository URL: `https://github.com/bthos/ha-octopus-energy-es`
5. Set category to **Integration**
6. Search for **"Octopus Energy España"** and install
7. **Restart Home Assistant**

### 📁 Manual Installation

1. Copy the `custom_components/octopus_energy_es` folder to your Home Assistant `custom_components` directory
2. **Restart Home Assistant**
3. Go to **Settings → Devices & Services → Add Integration**
4. Search for **"Octopus Energy España"**

## ⚙️ Configuration

The configuration flow guides you through setting up your tariff. You can choose between **automatic** (recommended) or **manual** configuration:

### Step 1: Octopus Energy Credentials (Required)

Enter your Octopus Energy España account credentials:
- **📧 Email**: Your Octopus Energy email address (required)
- **🔐 Password**: Your account password (required)

> **💡 Note**: Your account number will be automatically detected after authentication. If you have multiple accounts, you'll be able to select which one to use.

### Step 2: Tariff Configuration Mode

Choose how you want to configure your tariff:
- **🔄 Automatic** (Recommended): Fetch tariff information from Octopus Energy API. The integration will automatically detect your tariff type, rates, and configuration. Forms will only be shown for fields that couldn't be fetched from the API.
- **✏️ Manual**: Configure all tariff settings manually. Useful if automatic detection fails or you want to customize settings.

### Step 3: Tariff-Specific Configuration

Depending on your tariff type, you'll be asked to configure:
- **Market-based tariffs** (Flexi, Solar, Go): PVPC sensor selection
- **Fixed tariffs** (Relax): Manual rate entry
- **Time-of-use tariffs** (Solar, Go): Period definitions (P1/P2/P3)
- **Discount programs** (SUN CLUB): Discount hours and rates

## 🔄 Tariff Comparison Services

The integration provides services for comparing tariffs programmatically:

**Service: `octopus_energy_es.compare_tariffs`**
```yaml
service: octopus_energy_es.compare_tariffs
data:
  tariff_entry_ids:
    - "entry_id_1"
    - "entry_id_2"
  source_entry_id: "entry_id_1"  # Optional, defaults to first tariff
  period: "daily"  # "daily", "weekly", "monthly", "custom"
  start_date: "2024-01-01"  # Required for custom period
  end_date: "2024-01-31"  # Required for custom period
  power_kw: 5.5  # Optional, power value in kW
```

**Service: `octopus_energy_es.fetch_consumption`**
```yaml
service: octopus_energy_es.fetch_consumption
data:
  entry_id: "entry_id"
  start_date: "2024-01-01"  # Optional
  end_date: "2024-01-31"  # Optional
  granularity: "hourly"  # "hourly", "daily", "monthly"
  apply_tariffs:  # Optional, calculate costs for specified tariffs
    - "entry_id_1"
    - "entry_id_2"
```

## 📊 Sensors

### Price Sensors

- **`sensor.octopus_energy_es_price`**: Main price sensor with hourly data array
- **`sensor.octopus_energy_es_price_current`**: Current price
- **`sensor.octopus_energy_es_price_min`**: Minimum price for today
- **`sensor.octopus_energy_es_price_max`**: Maximum price for today
- **`sensor.octopus_energy_es_price_cheapest_hour`**: Cheapest hour sensor

### Consumption Sensors

- **`sensor.octopus_energy_es_daily_consumption`**: Daily consumption with hourly breakdown
- **`sensor.octopus_energy_es_weekly_consumption`**: Weekly consumption
- **`sensor.octopus_energy_es_monthly_consumption`**: Monthly consumption
- **`sensor.octopus_energy_es_yearly_consumption`**: Yearly consumption

### Billing Sensors

- **`sensor.octopus_energy_es_last_invoice`**: Last invoice information
- **`sensor.octopus_energy_es_account`**: Account information (CUPS, address, tariff)
- **`sensor.octopus_energy_es_credits`**: Last month's credits
- **`sensor.octopus_energy_es_estimated_credits`**: Estimated future credits

## 🔄 Data Updates

- **📅 Today's Prices**: Updated every hour
- **📅 Tomorrow's Prices**: Updated once per day (usually around 20:30 CET)
- **📊 Consumption Data**: Updated every 6 hours
- **🧾 Billing Data**: Updated daily

## 🔧 Options Flow

You can modify integration settings after initial setup:
1. Go to **Settings → Devices & Services**
2. Find **Octopus Energy España** integration
3. Click on the integration → **Options**
4. Modify settings as needed

## 🐛 Troubleshooting

### Price Sensors Not Updating

- Verify PVPC integration is configured and working
- Check Home Assistant logs for errors
- Ensure your tariff is market-based (Flexi, Solar, Go)

### Consumption Data Not Available

- Verify Octopus Energy credentials are correct
- Check that your account has consumption data available
- Review Home Assistant logs for API errors

### Configuration Issues

- For fixed pricing, ensure all required rates are entered correctly
- Verify that time-of-use periods cover all 24 hours for weekdays
- Check that discount hours are valid (0-23) if discount program is configured

## 📚 Dependencies

- **Octopus Energy España Account**: Required for consumption and billing data access.
- **PVPC Hourly Pricing Integration**: Required for market-based tariffs only. See [installation instructions](https://www.home-assistant.io/integrations/pvpc_hourly_pricing/).

## 🌍 Timezone Handling

All timestamps are handled in **Europe/Madrid** timezone (CET/CEST) with automatic DST handling.

## 🛡️ Error Handling

The integration includes robust error handling:
- Automatic retry logic for API failures
- Fallback to cached data when APIs are unavailable
- Graceful degradation if optional features (consumption, billing) are unavailable

## 🤝 Compatibility

- Compatible with `price-timeline-card` Lovelace card
- Compatible with `ha_epex_spot` format
- Works with ApexCharts and other visualization tools
- Supports Home Assistant 2023.1.0 and later
- Automatic tariff configuration via Octopus Energy GraphQL API
- Options flow for modifying configuration after initial setup

## 💬 Support

For issues, feature requests, or questions:
- 📝 Open an issue on [GitHub](https://github.com/bthos/ha-octopus-energy-es/issues)
- 🔍 Check existing issues for similar problems

## 📄 License

This project is licensed under the **MIT License**.
