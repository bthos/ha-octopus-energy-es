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

> **ℹ️ Note**: 
> - Octopus Energy España uses a GraphQL API at `https://octopusenergy.es/api/graphql/kraken`. The integration connects to this API for consumption, billing, and account data.
> - **PVPC Hourly Pricing integration is required only for market-based tariffs.** For fixed tariffs, you can configure rates manually without PVPC.
> - **Octopus Energy credentials (email/password) are required** to access consumption and billing data.

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
4. Add this repository URL
5. Search for **"Octopus Energy España"** and install
6. **Restart Home Assistant**

### 📁 Manual Installation

1. Copy the `custom_components/octopus_energy_es` folder to your Home Assistant `custom_components` directory
2. **Restart Home Assistant**
3. Go to **Settings → Devices & Services → Add Integration**
4. Search for **"Octopus Energy España"**

## ⚙️ Configuration

The configuration flow guides you through setting up your tariff using a category-based approach:

### Step 1: Octopus Energy Credentials (Required)

Enter your Octopus Energy España account credentials:
- **📧 Email**: Your Octopus Energy email address (required)
- **🔐 Password**: Your account password (required)

> **💡 Note**: Your account number will be automatically detected after authentication. If you have multiple accounts, you'll be able to select which one to use.

### Step 2: Pricing Model

Choose your pricing model:
- **📈 Market**: Prices vary based on the electricity market (requires PVPC sensor)
- **🔒 Fixed**: Fixed price per kWh regardless of market fluctuations

### Step 3: Time Structure (Fixed pricing only)

If you selected Fixed pricing, choose your time structure:
- **⚡ Single Rate**: Same price throughout the day
- **⏰ Time-of-Use**: Different prices for different periods (P1/P2/P3)

### Step 4: Energy Rates Configuration

**For Market pricing:**
- No rates needed (uses market prices from PVPC sensor)

**For Fixed pricing:**
- **Single Rate**: Enter your fixed rate in €/kWh
- **Time-of-Use**: Enter rates for each period:
  - **P1 Rate**: Peak period rate (€/kWh)
  - **P2 Rate**: Flat period rate (€/kWh)
  - **P3 Rate**: Base period rate (€/kWh)
  - **Management Fee**: Monthly management fee (€/month)

**Default time-of-use periods (weekdays):**
- **P1 (Peak)**: 11:00-14:00 & 19:00-22:00
- **P2 (Flat)**: 09:00-10:00, 15:00-18:00, 23:00
- **P3 (Base)**: 00:00-08:00
- **Weekends/Holidays**: All hours are P3 (Base)

### Step 5: Power Rates (Optional)

Configure power (potencia) rates:
- **Power P1 Rate**: Peak period power rate (€/kW/day)
- **Power P2 Rate**: Base period power rate (€/kW/day)

### Step 6: Solar Features (Optional)

If you have solar panels:
- **Solar Surplus Rate**: Compensation rate for surplus energy (€/kWh)

### Step 7: Discount Programs (Optional)

Configure discount hours:
- **Discount Start Hour**: Start hour for discount period (0-23)
- **Discount End Hour**: End hour for discount period (0-23)
- **Discount Percentage**: Discount percentage (0-100%)

### Step 8: PVPC Sensor Selection (Market pricing only)

If you selected Market pricing, select the PVPC Hourly Pricing sensor:
- **Default**: `sensor.pvpc` (if you haven't changed the sensor name)
- **Custom**: Enter your custom PVPC sensor entity ID if you renamed it

> **💡 Note**: Fixed pricing tariffs skip this step as they don't require market price data.

## 📊 Sensors

### 💰 Price Sensors

- `sensor.octopus_energy_es_price`: Main price sensor with average daily price and data array for price-timeline-card
  - **Attributes**: `data` (all prices), `today`, `tomorrow`, `price_00h` through `price_23h`
- `sensor.octopus_energy_es_current_price`: Current hour price
- `sensor.octopus_energy_es_min_price`: Minimum price for today
- `sensor.octopus_energy_es_max_price`: Maximum price for today
- `sensor.octopus_energy_es_cheapest_hour`: Cheapest hour of the day

### 📈 Consumption Sensors

- `sensor.octopus_energy_es_daily_consumption`: Daily consumption in kWh (shows latest available if today's data isn't processed yet)
  - **Attributes**: `hour_00` through `hour_23` (hourly breakdown for the selected day)
- `sensor.octopus_energy_es_weekly_consumption`: Weekly consumption in kWh (updates daily)
  - **Attributes**: `monday`, `tuesday`, `wednesday`, `thursday`, `friday`, `saturday`, `sunday` (daily breakdown)
- `sensor.octopus_energy_es_monthly_consumption`: Monthly consumption in kWh (updates weekly)
  - **Attributes**: `week_1`, `week_2`, `week_3`, `week_4`, `week_5` (weekly breakdown)
- `sensor.octopus_energy_es_yearly_consumption`: Yearly consumption in kWh (updates monthly)
  - **Attributes**: `january`, `february`, `march`, etc. (monthly breakdown)
- `sensor.octopus_energy_es_daily_cost`: Daily cost in € (calculated from consumption and prices)

### 🧾 Billing Sensors

- `sensor.octopus_energy_es_last_invoice`: Last invoice amount in €
- `sensor.octopus_energy_es_billing_period`: Current billing period date range

### 💰 Credits Sensors

- `sensor.octopus_energy_es_credits`: Credits from Octopus Energy (shows last month's credits as Octopus calculates them postfactum)
  - **Attributes**: Breakdown by reason code (e.g., SUN_CLUB, SUN_CLUB_POWER_UP)
- `sensor.octopus_energy_es_credits_estimated`: Estimated credits for current month based on consumption during discount hours
  - **Attributes**: Discount hours and discount percentage
  - **Note**: Only available if discount program is configured

### 👤 Account Sensor

- `sensor.octopus_energy_es_account`: Account information
  - **State**: Account ID
  - **Attributes**: `name`, `email`, `mobile`, `address`, `tariff`, `cups`

## 🎨 Usage with price-timeline-card

The main price sensor (`sensor.octopus_energy_es_price`) is compatible with the `price-timeline-card` Lovelace card:

```yaml
type: custom:price-timeline-card
entity: sensor.octopus_energy_es_price
```

The sensor provides data in the required format:
- `attributes.data`: Array of price objects with `start_time` (ISO 8601) and `price_per_kwh` (float)
- `attributes.today`: Today's prices only
- `attributes.tomorrow`: Tomorrow's prices only
- `attributes.price_00h` through `attributes.price_23h`: Individual hour prices

## 🔄 Data Updates

- **📅 Today's Prices**: Updated every hour
- **📅 Tomorrow's Prices**: Updated daily at 14:00 CET (when Spanish market publishes)
- **📈 Consumption Data**: Updated daily (Octopus Energy provides data for past dates only)
- **🧾 Billing Data**: Updated daily
- **💰 Credits Data**: Updated daily
- **👤 Account Data**: Updated daily

## 🔧 Troubleshooting

### 🔐 Authentication Errors

**Error**: `Invalid Octopus Energy credentials` or connection errors

**Solution**: 
- Verify your email and password are correct
- Check that your account is active
- The integration uses the GraphQL API at `https://octopusenergy.es/api/graphql/kraken` (also functions at `https://api.oees-kraken.energy/v1/graphql/`)

### 💰 Prices Not Updating (Market tariffs only)

- Ensure the PVPC Hourly Pricing integration is configured and working
- Verify the PVPC sensor entity ID is correct (default: `sensor.pvpc`)
- Check that the PVPC sensor has price data available
- Check Home Assistant logs for API errors
- ⏰ Spanish market publishes tomorrow's prices at 14:00 CET - prices may not be available before that time
- **Note**: Fixed pricing tariffs don't require PVPC sensor

### 📈 Consumption Data Not Available

- Verify your Octopus Energy credentials are correct
- Check that your account number was detected correctly
- Ensure your account has consumption data available
- ⏰ Consumption data may take some time to appear after initial setup

### 🔒 Configuration Issues

- For fixed pricing, ensure all required rates are entered correctly
- Verify that time-of-use periods cover all 24 hours for weekdays
- Check that discount hours are valid (0-23) if discount program is configured
- Ensure power rates are configured if you want power cost calculations

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

## 💬 Support

For issues, feature requests, or questions:
- 📝 Open an issue on [GitHub](https://github.com/bthos/ha-octopus-energy-es/issues)
- 🔍 Check existing issues for similar problems

## 📄 License

This project is licensed under the **MIT License**.

## 🙏 Acknowledgments

- Based on the Spanish electricity market integration plan
- Uses [PVPC Hourly Pricing integration](https://www.home-assistant.io/integrations/pvpc_hourly_pricing/) for market data from Red Eléctrica de España
