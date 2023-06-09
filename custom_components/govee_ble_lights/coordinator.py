from homeassistant.components import bluetooth
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    CoordinatorEntity,
    UpdateFailed,
)
from homeassistant.util import color as color_util
from bleak import BleakClient

import logging
from datetime import timedelta

from .scenes import H7020

_LOGGER = logging.getLogger(__name__)

GOVEE_READ_CHAR = "00010203-0405-0607-0809-0a0b0c0d2b10"
GOVEE_WRITE_CHAR = "00010203-0405-0607-0809-0a0b0c0d2b11"

class BaseEntity(CoordinatorEntity):

    def __init__(self, coordinator: DataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_has_entity_name = True

    @property
    def _data(self):
        return self.coordinator.data

    @property
    def device_info(self):
        return {
            "identifiers": {
                ("govee_address", self._data["address"]),
            },
            "name": self._data["name"],
            "model": self._data["model"],
        }

    def _object_id(self, prefix):
        return "%s %s" % (self._data["name"], prefix)

    def _unique_id(self, prefix):
        return "govee_ble_%s_%s" % (self._data["address"], prefix)


class DeviceCoordinator:

    def __init__(self, hass, config: dict):
        self._config = config
        self._hass = hass
        self._data = {
            "name": config["name"],
            "address": config["address"],
            "model": config["model"],
        }
        self._coordinator = DataUpdateCoordinator(
            hass,
            _LOGGER,
            name="govee_ble_lights",
            update_method=self.async_update_data,
        )

    async def async_update_data(self):
        return self._data

    @property
    def coordinator(self) -> DataUpdateCoordinator:
        return self._coordinator

    async def _discover(self):
        def callback(info, change):
            _LOGGER.debug(f"async_setup_device():callback(): {info.address}, {info.name}, {change}")
        bluetooth.async_register_callback(self._hass, callback, None, "active")
        _LOGGER.debug(f"_discover: {bluetooth.async_scanner_count(self._hass, True)}, {bluetooth.async_scanner_count(self._hass, False)}")

    def _on_disconnected(self, client):
        self._client = None
        self._connected = False
        _LOGGER.debug(f"on_disconnected(): {self._ble_device}")

    async def _on_notify(self, chr, data):
        _LOGGER.debug(f"on_notify(): {data}")

    async def _connect(self):
        pass

    async def async_exec_cmds(self, cmds):
        address = self._config.get("address")
        _LOGGER.debug(f"Exec BLE command: {address}, {cmds}")
        def on_disconnected(client):
            _LOGGER.debug("Connection done")
        async def on_notify(chr, data):
            _LOGGER.debug(f"on_notify(): {data}")
        try:
            ble_device = bluetooth.async_ble_device_from_address(self._hass, address.upper(), True)
            _LOGGER.debug(f"BLE Device: {ble_device}")
            client = BleakClient(ble_device if ble_device else address, on_disconnected)
            await client.connect()
            _LOGGER.debug(f"Connected: {ble_device}")
            await client.start_notify(GOVEE_READ_CHAR, on_notify)
            async def send(data):
                _LOGGER.debug(f"Sending: {data}")
                await client.write_gatt_char(GOVEE_WRITE_CHAR, data, False)
            if "scene" in cmds:
                code = H7020.get(cmds["scene"])
                if code >= 0:
                    _LOGGER.debug(f"Applying scene: {code}")
                    await send(_prepare_payload(0x05, [0x04, code & 0xff, (code >> 8) & 0xff]))
                else:
                    _LOGGER.warn(f"Invalid scene: {cmds}")
            elif "music" in cmds:
                _LOGGER.debug(f"Music mode: {cmds}")
                await send(_prepare_payload(0x05, _prepare_music_req(cmds)))
            elif "video" in cmds:
                _LOGGER.debug(f"Video mode: {cmds}")
                await send(_prepare_payload(0x05, _prepare_video_req(cmds)))
            elif "color" in cmds or "temp" in cmds:
                _LOGGER.debug(f"Static color: {cmds}")
                await send(_prepare_payload(0x05, _prepare_color_req(cmds)))
            if "brightness" in cmds:
                _LOGGER.debug(f"Set brightness: {cmds}")
                await send(_prepare_payload(0x04, [cmds["brightness"]]))
            if "on_off" in cmds:
                _LOGGER.debug(f"Toggle: {cmds}")
                await send(_prepare_payload(0x01, [0x01 if cmds["on_off"] else 0x00]))
            await client.disconnect()
            _LOGGER.debug(f"do_exec(): Done {ble_device} {cmds}")
            self._data["cmd_success"] = True
        except Exception as e:
            _LOGGER.exception(f"do_exec()")
            self._data["cmd_success"] = False
        self._coordinator.async_set_updated_data(self._data)



def _prepare_payload(cmd, payload):
    if len(payload) > 17:
        raise ValueError('Payload too long')

    cmd = cmd & 0xFF
    payload = bytes(payload)

    frame = bytes([0x33, cmd]) + bytes(payload)
    # pad frame data to 19 bytes (plus checksum)
    frame += bytes([0] * (19 - len(frame)))
    
    # The checksum is calculated by XORing all data bytes
    checksum = 0
    for b in frame:
        checksum ^= b
    
    frame += bytes([checksum & 0xFF])
    return frame

def _prepare_video_req(cmds):
    # 00 00 - Part/All 00 - Movie/Game 32 - ?? 00 - sound 63 - sound sensivity 00 - ?? 41414141 - bri 00000000000067
    extra = cmds.get("extra", {})
    is_all = cmds["video"] == "all"
    is_game = extra.get("mode") == "game"
    is_sound = extra.get("sound_effect") == True
    resp = [0x00, 0x01 if is_all else 0x00, 0x01 if is_game else 0x00, 0x00, 0x01 if is_sound else 0x00]
    resp += [extra.get("sensivity", 100), 0x00]
    bri = extra.get("tv_brightness", [])
    if len(bri) != 4:
        bri = [100, 100, 100, 100]
    resp += bri
    return resp

def _prepare_music_req(cmds):
    # 03 - rhytm, 05 - energetic, 04 - spectrum, 06 - rolling
    mapping = {
        "rhytm": 0x03,
        "energetic": 0x05,
        "spectrum": 0x04,
        "rolling": 0x06,
    }
    extra = cmds.get("extra", {})
    is_calm = extra.get("mode", "calm") == "calm"
    resp = [0x13, mapping.get(cmds["music"]), extra.get("sensivity", 100), 0x01 if is_calm else 0x00]
    if "color" in cmds:
        rgb = cmds["color"]
        resp += [0x01, int(rgb[0]), int(rgb[1]), int(rgb[2])]
    return resp

def _prepare_color_req(cmds):
    def _prepare_mask_bytes():
        if "mask" not in cmds:
            return [0xff, 0xff, 0xff]
        val = 0
        for ch in cmds["mask"]:
            val = (val << 1) | (1 if ch in ("1", "x", "X", "+", "#") else 0)
        return [val & 0xff, (val >> 8) & 0xff, (val >> 16) & 0xff]
    resp = [0x15, 0x01]
    if "temp" in cmds:
        resp += [0x00, 0x00, 0x00]
        color_k = color_util.color_temperature_mired_to_kelvin(cmds["temp"])
        rgb = color_util.color_temperature_to_rgb(color_k)
        resp += [color_k & 0xff, (color_k >> 8) & 0xff] + [int(rgb[0]), int(rgb[1]), int(rgb[2])]
    else:
        rgb = cmds["color"]
        resp += [int(rgb[0]), int(rgb[1]), int(rgb[2])] + [0x00, 0x00, 0x00, 0x00, 0x00]
    resp += _prepare_mask_bytes()
    return resp

    pass


"""
H7020 color

33051501 00ffff 0000000000 807f 0000000000dd
33051501 ff0000 0000000000 ff7f 00000000005d
33051501 ffff00 0000000000 ff7f 0000000000a2
33051501 0000ff 0000000000 ff7f 00000000005d
33051501 8b00ff 0000000000 807f 0000000000a9
33051501 00ffff 0000000000 807f 0000000000dd
33051501 ffffff 07d0ff8d0b ff7f 0000000000f3
33051501 ffffff 22c4dae2ff ff7f 00000000007c
33051501 ffffff 14b4ffebd7 ff7f00 000000003e

33051501 ffffff 0000000000 555500 00000000dd
33051501 0000ff 0000000000 ffffff 0000000022
33051501 ffff00 0000000000 555555 0000000077
33051501 000000 07d0ff8d0b ffffff 0000000073
33051501 010101 0000000000 ffffff 00000000dc
33051501 000000 22c4dae2ff ffffff 00000000fc
33051501 000000 0c80ffc076 ffffff 0000000018
33051501 000000 1edce7eaff ffffff 00000000ed
33051501 ff0000 0000000000 333333 00000000ee
Scene
330504 4100 000000000000000000000000000073
330504 b10b 000000000000000000000000000088

Music
Value: 330513 05 630001ff 0000000000000000000000bd
Value: 330513 04 630001ff 0000000000000000000000bc
Value: 330513 06 630001ff 0000000000000000000000be
Value: 330513 06 2c0001ff 0000000000000000000000f1
Value: 330513 05 2c0001ff 0000000000000000000000f2
Value: 330513 05 630001ff 0000000000000000000000bd
Value: 33051501 00000000000000000000000000000022
Value: 3301000000000000000000000000000000000032
Value: 330908040802010200000000000000000000003f

Music:
03 - rhytm, 05 - energetic, 04 - spectrum, 06 - rolling

Value: 330513 05 63 00 01 ff0000 000000000000000000bd
Value: 330513 05 29 00 01 ff0000 000000000000000000f7
Value: 330513 05 63 00 01 ff0000 000000000000000000bd

Value: 330513 03 63 00 01 ff0000 000000000000000000bb
Value: 330513 03 2c 00 01 ff0000 000000000000000000f4
Value: 330513 03 5e 00 01 ff0000 00000000000000000086
Value: 330513 03 63 00 01 ff0000 000000000000000000bb
Value: 330513 03 63 01 01 ff0000 000000000000000000ba
Value: 330513 03 63 00 01 ff0000 000000000000000000bb

Value: 330513 04 63 00 01 ff0000 000000000000000000bc
Value: 330513 04 25 00 01 ff0000 000000000000000000fa
Value: 330513 04 61 00 01 ff0000 000000000000000000be
Value: 330513 04 63 00 01 ff0000 000000000000000000bc

Value: 330513 06 63 00 01 ff0000 000000000000000000be
Value: 330513 06 63 00 01 ffffff 000000000000000000be

Value: 330513 03 63 01 00 000000 00000000000000000044
Value: 330513 03 63 00 00 000000 00000000000000000045
Value: 330513 06 63 00 00 ffff00 00000000000000000040

Video:
Value: 330500 00 00 32 00 63001e4c1e4c00000000000067
Value: 330500 00 01 32 00 63001e4c1e4c00000000000066
Value: 330500 00 00 32 00 63001e4c1e4c00000000000067
Value: 330500 01 00 32 00 63001e4c1e4c00000000000066
Value: 330500 01 01 32 00 63001e4c1e4c00000000000067
Value: 330500 01 00 32 00 63001e4c1e4c00000000000066
Value: 330500 01 00 32 01 63001e4c1e4c00000000000067
Value: 330500 01 00 32 01 2b001e4c1e4c0000000000002f
Value: 330500 01 00 32 00 2b001e4c1e4c0000000000002e
Value: 330500 01 00 32 00 2b00646464640000000000002e
Value: 330500 01 00 32 00 2b00303030300000000000002e
Value: 330500 01 00 32 00 2b003030301900000000000007
Value: 330500 01 00 32 00 2b00213030210000000000002e
Value: 330500 01 00 32 00 63004141414100000000000066
Value: 330500 01 00 32 00 63004141414100000000000066
Value: 330500 00 00 32 00 63004141414100000000000067
"""