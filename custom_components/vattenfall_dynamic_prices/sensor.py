from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_ENABLE_BEURS,
    CONF_ENABLE_FLEX,
    DEFAULT_ENABLE_BEURS,
    DEFAULT_ENABLE_FLEX,
    DOMAIN,
)
from .coordinator import VattenfallDataUpdateCoordinator


@dataclass(frozen=True, kw_only=True)
class VattenfallSensorDescription(SensorEntityDescription):
    section: str
    mode: str
    value_key: str


SENSOR_DESCRIPTIONS: tuple[VattenfallSensorDescription, ...] = (
    VattenfallSensorDescription(
        key='electricity_flex_current',
        name='Stroom FlexPrijs Huidig',
        section='electricity',
        mode='flex',
        value_key='current',
        native_unit_of_measurement='€/kWh',
    ),
    VattenfallSensorDescription(
        key='electricity_flex_peak_24h',
        name='Stroom FlexPrijs Hoogste 24h',
        section='electricity',
        mode='flex',
        value_key='peak_24h',
        native_unit_of_measurement='€/kWh',
    ),
    VattenfallSensorDescription(
        key='electricity_flex_low_24h',
        name='Stroom FlexPrijs Laagste 24h',
        section='electricity',
        mode='flex',
        value_key='low_24h',
        native_unit_of_measurement='€/kWh',
    ),
    VattenfallSensorDescription(
        key='electricity_beurs_current',
        name='Stroom Beursprijs Huidig',
        section='electricity',
        mode='beurs',
        value_key='current',
        native_unit_of_measurement='€/kWh',
    ),
    VattenfallSensorDescription(
        key='electricity_beurs_peak_24h',
        name='Stroom Beursprijs Hoogste 24h',
        section='electricity',
        mode='beurs',
        value_key='peak_24h',
        native_unit_of_measurement='€/kWh',
    ),
    VattenfallSensorDescription(
        key='electricity_beurs_low_24h',
        name='Stroom Beursprijs Laagste 24h',
        section='electricity',
        mode='beurs',
        value_key='low_24h',
        native_unit_of_measurement='€/kWh',
    ),
    VattenfallSensorDescription(
        key='gas_flex_current',
        name='Gas FlexPrijs Huidig',
        section='gas',
        mode='flex',
        value_key='current',
        native_unit_of_measurement='€/m³',
    ),
    VattenfallSensorDescription(
        key='gas_flex_peak_24h',
        name='Gas FlexPrijs Hoogste 24h',
        section='gas',
        mode='flex',
        value_key='peak_24h',
        native_unit_of_measurement='€/m³',
    ),
    VattenfallSensorDescription(
        key='gas_flex_low_24h',
        name='Gas FlexPrijs Laagste 24h',
        section='gas',
        mode='flex',
        value_key='low_24h',
        native_unit_of_measurement='€/m³',
    ),
    VattenfallSensorDescription(
        key='gas_beurs_current',
        name='Gas Beursprijs Huidig',
        section='gas',
        mode='beurs',
        value_key='current',
        native_unit_of_measurement='€/m³',
    ),
    VattenfallSensorDescription(
        key='gas_beurs_peak_24h',
        name='Gas Beursprijs Hoogste 24h',
        section='gas',
        mode='beurs',
        value_key='peak_24h',
        native_unit_of_measurement='€/m³',
    ),
    VattenfallSensorDescription(
        key='gas_beurs_low_24h',
        name='Gas Beursprijs Laagste 24h',
        section='gas',
        mode='beurs',
        value_key='low_24h',
        native_unit_of_measurement='€/m³',
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: VattenfallDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    config = {**entry.data, **entry.options}

    enable_flex = bool(config.get(CONF_ENABLE_FLEX, DEFAULT_ENABLE_FLEX))
    enable_beurs = bool(config.get(CONF_ENABLE_BEURS, DEFAULT_ENABLE_BEURS))

    entities: list[VattenfallSensor] = []

    for description in SENSOR_DESCRIPTIONS:
        if description.mode == 'flex' and not enable_flex:
            continue
        if description.mode == 'beurs' and not enable_beurs:
            continue
        entities.append(VattenfallSensor(coordinator, entry, description))

    async_add_entities(entities)


class VattenfallSensor(CoordinatorEntity[VattenfallDataUpdateCoordinator], SensorEntity):
    entity_description: VattenfallSensorDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: VattenfallDataUpdateCoordinator,
        entry: ConfigEntry,
        description: VattenfallSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f'{entry.entry_id}_{description.key}'
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name='Vattenfall Dynamic Prices',
            manufacturer='MiranoVerhoef',
            model='HACS Integration',
            configuration_url='https://www.vattenfall.nl/klantenservice/alles-over-je-dynamische-contract/',
        )

    @property
    def native_value(self):
        data = self.coordinator.data or {}
        return (
            ((data.get(self.entity_description.section) or {}).get(self.entity_description.mode) or {})
            .get(self.entity_description.value_key)
        )

    @property
    def extra_state_attributes(self) -> dict:
        data = self.coordinator.data or {}
        block = ((data.get(self.entity_description.section) or {}).get(self.entity_description.mode) or {})
        return {
            'last_update': data.get('last_update'),
            'current_at': block.get('current_at'),
            'peak_at': block.get('peak_at'),
            'low_at': block.get('low_at'),
        }
