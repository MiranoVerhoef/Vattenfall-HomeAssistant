from __future__ import annotations

DOMAIN = "vattenfall_dynamic_prices"

DEFAULT_SCAN_INTERVAL = 900
DEFAULT_ENABLE_FLEX = True
DEFAULT_ENABLE_BEURS = False

CONF_SCAN_INTERVAL = "scan_interval"
CONF_ENABLE_FLEX = "enable_flex"
CONF_ENABLE_BEURS = "enable_beurs"

DEFAULT_SCRAPE_URL = "https://www.vattenfall.nl/klantenservice/alles-over-je-dynamische-contract/"

DEVICE_IDENTIFIER = "vattenfall_dynamic_prices"
NL_TZ = "Europe/Amsterdam"
