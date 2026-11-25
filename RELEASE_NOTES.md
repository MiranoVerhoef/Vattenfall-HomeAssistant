## 2.0.6

### Fixed
- Prices stopped loading with `403 Site Disabled` (#13). Vattenfall retired the old
  `dynamic-tariff-prd/api/v1/DynamicTariff` endpoint. The integration now reads the
  endpoint and key that Vattenfall's own price widget uses
  (`cepTouchPointBaseUrl` / `cepTouchPointSubscriptionKey`) and requests
  `/consumptions/v1/DynamicTariff`.

After updating, restart Home Assistant. The integration should recover on its own;
reload it from Settings → Devices & services if it stays in "Failed setup".
