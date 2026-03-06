# Vattenfall Dynamic Prices

Unofficial Home Assistant HACS integration for Vattenfall dynamic electricity and gas prices.

## Features

Creates sensors for:

- Stroom current price
- Stroom peak 24h
- Stroom lowest 24h
- Gas current price
- Gas peak 24h
- Gas lowest 24h

Options:

- Enable FlexPrijs sensors
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
