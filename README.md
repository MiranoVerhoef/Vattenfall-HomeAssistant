# Vattenfall Dynamic Prices

Unofficial Home Assistant HACS integration for Vattenfall dynamic prices.

## What it adds

For both **Stroom** and **Gas**:
- Current price
- Peak 24 hours price
- Lowest 24 hours price

Options:
- Enable or disable **FlexPrijs** sensors
- Enable or disable **Beursprijs** sensors
- Set refresh interval

## Install

1. Add this repo to **HACS** as an **Integration**
2. Install **Vattenfall Dynamic Prices**
3. Restart Home Assistant
4. Go to **Settings → Devices & services → Add integration**
5. Search for **Vattenfall Dynamic Prices**

## Notes

- This integration uses Vattenfall's public dynamic pricing webpage to discover the current backend API details.
- Vattenfall can change the site or API at any time.
- If setup fails, check **Settings → System → Logs → Home Assistant Core → Show raw logs**

## Logging help

To make debugging easier, you can add this to `configuration.yaml`:

```yaml
logger:
  default: warning
  logs:
    custom_components.vattenfall_dynamic_prices: debug
```

## Repo

Documentation: https://github.com/MiranoVerhoef/Vattenfal-HomeAssistant
Issues: https://github.com/MiranoVerhoef/Vattenfal-HomeAssistant/issues
