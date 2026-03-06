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

Options:

- Enable All-in / FlexPrijs sensors
- Enable Beursprijs sensors
- Set refresh interval

## Security hardening

- HTTPS-only URL validation
- Embedded credentials blocked in URLs
- No redirect following for discovery/API calls
- Discovery restricted to expected Vattenfall domains
- Private and non-public IP targets blocked to reduce SSRF risk
- In-memory discovery caching with retry on failure

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

## Notes

This integration depends on Vattenfall's public website/API structure and can break if they change it.

## 1.3.0

- Version bump to 1.3.0
- Added a clear copy-paste repository URL in the install instructions
