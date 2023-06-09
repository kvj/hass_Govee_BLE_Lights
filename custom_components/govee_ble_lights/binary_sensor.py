from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory


import logging

from .coordinator import BaseEntity
from .constants import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass,
    entry,
    async_add_entities
) -> None:
    entities = []
    coordinator = hass.data[DOMAIN]["devices"][entry.entry_id]
    entities.append(LastOpSuccess(coordinator._coordinator))
    async_add_entities(entities)


class LastOpSuccess(BaseEntity, BinarySensorEntity):

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = self._unique_id("last_op_success")
        self._attr_name = "Last Operation Status"
        self._attr_device_class = "connectivity"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        # self._attr_icon = "mdi:selection-marker"

    @property
    def is_on(self):
        return self._data.get("cmd_success", False)

    # @property
    # def extra_state_attributes(self):
    #     result = dict(min_distance=self._device.room_distance)
    #     for k, v in self._device.rooms.items():
    #         if v:
    #             result[k] = v.distance
    #     return result