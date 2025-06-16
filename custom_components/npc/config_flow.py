import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_USERNAME
import logging
from homeassistant.helpers import selector

_LOGGER = logging.getLogger(__name__)
CONF_NGAYDAUKY = "ngaydauky"

DATA_SCHEMA = vol.Schema({
    CONF_USERNAME: str,
    CONF_NGAYDAUKY: selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=1,
            max=31,
            mode=selector.NumberSelectorMode.BOX
        )
    ),
})


class EVNConfigFlow(config_entries.ConfigFlow, domain="npc"):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA)
        await self.async_set_unique_id(user_input[CONF_USERNAME])
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title=user_input[CONF_USERNAME],
            data=user_input
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler()


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow."""

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        errors = {}
        current_ngaydauky = self.config_entry.options.get(
            CONF_NGAYDAUKY,
            self.config_entry.data.get(CONF_NGAYDAUKY, 1)
        )
        if user_input is not None:
            try:
                ngaydauky = int(user_input[CONF_NGAYDAUKY])
                if 1 <= ngaydauky <= 31:
                    options = {CONF_NGAYDAUKY: ngaydauky}
                    return self.async_create_entry(title="", data=options)
                else:
                    errors[CONF_NGAYDAUKY] = "invalid_day"
            except (ValueError, KeyError) as ex:
                _LOGGER.error(f"Error processing options: {ex}")
                errors["base"] = "unknown"
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(CONF_NGAYDAUKY, default=current_ngaydauky): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1,
                        max=31,
                        mode=selector.NumberSelectorMode.BOX
                    )
                )
            }),
            errors=errors
        )
