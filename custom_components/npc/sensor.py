from homeassistant.components.sensor import SensorEntity
from homeassistant.const import CONF_USERNAME, STATE_UNKNOWN
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from .const import DOMAIN


async def async_setup_entry(hass, config_entry, async_add_entities):
    userevn = config_entry.data[CONF_USERNAME]
    sensor_map = {}

    async def handle_new_sensor(sensor_type, unique_id, payload, unit):
        if unique_id not in sensor_map:
            sensor = EVNSensor(hass, userevn, sensor_type, unique_id, unit)
            sensor_map[unique_id] = sensor
            sensor._state = payload
            async_add_entities([sensor])
        else:
            sensor_map[unique_id].update_state(payload)

    async def handle_sensor_attributes(sensor_type, unique_id, attributes):
        if unique_id in sensor_map:
            sensor_map[unique_id].update_attributes(attributes)
    async_dispatcher_connect(
        hass, f"evn_sensor_new_{userevn}", handle_new_sensor
    )
    async_dispatcher_connect(  # Thêm đăng ký tín hiệu attributes
        hass, f"evn_sensor_attributes_{userevn}", handle_sensor_attributes
    )
    return True

VIETNAMESE_NAMES = {
    "chi_so_dau_ky": "Chỉ số đầu kỳ",
    "chi_so_cuoi_ky": "Chỉ số cuối kỳ",
    "chi_so_tam_chot": "Chỉ số tạm chốt",
    "tieu_thu_thang_nay": "Tiêu thụ tháng này",
    "tieu_thu_hom_nay": "Tiêu thụ hôm nay",
    "tieu_thu_hom_qua": "Tiêu thụ hôm qua",
    "tieu_thu_hom_kia": "Tiêu thụ hôm kia",
    "tieu_thu_thang_truoc": "Tiêu thụ tháng trước",
    "tien_dien_thang_truoc": "Tiền điện tháng trước",
    "tien_dien_thang_nay": "Tiền điện tháng này",
    "lan_cap_nhat_cuoi": "Update Last",
    "chi_tiet_dien_tieu_thu_thang_nay": "Chi tiết tháng này",
    "tien_dien_san_luong_nam_nay": "Tiền điện sản lượng năm nay",
    "lich_cat_dien": "Lịch cắt điện",
    "cookie_status": "Trạng thái cookie",
}


class EVNSensor(SensorEntity):
    def __init__(self, hass, userevn, sensor_type, unique_id, unit=None):
        self._hass = hass
        self._userevn = userevn
        self._sensor_type = sensor_type
        self._unique_id = unique_id
        self._unit = unit
        self._state = STATE_UNKNOWN
        self._attributes = {}

    def update_state(self, payload):
        self._state = payload
        self.async_write_ha_state()

    def update_attributes(self, attributes):
        self._attributes = attributes
        self.async_write_ha_state()

    @property
    def name(self):
        return VIETNAMESE_NAMES.get(
            self._sensor_type, 
            self._sensor_type.replace('_', ' ').title()
        )

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def state(self):
        return self._state

    @property
    def unit_of_measurement(self):
        return self._unit

    @property
    def icon(self):
        ICON_MAPPING = {
            "cookie_status": "mdi:cookie",
            "chi_so_dau_ky": "mdi:transmission-tower-export",
            "chi_so_cuoi_ky": "mdi:transmission-tower-export",
            "chi_so_tam_chot": "mdi:transmission-tower-export",
            "tieu_thu_thang_nay": "mdi:transmission-tower-export",
            "tieu_thu_hom_nay": "mdi:transmission-tower-export",
            "tieu_thu_hom_qua": "mdi:transmission-tower-export",
            "tieu_thu_hom_kia": "mdi:transmission-tower-export",
            "tieu_thu_thang_truoc": "mdi:transmission-tower-export",
            "tien_dien_thang_truoc": "mdi:cash-multiple",
            "tien_dien_thang_nay": "mdi:cash-multiple",
            "lan_cap_nhat_cuoi": "mdi:clock-time-eight",
            "chi_tiet_dien_tieu_thu_thang_nay": "mdi:calendar-month",
            "tien_dien_san_luong_nam_nay": "mdi:calendar-month",
            "lich_cat_dien": "mdi:calendar-month",
        }
        return ICON_MAPPING.get(self._sensor_type, None)

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._userevn)},
            "name": f"EVN VN Device ({self._userevn})",
            "manufacturer": "EVN VN",
            "model": "Electricity Meter",
        }

    @property
    def should_poll(self):
        return False

    @property
    def extra_state_attributes(self):
        return self._attributes

    @property
    def device_class(self):
        if self._sensor_type == "lan_cap_nhat_cuoi":
            return "timestamp"
        return None
