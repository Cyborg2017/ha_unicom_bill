"""Config flow for China Unicom Bill."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .const import (
    CONF_CREATE_INDIVIDUAL_SENSORS,
    CONF_OPENID,
    CONF_REFRESH_INTERVAL,
    DEFAULT_CREATE_INDIVIDUAL_SENSORS,
    DEFAULT_NAME,
    DEFAULT_REFRESH_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class UnicomBillConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for China Unicom Bill."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Basic validation
            if not user_input.get(CONF_OPENID):
                errors["base"] = "openid_required"
            else:
                return self.async_create_entry(
                    title=DEFAULT_NAME, data=user_input
                )

        data_schema = vol.Schema(
            {
                vol.Required(CONF_OPENID): str,
                vol.Required(
                    CONF_REFRESH_INTERVAL, default=DEFAULT_REFRESH_INTERVAL
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=60)),
                vol.Optional(
                    CONF_CREATE_INDIVIDUAL_SENSORS,
                    default=DEFAULT_CREATE_INDIVIDUAL_SENSORS,
                ): bool,
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> UnicomBillOptionsFlow:
        """Get the options flow for this handler."""
        return UnicomBillOptionsFlow(config_entry)


class UnicomBillOptionsFlow(config_entries.OptionsFlowWithConfigEntry):
    """Handle an options flow for China Unicom Bill."""

    VERSION = 1

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Manage the options."""
        if user_input is not None:
            # Update the config entry data
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data={
                    **self.config_entry.data,
                    **user_input,
                },
            )
            
            # Reload the integration to apply changes
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            
            return self.async_create_entry(title="", data={})

        options_schema = vol.Schema(
            {
                vol.Required(
                    CONF_OPENID,
                    default=self.config_entry.data.get(CONF_OPENID),
                ): str,
                vol.Required(
                    CONF_REFRESH_INTERVAL,
                    default=self.config_entry.data.get(
                        CONF_REFRESH_INTERVAL, DEFAULT_REFRESH_INTERVAL
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=60)),
                vol.Optional(
                    CONF_CREATE_INDIVIDUAL_SENSORS,
                    default=self.config_entry.data.get(
                        CONF_CREATE_INDIVIDUAL_SENSORS,
                        DEFAULT_CREATE_INDIVIDUAL_SENSORS,
                    ),
                ): bool,
            }
        )

        return self.async_show_form(step_id="init", data_schema=options_schema)
