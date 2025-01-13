"""Represent the Freebox router and its devices and sensors."""
from __future__ import annotations

from datetime import datetime, timedelta
import logging
import os
from pathlib import Path
from typing import Any
from functools import partial
import ssl
import aiofiles

from freebox_api import Freepybox
from freebox_api.api.wifi import Wifi
from freebox_api.exceptions import HttpRequestError, InsufficientPermissionsError

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import slugify
from homeassistant.helpers import storage

from .const import (
    API_VERSION,
    APP_DESC,
    CONF_USE_HOME,
    CONNECTION_SENSORS,
    DOMAIN,
    STORAGE_KEY,
    STORAGE_VERSION,
)

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=10)

def _configure_ssl_context(api: Freepybox) -> None:
    """Configure the SSL context in a separate thread."""
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE
    ssl_ctx.set_alpn_protocols(['http/1.1'])
    api._ssl_context = ssl_ctx

async def get_api(hass: HomeAssistant, host: str) -> Freepybox:
    """Get the Freebox API."""
    store = storage.Store(hass, STORAGE_KEY, str(STORAGE_VERSION))
    freebox_path = store.path

    if not os.path.exists(freebox_path):
        await hass.async_add_executor_job(os.makedirs, freebox_path)

    token_file = Path(f"{freebox_path}/{slugify(host)}.conf")
    
    # Créer l'API avec un contexte SSL préconfiguré
    api = Freepybox(APP_DESC, token_file, API_VERSION)
    
    # Configuration SSL dans un executor
    await hass.async_add_executor_job(
        partial(_configure_ssl_context, api)
    )
    
    return api

async def reset_api(hass: HomeAssistant, host: str):
    """Delete the config file to be able to restart a new pairing process."""
    store = storage.Store(hass, STORAGE_KEY, str(STORAGE_VERSION))
    freebox_path = store.path
    token_file = Path(f"{freebox_path}/{slugify(host)}.conf")
    await hass.async_add_executor_job(token_file.unlink, True)

class FreeboxRouter:
    """Representation of a Freebox router."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize a Freebox router."""
        self.hass = hass
        self._entry = entry
        self._host = entry.data[CONF_HOST]
        self._port = entry.data[CONF_PORT]
        self._use_home = entry.options.get(
            CONF_USE_HOME, entry.data.get(CONF_USE_HOME, False)
        )

        self._api: Freepybox = None
        self.name = None
        self.mac = None
        self._sw_v = None
        self._attrs = {}

        self.devices: dict[str, dict[str, Any]] = {}
        self.disks: dict[int, dict[str, Any]] = {}
        self.sensors_temperature: dict[str, int] = {}
        self.sensors_connection: dict[str, float] = {}
        self.call_list: list[dict[str, Any]] = []
        self.home_devices: dict[str, Any] = {}

        self._unsub_dispatcher = None
        self._option_listener = None
        self.listeners = []
        self._warning_once = False

    async def setup(self) -> None:
        """Set up a Freebox router."""
        try:
            # Get API with preconfigured SSL context
            self._api = await get_api(self.hass, self._host)
            
            # Open connection
            await self._api.open(self._host, self._port)  # Revenons à la méthode standard
    
            # System
            fbx_config = await self._api.system.get_config()
            self.mac = fbx_config["mac"]
            self.name = fbx_config["model_info"]["pretty_name"]
            self._sw_v = fbx_config["firmware_version"]
    
        except HttpRequestError as e:
            _LOGGER.error("Failed to connect to Freebox: %s", str(e))
            raise ConfigEntryNotReady("Failed to connect to Freebox") from e
        except Exception as e:
            _LOGGER.error("Unexpected error while connecting to Freebox: %s", str(e))
            raise ConfigEntryNotReady(f"Unexpected error: {str(e)}") from e
    
        # Devices & sensors
        await self.update_all()
        self._unsub_dispatcher = async_track_time_interval(
            self.hass, self.update_all, SCAN_INTERVAL
        )

    async def update_all(self, now: datetime | None = None) -> None:
        """Update all Freebox platforms."""
        await self.update_device_trackers()
        await self.update_sensors()
        if self._use_home:
            await self.update_home_devices()

    async def update_device_trackers(self) -> None:
        """Update Freebox devices."""
        new_device = False
        fbx_devices: [dict[str, Any]] = await self._api.lan.get_hosts_list()

        # Adds the Freebox itself
        fbx_devices.append(
            {
                "primary_name": self.name,
                "l2ident": {"id": self.mac},
                "vendor_name": "Freebox SAS",
                "host_type": "router",
                "active": True,
                "attrs": self._attrs,
            }
        )

        for fbx_device in fbx_devices:
            device_mac = fbx_device["l2ident"]["id"]

            if self.devices.get(device_mac) is None:
                new_device = True

            self.devices[device_mac] = fbx_device

        async_dispatcher_send(self.hass, self.signal_device_update)

        if new_device:
            async_dispatcher_send(self.hass, self.signal_device_new)

    async def update_sensors(self) -> None:
        """Update Freebox sensors."""
        # System sensors
        syst_datas: dict[str, Any] = await self._api.system.get_config()

        # According to the doc `syst_datas["sensors"]` is temperature sensors in celsius degree.
        # Name and id of sensors may vary under Freebox devices.
        for sensor in syst_datas["sensors"]:
            if "value" in sensor:
                self.sensors_temperature[sensor["name"]] = sensor["value"]

        # Connection sensors
        connection_datas: dict[str, Any] = await self._api.connection.get_status()
        for sensor_key in CONNECTION_SENSORS:
            self.sensors_connection[sensor_key] = connection_datas[sensor_key]

        self._attrs = {
            "IPv4": connection_datas.get("ipv4"),
            "IPv6": connection_datas.get("ipv6"),
            "connection_type": connection_datas["media"],
            "uptime": datetime.fromtimestamp(
                round(datetime.now().timestamp()) - syst_datas["uptime_val"]
            ),
            "firmware_version": self._sw_v,
            "serial": syst_datas["serial"],
        }

        self.call_list = await self._api.call.get_calls_log()

        await self._update_disks_sensors()

        async_dispatcher_send(self.hass, self.signal_sensor_update)

    async def _update_disks_sensors(self) -> None:
        """Update Freebox disks."""
        # None at first request
        fbx_disks: [dict[str, Any]] = await self._api.storage.get_disks() or []

        for fbx_disk in fbx_disks:
            self.disks[fbx_disk["id"]] = fbx_disk

    async def update_home_devices(self) -> None:
        """Update Home devices (light, cover, alarm, sensors ...)."""
        new_device = False
        try:
            home_nodes: dict[str, Any] = await self._api.home.get_home_nodes()
        except InsufficientPermissionsError:
            _LOGGER.warning("Home access is not granted")
            return

        for home_node in home_nodes:
            if home_node["category"] not in [
                "pir",
                "camera",
                "alarm",
                "dws",
                "kfb",
                "basic_shutter",
                "opener",
                "shutter",
            ]:
                if self._warning_once is False:
                    _LOGGER.warning("Node not supported:\n" + str(home_node))
                continue

            if self.home_devices.get(home_node["id"]) is None:
                new_device = True
            self.home_devices[home_node["id"]] = home_node

        self._warning_once = True

        async_dispatcher_send(self.hass, self.signal_home_device_update)

        if new_device:
            async_dispatcher_send(self.hass, self.signal_home_device_new)

    async def reboot(self) -> None:
        """Reboot the Freebox."""
        await self._api.system.reboot()

    async def close(self) -> None:
        """Close the connection."""
        if self._api is not None:
            await self._api.close()
            self._api = None

        if self._unsub_dispatcher is not None:
            self._unsub_dispatcher()

        if self._option_listener is not None:
            self._option_listener()

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device information."""
        return {
            "connections": {(CONNECTION_NETWORK_MAC, self.mac)},
            "identifiers": {(DOMAIN, self.mac)},
            "name": self.name,
            "manufacturer": "Freebox SAS",
            "sw_version": self._sw_v,
        }

    @property
    def signal_device_new(self) -> str:
        """Event specific per Freebox entry to signal new device."""
        return f"{DOMAIN}-{self._host}-device-new"

    @property
    def signal_home_device_new(self) -> str:
        """Event specific per Freebox entry to signal new home device."""
        return f"{DOMAIN}-{self._host}-home-device-new"

    @property
    def signal_home_device_update(self) -> str:
        """Event specific per Freebox entry to signal update in home devices."""
        return f"{DOMAIN}-{self._host}-home-device-update"

    @property
    def signal_device_update(self) -> str:
        """Event specific per Freebox entry to signal updates in devices."""
        return f"{DOMAIN}-{self._host}-device-update"

    @property
    def signal_sensor_update(self) -> str:
        """Event specific per Freebox entry to signal updates in sensors."""
        return f"{DOMAIN}-{self._host}-sensor-update"

    @property
    def sensors(self) -> dict[str, Any]:
        """Return sensors."""
        return {**self.sensors_temperature, **self.sensors_connection}

    @property
    def wifi(self) -> Wifi:
        """Return the wifi."""
        return self._api.wifi
