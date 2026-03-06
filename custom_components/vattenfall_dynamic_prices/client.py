from __future__ import annotations

import asyncio
import ipaddress
import logging
import socket
import re
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urljoin, urlparse
from zoneinfo import ZoneInfo

import httpx

from .const import SCRAPE_URL

_LOGGER = logging.getLogger(__name__)

TZ = ZoneInfo("Europe/Amsterdam")

RE_BASE = re.compile(r'dynamicTariffsBaseApiURL:"(?P<url>[^"]+)"')
RE_KEY = re.compile(r'ocpApimSubscriptionFeaturesDynamicTariffsKey:"(?P<key>[^"]+)"')
RE_SCRIPT_SRC = re.compile(r'<script[^>]+src="(?P<src>[^"]+)"', re.IGNORECASE)

ALLOWED_PAGE_HOSTS = {"www.vattenfall.nl", "vattenfall.nl"}
ALLOWED_SCRIPT_SUFFIXES = ("vattenfall.nl", "vattenfall.com")


class VattenfallError(Exception):
    """Base integration error."""


class VattenfallDiscoveryError(VattenfallError):
    """Raised when discovery from the public page fails."""


class VattenfallApiError(VattenfallError):
    """Raised when the tariff API call fails."""


class VattenfallClient:
    def __init__(self, http_client: httpx.AsyncClient) -> None:
        self.client = http_client
        self._discovery_cache: tuple[str, str] | None = None
        self._discovery_lock = asyncio.Lock()

    async def async_get_summary(
        self,
        include_flex: bool,
        include_beurs: bool,
    ) -> dict[str, Any]:
        raw = await self.async_fetch_tariffs()
        return self._compute_summary(raw, include_flex=include_flex, include_beurs=include_beurs)

    async def async_fetch_tariffs(self) -> Any:
        base_url, api_key = await self._async_discover_api()

        try:
            return await self._async_request_tariffs(base_url, api_key)
        except Exception:
            # clear cached discovery once and retry in case the endpoint/key changed
            self._discovery_cache = None
            base_url, api_key = await self._async_discover_api()
            return await self._async_request_tariffs(base_url, api_key)

    async def _async_request_tariffs(self, base_url: str, api_key: str) -> Any:
        await self._async_validate_url(base_url, allow_public_host_only=True)

        url = f"{base_url.rstrip('/')}/DynamicTariff"
        _LOGGER.debug("Fetching Vattenfall tariffs from discovered endpoint")

        try:
            response = await self.client.get(
                url,
                headers={"ocp-apim-subscription-key": api_key},
                timeout=30.0,
                follow_redirects=False,
            )
            response.raise_for_status()
            return response.json()
        except Exception as err:
            raise VattenfallApiError(f"Tariff API request error: {err}") from err

    async def _async_discover_api(self) -> tuple[str, str]:
        if self._discovery_cache is not None:
            return self._discovery_cache

        async with self._discovery_lock:
            if self._discovery_cache is not None:
                return self._discovery_cache

            page_headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/123.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }

            _LOGGER.debug("Discovering Vattenfall API details from pricing page")
            await self._async_validate_url(
                SCRAPE_URL,
                allow_exact_hosts=ALLOWED_PAGE_HOSTS,
                allow_suffixes=ALLOWED_SCRIPT_SUFFIXES,
                allow_public_host_only=True,
            )

            try:
                response = await self.client.get(
                    SCRAPE_URL,
                    headers=page_headers,
                    timeout=30.0,
                    follow_redirects=False,
                )
                response.raise_for_status()
                html = response.text
            except Exception as err:
                raise VattenfallDiscoveryError(f"Pricing page request error: {err}") from err

            base_url = self._find(RE_BASE, html)
            api_key = self._find(RE_KEY, html)
            if base_url and api_key:
                await self._async_validate_url(base_url, allow_public_host_only=True)
                self._discovery_cache = (base_url.rstrip("/"), api_key)
                return self._discovery_cache

            scripts = [urljoin(SCRAPE_URL, match.group("src")) for match in RE_SCRIPT_SRC.finditer(html)]

            for script_url in scripts:
                try:
                    await self._async_validate_url(
                        script_url,
                        allow_suffixes=ALLOWED_SCRIPT_SUFFIXES,
                        allow_public_host_only=True,
                    )
                    script_response = await self.client.get(
                        script_url,
                        headers={"User-Agent": page_headers["User-Agent"]},
                        timeout=30.0,
                        follow_redirects=False,
                    )
                    script_response.raise_for_status()
                    js = script_response.text
                except Exception as err:
                    _LOGGER.debug("Skipping script %s due to error: %s", script_url, err)
                    continue

                base_url = self._find(RE_BASE, js)
                api_key = self._find(RE_KEY, js)
                if base_url and api_key:
                    await self._async_validate_url(base_url, allow_public_host_only=True)
                    self._discovery_cache = (base_url.rstrip("/"), api_key)
                    return self._discovery_cache

            raise VattenfallDiscoveryError("Could not discover the Vattenfall dynamic pricing API details")

    async def _async_validate_url(
        self,
        url: str,
        *,
        allow_exact_hosts: set[str] | None = None,
        allow_suffixes: tuple[str, ...] | None = None,
        allow_public_host_only: bool = False,
    ) -> None:
        parsed = urlparse(url)

        if parsed.scheme != "https":
            raise VattenfallDiscoveryError(f"Only https URLs are allowed: {url}")

        if parsed.username or parsed.password:
            raise VattenfallDiscoveryError(f"URLs with embedded credentials are not allowed: {url}")

        host = parsed.hostname
        if not host:
            raise VattenfallDiscoveryError(f"Invalid URL host: {url}")

        normalized_host = host.lower()

        if allow_exact_hosts and normalized_host not in {h.lower() for h in allow_exact_hosts}:
            if not allow_suffixes:
                raise VattenfallDiscoveryError(f"Host is not allowed: {normalized_host}")

        if allow_suffixes:
            if not any(
                normalized_host == suffix.lower() or normalized_host.endswith("." + suffix.lower())
                for suffix in allow_suffixes
            ):
                if not (allow_exact_hosts and normalized_host in {h.lower() for h in allow_exact_hosts}):
                    raise VattenfallDiscoveryError(f"Host is not allowed: {normalized_host}")

        if allow_public_host_only:
            await self._async_assert_public_host(normalized_host, parsed.port or 443)

    async def _async_assert_public_host(self, host: str, port: int) -> None:
        # Explicit literal IP check first
        try:
            ip = ipaddress.ip_address(host)
        except ValueError:
            ip = None

        if ip is not None:
            if not ip.is_global:
                raise VattenfallDiscoveryError(f"Private or non-public IPs are not allowed: {host}")
            return

        loop = asyncio.get_running_loop()
        try:
            infos = await loop.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        except Exception as err:
            raise VattenfallDiscoveryError(f"Could not resolve host {host}: {err}") from err

        for info in infos:
            address = info[4][0]
            try:
                ip = ipaddress.ip_address(address)
            except ValueError:
                continue

            if not ip.is_global:
                raise VattenfallDiscoveryError(f"Private or non-public IPs are not allowed: {host} -> {address}")

    def _find(self, regex: re.Pattern[str], text: str) -> str | None:
        match = regex.search(text)
        return match.group(1) if match else None

    def _compute_summary(
        self,
        raw: Any,
        *,
        include_flex: bool,
        include_beurs: bool,
    ) -> dict[str, Any]:
        products = raw if isinstance(raw, list) else raw.get("data") or []

        electricity = next((item for item in products if item.get("product") == "E"), None)
        gas = next((item for item in products if item.get("product") == "G"), None)

        now = datetime.now(TZ)

        summary: dict[str, Any] = {
            "last_refresh": now.isoformat(),
            "electricity": {},
            "gas": {},
        }

        if electricity:
            summary["electricity"] = self._product_summary(
                electricity,
                product_kind="electricity",
                now=now,
                unit="€/kWh",
                include_flex=include_flex,
                include_beurs=include_beurs,
            )

        if gas:
            summary["gas"] = self._product_summary(
                gas,
                product_kind="gas",
                now=now,
                unit="€/m³",
                include_flex=include_flex,
                include_beurs=include_beurs,
            )

        return summary

    def _product_summary(
        self,
        product: dict[str, Any],
        *,
        product_kind: str,
        now: datetime,
        unit: str,
        include_flex: bool,
        include_beurs: bool,
    ) -> dict[str, Any]:
        tariffs = product.get("tariffData") or []
        result: dict[str, Any] = {}

        if include_flex:
            flex_series = self._series_from_tariffs(tariffs, mode="flex")
            result["flex"] = self._series_stats(
                flex_series,
                now,
                include_day_range=product_kind == "electricity",
            )
            result["flex"]["unit"] = unit
            if product_kind == "electricity":
                result["flex"]["forecast_24h"] = self._forecast_24h(flex_series, now, unit)

        if include_beurs:
            beurs_series = self._series_from_tariffs(tariffs, mode="beurs")
            result["beurs"] = self._series_stats(
                beurs_series,
                now,
                include_day_range=product_kind == "electricity",
            )
            result["beurs"]["unit"] = unit
            if product_kind == "electricity":
                result["beurs"]["forecast_24h"] = self._forecast_24h(beurs_series, now, unit)

        return result

    def _series_from_tariffs(
        self,
        tariffs: list[dict[str, Any]],
        *,
        mode: str,
    ) -> list[tuple[datetime, datetime, float]]:
        series: list[tuple[datetime, datetime, float]] = []

        for item in tariffs:
            start = self._parse_datetime(item["startTime"])
            end = self._parse_datetime(item["endTime"])

            if mode == "flex":
                amount = item.get("amountInclVat")
                if amount is None:
                    continue
                value = float(amount)
            else:
                value = self._extract_beurs(item.get("details") or [])
                if value is None:
                    continue

            series.append((start, end, float(value)))

        series.sort(key=lambda row: row[0])
        return series

    def _extract_beurs(self, details: list[dict[str, Any]]) -> float | None:
        tokens = ("beurs", "spot", "market", "epex", "eex")
        values: list[float] = []

        for detail in details:
            detail_type = (detail.get("type") or "").lower()
            if any(token in detail_type for token in tokens):
                amount = detail.get("amountInclVat", detail.get("amount"))
                if amount is not None:
                    values.append(float(amount))

        if not values:
            return None

        return sum(values)

    def _parse_datetime(self, value: str) -> datetime:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.astimezone(TZ) if parsed.tzinfo else parsed.replace(tzinfo=TZ)

    def _series_stats(
        self,
        series: list[tuple[datetime, datetime, float]],
        now: datetime,
        *,
        include_day_range: bool,
    ) -> dict[str, Any]:
        current: tuple[float, datetime] | None = None
        for start, end, value in series:
            if start <= now < end:
                current = (value, start)
                break

        result = {
            "current": current[0] if current else None,
            "current_at": current[1].isoformat() if current else None,
        }

        if include_day_range:
            window_end = now + timedelta(hours=24)
            future = [(value, start) for start, end, value in series if start >= now and start < window_end]

            peak = max(future, default=None, key=lambda item: item[0])
            low = min(future, default=None, key=lambda item: item[0])

            result.update(
                {
                    "peak_24h": peak[0] if peak else None,
                    "peak_at": peak[1].isoformat() if peak else None,
                    "low_24h": low[0] if low else None,
                    "low_at": low[1].isoformat() if low else None,
                }
            )

        return result

    def _forecast_24h(
        self,
        series: list[tuple[datetime, datetime, float]],
        now: datetime,
        unit: str,
    ) -> list[dict[str, Any]]:
        window_end = now + timedelta(hours=24)
        points: list[dict[str, Any]] = []

        for start, end, value in series:
            if start >= now and start < window_end:
                points.append(
                    {
                        "start": start.isoformat(),
                        "end": end.isoformat(),
                        "value": value,
                        "unit": unit,
                    }
                )

        return points
