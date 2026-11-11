# Vattenfall Dynamic Prices

Unofficial Home Assistant HACS integration for Vattenfall dynamic electricity and gas prices.

## Repository URL to copy

```text
https://github.com/MiranoVerhoef/Vattenfall-HomeAssistant
```

Add this repository in **HACS → Integrations → 3 dots → Custom repositories**  
Choose category: **Integration**

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

Forecast sensors now expose color-ready block data for the next 24 hours.

## Install

1. Open **HACS**
2. Open **Integrations**
3. Click the **3 dots** in the top right
4. Click **Custom repositories**
5. Paste this URL:

   `https://github.com/MiranoVerhoef/Vattenfall-HomeAssistant`

6. Set category to **Integration**
7. Click **Add**
8. Search for **Vattenfall Dynamic Prices**
9. Install it
10. Restart Home Assistant
11. Go to **Settings → Devices & services**
12. Add **Vattenfall Dynamic Prices**

## Upgrade from a commit-based HACS install

If HACS says **Up-to-date** but shows a commit SHA under **Installed version**
and a newer tagged release under **Latest version**, switch to a tagged release
once. This can happen when an integration publishes its first GitHub release.

1. Open **HACS → Vattenfall Dynamic Prices → ⋮ → Install another version**.
2. Select the latest tagged version and install it.
3. Restart Home Assistant and confirm **Installed version** shows the version number.

## Enable Beurs sensors

All-in sensors are enabled by default. To add Beurs sensors, go to
**Settings → Devices & services → Integrations → Vattenfall Dynamic Prices → Configure**,
enable **Beursprijs**, and save. Leave All-in enabled if you want both groups.

## 24-hour forecast card examples

Add either example as a **Markdown** card. If you renamed a forecast sensor,
replace the entity ID in the example with the one in your installation. Colors
show how each price compares with the other available prices in the forecast.

### All-in

```yaml
type: markdown
title: Stroom All-in forecast 24 uur
content: |
  {% set blocks = state_attr('sensor.stroom_all_in_forecast_24_uur', 'forecast_blocks') or [] %}
  {% if blocks %}
  {% set prices = blocks | map(attribute='value') | list %}
  {% set low = prices | min %}
  {% set spread = (prices | max) - low %}
  | Periode | Prijs (€/kWh) | Niveau |
  | --- | ---: | --- |
  {% for block in blocks -%}
  {% set relative = (block.value - low) / spread if spread else 0 -%}
  | {{ block.period }} | {{ block.display_value }} | {{ '🟢 Laag' if relative < 1/3 else '🟡 Gemiddeld' if relative < 2/3 else '🔴 Hoog' }} |
  {% endfor %}
  {% else %}
  Geen prijsverwachting beschikbaar.
  {% endif %}
```

### Beurs

```yaml
type: markdown
title: Stroom Beurs forecast 24 uur
content: |
  {% set blocks = state_attr('sensor.stroom_beurs_forecast_24_uur', 'forecast_blocks') or [] %}
  {% if blocks %}
  {% set prices = blocks | map(attribute='value') | list %}
  {% set low = prices | min %}
  {% set spread = (prices | max) - low %}
  | Periode | Prijs (€/kWh) | Niveau |
  | --- | ---: | --- |
  {% for block in blocks -%}
  {% set relative = (block.value - low) / spread if spread else 0 -%}
  | {{ block.period }} | {{ block.display_value }} | {{ '🟢 Laag' if relative < 1/3 else '🟡 Gemiddeld' if relative < 2/3 else '🔴 Hoog' }} |
  {% endfor %}
  {% else %}
  Geen prijsverwachting beschikbaar.
  {% endif %}
```

## Troubleshooting

If setup reports that it could not discover the pricing API, include the full
discovery error when reporting the issue. It shows how many scripts were read
and whether the API URL and subscription key were found. Enable debug logging
for the integration to see HTTP status codes for failed script requests.

## Notes

- The forecast includes tariff blocks that overlap the next 24 elapsed hours,
  starting with the active block when available. Block timestamps retain their
  published boundaries.
- Forecast sensors expose:
  - `forecast_blocks`
  - `forecast_lines`
  - `forecast_text`
  - `forecast_count` (number of tariff blocks)
  - `forecast_available_hours` (hours covered by available prices within the window)
- `forecast_blocks` includes:
  - `period`
  - `display_value`
  - `price_label`
  - `color`
  - `text_color`
  - `is_current`

## 2.0.0

- Added color-coded 24-hour forecast blocks
- Forecast sensors now expose `forecast_blocks`
- Added ready-to-use block card examples to the README

## 2.0.1

- Forecast sensor state now shows the active/current block, for example `17:00-18:00 0,35`, instead of `24 blokken`.
