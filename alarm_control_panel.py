"""Support for Freebox alarms."""
from datetime import timedelta
import logging
from typing import Dict, Optional

from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelEntityFeature,
    AlarmControlPanelState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .base_class import FreeboxHomeBaseClass
from .const import DOMAIN
from .router import FreeboxRouter

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry: ConfigEntry, async_add_entities) -> None:
    """Set up alarms."""
    router = hass.data[DOMAIN][entry.unique_id]
    tracked = set()

    @callback
    def update_callback():
        add_entities(hass, router, async_add_entities, tracked)

    router.listeners.append(
        async_dispatcher_connect(hass, router.signal_home_device_new, update_callback)
    )
    update_callback()


@callback
def add_entities(hass, router, async_add_entities, tracked):
    """Add new alarms from the router."""
    new_tracked = []

    for nodeId, node in router.home_devices.items():
        if node["category"] != "alarm":
            continue

        if nodeId in tracked:
            continue

        try:
            entity = FreeboxAlarm(hass, router, node)
            new_tracked.append(entity)
            tracked.add(nodeId)
        except Exception as e:
            _LOGGER.error(f"Error creating alarm entity for node {nodeId}: {e}")

    if new_tracked:
        async_add_entities(new_tracked, True)


class FreeboxAlarm(FreeboxHomeBaseClass, AlarmControlPanelEntity):
    """Representation of a Freebox alarm."""

    def __init__(self, hass, router: FreeboxRouter, node: Dict[str, any]) -> None:
        """Initialize an alarm."""
        super().__init__(hass, router, node)
        self._state: AlarmControlPanelState = AlarmControlPanelState.DISARMED
        self._supported_features = AlarmControlPanelEntityFeature.ARM_AWAY
        self.update_node()

    @property
    def alarm_state(self) -> AlarmControlPanelState:
        """Return the alarm state using the AlarmControlPanelState enum."""
        return self._state

    @property
    def supported_features(self) -> int:
        """Return the list of supported features."""
        return self._supported_features

    async def async_alarm_disarm(self, code=None) -> None:
        """Send disarm command."""
        if await self.set_home_endpoint_value(self._command_off):
            self._state = AlarmControlPanelState.DISARMED
            self.async_write_ha_state()

    async def async_alarm_arm_away(self, code=None) -> None:
        """Send arm away command."""
        if await self.set_home_endpoint_value(self._command_alarm1):
            self._state = AlarmControlPanelState.ARMING
            self.async_write_ha_state()

    async def async_alarm_arm_night(self, code=None) -> None:
        """Send arm night command."""
        if await self.set_home_endpoint_value(self._command_alarm2):
            self._state = AlarmControlPanelState.ARMING
            self.async_write_ha_state()

    async def async_update_node(self):
        """Get the state and update it."""
        self._state = await self.get_home_endpoint_value(self._command_state)
        self.async_write_ha_state()

    def update_node(self):
        """Update the alarm."""
        # Search if Alarm2
        has_alarm2 = False
        for nodeId, local_node in self._router.home_devices.items():
            alarm2 = next(
                filter(
                    lambda x: (x["name"] == "alarm2" and x["ep_type"] == "signal"),
                    local_node["show_endpoints"],
                ),
                None,
            )
            if alarm2:
                has_alarm2 = alarm2["value"]
                break

        if has_alarm2:
            self._supported_features = (
                AlarmControlPanelEntityFeature.ARM_AWAY |
                AlarmControlPanelEntityFeature.ARM_NIGHT
            )
        else:
            self._supported_features = AlarmControlPanelEntityFeature.ARM_AWAY
