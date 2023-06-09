from homeassistant import config_entries
import homeassistant.helpers.config_validation as cv
from .constants import DOMAIN

import voluptuous as vol
import logging

_LOGGER = logging.getLogger(__name__)

class ConfigFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):

    async def async_step_bluetooth(self, info):
        _LOGGER.debug(f"BT Discovery: {info.as_dict()}")
        await self.async_set_unique_id(info.address)
        self._abort_if_unique_id_configured()
        self.info = {
            "address": info.address,
            "model": info.name.split("_")[1],
            "name": info.name,
        }
        return await self.async_step_input()
    
    async def async_step_user(self, user_input=None):
        self.info = {
            "address": "",
            "model": "",
            "name": "",
        }
        return await self.async_step_input()

    async def async_step_input(self, user_input=None):
        _LOGGER.debug(f"Input step: {user_input}")
        if user_input is None:
            schema = vol.Schema({
                vol.Required("name", default=self.info["name"]): cv.string,
                vol.Required("address", default=self.info["address"]): cv.string,
                vol.Required("model", default=self.info["model"]): cv.string,
            })
            return self.async_show_form(step_id="input", data_schema=schema)

        await self.async_set_unique_id(user_input["address"])
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title=user_input["name"], data=user_input, description_placeholders={
            "name": self.info["name"],
        })
