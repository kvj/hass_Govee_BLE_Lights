from __future__ import annotations
from .constants import DOMAIN, PLATFORMS
from .coordinator import DeviceCoordinator

from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers import service
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)

from homeassistant.components import bluetooth

import voluptuous as vol
import homeassistant.helpers.config_validation as cv
import logging

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
    }, extra=vol.ALLOW_EXTRA),
}, extra=vol.ALLOW_EXTRA)

async def async_setup_entry(hass: HomeAssistant, entry):
    data = entry.as_dict()["data"]

    device = DeviceCoordinator(hass, data)
    hass.data[DOMAIN]["devices"][entry.entry_id] = device
    await device.coordinator.async_config_entry_first_refresh()

    for p in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, p)
        )
    return True

async def async_unload_entry(hass: HomeAssistant, entry):
    for p in PLATFORMS:
        await hass.config_entries.async_forward_entry_unload(entry, p)
    hass.data[DOMAIN]["devices"].pop(entry.entry_id)
    return True


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    hass.data[DOMAIN] = {"devices": {}}

    async def async_exec(call):
        for entry_id in await service.async_extract_config_entry_ids(hass, call):
            await hass.data[DOMAIN]["devices"][entry_id].async_exec_cmds(call.data)

    hass.services.async_register(DOMAIN, "ble_command", async_exec)

    return True
