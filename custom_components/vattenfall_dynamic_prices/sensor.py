from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import VattenfallConfigEntry
from .const import (
    ATTR_CURRENT_AT,
    ATTR_FORECAST,
    ATTR_FORECAST_COUNT,
    ATTR_LAST_REFRESH,
    ATTR_LOW_AT,
    ATTR_PEAK_AT,
    DOMAIN,
)


@dataclass(frozen=True, kw_only=True)
class VattenfallSensorDescription(SensorEntityDescription):
    section: str
    mode: str
    metric: str
    suggested_unit_of_measurement: str | None = None
    is_forecast: bool = False


SENSOR_DESCRIPTIONS: tuple[VattenfallSensorDescription, ...] = (
    VattenfallSensorDescription(
        key="electricity_flex_current",
        name="Stroom All-in huidig",
        section="electricity",
        mode="flex",
        metric="current",
        suggested_unit_of_measurement="€/kWh",
    ),
    VattenfallSensorDescription(
        key="electricity_flex_peak_24h",
        name="Stroom All-in piek 24 uur",
        section="electricity",
        mode="flex",
        metric="peak_24h",
        suggested_unit_of_measurement="€/kWh",
    ),
    VattenfallSensorDescription(
        key="electricity_flex_low_24h",
        name="Stroom All-in laagste 24 uur",
        section="electricity",
        mode="flex",
        metric="low_24h",
        suggested_unit_of_measurement="€/kWh",
    ),
    VattenfallSensorDescription(
        key="electricity_flex_forecast_24h",
        name="Stroom All-in forecast 24 uur",
        section="electricity",
        mode="flex",
        metric="current",
        suggested_unit_of_measurement="€/kWh",
        is_forecast=True,
    ),
    VattenfallSensorDescription(
        key="gas_flex_current",
        name="Gas All-in huidig",
        section="gas",
        mode="flex",
        metric="current",
        suggested_unit_of_measurement="€/m³",
    ),
    VattenfallSensorDescription(
        key="electricity_beurs_current",
        name="Stroom Beurs huidig",
        section="electricity",
        mode="beurs",
        metric="current",
        suggested_unit_of_measurement="€/kWh",
    ),
    VattenfallSensorDescription(
        key="electricity_beurs_peak_24h",
        name="Stroom Beurs piek 24 uur",
        section="electricity",
        mode="beurs",
        metric="peak_24h",
        suggested_unit_of_measurement="€/kWh",
    ),
    VattenfallSensorDescription(
        key="electricity_beurs_low_24h",
        name="Stroom Beurs laagste 24 uur",
        section="electricity",
        mode="beurs",
        metric="low_24h",
        suggested_unit_of_measurement="€/kWh",
    ),
    VattenfallSensorDescription(
        key="electricity_beurs_forecast_24h",
        name="Stroom Beurs forecast 24 uur",
        section="electricity",
        mode="beurs",
        metric="current",
        suggested_unit_of_measurement="€/kWh",
        is_forecast=True,
    ),
    VattenfallSensorDescription(
        key="gas_beurs_current",
        name="Gas Beurs huidig",
        section="gas",
        mode="beurs",
        metric="current",
        suggested_unit_of_measurement="€/m³",
    ),
)


async def async_setup_entry(hass, entry: VattenfallConfigEntry, async_add_entities) -> None:
    config = entry.options or entry.data

    entities = [
        VattenfallSensor(entry, description)
        for description in SENSOR_DESCRIPTIONS
        if (description.mode == "flex" and config.get("enable_flex", True))
        or (description.mode == "beurs" and config.get("enable_beurs", False))
    ]

    async_add_entities(entities)


class VattenfallSensor(CoordinatorEntity, SensorEntity):
    entity_description: VattenfallSensorDescription
    has_entity_name = False

    def __init__(self, entry: VattenfallConfigEntry, description: VattenfallSensorDescription) -> None:
        super().__init__(entry.runtime_data.coordinator)
        self.entity_description = description
        self._attr_name = description.name
        self._attr_unique_id = f"{DOMAIN}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, DOMAIN)},
            name="Vattenfall Dynamic Prices",
            manufacturer="Vattenfall",
        )

    @property
    def native_unit_of_measurement(self) -> str | None:
        return self.entity_description.suggested_unit_of_measurement

    @property
    def native_value(self) -> Any:
        block = self._data_block()
        return block.get(self.entity_description.metric)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        block = self._data_block()
        data = self.coordinator.data or {}
        attrs = {
            ATTR_LAST_REFRESH: data.get("last_refresh"),
            ATTR_CURRENT_AT: block.get("current_at"),
            ATTR_PEAK_AT: block.get("peak_at"),
            ATTR_LOW_AT: block.get("low_at"),
        }

        if self.entity_description.is_forecast:
            forecast = block.get("forecast_24h") or []
            attrs[ATTR_FORECAST] = forecast
            attrs[ATTR_FORECAST_COUNT] = len(forecast)

        return attrs

    def _data_block(self) -> dict[str, Any]:
        data = self.coordinator.data or {}
        return data.get(self.entity_description.section, {}).get(self.entity_description.mode, {})
