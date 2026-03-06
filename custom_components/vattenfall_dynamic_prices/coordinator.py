from __future__ import annotations

from datetime import timedelta

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import VattenfallClient
from .const import CONF_ENABLE_BEURS, CONF_ENABLE_FLEX, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL


class VattenfallDataUpdateCoordinator(DataUpdateCoordinator[dict]):
    def __init__(self, hass, client: VattenfallClient, entry) -> None:
        self.client = client
        self.entry = entry

        scan_interval = entry.options.get(
            CONF_SCAN_INTERVAL,
            entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )

        super().__init__(
            hass,
            logger=__import__("logging").getLogger(__name__),
            name="Vattenfall Dynamic Prices",
            update_interval=timedelta(seconds=scan_interval),
        )

    async def _async_update_data(self) -> dict:
        include_flex = self.entry.options.get(
            CONF_ENABLE_FLEX,
            self.entry.data.get(CONF_ENABLE_FLEX, True),
        )
        include_beurs = self.entry.options.get(
            CONF_ENABLE_BEURS,
            self.entry.data.get(CONF_ENABLE_BEURS, False),
        )

        try:
            return await self.client.async_get_summary(
                include_flex=include_flex,
                include_beurs=include_beurs,
            )
        except Exception as err:
            raise UpdateFailed(str(err)) from err
