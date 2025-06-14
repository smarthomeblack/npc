import logging
import json
from homeassistant import config_entries
from homeassistant.components import mqtt
from homeassistant.const import CONF_USERNAME
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers import config_validation as cv
from .const import DOMAIN
DOMAIN = "npc"
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
_LOGGER = logging.getLogger(__name__)

UNIT_MAPPING = {
    "chi_so_dau_ky": "kWh",
    "chi_so_cuoi_ky": "kWh",
    "chi_so_tam_chot": "kWh",
    "tieu_thu_thang_nay": "kWh",
    "tieu_thu_hom_nay": "kWh",
    "tieu_thu_hom_qua": "kWh",
    "tieu_thu_hom_kia": "kWh",
    "tieu_thu_thang_truoc": "kWh",
    "tien_dien_thang_truoc": "₫",
    "tien_dien_thang_nay": "₫",
}

async def async_setup(hass, config):
    return True

async def async_setup_entry(hass, entry):
    userevn = entry.data[CONF_USERNAME]
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {"userevn": userevn, "sensor_states": {}}
    
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])

    async def message_handler(msg):
        topic = msg.topic
        payload = str(msg.payload)
        parts = topic.split("/")
        sensor_type = parts[3]
        unique_id = f"{userevn}_{sensor_type}"

        if parts[-1] == "state":  # Giữ nguyên xử lý state
            hass.data[DOMAIN][entry.entry_id]["sensor_states"][unique_id] = payload
            unit = UNIT_MAPPING.get(sensor_type, None)
            async_dispatcher_send(hass, f"evn_sensor_new_{userevn}", sensor_type, unique_id, payload, unit)
        
        elif parts[-1] == "attributes":  # Thêm xử lý attributes
            try:
                attributes = json.loads(payload)  # Sửa: dùng payload trực tiếp, không decode
                async_dispatcher_send(hass, f"evn_sensor_attributes_{userevn}", sensor_type, unique_id, attributes)
            except json.JSONDecodeError:
                _LOGGER.error(f"Không thể parse JSON attributes cho {sensor_type}: {payload}")

    await mqtt.async_subscribe(
        hass, f"homeassistant/{userevn}/sensor/+/state", message_handler
    )
    await mqtt.async_subscribe(  # Thêm đăng ký chủ đề attributes
        hass, f"homeassistant/{userevn}/sensor/+/attributes", message_handler
    )
    _LOGGER.info(f"Subscribed to MQTT topics: homeassistant/{userevn}/sensor/+/state and homeassistant/{userevn}/sensor/+/attributes")
    return True
