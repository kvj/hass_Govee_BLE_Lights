from homeassistant.components import bluetooth
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from bleak import BleakClient

import logging
from datetime import timedelta

_LOGGER = logging.getLogger(__name__)

GOVEE_READ_CHAR = "00010203-0405-0607-0809-0a0b0c0d2b10"
GOVEE_WRITE_CHAR = "00010203-0405-0607-0809-0a0b0c0d2b11"

class DeviceCoordinator:

    def __init__(self, hass, config: dict):
        self._config = config
        self._hass = hass
        hass.async_create_task(
            self._discover()
        )

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
        self._connected = False
        try:
            _LOGGER.debug(f"Attempting to connect: {self._ble_device}")
            self._client = BleakClient(self._ble_device, self._on_disconnected)
            await self._client.connect()
            await self._client.start_notify(GOVEE_READ_CHAR, self._on_notify)
            self._connected = True
            _LOGGER.info(f"Connected to: {self._ble_device}")
            await self._cmd_toggle(True)
        except Exception as e:
            _LOGGER.warn(f"_connect(): failed to connect to {self._ble_device}: {e}")

    async def _cmd_toggle(self, is_on):
        _LOGGER.debug(f"Sending toggle... {is_on}")
        await self._send(_prepare_payload(0x01, [0x01 if is_on else 0x00]))

    async def _send(self, data):
        if not self._connected:
            _LOGGER.warn("Not connected, skip send")
            return False
        try:
            _LOGGER.debug(f"Sending: {data}")
            await self._client.write_gatt_char(GOVEE_WRITE_CHAR, data, False)
        except Exception as e:
            _LOGGER.exception(f"Failed to write GATT: {data}")



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


async def do_exec(hass, address, cmds):
    _LOGGER.debug(f"Exec BLE command: {address}, {cmds}")
    def on_disconnected(client):
        _LOGGER.debug("Connection done")
    async def on_notify(chr, data):
        _LOGGER.debug(f"on_notify(): {data}")
    try:
        ble_device = bluetooth.async_ble_device_from_address(hass, address.upper(), True)
        _LOGGER.debug(f"BLE Device: {ble_device}")
        client = BleakClient(ble_device if ble_device else address, on_disconnected)
        await client.connect()
        _LOGGER.debug(f"Connected: {ble_device}")
        await client.start_notify(GOVEE_READ_CHAR, on_notify)
        async def send(data):
            _LOGGER.debug(f"Sending: {data}")
            await client.write_gatt_char(GOVEE_WRITE_CHAR, data, False)
        if "brightness" in cmds:
            _LOGGER.debug(f"Set brightness: {cmds}")
            await send(_prepare_payload(0x04, [round(float(cmds["brightness"] / 100 * 0xff))]))
        if "on_off" in cmds:
            _LOGGER.debug(f"Toggle: {cmds}")
            await send(_prepare_payload(0x01, [0x01 if cmds["on_off"] else 0x00]))
        await client.disconnect()
        _LOGGER.debug(f"do_exec(): Done {ble_device} {cmds}")
    except Exception as e:
        _LOGGER.exception(f"do_exec()")
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
"""