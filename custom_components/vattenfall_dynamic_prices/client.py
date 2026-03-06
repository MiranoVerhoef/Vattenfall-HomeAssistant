from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urljoin

from aiohttp import ClientError
from dateutil import parser as dtparser
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DEFAULT_BEURS_TYPE_CONTAINS, DEFAULT_SCRAPE_URL

_LOGGER = logging.getLogger(__name__)

RE_BASE = re.compile(r'dynamicTariffsBaseApiURL:"(?P<url>[^"]+)"')
RE_KEY = re.compile(r'ocpApimSubscriptionFeaturesDynamicTariffsKey:"(?P<key>[^"]+)"')
RE_SCRIPT_SRC = re.compile(r'<script[^>]+src="(?P<src>[^"]+)"', re.IGNORECASE)


class VattenfallError(Exception):
    """Base Vattenfall integration error."""


class VattenfallDiscoveryError(VattenfallError):
    """Raised when API discovery fails."""


class VattenfallApiError(VattenfallError):
    """Raised when the API call fails."""


@dataclass(slots=True)
class DiscoveredApi:
    base_url: str
    subscription_key: str


class VattenfallClient:
    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self.session = async_get_clientsession(hass)
        self.scrape_url = DEFAULT_SCRAPE_URL
        self.beurs_tokens = DEFAULT_BEURS_TYPE_CONTAINS

    async def async_get_summary(self, *, include_flex: bool, include_beurs: bool) -> dict[str, Any]:
        raw = await self.async_fetch_tariffs()
        return self._compute_summary(raw=raw, include_flex=include_flex, include_beurs=include_beurs)

    async def async_fetch_tariffs(self) -> Any:
        discovered = await self._async_discover_api()
        headers = {
            'ocp-apim-subscription-key': discovered.subscription_key,
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/131.0.0.0 Safari/537.36'
            ),
            'Accept': 'application/json, text/plain, */*',
            'Referer': self.scrape_url,
        }
        url = f"{discovered.base_url}/DynamicTariff"

        try:
            async with self.session.get(url, headers=headers, timeout=30) as response:
                text = await response.text()
                if response.status >= 400:
                    raise VattenfallApiError(
                        f'DynamicTariff request failed with HTTP {response.status}: {text[:300]}'
                    )
                try:
                    return await response.json(content_type=None)
                except Exception as err:
                    raise VattenfallApiError(
                        f'DynamicTariff returned non-JSON content: {text[:300]}'
                    ) from err
        except ClientError as err:
            raise VattenfallApiError(f'DynamicTariff request error: {err}') from err

    async def _async_discover_api(self) -> DiscoveredApi:
        page_headers = {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/131.0.0.0 Safari/537.36'
            ),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'nl-NL,nl;q=0.9,en;q=0.8',
        }

        try:
            async with self.session.get(self.scrape_url, headers=page_headers, timeout=30) as response:
                html = await response.text()
                if response.status >= 400:
                    raise VattenfallDiscoveryError(
                        f'Pricing page request failed with HTTP {response.status}'
                    )
        except ClientError as err:
            raise VattenfallDiscoveryError(f'Pricing page request error: {err}') from err

        inline = self._extract_api_details(html)
        if inline:
            _LOGGER.debug('Discovered Vattenfall API details from inline page content')
            return inline

        scripts = [urljoin(self.scrape_url, match.group('src')) for match in RE_SCRIPT_SRC.finditer(html)]
        _LOGGER.debug('Scanning %s Vattenfall script files for API details', len(scripts))

        for script_url in scripts:
            try:
                async with self.session.get(script_url, headers=page_headers, timeout=30) as response:
                    script_text = await response.text()
                    if response.status >= 400:
                        continue
            except ClientError:
                continue

            discovered = self._extract_api_details(script_text)
            if discovered:
                _LOGGER.debug('Discovered Vattenfall API details in script: %s', script_url)
                return discovered

        raise VattenfallDiscoveryError(
            'Could not discover the Vattenfall dynamic pricing API details from the public webpage.'
        )

    def _extract_api_details(self, text: str) -> DiscoveredApi | None:
        base_match = RE_BASE.search(text)
        key_match = RE_KEY.search(text)
        if not base_match or not key_match:
            return None

        base_url = base_match.group('url').rstrip('/')
        subscription_key = key_match.group('key')
        return DiscoveredApi(base_url=base_url, subscription_key=subscription_key)

    def _compute_summary(self, *, raw: Any, include_flex: bool, include_beurs: bool) -> dict[str, Any]:
        products = raw if isinstance(raw, list) else raw.get('data') or []

        electricity = next((p for p in products if p.get('product') == 'E'), None)
        gas = next((p for p in products if p.get('product') == 'G'), None)

        now = datetime.now().astimezone()

        summary: dict[str, Any] = {
            'last_update': now.isoformat(),
            'electricity': {},
            'gas': {},
        }

        if electricity:
            summary['electricity'] = self._product_summary(
                product=electricity,
                now=now,
                include_flex=include_flex,
                include_beurs=include_beurs,
                unit='€/kWh',
            )

        if gas:
            summary['gas'] = self._product_summary(
                product=gas,
                now=now,
                include_flex=include_flex,
                include_beurs=include_beurs,
                unit='€/m³',
            )

        return summary

    def _product_summary(
        self,
        *,
        product: dict[str, Any],
        now: datetime,
        include_flex: bool,
        include_beurs: bool,
        unit: str,
    ) -> dict[str, Any]:
        tariffs = product.get('tariffData') or []
        data: dict[str, Any] = {}

        if include_flex:
            flex_series = self._build_series(tariffs, mode='flex')
            data['flex'] = self._stats_from_series(flex_series, now)
            data['flex']['unit'] = unit

        if include_beurs:
            beurs_series = self._build_series(tariffs, mode='beurs')
            data['beurs'] = self._stats_from_series(beurs_series, now)
            data['beurs']['unit'] = unit

        return data

    def _build_series(self, tariffs: list[dict[str, Any]], *, mode: str) -> list[tuple[datetime, datetime, float]]:
        series: list[tuple[datetime, datetime, float]] = []

        for tariff in tariffs:
            start = self._parse_dt(tariff['startTime'])
            end = self._parse_dt(tariff['endTime'])

            if mode == 'flex':
                value = tariff.get('amountInclVat')
                if value is None:
                    continue
                series.append((start, end, float(value)))
                continue

            beurs_value = self._extract_beurs_value(tariff.get('details') or [])
            if beurs_value is not None:
                series.append((start, end, beurs_value))

        series.sort(key=lambda item: item[0])
        return series

    def _extract_beurs_value(self, details: list[dict[str, Any]]) -> float | None:
        matches: list[float] = []

        for detail in details:
            detail_type = str(detail.get('type') or '').lower()
            if any(token in detail_type for token in self.beurs_tokens):
                amount = detail.get('amountInclVat', detail.get('amount'))
                if amount is not None:
                    matches.append(float(amount))

        if not matches:
            return None

        return sum(matches)

    def _stats_from_series(self, series: list[tuple[datetime, datetime, float]], now: datetime) -> dict[str, Any]:
        current_value: float | None = None
        current_start: datetime | None = None

        for start, end, value in series:
            if start <= now < end:
                current_value = value
                current_start = start
                break

        end_of_window = now + timedelta(hours=24)
        upcoming = [(value, start) for start, _, value in series if now <= start < end_of_window]

        peak = max(upcoming, default=None, key=lambda item: item[0])
        low = min(upcoming, default=None, key=lambda item: item[0])

        return {
            'current': current_value,
            'current_at': current_start.isoformat() if current_start else None,
            'peak_24h': peak[0] if peak else None,
            'peak_at': peak[1].isoformat() if peak else None,
            'low_24h': low[0] if low else None,
            'low_at': low[1].isoformat() if low else None,
        }

    def _parse_dt(self, value: str) -> datetime:
        parsed = dtparser.isoparse(value)
        if parsed.tzinfo is None:
            return parsed.astimezone()
        return parsed.astimezone()
