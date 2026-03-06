from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant import config_entries

from .client import VattenfallClient
from .const import (
    CONF_ENABLE_BEURS,
    CONF_ENABLE_FLEX,
    CONF_SCAN_INTERVAL,
    DEFAULT_ENABLE_BEURS,
    DEFAULT_ENABLE_FLEX,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_ENABLE_FLEX, default=DEFAULT_ENABLE_FLEX): bool,
        vol.Optional(CONF_ENABLE_BEURS, default=DEFAULT_ENABLE_BEURS): bool,
        vol.Optional(
            CONF_SCAN_INTERVAL,
            default=DEFAULT_SCAN_INTERVAL,
        ): vol.All(int, vol.Range(min=300, max=86400)),
    }
)


async def _async_validate_input(hass, data: dict) -> None:
    client = VattenfallClient(hass)
    await client.async_get_summary(
        include_flex=data[CONF_ENABLE_FLEX],
        include_beurs=data[CONF_ENABLE_BEURS],
    )


class VattenfallConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None):
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()

            if not user_input[CONF_ENABLE_FLEX] and not user_input[CONF_ENABLE_BEURS]:
                errors['base'] = 'select_at_least_one'
            else:
                try:
                    await _async_validate_input(self.hass, user_input)
                except Exception:
                    _LOGGER.exception('Failed to validate Vattenfall integration setup')
                    errors['base'] = 'cannot_connect'
                else:
                    return self.async_create_entry(
                        title='Vattenfall Dynamic Prices',
                        data=user_input,
                    )

        return self.async_show_form(
            step_id='user',
            data_schema=STEP_SCHEMA,
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        return VattenfallOptionsFlow(config_entry)


class VattenfallOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict | None = None):
        errors: dict[str, str] = {}

        if user_input is not None:
            if not user_input[CONF_ENABLE_FLEX] and not user_input[CONF_ENABLE_BEURS]:
                errors['base'] = 'select_at_least_one'
            else:
                try:
                    await _async_validate_input(self.hass, user_input)
                except Exception:
                    _LOGGER.exception('Failed to validate Vattenfall integration options')
                    errors['base'] = 'cannot_connect'
                else:
                    return self.async_create_entry(title='', data=user_input)

        current = {**self.config_entry.data, **self.config_entry.options}

        return self.async_show_form(
            step_id='init',
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_ENABLE_FLEX,
                        default=current.get(CONF_ENABLE_FLEX, DEFAULT_ENABLE_FLEX),
                    ): bool,
                    vol.Optional(
                        CONF_ENABLE_BEURS,
                        default=current.get(CONF_ENABLE_BEURS, DEFAULT_ENABLE_BEURS),
                    ): bool,
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                        default=current.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                    ): vol.All(int, vol.Range(min=300, max=86400)),
                }
            ),
            errors=errors,
        )
