# Octopus Energy España - Home Assistant Integration

Home Assistant custom component for Octopus Energy Spain, providing electricity price sensors, consumption tracking, and billing data integration.

## Features

- **Multiple Tariff Support**: Supports all Octopus Energy Spain tariff types:
  - **Octopus Flexi**: Variable market price (0€/kWh admin cost)
  - **Octopus Relax**: Fixed price 24/7
  - **Octopus Solar**: Time-of-use tariff with P1/P2/P3 periods
  - **Octopus Go**: EV tariff with optimized periods
  - **SUN CLUB**: Daylight discount tariff (45% discount during sunny hours)

- **Price Sensors**: 
  - Main price sensor with data array compatible with `price-timeline-card`
  - Current, min, max price sensors
  - Cheapest hour sensor

- **Consumption Tracking**:
  - Daily, hourly, and monthly consumption sensors
  - Daily cost calculation

- **Billing Integration**:
  - Current bill, monthly bill, and last invoice sensors
  - Billing period tracking

- **Data Sources**:
  - Primary: PVPC Hourly Pricing integration ([pvpc_hourly_pricing](https://www.home-assistant.io/integrations/pvpc_hourly_pricing/)) for market prices
  - Fallback: OMIE API for wholesale market prices
  - Octopus Energy API for consumption and billing data (if available)
  - Web scraping fallback for fixed tariff rates

**Note**: 
- Octopus Energy Spain uses a GraphQL API at `https://api.oees-kraken.energy/v1/graphql/`. The integration connects to this API for billing and account data.
- **This integration requires the [PVPC Hourly Pricing integration](https://www.home-assistant.io/integrations/pvpc_hourly_pricing/) to be configured first.** The PVPC integration provides market price data that this integration uses to calculate tariff-specific prices.

## Installation

### Prerequisites

**This integration requires the [PVPC Hourly Pricing integration](https://www.home-assistant.io/integrations/pvpc_hourly_pricing/) to be configured first.**

1. Go to Settings → Devices & Services → Add Integration
2. Search for "Spain electricity hourly pricing (PVPC)" and configure it
3. Note the sensor entity ID (default is `sensor.pvpc`)

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Go to Integrations
3. Click the three dots menu → Custom repositories
4. Add this repository URL
5. Search for "Octopus Energy Spain" and install
6. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/octopus_energy_es` folder to your Home Assistant `custom_components` directory
2. Restart Home Assistant
3. Go to Settings → Devices & Services → Add Integration
4. Search for "Octopus Energy Spain"

## Configuration

### Step 1: Select Tariff Type

Choose your Octopus Energy Spain tariff:
- **Flexi**: Variable market price (no additional configuration needed)
- **Relax**: Fixed price tariff
- **Solar**: Time-of-use tariff with periods
- **Go**: EV tariff
- **SUN CLUB**: Daylight discount tariff

### Step 2: Octopus Energy Credentials

Enter your Octopus Energy Spain account credentials:
- **Email**: Your Octopus Energy email address
- **Password**: Your account password

**Note**: Your account number will be automatically detected after authentication. If you have multiple accounts, you'll be able to select which one to use in the next step.

### Step 3: Tariff-Specific Configuration

#### Flexi
No additional configuration required (uses market price directly).

#### Relax
- **Fixed Rate**: Enter your fixed rate in €/kWh

#### Solar
- **P1 Rate**: Peak period rate (€/kWh)
- **P2 Rate**: Standard period rate (€/kWh)
- **P3 Rate**: Valley period rate (€/kWh)
- **Solar Surplus Rate**: Compensation rate for solar surplus (default: 0.04 €/kWh)

Default periods:
- **P1 (Peak)**: 10:00-14:00 & 18:00-22:00
- **P2 (Standard)**: 08:00-10:00 & 14:00-18:00 & 22:00-00:00
- **P3 (Valley)**: 00:00-08:00

#### Go
- **P1 Rate**: Peak period rate (€/kWh)
- **P2 Rate**: Standard period rate (€/kWh)
- **P3 Rate**: Valley period rate (€/kWh)

Periods are similar to Solar but optimized for EV charging.

#### SUN CLUB
- **Daylight Start**: Start hour for daylight discount (default: 12)
- **Daylight End**: End hour for daylight discount (default: 18)
- **Discount Percentage**: Discount percentage (default: 0.45 = 45%)

### Step 4: PVPC Sensor Selection

Select the PVPC Hourly Pricing sensor to use for market price data:
- **Default**: `sensor.pvpc` (if you haven't changed the sensor name)
- **Custom**: Enter your custom PVPC sensor entity ID if you renamed it

The integration will read price data from this sensor and calculate tariff-specific prices based on your selected tariff type.

## Sensors

### Price Sensors

- `sensor.octopus_energy_es_price`: Main price sensor with average daily price and data array for price-timeline-card
- `sensor.octopus_energy_es_current_price`: Current hour price
- `sensor.octopus_energy_es_min_price`: Minimum price for today
- `sensor.octopus_energy_es_max_price`: Maximum price for today
- `sensor.octopus_energy_es_cheapest_hour`: Cheapest hour of the day

### Consumption Sensors

- `sensor.octopus_energy_es_daily_consumption`: Daily consumption in kWh
- `sensor.octopus_energy_es_hourly_consumption`: Current hour consumption in kWh
- `sensor.octopus_energy_es_monthly_consumption`: Monthly consumption in kWh
- `sensor.octopus_energy_es_daily_cost`: Daily cost in €

### Billing Sensors

- `sensor.octopus_energy_es_current_bill`: Current bill amount in €
- `sensor.octopus_energy_es_monthly_bill`: Monthly bill amount in €
- `sensor.octopus_energy_es_last_invoice`: Last invoice amount in €
- `sensor.octopus_energy_es_billing_period`: Current billing period date range

## Usage with price-timeline-card

The main price sensor (`sensor.octopus_energy_es_price`) is compatible with the `price-timeline-card` Lovelace card:

```yaml
type: custom:price-timeline-card
entity: sensor.octopus_energy_es_price
```

The sensor provides data in the required format:
- `attributes.data`: Array of price objects with `start_time` (ISO 8601) and `price_per_kwh` (float)

## Data Updates

- **Today's Prices**: Updated every hour
- **Tomorrow's Prices**: Updated daily at 14:00 CET (when Spanish market publishes)
- **Consumption Data**: Updated every 15 minutes (if available)
- **Billing Data**: Updated daily

## Troubleshooting

### Authentication Errors

**Error**: `Invalid Octopus Energy credentials` or connection errors

**Solution**: 
- Verify your email and password are correct
- Check that your account is active
- The integration uses the GraphQL API at `https://api.oees-kraken.energy/v1/graphql/`
- If you see connection errors, check your internet connection and firewall settings

### Prices Not Updating

- Ensure the PVPC Hourly Pricing integration is configured and working
- Verify the PVPC sensor entity ID is correct (default: `sensor.pvpc`)
- Check that the PVPC sensor has price data available
- Verify your internet connection
- Check Home Assistant logs for API errors
- Spanish market publishes tomorrow's prices at 14:00 CET - prices may not be available before that time

### Consumption Data Not Available

- Verify your Octopus Energy credentials are correct
- Check that your account number was detected correctly
- Ensure your account has consumption data available
- Consumption data may take some time to appear after initial setup

### Authentication Errors

- Verify your email and password are correct
- Check that your account is active
- Try removing and re-adding the integration

### Tariff Rates Not Found

- For fixed tariffs (Relax, Solar, Go), rates can be entered manually
- The integration will attempt to scrape rates from the Octopus Energy website as a fallback
- If scraping fails, manual entry is required

## Dependencies

- **PVPC Hourly Pricing Integration**: Required for market price data. See [installation instructions](https://www.home-assistant.io/integrations/pvpc_hourly_pricing/).

## API Rate Limits

- PVPC Integration: Uses the official PVPC integration which handles rate limits
- Octopus Energy API: Standard rate limits apply
- Web scraping: Limited to avoid overloading servers (cached for 1 week)

## Timezone Handling

All timestamps are handled in Europe/Madrid timezone (CET/CEST) with automatic DST handling.

## Error Handling

The integration includes robust error handling:
- Automatic retry logic for API failures
- Fallback to cached data when APIs are unavailable
- Fallback from PVPC sensor to OMIE API for market prices
- Graceful degradation if optional features (consumption, billing) are unavailable

## Support

For issues, feature requests, or questions:
- Open an issue on GitHub
- Check existing issues for similar problems

## License

This project is licensed under the MIT License.

## Acknowledgments

- Based on the Spanish electricity market integration plan
- Uses [PVPC Hourly Pricing integration](https://www.home-assistant.io/integrations/pvpc_hourly_pricing/) for market data from Red Eléctrica de España
