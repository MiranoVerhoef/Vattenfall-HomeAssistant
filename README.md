# Vattenfall Dynamic Prices

Unofficial Home Assistant HACS integration for Vattenfall dynamic electricity and gas prices.

## Repository URL to copy

```text
https://github.com/MiranoVerhoef/Vattenfal-HomeAssistant
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

   `https://github.com/MiranoVerhoef/Vattenfal-HomeAssistant`

6. Set category to **Integration**
7. Click **Add**
8. Search for **Vattenfall Dynamic Prices**
9. Install it
10. Restart Home Assistant
11. Go to **Settings → Devices & services**
12. Add **Vattenfall Dynamic Prices**

## 24-hour block card example

This example renders blocks like:

- `17:00-18:00`
- `18:00-19:00`
- `19:00-20:00`

with the matching price in each block and a color based on the relative price level.

### All-in blocks

```yaml
type: markdown
title: Stroom All-in blokken 24 uur
content: |
  {% set blocks = state_attr('sensor.stroom_all_in_forecast_24_uur', 'forecast_blocks') or [] %}
  <div style="display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;">
  {% for block in blocks %}
    <div style="background:{ block.color };color:{ block.text_color };padding:12px;border-radius:12px;">
      <div style="font-size:13px;font-weight:600;">{{ block.period }}</div>
      <div style="font-size:18px;font-weight:700;margin-top:4px;">€ {{ block.display_value }}</div>
    </div>
  {% endfor %}
  </div>
```

### Beurs blocks

```yaml
type: markdown
title: Stroom Beurs blokken 24 uur
content: |
  {% set blocks = state_attr('sensor.stroom_beurs_forecast_24_uur', 'forecast_blocks') or [] %}
  <div style="display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;">
  {% for block in blocks %}
    <div style="background:{ block.color };color:{ block.text_color };padding:12px;border-radius:12px;">
      <div style="font-size:13px;font-weight:600;">{{ block.period }}</div>
      <div style="font-size:18px;font-weight:700;margin-top:4px;">€ {{ block.display_value }}</div>
    </div>
  {% endfor %}
  </div>
```

## Notes

- Forecast sensors expose:
  - `forecast_blocks`
  - `forecast_lines`
  - `forecast_text`
  - `forecast_count`
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
