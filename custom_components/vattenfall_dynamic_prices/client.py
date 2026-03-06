from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
import re
from typing import Any
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

from aiohttp import ClientError, ClientResponseError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DEFAULT_SCRAPE_URL, NL_TZ

_LOGGER = logging.getLogger(__name__)

RE_BASE = re.compile(r'dynamicTariffsBaseApiURL:"(?P<url>[^"]+)"')
RE_KEY = re.compile(r'ocpApimSubscriptionFeaturesDynamicTariffsKey:"(?P<key>[^"]+)"')
RE_SCRIPT_SRC = re.compile(r'<script[^>]+src="(?P<src>[^"]+)"', re.IGNORECASE)


@dataclass(slots=True)
class ApiDiscovery:
    base_url: str
    api_key: str
    discovered_at: datetime


class VattenfallClient:
    def __init__(self, hass, scrape_url: str = DEFAULT_SCRAPE_URL) -> None:
        self._hass = hass
        self._session = async_get_clientsession(hass)
        self._scrape_url = scrape_url
        self._discovery: ApiDiscovery | None = None
        self._tz = ZoneInfo(NL_TZ)

    async def async_get_summary(self, *, include_flex: bool, include_beurs: bool) -> dict[str, Any]:
        raw = await self.async_fetch_tariffs()
        return self.compute_summary(raw, include_flex=include_flex, include_beurs=include_beurs)

    async def async_fetch_tariffs(self) -> Any:
        discovery = self._discovery
        if discovery is None or datetime.now(self._tz) - discovery.discovered_at > timedelta(hours=6):
            discovery = await self._async_discover_api()
            self._discovery = discovery

        try:
            return await self._async_call_api(discovery.base_url, discovery.api_key)
        except ClientError as err:
            _LOGGER.debug("Cached Vattenfall API details failed, rediscovering: %s", err)

        discovery = await self._async_discover_api()
        self._discovery = discovery
        return await self._async_call_api(discovery.base_url, discovery.api_key)

    async def _async_discover_api(self) -> ApiDiscovery:
        async with self._session.get(self._scrape_url, timeout=20) as response:
            response.raise_for_status()
            html = await response.text()

        base_url = self._find(RE_BASE, html)
        api_key = self._find(RE_KEY, html)
        if base_url and api_key:
            return ApiDiscovery(base_url.rstrip("/"), api_key, datetime.now(self._tz))

        script_urls = [urljoin(self._scrape_url, match.group("src")) for match in RE_SCRIPT_SRC.finditer(html)]

        for script_url in script_urls:
            try:
                async with self._session.get(script_url, timeout=20) as response:
                    response.raise_for_status()
                    script = await response.text()
            except ClientError:
                continue

            base_url = self._find(RE_BASE, script)
            api_key = self._find(RE_KEY, script)
            if base_url and api_key:
                return ApiDiscovery(base_url.rstrip("/"), api_key, datetime.now(self._tz))

        raise RuntimeError("Could not discover the Vattenfall dynamic pricing API details")

    async def _async_call_api(self, base_url: str, api_key: str) -> Any:
        url = f"{base_url}/DynamicTariff"
        headers = {"ocp-apim-subscription-key": api_key}

        async with self._session.get(url, headers=headers, timeout=20) as response:
            response.raise_for_status()
            return await response.json()

    def compute_summary(
        self,
        raw: Any,
        *,
        include_flex: bool,
        include_beurs: bool,
    ) -> dict[str, Any]:
        products = raw if isinstance(raw, list) else raw.get("data") or []

        electricity = self._find_product(products, {"E", "electricity", "stroom"})
        gas = self._find_product(products, {"G", "gas"})

        result: dict[str, Any] = {"electricity": {}, "gas": {}}

        if electricity is not None:
            result["electricity"] = self._compute_product(
                electricity,
                unit="€/kWh",
                include_flex=include_flex,
                include_beurs=include_beurs,
            )

        if gas is not None:
            result["gas"] = self._compute_product(
                gas,
                unit="€/m³",
                include_flex=include_flex,
                include_beurs=include_beurs,
            )

        return result

    def _find_product(self, products: list[dict[str, Any]], match_values: set[str]) -> dict[str, Any] | None:
        for product in products:
            value = str(product.get("product", "")).strip().lower()
            if value in {item.lower() for item in match_values}:
                return product
        return None

    def _compute_product(
        self,
        product: dict[str, Any],
        *,
        unit: str,
        include_flex: bool,
        include_beurs: bool,
    ) -> dict[str, Any]:
        tariffs = product.get("tariffData") or []
        now = datetime.now(self._tz)

        result: dict[str, Any] = {}

        if include_flex:
            flex_series = self._series_from_tariffs(tariffs, mode="flex")
            result["flex"] = self._stats(flex_series, now)
            result["flex"]["unit"] = unit

        if include_beurs:
            beurs_series = self._series_from_tariffs(tariffs, mode="beurs")
            result["beurs"] = self._stats(beurs_series, now)
            result["beurs"]["unit"] = unit

        return result

    def _series_from_tariffs(self, tariffs: list[dict[str, Any]], *, mode: str) -> list[tuple[datetime, datetime, float]]:
        series: list[tuple[datetime, datetime, float]] = []

        for item in tariffs:
            start_raw = item.get("startTime")
            end_raw = item.get("endTime")
            if not start_raw or not end_raw:
                continue

            start = self._parse_datetime(start_raw)
            end = self._parse_datetime(end_raw)

            if mode == "flex":
                value = self._float_or_none(item.get("amountInclVat"))
            else:
                value = self._extract_beurs_price(item.get("details") or [])

            if value is None:
                continue

            series.append((start, end, value))

        series.sort(key=lambda entry: entry[0])
        return series

    def _extract_beurs_price(self, details: list[dict[str, Any]]) -> float | None:
        matches: list[float] = []

        for detail in details:
            detail_type = str(detail.get("type", "")).lower()
            if any(token in detail_type for token in ("beurs", "spot", "market", "epex", "eex")):
                value = self._float_or_none(
                    detail.get("amountInclVat", detail.get("amountInclVAT", detail.get("amount")))
                )
                if value is not None:
                    matches.append(value)

        if not matches:
            return None

        return sum(matches)

    def _stats(self, series: list[tuple[datetime, datetime, float]], now: datetime) -> dict[str, Any]:
        current: tuple[float, datetime] | None = None
        for start, end, value in series:
            if start <= now < end:
                current = (value, start)
                break

        window_end = now + timedelta(hours=24)
        window_values = [
            (value, start)
            for start, end, value in series
            if end > now and start < window_end
        ]

        peak = max(window_values, default=None, key=lambda item: item[0])
        low = min(window_values, default=None, key=lambda item: item[0])

        return {
            "current": current[0] if current else None,
            "peak_24h": peak[0] if peak else None,
            "low_24h": low[0] if low else None,
            "current_at": current[1].isoformat() if current else None,
            "peak_at": peak[1].isoformat() if peak else None,
            "low_at": low[1].isoformat() if low else None,
        }

    def _parse_datetime(self, value: str) -> datetime:
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=self._tz)
        return parsed.astimezone(self._tz)

    @staticmethod
    def _find(regex: re.Pattern[str], text: str) -> str | None:
        match = regex.search(text)
        return match.group(1) if match else None

    @staticmethod
    def _float_or_none(value: Any) -> float | None:
        try:
            if value is None:
                return None
            return float(value)
        except (TypeError, ValueError):
            return None
