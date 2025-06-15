from homeassistant.components.sensor import SensorEntity
from homeassistant.const import CONF_USERNAME, STATE_UNKNOWN
from homeassistant.util import dt as dt_util
from .const import DOMAIN
from .utils import tinhngaydauky, laychisongay, laydientieuthungay, \
    laydientieuthuthang, laykhoangtieuthukynay, tinhtiendien, \
    layhoadon, set_lancapnhapcuoi, get_lancapnhapcuoi, \
    laylichcatdien, laychisongaygannhat, tinhkytruoc
from .config_flow import CONF_NGAYDAUKY
from datetime import timedelta, datetime
import logging

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    userevn = config_entry.data[CONF_USERNAME]
    ngaydauky = None
    if config_entry.options and CONF_NGAYDAUKY in config_entry.options:
        ngaydauky = int(config_entry.options[CONF_NGAYDAUKY])
        _LOGGER.info(f"Setting up EVN VN sensors with ngaydauky={ngaydauky} from options")
    else:
        ngaydauky = int(config_entry.data.get(CONF_NGAYDAUKY, 1))
        _LOGGER.info(f"Setting up EVN VN sensors with ngaydauky={ngaydauky} from data")

    SENSOR_TYPES = [
        "chi_so_dau_ky", "chi_so_cuoi_ky", "chi_so_tam_chot",
        "tieu_thu_ky_nay", "tien_dien_ky_nay",
        "tieu_thu_ky_truoc", "tien_dien_ky_truoc",
        "tieu_thu_ky_truoc_nua", "tien_dien_ky_truoc_nua",
        "tieu_thu_hom_nay", "tieu_thu_hom_qua", "tieu_thu_hom_kia",
        "chi_tiet_dien_tieu_thu_ky_nay", "tien_dien_san_luong_nam_nay",
        "lich_cat_dien", "lan_cap_nhat_cuoi"
    ]
    entities = []
    for sensor_type in SENSOR_TYPES:
        unique_id = f"{userevn}_{sensor_type}"
        unit = None
        entities.append(EVNSensor(hass, userevn, sensor_type, unique_id, unit, ngaydauky))
        _LOGGER.debug(f"Adding {len(entities)} sensors for {userevn}")
    async_add_entities(entities)
    return True


VIETNAMESE_NAMES = {
    "chi_so_dau_ky": "Chỉ số đầu kỳ",
    "chi_so_cuoi_ky": "Chỉ số cuối kỳ trước",
    "chi_so_tam_chot": "Chỉ số tạm chốt",
    "tieu_thu_ky_nay": "Tiêu thụ kỳ này",
    "tien_dien_ky_nay": "Kỳ này",
    "tieu_thu_ky_truoc": "Tiêu thụ kỳ trước",
    "tien_dien_ky_truoc": "Kỳ trước",
    "tieu_thu_ky_truoc_nua": "Tiêu thụ kỳ trước nữa",
    "tien_dien_ky_truoc_nua": "Kỳ trước nữa",
    "tieu_thu_hom_nay": "Tiêu thụ hôm nay",
    "tieu_thu_hom_qua": "Tiêu thụ hôm qua",
    "tieu_thu_hom_kia": "Tiêu thụ hôm kia",
    "chi_tiet_dien_tieu_thu_ky_nay": "Chi tiết kỳ này",
    "tien_dien_san_luong_nam_nay": "Hóa đơn năm nay",
    "lich_cat_dien": "Lịch cắt điện",
    "lan_cap_nhat_cuoi": "Update Last",
}


class EVNSensor(SensorEntity):
    def __init__(self, hass, userevn, sensor_type, unique_id, unit=None, ngaydauky=1):
        self._hass = hass
        self._userevn = userevn
        self._sensor_type = sensor_type
        self._unique_id = unique_id
        self._unit = unit
        self._ngaydauky = ngaydauky
        self._state = STATE_UNKNOWN
        self._attributes = {}

    async def async_added_to_hass(self):
        """Run when entity is added to hass."""
        _LOGGER.debug(f"Added {self._sensor_type} sensor to hass for {self._userevn}")

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
        # Cập nhật thời gian mỗi lần bất kỳ cảm biến nào được truy cập
        set_lancapnhapcuoi(self._hass, self._userevn)
        today = dt_util.now().date()
        # Chỉ số đầu kỳ
        if self._sensor_type == "chi_so_dau_ky":
            start, _, _, _ = tinhngaydauky(self._ngaydauky, today)
            chi_so = laychisongay(self._userevn, start.strftime("%Y-%m-%d"))
            self._attributes = {"Ngày": start.strftime("%d-%m-%Y")}
            return chi_so if chi_so is not None else 0
        # Chỉ số cuối kỳ trước
        if self._sensor_type == "chi_so_cuoi_ky":
            _, _, _, prev_end_ky = tinhngaydauky(self._ngaydauky, today)
            chi_so = laychisongay(self._userevn, prev_end_ky.strftime("%Y-%m-%d"))
            self._attributes = {"Ngày": prev_end_ky.strftime("%d-%m-%Y")}
            return chi_so if chi_so is not None else 0
        if self._sensor_type == "chi_so_tam_chot":
            chi_so, ngay = laychisongaygannhat(self._userevn, today.strftime("%Y-%m-%d"))
            if chi_so is not None:
                # ngay có thể đã là string, cần convert về date trước khi format lại
                try:
                    ngay_fmt = datetime.strptime(ngay, "%Y-%m-%d").strftime("%d-%m-%Y")
                except Exception:
                    ngay_fmt = ngay
                self._attributes = {"Ngày": ngay_fmt}
                return chi_so
            return 0
        # Tiêu thụ kỳ này: chỉ số tạm chốt - chỉ số cuối kỳ trước
        if self._sensor_type == "tieu_thu_ky_nay":
            _, _, _, prev_end_ky = tinhngaydauky(self._ngaydauky, today)
            chi_so_prev = laychisongay(self._userevn, prev_end_ky.strftime("%Y-%m-%d"))
            chi_so_tam_chot, _ = laychisongaygannhat(self._userevn, today.strftime("%Y-%m-%d"))

            if chi_so_tam_chot is not None and chi_so_prev is not None:
                self._attributes = {
                    "Bắt đầu": tinhngaydauky(self._ngaydauky, today)[0].strftime("%d-%m-%Y"),
                    "Kết thúc": today.strftime("%d-%m-%Y")
                }
                return chi_so_tam_chot - chi_so_prev
            return 0
        # Tiền điện kỳ này: tiêu thụ kỳ này nhân công thức tính tiền điện
        if self._sensor_type == "tien_dien_ky_nay":
            _, _, _, prev_end_ky = tinhngaydauky(self._ngaydauky, today)
            chi_so_prev = laychisongay(self._userevn, prev_end_ky.strftime("%Y-%m-%d"))
            chi_so_tam_chot, _ = laychisongaygannhat(self._userevn, today.strftime("%Y-%m-%d"))
            if chi_so_tam_chot is not None and chi_so_prev is not None:
                tieu_thu = chi_so_tam_chot - chi_so_prev
                tongtien, _ = tinhtiendien(tieu_thu)
                self._attributes = {
                    "Bắt đầu": tinhngaydauky(self._ngaydauky, today)[0].strftime("%d-%m-%Y"),
                    "Kết thúc": today.strftime("%d-%m-%Y"),
                    "Tiêu thụ": tieu_thu
                }
                return tongtien if tongtien is not None else 0
            return 0
        # Tiêu thụ hôm nay
        if self._sensor_type == "tieu_thu_hom_nay":
            kwh = laydientieuthungay(self._userevn, today.strftime("%Y-%m-%d"))
            self._attributes = {"Ngày": today.strftime("%d-%m-%Y")}
            return kwh if kwh is not None else 0
        # Tiêu thụ hôm qua
        if self._sensor_type == "tieu_thu_hom_qua":
            yesterday = today - timedelta(days=1)
            kwh = laydientieuthungay(self._userevn, yesterday.strftime("%Y-%m-%d"))
            self._attributes = {"Ngày": yesterday.strftime("%d-%m-%Y")}
            return kwh if kwh is not None else 0
        # Tiêu thụ hôm kia
        if self._sensor_type == "tieu_thu_hom_kia":
            day_before = today - timedelta(days=2)
            kwh = laydientieuthungay(self._userevn, day_before.strftime("%Y-%m-%d"))
            self._attributes = {"Ngày": day_before.strftime("%d-%m-%Y")}
            return kwh if kwh is not None else 0
        # Tiêu thụ kỳ trước
        if self._sensor_type == "tieu_thu_ky_truoc":
            start, end, prev_month, prev_year = tinhkytruoc(self._ngaydauky, today, 1)
            _, san_luong = laydientieuthuthang(self._userevn, prev_month, prev_year)
            self._attributes = {
                "Bắt đầu": start.strftime("%d-%m-%Y"),
                "Kết thúc": end.strftime("%d-%m-%Y")
            }
            return san_luong if san_luong is not None else 0
        # Tiêu thụ kỳ trước nữa
        if self._sensor_type == "tieu_thu_ky_truoc_nua":
            start, end, prev_month, prev_year = tinhkytruoc(self._ngaydauky, today, 2)
            _, san_luong = laydientieuthuthang(self._userevn, prev_month, prev_year)
            self._attributes = {
                "Bắt đầu": start.strftime("%d-%m-%Y"),
                "Kết thúc": end.strftime("%d-%m-%Y")
            }
            return san_luong if san_luong is not None else 0
        # Tiền điện kỳ trước
        if self._sensor_type == "tien_dien_ky_truoc":
            start, end, prev_month, prev_year = tinhkytruoc(self._ngaydauky, today, 1)
            tien, _ = laydientieuthuthang(self._userevn, prev_month, prev_year)
            self._attributes = {
                "Bắt đầu": start.strftime("%d-%m-%Y"),
                "Kết thúc": end.strftime("%d-%m-%Y")
            }
            return tien if tien is not None else 0
        # Tiền điện kỳ trước nữa
        if self._sensor_type == "tien_dien_ky_truoc_nua":
            start, end, prev_month, prev_year = tinhkytruoc(self._ngaydauky, today, 2)
            tien, _ = laydientieuthuthang(self._userevn, prev_month, prev_year)
            self._attributes = {
                "Bắt đầu": start.strftime("%d-%m-%Y"),
                "Kết thúc": end.strftime("%d-%m-%Y")
            }
            return tien if tien is not None else 0
        # Chi tiết tiêu thụ kỳ này
        if self._sensor_type == "chi_tiet_dien_tieu_thu_ky_nay":
            today = dt_util.now().date()
            if self._ngaydauky == 1:
                start = today.replace(day=1)
            elif today.day < self._ngaydauky:
                prev_month = today.month - 1 if today.month > 1 else 12
                prev_year = today.year if today.month > 1 else today.year - 1
                start = today.replace(year=prev_year, month=prev_month, day=self._ngaydauky)
            else:
                start = today.replace(day=self._ngaydauky)
            end = today
            all_dates = [start + timedelta(days=i) for i in range((end - start).days + 1)][::-1]
            start_db = all_dates[-1].strftime("%d-%m-%Y")
            end_db = all_dates[0].strftime("%d-%m-%Y")
            rows = laykhoangtieuthukynay(self._userevn, start_db, end_db)
            rows_dict = {row[0].strip(): {"chi_so": row[1], "dien": row[2]} for row in rows} if rows else {}
            data = [
                {
                    "Ngày": d.strftime("%d-%m-%Y"),
                    "Chỉ số": rows_dict.get(d.strftime("%d-%m-%Y"), {}).get("chi_so", "Không có dữ liệu"),
                    "Điện tiêu thụ (kWh)": rows_dict.get(d.strftime("%d-%m-%Y"), {}).get("dien", "Không có dữ liệu")
                }
                for d in all_dates
            ]
            self._attributes = {
                "Bắt đầu": start.strftime("%d-%m-%Y"),
                "Kết thúc": end.strftime("%d-%m-%Y"),
                "Chi Tiết": data
            }
            return end.strftime("%m-%Y")
        # Tiền điện sản lượng năm nay
        if self._sensor_type == "tien_dien_san_luong_nam_nay":
            now = dt_util.now()
            rows = layhoadon(self._userevn, now.year)
            tien_dien_data = []
            san_luong_data = []
            sorted_rows = sorted(rows, key=lambda x: x[0], reverse=True)
            for row in sorted_rows:
                thang, tien_dien, san_luong_kwh = row
                thang_fmt = f"01-{int(thang):02d}-{now.year}"
                tien_dien_data.append({
                    "Tháng": thang_fmt,
                    "Năm": now.year,
                    "Tiền Điện": str(tien_dien)
                })
                san_luong_data.append({
                    "Tháng": thang_fmt,
                    "Năm": now.year,
                    "Điện tiêu thụ (KWh)": str(san_luong_kwh)
                })
            self._attributes = {
                "TienDien": tien_dien_data,
                "SanLuong": san_luong_data
            }
            return str(now.year)
        # Lịch cắt điện
        if self._sensor_type == "lich_cat_dien":
            lich_cat_dien = laylichcatdien(self._userevn)
            if lich_cat_dien:
                today_date = dt_util.now().date()
                future_events = [
                    event for event in lich_cat_dien
                    if datetime.strptime(event["Ngày"], "%d-%m-%Y").date() > today_date
                ]
                past_events = [
                    event for event in lich_cat_dien
                    if datetime.strptime(event["Ngày"], "%d-%m-%Y").date() <= today_date
                ]
                future_events.sort(key=lambda x: datetime.strptime(x["Ngày"], "%d-%m-%Y"))
                past_events.sort(key=lambda x: datetime.strptime(x["Ngày"], "%d-%m-%Y"), reverse=True)
                self._attributes = {
                    "Tương Lai": future_events,
                    "Quá Khứ": past_events
                }
                if future_events:
                    earliest_event = min(
                        future_events,
                        key=lambda x: datetime.strptime(x["Ngày"], "%d-%m-%Y")
                    )
                    self._attributes.update({
                        "Ngày": earliest_event["Ngày"],
                        "Thời gian từ": earliest_event["Thời gian từ"],
                        "Thời gian đến": earliest_event["Thời gian đến"],
                        "Khu vực": earliest_event["Khu vực"],
                        "Lý do": earliest_event["Lý do"],
                    })
                    return (
                        f"Có ({earliest_event['Ngày']} "
                        f"{earliest_event['Thời gian từ']} - "
                        f"{earliest_event['Thời gian đến']})"
                    )
                else:
                    return "Không có lịch cắt điện"
            else:
                self._attributes = {
                    "Tương Lai": [],
                    "Quá Khứ": []
                }
                return "Không có lịch cắt điện"
        # Thời gian cập nhật cuối cùng
        if self._sensor_type == "lan_cap_nhat_cuoi":
            last_update = get_lancapnhapcuoi(self._hass, self._userevn)
            self._attributes = {"device_class": "timestamp"}
            if last_update is not None:
                return last_update.isoformat()
            else:
                return None

    @property
    def icon(self):
        ICON_MAPPING = {
            "chi_so_dau_ky": "mdi:transmission-tower-export",
            "chi_so_cuoi_ky": "mdi:transmission-tower-export",
            "chi_so_tam_chot": "mdi:transmission-tower-export",
            "tieu_thu_ky_nay": "mdi:transmission-tower-export",
            "tieu_thu_hom_nay": "mdi:transmission-tower-export",
            "tieu_thu_hom_qua": "mdi:transmission-tower-export",
            "tieu_thu_hom_kia": "mdi:transmission-tower-export",
            "tieu_thu_ky_truoc": "mdi:transmission-tower-export",
            "tieu_thu_ky_truoc_nua": "mdi:transmission-tower-export",
            "tien_dien_ky_truoc": "mdi:cash-multiple",
            "tien_dien_ky_nay": "mdi:cash-multiple",
            "tien_dien_ky_truoc_nua": "mdi:cash-multiple",
            "lan_cap_nhat_cuoi": "mdi:clock-time-eight",
            "chi_tiet_dien_tieu_thu_ky_nay": "mdi:calendar-month",
            "tien_dien_san_luong_nam_nay": "mdi:calendar-month",
            "lich_cat_dien": "mdi:calendar-alert"
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

    async def async_update(self):
        pass

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return self._attributes

    @property
    def unit_of_measurement(self):
        if self._sensor_type == "tien_dien_san_luong_nam_nay":
            return None
        if self._sensor_type.startswith("chi_so_"):
            return "kWh"
        if self._sensor_type.startswith("tieu_thu"):
            return "kWh"
        if self._sensor_type.startswith("tien_dien"):
            return "VNĐ"
        return self._unit
