"""Support for Freebox Delta, Revolution and Mini 4K."""

import logging
from typing import Any, override

from freebox_api.exceptions import HttpRequestError, InsufficientPermissionsError

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .router import FreeboxConfigEntry, FreeboxRouter

_LOGGER = logging.getLogger(__name__)


SWITCH_DESCRIPTIONS = [
    SwitchEntityDescription(
        key="wifi",
        translation_key="wifi",
    )
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FreeboxConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the switch."""
    router = entry.runtime_data
    entities: list[SwitchEntity] = [
        FreeboxSwitch(router, entity_description)
        for entity_description in SWITCH_DESCRIPTIONS
    ]
    try:
        profiles = await router.get_profiles()
        # Reading a profile's access needs the parental control permission too
        for profile in profiles:
            await router.get_network_control(profile["id"])
    except InsufficientPermissionsError:
        _LOGGER.warning(
            "Home Assistant is not allowed to manage the Freebox parental control:"
            " no Internet access switch for the profiles. Grant the permission in"
            " Freebox OS, then reload the integration"
        )
        profiles = []
    except HttpRequestError as err:
        _LOGGER.warning("Unable to read the Freebox profiles: %s", err)
        profiles = []
    entities.extend(FreeboxProfileSwitch(router, profile) for profile in profiles)
    async_add_entities(entities, True)


class FreeboxSwitch(SwitchEntity):
    """Representation of a freebox switch."""

    _attr_has_entity_name = True

    def __init__(
        self, router: FreeboxRouter, entity_description: SwitchEntityDescription
    ) -> None:
        """Initialize the switch."""
        self.entity_description = entity_description
        self._router = router
        self._attr_device_info = router.device_info
        self._attr_unique_id = f"{router.mac} {entity_description.key}"

    async def _async_set_state(self, enabled: bool) -> None:
        """Turn the switch on or off."""
        try:
            await self._router.wifi.set_global_config({"enabled": enabled})
        except InsufficientPermissionsError:
            _LOGGER.warning(
                "Home Assistant does not have permissions to modify the Freebox"
                " settings. Please refer to documentation"
            )

    @override
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self._async_set_state(True)

    @override
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self._async_set_state(False)

    async def async_update(self) -> None:
        """Get the state and update it."""
        data = await self._router.wifi.get_global_config()
        self._attr_is_on = bool(data["enabled"])


class FreeboxProfileSwitch(SwitchEntity):
    """Internet access of a parental control profile: off pauses it."""

    _attr_has_entity_name = True
    _attr_translation_key = "profile_internet"

    def __init__(self, router: FreeboxRouter, profile: dict[str, Any]) -> None:
        """Initialize the switch."""
        self._router = router
        self._profile_id: int = profile["id"]
        self._attr_translation_placeholders = {"name": profile["name"].strip()}
        self._attr_device_info = router.device_info
        self._attr_unique_id = f"{router.mac} profile {self._profile_id} internet"

    async def _async_set_paused(self, paused: bool) -> None:
        """Pause or resume the Internet access of the profile."""
        try:
            await self._router.set_profile_paused(self._profile_id, paused)
        except InsufficientPermissionsError:
            _LOGGER.warning(
                "Home Assistant does not have permissions to manage the Freebox"
                " parental control. Please refer to documentation"
            )
            return
        await self.async_update()

    @override
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Lift the pause: the profile follows its planning again."""
        await self._async_set_paused(False)

    @override
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Pause the Internet access until it is turned on again."""
        await self._async_set_paused(True)

    async def async_update(self) -> None:
        """Get the state and update it."""
        data = await self._router.get_network_control(self._profile_id)
        self._attr_is_on = not (
            data.get("override") and data.get("override_mode") == "denied"
        )
        # What the devices get right now, planning included: allowed, denied, webonly
        self._attr_extra_state_attributes = {
            "current_mode": data.get("current_mode"),
            "override_until": data.get("override_until"),
        }
