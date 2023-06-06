from __future__ import annotations
from .constants import DOMAIN, PLATFORMS
from .coordinator import DeviceCoordinator, do_exec

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
    for p in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, p)
        )
    return True

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    # hass.data[DOMAIN] = {"coordinator": DeviceCoordinator(hass, {})}
    devices = config.get(DOMAIN, {}).get("devices", [])
    _LOGGER.debug(f"async_setup(): devices: {devices}")

    async def async_exec(call):
        await do_exec(hass, call.data["address"], call.data)

    hass.services.async_register(DOMAIN, "ble_command", async_exec)

    return True
