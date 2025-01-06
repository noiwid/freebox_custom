"""Freebox integration constants."""
import socket

from homeassistant.const import (
    UnitOfDataRate,
    PERCENTAGE,
)
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import UnitOfTemperature  # Nouveau import

DOMAIN = "freebox"
SERVICE_REBOOT = "reboot"
VALUE_NOT_SET = None

APP_DESC = {
    "app_id": "hass",
    "app_name": "Home Assistant",
    "app_version": "0.106",
    "device_name": socket.gethostname(),
}

API_VERSION = "v6"
PLATFORMS = [
    "device_tracker",
    "sensor",
    "switch",
    "cover",
    "alarm_control_panel",
    "camera",
    "binary_sensor"
]

DEFAULT_DEVICE_NAME = "Unknown device"
# to store the cookie
STORAGE_KEY = DOMAIN
STORAGE_VERSION = 1

# Sensor
SENSOR_NAME = "name"
SENSOR_UNIT = "unit"
SENSOR_ICON = "icon"
SENSOR_DEVICE_CLASS = "device_class"

CONNECTION_SENSORS = {
    "rate_down": {
        SENSOR_NAME: "Freebox download speed",
        SENSOR_UNIT: UnitOfDataRate.KILOBYTES_PER_SECOND,
        SENSOR_ICON: "mdi:download-network",
        SENSOR_DEVICE_CLASS: None,
    },
    "rate_up": {
        SENSOR_NAME: "Freebox upload speed",
        SENSOR_UNIT: UnitOfDataRate.KILOBYTES_PER_SECOND,
        SENSOR_ICON: "mdi:upload-network",
        SENSOR_DEVICE_CLASS: None,
    },
}

CALL_SENSORS = {
    "missed": {
        SENSOR_NAME: "Freebox missed calls",
        SENSOR_UNIT: None,
        SENSOR_ICON: "mdi:phone-missed",
        SENSOR_DEVICE_CLASS: None,
    },
}

DISK_PARTITION_SENSORS = {
    "partition_free_space": {
        SENSOR_NAME: "free space",
        SENSOR_UNIT: PERCENTAGE,
        SENSOR_ICON: "mdi:harddisk",
        SENSOR_DEVICE_CLASS: None,
    },
}

TEMPERATURE_SENSOR_TEMPLATE = {
    SENSOR_NAME: None,
    SENSOR_UNIT: UnitOfTemperature.CELSIUS,  # Remplacé ici
    SENSOR_ICON: "mdi:thermometer",
    SENSOR_DEVICE_CLASS: SensorDeviceClass.TEMPERATURE,
}

# Icons
DEVICE_ICONS = {
    "freebox_delta": "mdi:television-guide",
    "freebox_hd": "mdi:television-guide",
    "freebox_mini": "mdi:television-guide",
    "freebox_player": "mdi:television-guide",
    "ip_camera": "mdi:cctv",
    "ip_phone": "mdi:phone-voip",
    "laptop": "mdi:laptop",
    "multimedia_device": "mdi:play-network",
    "nas": "mdi:nas",
    "networking_device": "mdi:network",
    "printer": "mdi:printer",
    "router": "mdi:router-wireless",
    "smartphone": "mdi:cellphone",
    "tablet": "mdi:tablet",
    "television": "mdi:television",
    "vg_console": "mdi:gamepad-variant",
    "workstation": "mdi:desktop-tower-monitor",
}

# Home config
CONF_HAS_HOME = "has_home_api"
CONF_USE_HOME = "use_home_api"
PERMISSION_DEFAULT = 1
PERMISSION_HOME = 2
STATUS_PERMISSION_ERROR = 0
STATUS_OK = 1
STATUS_HAS_HOME = 2