# PowerAnt API – Home Assistant Integration

[![Release](https://img.shields.io/github/v/release/MikaOOinonen/powerant-home-assistant?label=release)](https://github.com/MikaOOinonen/powerant-home-assistant/releases/latest)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![HACS](https://img.shields.io/badge/HACS-Custom-blue.svg)](https://github.com/MikaOOinonen/powerant-home-assistant)
[![ChatGPT](https://img.shields.io/badge/Built%20with-ChatGPT-10a37f)](https://chatgpt.com/)

A custom Home Assistant integration for PowerAnt smart energy control devices, using the official PowerAnt cloud API.

Monitor your PowerAnt devices, view electricity prices and calculated operating schedules, and manage supported device settings directly from Home Assistant.

> **Note:** The PowerAnt API is currently marked as Beta by the manufacturer. API functionality may change.

## Features

- Monitor device power state and current electricity price.
- View the current price period and next scheduled state change.
- View calculated operating schedules for today and tomorrow.
- View estimated electricity cost savings for today and tomorrow based on calculated operating schedules.
- Configure supported operating modes.
- Adjust cheapest operating hours, price triggers, and time slots.
- Select electricity price area and 15-minute or 60-minute price resolution.
- Enable or disable tariff adjustments.
- Configure hourly tariff values and transmission fees.
- View device information, including model and firmware version.
- Configure multiple PowerAnt devices independently.

Available entities and controls depend on the device and its configuration.

## Supported devices

The integration has been developed and tested with:

- PowerAnt Switch 63A
- PowerAnt Switch 32A

Other PowerAnt devices using the same API may work but have not yet been verified.

## Installation

### HACS (Custom repository)

1. Open **HACS** in Home Assistant.
2. Open the menu and select **Custom repositories**.
3. Add the repository URL:

   `https://github.com/MikaOOinonen/powerant-home-assistant`

4. Select **Integration** as the repository type.
5. Find and download **PowerAnt API**.
6. Restart Home Assistant.

### Manual installation

1. Download the latest release.
2. Copy the `custom_components/powerant_api` directory into your Home Assistant `custom_components` directory.
3. Restart Home Assistant.

## Updating

For HACS installations, update PowerAnt API through HACS and restart Home Assistant.

For manual installations, back up the existing `custom_components/powerant_api` directory and replace it with the version from the new release.

Updating from v0.1.0 to v0.2.0 does not require reconfiguring existing devices.

## Getting your PowerAnt API credentials

Each device requires its own **API key** and **Product key**.

### Step 1 – Generate your API key

1. Open [https://powerant.app/](https://powerant.app/) and log in to your PowerAnt account.
2. Navigate to **My Devices**.
3. Select the device you want to integrate with Home Assistant.
4. Open the **Settings** menu in the upper-right corner.
5. Select **Share device / API (Beta)**.
6. Generate a new API key.
7. **Copy and save the generated API key in a secure location.**

**Important:** Remember to save your API key when you generate it. Keep it private, as it grants access to your PowerAnt device.

### Step 2 – Get your Product key

1. Open the same device in the PowerAnt web application.
2. Select **Settings → Device info**.
3. Find the **Product key** field.
4. Copy the Product key.

### Step 3 – Configure Home Assistant

1. Open Home Assistant.
2. Navigate to **Settings → Devices & services**.
3. Select **Add integration**.
4. Search for **PowerAnt API**.
5. Enter the Product key and generated API key.
6. Complete the configuration.

Repeat these steps for each additional PowerAnt device.

## Operating modes

The integration supports the operating modes exposed by the PowerAnt API:

| Mode | Description |
|---|---|
| Cheapest time | Uses the configured cheapest operating hours |
| Cheapest time per time slot | Uses cheapest hours within configured time slots |
| Price trigger | Controls operation based on a price threshold |
| Cheapest time AND price trigger | Combines cheapest-time and price-trigger conditions |
| Cheapest time OR price trigger | Uses either condition |
| Reverse | Reverse operating logic |
| On/Off switch | Manual on/off control |

Actual behavior is determined by the PowerAnt service and device firmware.

### Calculated schedules

The schedules displayed in Home Assistant are calculated locally by the integration using electricity prices and device settings retrieved from the PowerAnt API.

These schedules are for monitoring and visualization purposes only. Home Assistant does not execute the calculated schedules or directly control the device based on them.

Actual device operation is managed by the PowerAnt service and device firmware. The calculated schedules may differ from actual operation if device settings, electricity prices, or service behavior change.

## Electricity prices and tariffs

The integration supports both 15-minute and 60-minute electricity price resolution, depending on the selected price area.

Hourly tariffs can be configured to adjust the effective electricity price.

The PowerAnt API also supports special tariff values:

- `ON` – Force operation on for the specified hour.
- `OFF` – Force operation off for the specified hour.
- Numeric value – Add the configured tariff to the electricity spot price.

These settings affect device control and should be used carefully.

## Example Dashboard

An example Home Assistant dashboard is available for visualizing PowerAnt schedules, electricity prices, device settings, and hourly tariffs.

The dashboard includes:
- Today's and tomorrow's calculated schedules.
- Power ON/OFF periods and current time highlighting.
- Device settings and hourly tariff configuration.
- An optional **Show tomorrow** toggle.

**Files:**
- [Dashboard YAML](examples/dashboard/powerant_dashboard.yaml)
- [Dashboard setup instructions](examples/dashboard/powerant_dashboard_README.md)

The example requires **ApexCharts Card** and **card-mod**, both available through HACS.

Follow the setup instructions to configure the dashboard for your own PowerAnt device.

## Architecture

The integration is organized into separate modules to make the code easier to maintain, test, and extend.

```text
custom_components/powerant_api/
├── __init__.py          # Integration setup
├── api.py               # PowerAnt cloud API client
├── binary_sensor.py     # Binary sensor entities
├── config_flow.py       # Configuration and authentication
├── const.py             # Constants
├── coordinator.py       # Data update coordination
├── device.py            # Device information and capabilities
├── entity.py            # Base entity definitions
├── helpers.py           # Shared helper functions
├── number.py            # Numeric configuration entities
├── prices.py            # Electricity price processing
├── savings.py           # Estimated savings calculations
├── schedule.py          # Operating schedule calculations
├── select.py            # Selection entities
├── sensor.py            # Sensor entities
├── switch.py            # Switch entities
├── manifest.json        # Integration metadata
├── strings.json         # UI strings
├── brand/
│   └── icon.png         # Integration icon
└── translations/
    └── en.json          # English translations
```

The main calculation logic is separated into `prices.py`, `schedule.py`, and `savings.py`, while `coordinator.py` manages data updates and provides the results to Home Assistant entities.

## Troubleshooting

If a device cannot be added or updated:

1. Verify that the Product key belongs to the correct device.
2. Check that the API key was generated for that device.
3. Verify that the device is accessible in the PowerAnt web application.
4. Check the Home Assistant logs for errors related to `powerant_api`.
5. Check whether the PowerAnt cloud service is available.

## Disclaimer

This is an independent community integration and is not an official PowerAnt product.

The integration communicates with the PowerAnt cloud service and requires an internet connection.

Users are responsible for verifying device operation and settings, especially when controlling electrical heating equipment.

## Issues and feedback

Report bugs or suggest improvements through [GitHub Issues](https://github.com/MikaOOinonen/powerant-home-assistant/issues).

When reporting an issue, include the Home Assistant version, integration version, device model, and relevant logs. Remove API keys and other sensitive information before sharing.

## Development & Credits

Developed and maintained by **Mika Oinonen**, with significant assistance from **OpenAI ChatGPT**.

ChatGPT has been used throughout the project for architecture design, Python development, refactoring, debugging, automated testing, documentation, and Home Assistant dashboard development.

This project is an example of how AI-assisted development can help turn an idea into a working integration, combining practical Home Assistant experience with AI-supported software development.

**Built with the assistance of ChatGPT by OpenAI.**

## License

See the `LICENSE` file for licensing information.
