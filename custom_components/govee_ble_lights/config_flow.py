from homeassistant import config_entries
import homeassistant.helpers.config_validation as cv
from .constants import DOMAIN

import voluptuous as vol
import logging

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema({
    vol.Required("name"): cv.string,
    vol.Required("address"): cv.string,
    vol.Required("model"): cv.string,
})


class ConfigFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):

    async def async_step_user(self, user_input):
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )
        _LOGGER.debug(f"Input: {user_input}")
        await self.async_set_unique_id(user_input["address"])
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title=user_input["name"], data=user_input)
