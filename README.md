# Vattenfall Dynamic Prices for Home Assistant

Unofficial **HACS-only** Home Assistant integration for Vattenfall NL dynamic prices.

This integration fetches the public Vattenfall dynamic pricing data directly inside Home Assistant, so there is **no separate Docker container** to run.

## What it adds

For both **Stroom** and **Gas**:

- Current price
- Peak price for the next 24 hours
- Lowest price for the next 24 hours

You can enable or disable:

- **FlexPrijs** sensors
- **Beursprijs** sensors

## Install with HACS

1. Upload this repo to GitHub.
2. In Home Assistant go to **HACS → Integrations → Custom repositories**.
3. Add your GitHub repo as category **Integration**.
4. Install **Vattenfall Dynamic Prices**.
5. Restart Home Assistant.
6. Go to **Settings → Devices & services → Add integration**.
7. Search for **Vattenfall Dynamic Prices** and complete setup.

## Notes

- Electricity prices are hourly.
- Gas prices are daily, and Vattenfall states the gas day runs from **06:00 to 06:00**.
- The integration uses the public Vattenfall dynamic contract page to discover the current backend API and then reads the tariff data from there.
- This is an unofficial integration. Vattenfall can change the page or API at any time.

## Options

After setup, open the integration and use **Configure** to change:

- Refresh interval
- Enable FlexPrijs sensors
- Enable Beursprijs sensors
