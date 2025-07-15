from homeassistant.components.sensor import SensorEntity
from homeassistant.const import CONF_USERNAME, STATE_UNKNOWN
from homeassistant.util import dt as dt_util
from calendar import monthrange
from datetime import timedelta, datetime
import logging
import os
from .const import DOMAIN
from .utils import tinhngaydauky, laychisongay, laydientieuthungay, \
    laydientieuthuthang, laykhoangtieuthukynay, tinhtiendien, \
    layhoadon, set_lancapnhapcuoi, get_lancapnhapcuoi, \
    laylichcatdien, laychisongaygannhat, export_pdf_from_db
from .config_flow import CONF_NGAYDAUKY

CONF_MESSAGE_THREAD_ID = "message_thread_id"

# Thời gian scan file DB
SCAN_INTERVAL = timedelta(minutes=10)

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
        "lich_cat_dien", "lan_cap_nhat_cuoi", "tien_no"
    ]
    entities = []
    for sensor_type in SENSOR_TYPES:
        unique_id = f"{userevn}_{sensor_type}"
        unit = None
        entities.append(EVNSensor(hass, userevn, sensor_type, unique_id, unit, ngaydauky))
        _LOGGER.debug(f"Adding {len(entities)} sensors for {userevn}")
    # Thêm sensor tự động tải PDF
    pdf_unique_id = f"{userevn}_hoa_don"
    pdf_sensor = AutoPDFDownloadSensor(hass, userevn, pdf_unique_id, config_entry)
    entities.append(pdf_sensor)
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
    "hoa_don": "Hóa đơn",
    "tien_no": "Tiền nợ",
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

        def format_kwh(value):
            if value is None:
                return 0
            # Trả về int nếu là số nguyên, nếu không thì trả về round(value, 2) và loại bỏ phần thập phân dư thừa
            rounded = round(value, 2)
            return int(rounded) if rounded == int(rounded) else rounded
        # Chỉ số đầu kỳ
        if self._sensor_type == "chi_so_dau_ky":
            start, _, _, _ = tinhngaydauky(self._ngaydauky, today)
            chi_so = laychisongay(self._userevn, start.strftime("%Y-%m-%d"))
            self._attributes = {"Ngày": start.strftime("%d-%m-%Y")}
            return format_kwh(chi_so)
        # Chỉ số cuối kỳ trước
        if self._sensor_type == "chi_so_cuoi_ky":
            _, _, _, prev_end_ky = tinhngaydauky(self._ngaydauky, today)
            chi_so = laychisongay(self._userevn, prev_end_ky.strftime("%Y-%m-%d"))
            self._attributes = {"Ngày": prev_end_ky.strftime("%d-%m-%Y")}
            return format_kwh(chi_so)
        if self._sensor_type == "chi_so_tam_chot":
            chi_so, ngay = laychisongaygannhat(self._userevn, today.strftime("%Y-%m-%d"))
            if chi_so is not None:
                try:
                    ngay_fmt = datetime.strptime(ngay, "%Y-%m-%d").strftime("%d-%m-%Y")
                except Exception:
                    ngay_fmt = ngay
                self._attributes = {"Ngày": ngay_fmt}
                return format_kwh(chi_so)
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
                return format_kwh(chi_so_tam_chot - chi_so_prev)
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
                    "Tiêu thụ": round(tieu_thu, 2)
                }
                return int(round(tongtien, 0)) if tongtien is not None else 0
            return 0
        # Tiêu thụ hôm nay
        if self._sensor_type == "tieu_thu_hom_nay":
            kwh = laydientieuthungay(self._userevn, today.strftime("%Y-%m-%d"))
            self._attributes = {"Ngày": today.strftime("%d-%m-%Y")}
            return format_kwh(kwh)
        # Tiêu thụ hôm qua
        if self._sensor_type == "tieu_thu_hom_qua":
            yesterday = today - timedelta(days=1)
            kwh = laydientieuthungay(self._userevn, yesterday.strftime("%Y-%m-%d"))
            self._attributes = {"Ngày": yesterday.strftime("%d-%m-%Y")}
            return format_kwh(kwh)
        # Tiêu thụ hôm kia
        if self._sensor_type == "tieu_thu_hom_kia":
            day_before = today - timedelta(days=2)
            kwh = laydientieuthungay(self._userevn, day_before.strftime("%Y-%m-%d"))
            self._attributes = {"Ngày": day_before.strftime("%d-%m-%Y")}
            return format_kwh(kwh)
        # Tiêu thụ kỳ trước
        if self._sensor_type == "tieu_thu_ky_truoc":
            if self._ngaydauky == 1:
                thang = today.month - 1 if today.month > 1 else 12
                nam = today.year if today.month > 1 else today.year - 1
            else:
                if today.day < self._ngaydauky:
                    thang = today.month - 1 if today.month > 1 else 12
                    nam = today.year if today.month > 1 else today.year - 1
                else:
                    thang = today.month
                    nam = today.year
            _, san_luong = laydientieuthuthang(self._userevn, thang, nam)
            self._attributes = {
                "Tháng": f"{thang:02d}",
                "Năm": str(nam)
            }
            if san_luong is None:
                _LOGGER.debug("Không có dữ liệu tieu_thu_ky_truoc từ hóa đơn, tính theo chỉ số")
                start_current, _, end_current, _ = tinhngaydauky(self._ngaydauky, today)
                if self._ngaydauky == 1:
                    if today.month == 1:
                        end_prev = datetime(today.year - 1, 12, 31).date()
                    else:
                        last_day = (datetime(today.year, today.month, 1) - timedelta(days=1)).day
                        end_prev = datetime(today.year, today.month - 1, last_day).date()
                else:
                    end_prev = start_current - timedelta(days=1)
                if self._ngaydauky == 1:
                    if end_prev.month == 1:
                        end_prev_prev = datetime(end_prev.year - 1, 12, 31).date()
                    else:
                        last_day = (datetime(end_prev.year, end_prev.month, 1) - timedelta(days=1)).day
                        end_prev_prev = datetime(end_prev.year, end_prev.month - 1, last_day).date()
                else:
                    if end_prev.day < self._ngaydauky:
                        if end_prev.month == 1:
                            prev_start_month = 12
                            prev_start_year = end_prev.year - 1
                        else:
                            prev_start_month = end_prev.month - 1
                            prev_start_year = end_prev.year
                    else:
                        prev_start_month = end_prev.month
                        prev_start_year = end_prev.year
                    last_day_of_month = monthrange(prev_start_year, prev_start_month)[1]
                    day_to_use = min(self._ngaydauky, last_day_of_month)
                    prev_start = datetime(prev_start_year, prev_start_month, day_to_use).date()
                    end_prev_prev = prev_start - timedelta(days=1)
                end_prev_str = end_prev.strftime('%d-%m-%Y')
                end_prev_prev_str = end_prev_prev.strftime('%d-%m-%Y')
                _LOGGER.debug(f"Ngày cuối kỳ trước: {end_prev_str}, Ngày cuối kỳ trước nữa: {end_prev_prev_str}")
                chi_so_prev = laychisongay(self._userevn, end_prev.strftime("%Y-%m-%d"))
                chi_so_prev_prev = laychisongay(self._userevn, end_prev_prev.strftime("%Y-%m-%d"))
                if chi_so_prev is not None and chi_so_prev_prev is not None:
                    san_luong = chi_so_prev - chi_so_prev_prev
                    _LOGGER.debug(f"Tính tieu_thu_ky_truoc: {chi_so_prev} - {chi_so_prev_prev} = {san_luong}")
                    self._attributes.update({
                        "Tính theo chỉ số": True,
                        "Chỉ số đầu kỳ trước": format_kwh(chi_so_prev_prev),
                        "Chỉ số cuối kỳ trước": format_kwh(chi_so_prev)
                    })
            return format_kwh(san_luong)
        # Tiêu thụ kỳ trước nữa
        if self._sensor_type == "tieu_thu_ky_truoc_nua":
            if self._ngaydauky == 1:
                thang = today.month - 2 if today.month > 2 else (12 if today.month == 1 else 11)
                nam = today.year if today.month > 2 else today.year - 1
            else:
                if today.day < self._ngaydauky:
                    thang = today.month - 2 if today.month > 2 else (12 if today.month == 1 else 11)
                    nam = today.year if today.month > 2 else today.year - 1
                else:
                    thang = today.month - 1 if today.month > 1 else 12
                    nam = today.year if today.month > 1 else today.year - 1
            _, san_luong = laydientieuthuthang(self._userevn, thang, nam)
            self._attributes = {
                "Tháng": f"{thang:02d}",
                "Năm": str(nam)
            }
            return format_kwh(san_luong)
        # Tiền điện kỳ trước
        if self._sensor_type == "tien_dien_ky_truoc":
            if self._ngaydauky == 1:
                thang = today.month - 1 if today.month > 1 else 12
                nam = today.year if today.month > 1 else today.year - 1
            else:
                if today.day < self._ngaydauky:
                    thang = today.month - 1 if today.month > 1 else 12
                    nam = today.year if today.month > 1 else today.year - 1
                else:
                    thang = today.month
                    nam = today.year
            tien, _ = laydientieuthuthang(self._userevn, thang, nam)
            self._attributes = {
                "Tháng": f"{thang:02d}",
                "Năm": str(nam)
            }
            # Nếu không có dữ liệu từ hóa đơn tháng, tính bằng công thức tiền điện
            if tien is None:
                _LOGGER.debug("Không có dữ liệu tien_dien_ky_truoc từ hóa đơn, tính theo công thức")
                # Tạo một sensor tạm để lấy giá trị tiêu thụ kỳ trước
                temp_sensor = EVNSensor(self._hass, self._userevn, "tieu_thu_ky_truoc",
                                        f"{self._userevn}_tieu_thu_ky_truoc", None, self._ngaydauky)
                tieu_thu = temp_sensor.state
                if tieu_thu and tieu_thu > 0:
                    tien, tien_details = tinhtiendien(tieu_thu)
                    _LOGGER.debug(f"Tính tien_dien_ky_truoc theo công thức: {tieu_thu} kWh => {tien} VNĐ")
                    self._attributes.update({
                        "Tính theo công thức": True,
                        "Tiêu thụ": round(tieu_thu, 2),
                        "Chi tiết tính tiền": tien_details
                    })
                    if hasattr(temp_sensor, '_attributes'):
                        for key, value in temp_sensor._attributes.items():
                            if key not in self._attributes:
                                self._attributes[key] = value
            return int(round(tien, 0)) if tien is not None else 0
        # Tiền điện kỳ trước nữa
        if self._sensor_type == "tien_dien_ky_truoc_nua":
            if self._ngaydauky == 1:
                thang = today.month - 2 if today.month > 2 else (12 if today.month == 1 else 11)
                nam = today.year if today.month > 2 else today.year - 1
            else:
                if today.day < self._ngaydauky:
                    thang = today.month - 2 if today.month > 2 else (12 if today.month == 1 else 11)
                    nam = today.year if today.month > 2 else today.year - 1
                else:
                    thang = today.month - 1 if today.month > 1 else 12
                    nam = today.year if today.month > 1 else today.year - 1
            tien, _ = laydientieuthuthang(self._userevn, thang, nam)
            self._attributes = {
                "Tháng": f"{thang:02d}",
                "Năm": str(nam)
            }
            return int(round(tien, 0)) if tien is not None else 0
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
        # Tiền nợ
        if self._sensor_type == "tien_no":
            from .utils import lay_tien_no_evn
            tien_no, ngay_cap_nhat = lay_tien_no_evn(self._userevn)
            if tien_no is not None:
                self._attributes = {"Ngày cập nhật": ngay_cap_nhat}
                return tien_no
            else:
                self._attributes = {}
                return 0

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
            "tien_no": "mdi:cash-multiple",
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
        return True

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
        if self._sensor_type.startswith("tien_"):
            return "VNĐ"
        return self._unit


class AutoPDFDownloadSensor(SensorEntity):
    SCAN_INTERVAL = timedelta(minutes=10)

    def __init__(self, hass, userevn, unique_id, config_entry):
        self._hass = hass
        self._userevn = userevn
        self._unique_id = unique_id
        self._sensor_type = "hoa_don"
        self._state = STATE_UNKNOWN
        self._attributes = {}
        self._last_pdf_path = None
        self._last_result = None
        self._config_entry = config_entry

    async def async_added_to_hass(self):
        await self.async_update()

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
    def extra_state_attributes(self):
        return self._attributes

    @property
    def icon(self):
        return "mdi:file-pdf-box"

    @property
    def should_poll(self):
        return True

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._userevn)},
            "name": f"EVN VN Device ({self._userevn})",
            "manufacturer": "EVN VN",
            "model": "Electricity Meter",
        }

    async def async_update(self):
        import shutil
        try:
            pdf_infos = await self._hass.async_add_executor_job(
                export_pdf_from_db, self._userevn
            )
            if pdf_infos:
                num_downloaded = sum(1 for x in pdf_infos if x.get("downloaded"))
                num_total = len(pdf_infos)
                self._state = f"Đã lưu {num_total} file PDF, mới tải {num_downloaded}"
                self._last_pdf_path = pdf_infos
                self._last_result = "Thành công"
                self._attributes = {
                    "pdf_infos": pdf_infos,
                    "result": "Thành công"
                }
                # Gửi từng file PDF mới qua telegram_bot.send_document
                # Gửi từng file PNG qua zalo_bot.send_image
                if num_downloaded > 0:
                    www_dir = os.path.join(self._hass.config.path("www"), "evnvn")
                    if not os.path.exists(www_dir):
                        os.makedirs(www_dir, exist_ok=True)
                    for info in pdf_infos:
                        if info.get("downloaded") and os.path.exists(info["file"]):
                            basename = os.path.basename(info["file"])
                            temp_path = os.path.join(www_dir, basename)
                            try:
                                await self._hass.async_add_executor_job(shutil.copy2, info["file"], temp_path)
                                _LOGGER.debug(f"Đã copy file {info['file']} sang {temp_path}")
                            except Exception as copy_ex:
                                _LOGGER.debug(f"Lỗi khi copy file {info['file']} sang {temp_path}: {copy_ex}")
                                continue
                            caption = (
                                f"Hóa đơn điện {info['month']:02d}/{info['year']} cho {self._userevn}"
                            )
                            # Lấy message_thread_id từ config_entry
                            message_thread_id = None
                            try:
                                options = self._config_entry.options
                                data = self._config_entry.data
                                message_thread_id_raw = options.get(CONF_MESSAGE_THREAD_ID)
                                if not message_thread_id_raw:
                                    message_thread_id_raw = data.get(CONF_MESSAGE_THREAD_ID)
                                if message_thread_id_raw:
                                    try:
                                        message_thread_id = int(message_thread_id_raw)
                                        if message_thread_id <= 0:
                                            message_thread_id = None
                                    except Exception:
                                        message_thread_id = None
                            except Exception:
                                message_thread_id = None
                            payload = {
                                "file": temp_path,
                                "caption": caption
                            }
                            # Chỉ thêm nếu là số nguyên dương
                            if isinstance(message_thread_id, int) and message_thread_id > 0:
                                payload["message_thread_id"] = message_thread_id
                            try:
                                await self._hass.services.async_call(
                                    "telegram_bot", "send_document",
                                    payload,
                                    blocking=True
                                )
                            except Exception as send_ex:
                                _LOGGER.debug(f"Lỗi khi gửi file {temp_path} qua Telegram: {send_ex}")
                            try:
                                os.remove(temp_path)
                                _LOGGER.debug(f"Đã xóa file tạm {temp_path}")
                            except Exception as ex:
                                _LOGGER.debug(f"Không xóa được file tạm {temp_path}: {ex}")
                        # Gửi file PNG qua Zalo
                        png_files = info.get("png_files", [])
                        # Lấy cấu hình Zalo từ config_entry
                        zalo_thread_id = None
                        zalo_account_selection = "+84xxxxxxxxx"
                        zalo_type = "1"
                        try:
                            options = self._config_entry.options
                            data = self._config_entry.data
                            zalo_thread_id_raw = options.get("zalo_thread_id")
                            if not zalo_thread_id_raw:
                                zalo_thread_id_raw = data.get("zalo_thread_id")
                            # Đảm bảo zalo_thread_id là str
                            if zalo_thread_id_raw is not None:
                                zalo_thread_id = str(zalo_thread_id_raw)
                            else:
                                zalo_thread_id = ""
                            zalo_account_selection_raw = options.get("zalo_account_selection")
                            if not zalo_account_selection_raw:
                                zalo_account_selection_raw = data.get("zalo_account_selection")
                            if zalo_account_selection_raw:
                                zalo_account_selection = str(zalo_account_selection_raw)
                            zalo_type_raw = options.get("zalo_type")
                            if not zalo_type_raw:
                                zalo_type_raw = data.get("zalo_type")
                            if zalo_type_raw:
                                try:
                                    zalo_type = int(zalo_type_raw)
                                except Exception:
                                    zalo_type = 1
                        except Exception:
                            pass
                        for png_path in png_files:
                            zalo_image_path = os.path.join(www_dir, os.path.basename(png_path))
                            try:
                                await self._hass.async_add_executor_job(shutil.copy2, png_path, zalo_image_path)
                                _LOGGER.debug(f"Đã copy file {png_path} sang {zalo_image_path}")
                            except Exception as copy_ex:
                                _LOGGER.debug(f"Lỗi khi copy file {png_path} sang {zalo_image_path}: {copy_ex}")
                                continue
                            zalo_payload = {
                                "image_path": zalo_image_path,
                                "thread_id": zalo_thread_id,
                                "account_selection": zalo_account_selection,
                                "type": zalo_type
                            }
                            try:
                                await self._hass.services.async_call(
                                    "zalo_bot", "send_image",
                                    zalo_payload,
                                    blocking=True
                                )
                            except Exception as zalo_ex:
                                _LOGGER.debug(f"Lỗi khi gửi ảnh {zalo_image_path} qua Zalo: {zalo_ex}")
                            try:
                                os.remove(zalo_image_path)
                                _LOGGER.debug(f"Đã xóa file tạm {zalo_image_path}")
                            except Exception as ex:
                                _LOGGER.debug(f"Không xóa được file tạm {zalo_image_path}: {ex}")
            else:
                self._state = "Không tìm thấy PDF nào"
                self._last_result = "Không tìm thấy PDF"
                self._attributes = {
                    "pdf_infos": [],
                    "result": "Không tìm thấy PDF"
                }
        except Exception as e:
            import traceback
            _LOGGER.debug(f"[AutoPDFDownloadSensor] Exception: {e}\n{traceback.format_exc()}")
            self._state = "Lỗi"
            self._last_result = str(e)
            self._attributes = {
                "pdf_infos": [],
                "result": f"Lỗi: {e}"
            }
