from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import VattenfallClient, VattenfallError
from .const import (
    CONF_ENABLE_BEURS,
    CONF_ENABLE_FLEX,
    CONF_SCAN_INTERVAL,
    DEFAULT_ENABLE_BEURS,
    DEFAULT_ENABLE_FLEX,
    DEFAULT_SCAN_INTERVAL,
)


class VattenfallDataUpdateCoordinator(DataUpdateCoordinator[dict]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry
        self.client = VattenfallClient(hass)

        config = {**entry.data, **entry.options}
        interval = int(config.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))

        super().__init__(
            hass,
            logger=logging.getLogger(__name__),
            name='Vattenfall Dynamic Prices',
            update_interval=timedelta(seconds=interval),
        )

    async def _async_update_data(self) -> dict:
        config = {**self.entry.data, **self.entry.options}
        include_flex = bool(config.get(CONF_ENABLE_FLEX, DEFAULT_ENABLE_FLEX))
        include_beurs = bool(config.get(CONF_ENABLE_BEURS, DEFAULT_ENABLE_BEURS))

        try:
            return await self.client.async_get_summary(
                include_flex=include_flex,
                include_beurs=include_beurs,
            )
        except VattenfallError as err:
            raise UpdateFailed(str(err)) from err
