import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_USERNAME

DATA_SCHEMA = vol.Schema({CONF_USERNAME: str})

class EVNConfigFlow(config_entries.ConfigFlow, domain="npc"):
    async def async_step_user(self, user_input=None):
        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA)
        await self.async_set_unique_id(user_input[CONF_USERNAME])
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title=user_input[CONF_USERNAME], data=user_input)
