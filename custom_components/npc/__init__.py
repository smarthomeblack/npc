import logging
from homeassistant.const import CONF_USERNAME
from homeassistant.helpers import config_validation as cv
from .const import DOMAIN

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
_LOGGER = logging.getLogger(__name__)


async def async_setup(hass, config):
    """Set up EVN VN from yaml configuration."""
    return True


async def async_setup_entry(hass, entry):
    """Set up EVN VN from a config entry."""
    userevn = entry.data[CONF_USERNAME]
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {"userevn": userevn}
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    return True


async def async_unload_entry(hass, entry):
    """Unload a config entry."""
    return await hass.config_entries.async_forward_entry_unload(entry, "sensor")


async def async_reload_entry(hass, entry):
    """Reload config entry."""
    # Lấy thông tin người dùng trước khi unload
    userevn = entry.data[CONF_USERNAME]

    # Chỉ log thông tin mà không làm gì cả
    _LOGGER.info(f"Config changed for {userevn} - Manual restart required")

    # Trả về True để không gây lỗi cho HA
    return True
