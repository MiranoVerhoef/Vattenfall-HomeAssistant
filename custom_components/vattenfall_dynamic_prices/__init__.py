from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.httpx_client import get_async_client

from .client import VattenfallClient
from .const import DOMAIN
from .coordinator import VattenfallDataUpdateCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]


@dataclass
class VattenfallRuntimeData:
    client: VattenfallClient
    coordinator: VattenfallDataUpdateCoordinator


VattenfallConfigEntry = ConfigEntry[VattenfallRuntimeData]


async def async_setup_entry(hass: HomeAssistant, entry: VattenfallConfigEntry) -> bool:
    http_client = get_async_client(hass)
    client = VattenfallClient(http_client)
    config = {**entry.data, **entry.options}

    coordinator = VattenfallDataUpdateCoordinator(hass, client, config)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = VattenfallRuntimeData(client=client, coordinator=coordinator)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: VattenfallConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
