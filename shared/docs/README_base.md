# Octopus Energy España

Home Assistant integration and Lovelace card for Octopus Energy España, providing electricity price sensors, consumption tracking, billing data integration, and visualization.

## 💝 Support the Developer

**Love this integration?** Help support its development by joining Octopus Energy España!

When you sign up using the button below, **you'll receive 50€ credit** on your second electricity bill, and **the integration developer will also receive 50€** - a win-win that helps keep this project maintained and improved! 🎉

<div align="center">

[![Join Octopus Energy España - Get 50€](https://img.shields.io/badge/Join%20Octopus%20Energy-Get%2050€%20Credit-FF6B35?style=for-the-badge&logo=octopusdeploy&logoColor=white)](https://share.octopusenergy.es/graceful-banana-618)

</div>

✨ **100% renewable energy** • 📊 **Transparent pricing** • ⭐ **4.8/5 customer rating** • 🔓 **No permanence**

*La energía de la buena se comparte* - Your support helps make this integration better for everyone! 🌟

## 📦 Components

This repository contains two HACS components:

### 🔌 Integration

[**Octopus Energy España Integration**](integration/) - Backend integration providing:
- Price sensors compatible with `price-timeline-card`
- Consumption and billing tracking
- Tariff comparison services
- Support for all Octopus Energy España tariff types

[Install Integration →](integration/)

### 📊 Plugin

[**Octopus Energy España Consumption Card**](plugin/) - Lovelace card providing:
- Consumption visualization for day/week/month periods
- Tariff comparison with cost breakdown
- Period breakdown (P1/P2/P3) visualization
- Cost analysis with detailed breakdown

[Install Plugin →](plugin/)

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

### 🔄 Tariff Comparison
- Compare multiple tariffs side-by-side
- Calculate costs based on your actual consumption patterns
- Visual breakdown by P1/P2/P3 periods
- Identify the most economical tariff
- Calculate potential savings
- Available via Lovelace card and Home Assistant services

## 🔌 Data Sources

- **Octopus Energy API**: For consumption and billing data (requires credentials)
- **PVPC Hourly Pricing integration**: ([pvpc_hourly_pricing](https://www.home-assistant.io/integrations/pvpc_hourly_pricing/)) for market prices (required for market-based tariffs)

> **ℹ️ Note**: 
> - Octopus Energy España uses a GraphQL API at `https://octopusenergy.es/api/graphql/kraken`. The integration connects to this API for consumption, billing, and account data.
> - **PVPC Hourly Pricing integration is required only for market-based tariffs.** For fixed tariffs, you can configure rates manually without PVPC.
> - **Octopus Energy credentials (email/password) are required** to access consumption and billing data.

## 💬 Support

For issues, feature requests, or questions:
- 📝 Open an issue on [GitHub](https://github.com/bthos/ha-octopus-energy-es/issues)
- 🔍 Check existing issues for similar problems

## 📄 License

This project is licensed under the **MIT License**.
