from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_ENABLE_BEURS,
    CONF_ENABLE_FLEX,
    DEVICE_IDENTIFIER,
    DOMAIN,
)
from .coordinator import VattenfallDataUpdateCoordinator

SENSOR_DEFINITIONS = [
    ("stroom_flex_current", "Stroom Flex Current Price", "electricity", "flex", "current"),
    ("stroom_flex_peak_24h", "Stroom Flex Peak 24 Hours Price", "electricity", "flex", "peak_24h"),
    ("stroom_flex_low_24h", "Stroom Flex Lowest 24 Hours Price", "electricity", "flex", "low_24h"),
    ("gas_flex_current", "Gas Flex Current Price", "gas", "flex", "current"),
    ("gas_flex_peak_24h", "Gas Flex Peak 24 Hours Price", "gas", "flex", "peak_24h"),
    ("gas_flex_low_24h", "Gas Flex Lowest 24 Hours Price", "gas", "flex", "low_24h"),
    ("stroom_beurs_current", "Stroom Beurs Current Price", "electricity", "beurs", "current"),
    ("stroom_beurs_peak_24h", "Stroom Beurs Peak 24 Hours Price", "electricity", "beurs", "peak_24h"),
    ("stroom_beurs_low_24h", "Stroom Beurs Lowest 24 Hours Price", "electricity", "beurs", "low_24h"),
    ("gas_beurs_current", "Gas Beurs Current Price", "gas", "beurs", "current"),
    ("gas_beurs_peak_24h", "Gas Beurs Peak 24 Hours Price", "gas", "beurs", "peak_24h"),
    ("gas_beurs_low_24h", "Gas Beurs Lowest 24 Hours Price", "gas", "beurs", "low_24h"),
]


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    coordinator: VattenfallDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    enable_flex = entry.options.get(CONF_ENABLE_FLEX, entry.data.get(CONF_ENABLE_FLEX, True))
    enable_beurs = entry.options.get(CONF_ENABLE_BEURS, entry.data.get(CONF_ENABLE_BEURS, False))

    entities: list[VattenfallPriceSensor] = []
    for key, name, category, mode, metric in SENSOR_DEFINITIONS:
        if mode == "flex" and not enable_flex:
            continue
        if mode == "beurs" and not enable_beurs:
            continue
        entities.append(VattenfallPriceSensor(coordinator, entry.entry_id, key, name, category, mode, metric))

    async_add_entities(entities)


class VattenfallPriceSensor(CoordinatorEntity[VattenfallDataUpdateCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_suggested_display_precision = 5

    def __init__(
        self,
        coordinator: VattenfallDataUpdateCoordinator,
        entry_id: str,
        key: str,
        name: str,
        category: str,
        mode: str,
        metric: str,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_{key}"
        self._attr_name = name
        self._category = category
        self._mode = mode
        self._metric = metric

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, DEVICE_IDENTIFIER)},
            name="Vattenfall Dynamic Prices",
            manufacturer="Vattenfall",
            model="Dynamic Tariffs",
        )

    @property
    def native_unit_of_measurement(self) -> str | None:
        block = self._data_block
        return block.get("unit") if block else None

    @property
    def native_value(self):
        block = self._data_block
        if not block:
            return None
        return block.get(self._metric)

    @property
    def extra_state_attributes(self) -> dict[str, str | None]:
        block = self._data_block
        if not block:
            return {}
        return {
            "current_at": block.get("current_at"),
            "peak_at": block.get("peak_at"),
            "low_at": block.get("low_at"),
        }

    @property
    def _data_block(self) -> dict | None:
        root = self.coordinator.data.get(self._category) if self.coordinator.data else None
        if not root:
            return None
        block = root.get(self._mode)
        if not isinstance(block, dict):
            return None
        return block
