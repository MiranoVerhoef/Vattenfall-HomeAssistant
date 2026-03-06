from __future__ import annotations

from datetime import timedelta
from typing import Any

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import VattenfallClient
from .const import CONF_ENABLE_BEURS, CONF_ENABLE_FLEX, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL


class VattenfallDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(self, hass, client: VattenfallClient, config: dict[str, Any]) -> None:
        self.client = client
        self.config = config
        scan_interval = int(config.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))

        super().__init__(
            hass,
            logger=__import__("logging").getLogger(__name__),
            name="Vattenfall Dynamic Prices",
            update_interval=timedelta(seconds=scan_interval),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            return await self.client.async_get_summary(
                include_flex=self.config.get(CONF_ENABLE_FLEX, True),
                include_beurs=self.config.get(CONF_ENABLE_BEURS, False),
            )
        except Exception as err:
            raise UpdateFailed(str(err)) from err
