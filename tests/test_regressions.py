from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock, patch

from homeassistant.data_entry_flow import FlowResultType

try:
    import httpx2 as httpx
except ModuleNotFoundError:
    import httpx

from custom_components import vattenfall_dynamic_prices as integration
from custom_components.vattenfall_dynamic_prices import config_flow
from custom_components.vattenfall_dynamic_prices.client import (
    TZ,
    VattenfallApiError,
    VattenfallClient,
    VattenfallDiscoveryError,
)
from custom_components.vattenfall_dynamic_prices.const import SCRAPE_URL


class OptionsFlowTests(IsolatedAsyncioTestCase):
    async def test_open_and_save_options(self):
        entry = SimpleNamespace(
            data={"enable_flex": True, "enable_beurs": False, "scan_interval": 900},
            options={"enable_beurs": True},
        )
        flow = config_flow.VattenfallConfigFlow.async_get_options_flow(entry)
        flow.hass = Mock()
        flow.handler = "vattenfall"
        flow.flow_id = "options"
        flow.context = {}

        form = await flow.async_step_init()
        self.assertEqual(form["type"], FlowResultType.FORM)
        self.assertEqual(form["data_schema"]({}), {**entry.data, **entry.options})

        options = {"enable_flex": False, "enable_beurs": True, "scan_interval": 1800}
        with patch.object(config_flow, "_async_validate_input", new_callable=AsyncMock) as validate:
            result = await flow.async_step_init(options)

        self.assertEqual(result["type"], FlowResultType.CREATE_ENTRY)
        self.assertEqual(result["data"], options)
        validate.assert_awaited_once_with(flow.hass, options)

    async def test_setup_registers_reload_and_uses_saved_options(self):
        hass = Mock()
        hass.config_entries.async_forward_entry_setups = AsyncMock()
        hass.config_entries.async_reload = AsyncMock()
        entry = Mock(
            entry_id="vattenfall",
            data={"enable_flex": True, "enable_beurs": False, "scan_interval": 900},
            options={"enable_flex": False, "enable_beurs": True, "scan_interval": 1800},
        )
        with (
            patch.object(integration, "get_async_client"),
            patch.object(integration, "VattenfallDataUpdateCoordinator") as coordinator,
        ):
            coordinator.return_value.async_config_entry_first_refresh = AsyncMock()
            await integration.async_setup_entry(hass, entry)

        self.assertEqual(coordinator.call_args.args[2], entry.options)
        entry.async_on_unload.assert_called_once_with(entry.add_update_listener.return_value)
        listener = entry.add_update_listener.call_args.args[0]
        await listener(hass, entry)
        hass.config_entries.async_reload.assert_awaited_once_with(entry.entry_id)


class BeursPriceTests(IsolatedAsyncioTestCase):
    async def test_exchange_component_drives_current_and_forecast_prices(self):
        now = datetime(2026, 7, 1, 12, 30, tzinfo=TZ)
        start = now.replace(minute=0)
        details = [
            {"type": "PRICE", "amount": -0.05, "amountInclVat": -0.0605},
            {"type": "FEE", "amountInclVat": 0.015},
            {"type": "ENERGY_TAX", "amountInclVat": 0.11},
            {"type": "VAT", "amount": 0.015},
        ]
        tariffs = [
            {
                "product": product,
                "tariffData": [{
                    "startTime": start.isoformat(),
                    "endTime": (start + duration).isoformat(),
                    "amountInclVat": 0.07,
                    "details": details,
                }],
            }
            for product, duration in (("E", timedelta(hours=1)), ("G", timedelta(days=1)))
        ]
        client = VattenfallClient(Mock())
        with (
            patch.object(client, "async_fetch_tariffs", new=AsyncMock(return_value=tariffs)),
            patch.object(integration.client, "datetime", wraps=datetime) as clock,
        ):
            clock.now.return_value = now
            summary = await client.async_get_summary(include_flex=True, include_beurs=True)

        self.assertEqual(summary["electricity"]["flex"]["current"], 0.07)
        self.assertEqual(summary["electricity"]["beurs"]["current"], -0.0605)
        self.assertEqual(summary["electricity"]["beurs"]["forecast_24h"][0]["value"], -0.0605)
        self.assertEqual(summary["gas"]["beurs"]["current"], -0.0605)

    async def test_validation_requires_current_data_for_each_selected_mode(self):
        hass = Mock()
        options = {"enable_flex": True, "enable_beurs": True}
        summary = {"electricity": {"flex": {"current": 0.2}}, "gas": {}}
        with (
            patch.object(config_flow, "get_async_client"),
            patch.object(config_flow, "VattenfallClient") as client,
        ):
            client.return_value.async_get_summary = AsyncMock(return_value=summary)
            with self.assertRaisesRegex(VattenfallApiError, "No current tariff for beurs"):
                await config_flow._async_validate_input(hass, options)

            summary["electricity"]["beurs"] = {"current": 0.0}
            await config_flow._async_validate_input(hass, options)


class DiscoveryTests(IsolatedAsyncioTestCase):
    async def test_failed_discovery_reports_script_counts_without_key_value(self):
        def respond(request):
            if request.url == httpx.URL(SCRAPE_URL):
                return httpx.Response(200, text=(
                    '<script src="/first.js"></script>'
                    '<script src="/second.js?token=example-query"></script>'
                ))
            if request.url.path == "/first.js":
                return httpx.Response(200, text=(
                    'ocpApimSubscriptionFeaturesDynamicTariffsKey:"example-key"'
                ))
            return httpx.Response(403)

        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
            client = VattenfallClient(http)
            with (
                patch.object(client, "_async_validate_url", new_callable=AsyncMock),
                self.assertLogs(integration.client.__name__, level="DEBUG") as logs,
                self.assertRaises(VattenfallDiscoveryError) as error,
            ):
                await client._async_discover_api()

        message = str(error.exception)
        self.assertIn("Read 1 of 2 pricing scripts", message)
        self.assertIn("API URL found: no", message)
        self.assertIn("Subscription key found: yes", message)
        output = "\n".join(logs.output)
        self.assertIn("Pricing script 2 returned HTTP 403", output)
        self.assertNotIn("example-key", message + output)
        self.assertNotIn("example-query", message + output)

    async def test_discovery_still_uses_details_from_a_matching_script(self):
        def respond(request):
            if request.url == httpx.URL(SCRAPE_URL):
                return httpx.Response(200, text='<script src="/prices.js"></script>')
            return httpx.Response(200, text=(
                'dynamicTariffsBaseApiURL:"https://example.com/" '
                'ocpApimSubscriptionFeaturesDynamicTariffsKey:"example-key"'
            ))

        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
            client = VattenfallClient(http)
            with patch.object(client, "_async_validate_url", new_callable=AsyncMock):
                result = await client._async_discover_api()

        self.assertEqual(result, ("https://example.com", "example-key"))
