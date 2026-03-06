DOMAIN = "vattenfall_dynamic_prices"

CONF_ENABLE_FLEX = "enable_flex"
CONF_ENABLE_BEURS = "enable_beurs"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_ENABLE_FLEX = True
DEFAULT_ENABLE_BEURS = False
DEFAULT_SCAN_INTERVAL = 900

DEFAULT_SCRAPE_URL = "https://www.vattenfall.nl/klantenservice/alles-over-je-dynamische-contract/"
DEFAULT_BEURS_TYPE_CONTAINS = ("beurs", "spot", "market", "epex", "eex")
