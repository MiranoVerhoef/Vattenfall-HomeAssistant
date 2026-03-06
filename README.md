# Vattenfall Dynamic Prices 1.2.0

Unofficial Home Assistant HACS integration for Vattenfall dynamic electricity and gas prices.

## Features

Creates sensors for:

- Stroom All-in huidig
- Stroom All-in piek 24 uur
- Stroom All-in laagste 24 uur
- Stroom All-in forecast 24 uur
- Stroom Beurs huidig
- Stroom Beurs piek 24 uur
- Stroom Beurs laagste 24 uur
- Stroom Beurs forecast 24 uur
- Gas All-in huidig
- Gas Beurs huidig

Options:

- Enable All-in / FlexPrijs sensors
- Enable Beursprijs sensors
- Set refresh interval

## Install

1. Add this repository to HACS as **Integration**
2. Install it
3. Restart Home Assistant
4. Go to **Settings → Devices & services**
5. Add **Vattenfall Dynamic Prices**

## Notes

This integration depends on Vattenfall's public website/API structure and can break if they change it.

## 1.2.0

- Added bundled brand icon/logo assets for Home Assistant 2026.3+.
