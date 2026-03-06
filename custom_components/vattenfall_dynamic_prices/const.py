DOMAIN = "vattenfall_dynamic_prices"

CONF_ENABLE_FLEX = "enable_flex"
CONF_ENABLE_BEURS = "enable_beurs"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_ENABLE_FLEX = True
DEFAULT_ENABLE_BEURS = False
DEFAULT_SCAN_INTERVAL = 900

SCRAPE_URL = "https://www.vattenfall.nl/klantenservice/alles-over-je-dynamische-contract/"

ATTR_CURRENT_AT = "current_at"
ATTR_PEAK_AT = "peak_at"
ATTR_LOW_AT = "low_at"
ATTR_LAST_REFRESH = "last_refresh"
