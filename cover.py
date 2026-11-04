"""Volets de la Freebox Delta (ajout local, absent de l'intégration officielle).

- basic_shutter : volets Somfy RTS, sans retour de position. L'état est celui de
  la dernière commande, relu dans le signal « state » du nœud.
- shutter / opener : volets IO, stores et portes de garage avec position.
  Porté depuis l'ancien fork (FreeboxShutter), non testé sur matériel depuis.
"""

import base64
import logging
from typing import Any, override

from homeassistant.components.cover import (
    ATTR_POSITION,
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import FreeboxHomeCategory
from .entity import FreeboxHomeEntity
from .router import FreeboxConfigEntry, FreeboxRouter

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FreeboxConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Freebox shutters."""
    router = entry.runtime_data
    entities: list[CoverEntity] = []
    for node in router.home_devices.values():
        if node["category"] == FreeboxHomeCategory.SHUTTER:
            entities.append(FreeboxBasicShutter(router, node))
        elif node["category"] in (
            FreeboxHomeCategory.IO_SHUTTER,
            FreeboxHomeCategory.OPENER,
        ):
            entities.append(FreeboxShutter(router, node))
    async_add_entities(entities)


class FreeboxBasicShutter(FreeboxHomeEntity, CoverEntity):
    """Volet RTS : monter, descendre, stop, sans position."""

    _attr_device_class = CoverDeviceClass.SHUTTER
    _attr_supported_features = (
        CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE | CoverEntityFeature.STOP
    )
    _attr_name = None
    _attr_should_poll = False

    def __init__(self, router: FreeboxRouter, node: dict[str, Any]) -> None:
        """Initialize the shutter."""
        super().__init__(router, node)
        endpoints = node["show_endpoints"]
        self._command_up = self.get_command_id(endpoints, "slot", "up")
        self._command_down = self.get_command_id(endpoints, "slot", "down")
        self._command_stop = self.get_command_id(endpoints, "slot", "stop")
        self._attr_is_closed = self._to_closed(self.get_value("signal", "state"))

    @staticmethod
    def _to_closed(state: Any) -> bool | None:
        """Le signal « state » vaut True quand le volet est fermé."""
        return None if state is None else bool(state)

    @override
    async def async_update_signal(self) -> None:
        """Relit l'état connu de la Freebox à chaque rafraîchissement."""
        self._node = self._router.home_devices[self._id]
        self._attr_is_closed = self._to_closed(self.get_value("signal", "state"))
        await super().async_update_signal()

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the shutter."""
        await self.set_home_endpoint_value(self._command_up)
        self._attr_is_closed = False
        self.async_write_ha_state()

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the shutter."""
        await self.set_home_endpoint_value(self._command_down)
        self._attr_is_closed = True
        self.async_write_ha_state()

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop the shutter."""
        await self.set_home_endpoint_value(self._command_stop)
        self._attr_is_closed = None
        self.async_write_ha_state()


class FreeboxShutter(FreeboxHomeEntity, CoverEntity):
    """Volet IO, store ou porte de garage, avec position."""

    _attr_supported_features = (
        CoverEntityFeature.OPEN
        | CoverEntityFeature.CLOSE
        | CoverEntityFeature.SET_POSITION
        | CoverEntityFeature.STOP
    )
    _attr_name = None
    _attr_should_poll = False

    def __init__(self, router: FreeboxRouter, node: dict[str, Any]) -> None:
        """Initialize the cover."""
        super().__init__(router, node)
        endpoints = node["show_endpoints"]
        self._command_set_position = self.get_command_id(
            endpoints, "slot", "position_set"
        )
        self._command_stop = self.get_command_id(endpoints, "slot", "stop")
        self._attr_device_class = CoverDeviceClass.SHUTTER
        # La Freebox compte 0 = ouvert pour les volets IO, l'inverse de HA
        self._invert_position = True
        if node["category"] == FreeboxHomeCategory.OPENER:
            self._attr_device_class = CoverDeviceClass.AWNING
            if "Porte_Garage" in node["type"].get("icon", ""):  # Dexxo Smart IO
                self._invert_position = False
                self._attr_device_class = CoverDeviceClass.GARAGE
        self._update_current_position()

    @property
    def is_closed(self) -> bool | None:
        """Return if the cover is closed."""
        if self._attr_current_cover_position is None:
            return None
        return self._attr_current_cover_position == 0

    def _to_freebox(self, position: int) -> int:
        """Convertit une position HA en position Freebox, et inversement."""
        return 100 - position if self._invert_position else position

    @override
    async def async_update_signal(self) -> None:
        """Relit la position à chaque rafraîchissement."""
        self._node = self._router.home_devices[self._id]
        self._update_current_position()
        await super().async_update_signal()

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Move the cover to a specific position."""
        position = kwargs[ATTR_POSITION]
        await self.set_home_endpoint_value(
            self._command_set_position, self._to_freebox(position)
        )
        self._attr_current_cover_position = position
        self.async_write_ha_state()

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the cover."""
        await self.async_set_cover_position(**{ATTR_POSITION: 100})

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the cover."""
        await self.async_set_cover_position(**{ATTR_POSITION: 0})

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop the cover."""
        await self.set_home_endpoint_value(self._command_stop)
        self._update_current_position()
        self.async_write_ha_state()

    def _update_current_position(self) -> None:
        """Lit la position dans les signaux du nœud (logique de l'ancien fork)."""
        state = self.get_value("signal", "state")
        position_set = self.get_value("signal", "position_set")
        if position_set is None:
            self._attr_current_cover_position = None
            return
        try:
            hex_value = base64.b64decode(state).hex() if state else ""
        except (TypeError, ValueError):
            hex_value = ""
        if len(hex_value) != 118:
            self._attr_current_cover_position = self._to_freebox(position_set)
            return
        # Octet 50 de la trame d'état : 00 = ouvert, c8 = fermé
        flag = hex_value[100:102]
        if flag == "00":
            self._attr_current_cover_position = 100
        elif flag == "c8":
            self._attr_current_cover_position = 0
        elif 0 < position_set < 100:
            self._attr_current_cover_position = self._to_freebox(position_set)
        else:
            self._attr_current_cover_position = 50
        _LOGGER.debug("Position %s, trame %s", position_set, state)
