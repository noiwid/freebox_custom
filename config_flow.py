"""Config flow to configure the Freebox integration."""

import logging
from typing import Any, override

from freebox_api.exceptions import AuthorizationError, HttpRequestError
import probatio

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .const import CONF_ALLOWED_USERS, DOMAIN
from .router import (
    async_forget_registration,
    get_api,
    get_hosts_list_if_supported,
    is_invalid_token_error,
)

_LOGGER = logging.getLogger(__name__)


class FreeboxFlowHandler(ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 2

    def __init__(self) -> None:
        """Initialize config flow."""
        self._data: dict[str, Any] = {}

    @staticmethod
    @callback
    @override
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow."""
        return FreeboxOptionsFlow()

    @override
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a flow initiated by the user."""
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=probatio.Schema(
                    {
                        probatio.Required(CONF_HOST): str,
                        probatio.Required(CONF_PORT): int,
                    }
                ),
                errors={},
            )

        self._data = user_input

        # Check if already configured
        # Uses the host/IP value from CONF_HOST as unique ID, which is no longer allowed
        # pylint: disable-next=home-assistant-unique-id-ip-based
        await self.async_set_unique_id(self._data[CONF_HOST])
        self._abort_if_unique_id_configured()

        return await self.async_step_link()

    async def async_step_link(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Attempt to link with the Freebox router.

        Given a configured host, will ask the user to press the button
        to connect to the router.
        """
        if user_input is None:
            return self.async_show_form(step_id="link")

        errors = {}

        fbx = await get_api(self.hass, self._data[CONF_HOST])
        try:
            # Open connection and check authentication
            await fbx.open(self._data[CONF_HOST], self._data[CONF_PORT])

            # Check permissions
            await fbx.system.get_config()
            await get_hosts_list_if_supported(fbx)

            # Close connection
            await fbx.close()

            return self.async_create_entry(
                title=self._data[CONF_HOST],
                data=self._data,
            )

        except AuthorizationError as error:
            _LOGGER.error(error)
            errors["base"] = "register_failed"
            if is_invalid_token_error(error):
                # The stored application token was rejected by the
                # Freebox. Clear it so resubmitting this form performs a
                # fresh pairing instead of retrying with the same
                # rejected token forever.
                await async_forget_registration(self.hass, self._data[CONF_HOST])

        except HttpRequestError:
            _LOGGER.error(
                "Error connecting to the Freebox router at %s", self._data[CONF_HOST]
            )
            errors["base"] = "cannot_connect"

        except Exception:
            _LOGGER.exception(
                "Unknown error connecting with Freebox router at %s",
                self._data[CONF_HOST],
            )
            errors["base"] = "unknown"

        return self.async_show_form(step_id="link", errors=errors)

    @override
    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> ConfigFlowResult:
        """Initialize flow from zeroconf."""
        zeroconf_properties = discovery_info.properties
        host = zeroconf_properties.get("api_domain")
        if not host:
            return self.async_abort(reason="missing_api_domain")
        port = zeroconf_properties.get("https_port") or discovery_info.port
        return await self.async_step_user({CONF_HOST: host, CONF_PORT: port})


class FreeboxOptionsFlow(OptionsFlow):
    """Options: who may pause a parental control profile from Home Assistant."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Choose the users allowed to turn the Internet access switches."""
        if user_input is not None:
            return self.async_create_entry(
                data={**self.config_entry.options, **user_input}
            )
        # System users (Supervisor, add-ons, cloud) never flip a switch
        users = sorted(
            (
                user
                for user in await self.hass.auth.async_get_users()
                if not user.system_generated and user.is_active
            ),
            key=lambda user: (user.name or "").lower(),
        )
        user_ids = {user.id for user in users}
        current = [
            user_id
            for user_id in self.config_entry.options.get(CONF_ALLOWED_USERS, [])
            if user_id in user_ids
        ]
        return self.async_show_form(
            step_id="init",
            data_schema=probatio.Schema(
                {
                    probatio.Optional(
                        CONF_ALLOWED_USERS, default=current
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                selector.SelectOptionDict(
                                    value=user.id,
                                    label=f"{user.name} (administrator)"
                                    if user.is_admin
                                    else (user.name or user.id),
                                )
                                for user in users
                            ],
                            multiple=True,
                            mode=selector.SelectSelectorMode.LIST,
                        )
                    ),
                }
            ),
        )
