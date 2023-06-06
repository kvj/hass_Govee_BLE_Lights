from homeassistant import config_entries
from .constants import DOMAIN

import logging

_LOGGER = logging.getLogger(__name__)

class ConfigFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):

    async def async_step_user(self, user_input):
        return self.async_create_entry(
            title="MQTT Room NG",
            options={},
            data={},
        )
