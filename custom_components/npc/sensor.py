from homeassistant.components.sensor import SensorEntity
from homeassistant.const import CONF_USERNAME, STATE_UNKNOWN
from homeassistant.util import dt as dt_util
from calendar import monthrange
from datetime import timedelta, datetime
import logging
from .const import DOMAIN
from .utils import tinhngaydauky, laychisongay, laydientieuthungay, \
    laydientieuthuthang, laykhoangtieuthukynay, tinhtiendien, \
    layhoadon, set_lancapnhapcuoi, get_lancapnhapcuoi, \
    laylichcatdien, laychisongaygannhat
from .config_flow import CONF_NGAYDAUKY

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
        "chi_so_cuoi_ky", "chi_so_tam_chot",
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
    async_add_entities(entities)
    return True


VIETNAMESE_NAMES = {
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
        # Chỉ số cuối kỳ trước: chỉ số điện của ngày cuối kỳ trước
        if self._sensor_type == "chi_so_cuoi_ky":
            # Tính ngày cuối kỳ trước dựa trên ngaydauky
            _, _, _, prev_end_ky = tinhngaydauky(self._ngaydauky, today)
            # Thử lấy chỉ số trực tiếp từ ngày cuối kỳ trước
            chi_so = laychisongay(self._userevn, prev_end_ky.strftime("%Y-%m-%d"))
            # Nếu không tìm thấy chỉ số hoặc chỉ số <= 0, thử tìm chỉ số gần nhất
            if chi_so is None or chi_so <= 0:
                ngay_str = prev_end_ky.strftime('%d-%m-%Y')
                _LOGGER.debug(
                    f"Không tìm thấy chỉ số cuối kỳ trước cho ngày {ngay_str} "
                    f"hoặc chỉ số <= 0, thử tìm chỉ số gần nhất"
                )
                # Thử tìm chỉ số gần nhất SAU ngày cuối kỳ trước (reverse=False)
                chi_so_gan_nhat, ngay_gan_nhat = laychisongaygannhat(
                    self._userevn,
                    prev_end_ky.strftime("%Y-%m-%d"),
                    reverse=False  # Tìm ngày gần nhất SAU ngày cuối kỳ
                )
                if chi_so_gan_nhat is not None and chi_so_gan_nhat > 0:
                    _LOGGER.info(
                        f"Đã tìm thấy chỉ số gần nhất sau ngày cuối kỳ trước: "
                        f"{chi_so_gan_nhat} vào ngày {ngay_gan_nhat}"
                    )
                    chi_so = chi_so_gan_nhat
                    self._attributes = {
                        "Ngày": ngay_gan_nhat,
                        "Ghi chú": f"Sử dụng chỉ số gần nhất sau ngày {ngay_str}"
                    }
                    return chi_so
                else:
                    _LOGGER.warning(
                        f"Không tìm thấy chỉ số gần nhất sau ngày cuối kỳ trước {ngay_str}"
                    )
                    self._attributes = {"Ngày": ngay_str}
                    return 0
            else:
                self._attributes = {"Ngày": prev_end_ky.strftime("%d-%m-%Y")}
                return chi_so
        if self._sensor_type == "chi_so_tam_chot":
            chi_so, ngay = laychisongaygannhat(self._userevn, today.strftime("%Y-%m-%d"), reverse=True)
            if chi_so is not None:
                try:
                    ngay_fmt = datetime.strptime(ngay, "%d-%m-%Y").strftime("%d-%m-%Y")
                except Exception:
                    ngay_fmt = ngay
                self._attributes = {"Ngày": ngay_fmt}
                return format_kwh(chi_so)
            return 0
        # Tiêu thụ kỳ này: chỉ số tạm chốt - chỉ số cuối kỳ trước
        if self._sensor_type == "tieu_thu_ky_nay":
            # Lấy giá trị từ các cảm biến khác
            tam_chot_entity_id = f"sensor.{self._userevn}_chi_so_tam_chot"
            cuoi_ky_entity_id = f"sensor.{self._userevn}_chi_so_cuoi_ky"
            # Lấy trạng thái của các cảm biến
            tam_chot_state = self.hass.states.get(tam_chot_entity_id)
            cuoi_ky_state = self.hass.states.get(cuoi_ky_entity_id)
            # Cố gắng lấy giá trị từ cảm biến
            if tam_chot_state is not None and cuoi_ky_state is not None:
                try:
                    chi_so_tam_chot = float(tam_chot_state.state)
                    chi_so_cuoi_ky = float(cuoi_ky_state.state)
                    # Kiểm tra giá trị hợp lệ
                    if chi_so_tam_chot > 0 and chi_so_cuoi_ky > 0 and chi_so_tam_chot > chi_so_cuoi_ky:
                        tieu_thu = chi_so_tam_chot - chi_so_cuoi_ky
                        # Thêm thông tin thuộc tính
                        self._attributes = {
                            "Chỉ số tạm chốt": chi_so_tam_chot,
                            "Chỉ số cuối kỳ trước": chi_so_cuoi_ky
                        }
                        # Thêm ngày bắt đầu và kết thúc nếu có trong thuộc tính của cảm biến khác
                        if cuoi_ky_state.attributes.get("Ngày"):
                            self._attributes["Ngày bắt đầu"] = cuoi_ky_state.attributes.get("Ngày")
                        if tam_chot_state.attributes.get("Ngày"):
                            self._attributes["Ngày kết thúc"] = tam_chot_state.attributes.get("Ngày")
                        return format_kwh(tieu_thu)
                except (ValueError, TypeError):
                    _LOGGER.warning(
                        f"Không thể chuyển đổi giá trị cảm biến: tam_chot={tam_chot_state.state}, "
                        f"cuoi_ky={cuoi_ky_state.state}"
                    )
            # Nếu không lấy được từ cảm biến, tính trực tiếp
            _LOGGER.debug("Không thể lấy giá trị từ cảm biến, tính trực tiếp")
            # Lấy chỉ số tạm chốt trực tiếp
            chi_so_tam_chot, ngay_tam_chot = laychisongaygannhat(
                self._userevn, today.strftime("%Y-%m-%d"), reverse=True
            )
            # Tính ngày cuối kỳ trước
            _, _, _, prev_end_ky = tinhngaydauky(self._ngaydauky, today)
            # Lấy chỉ số cuối kỳ trước
            chi_so_cuoi_ky = laychisongay(self._userevn, prev_end_ky.strftime("%Y-%m-%d"))
            # Nếu không có chỉ số cuối kỳ trước, tìm chỉ số gần nhất sau ngày đó
            if chi_so_cuoi_ky is None or chi_so_cuoi_ky <= 0:
                chi_so_cuoi_ky, ngay_cuoi_ky = laychisongaygannhat(
                    self._userevn,
                    prev_end_ky.strftime("%Y-%m-%d"),
                    reverse=False
                )
            else:
                ngay_cuoi_ky = prev_end_ky.strftime("%d-%m-%Y")
            # Nếu có đủ dữ liệu, tính tiêu thụ
            if chi_so_tam_chot is not None and chi_so_cuoi_ky is not None:
                if chi_so_tam_chot > 0 and chi_so_cuoi_ky > 0 and chi_so_tam_chot > chi_so_cuoi_ky:
                    tieu_thu = chi_so_tam_chot - chi_so_cuoi_ky
                    # Thêm thông tin thuộc tính
                    self._attributes = {
                        "Chỉ số tạm chốt": chi_so_tam_chot,
                        "Chỉ số cuối kỳ trước": chi_so_cuoi_ky,
                        "Ngày bắt đầu": ngay_cuoi_ky,
                        "Ngày kết thúc": ngay_tam_chot
                    }
                    return format_kwh(tieu_thu)
            # Nếu không tính được, trả về 0
            self._attributes = {"Ghi chú": "Không đủ dữ liệu để tính tiêu thụ"}
            return 0

        # Tiền điện kỳ này: tiêu thụ kỳ này nhân công thức tính tiền điện
        if self._sensor_type == "tien_dien_ky_nay":
            # Lấy giá trị từ cảm biến tiêu thụ kỳ này
            tieu_thu_entity_id = f"sensor.{self._userevn}_tieu_thu_ky_nay"
            tieu_thu_state = self.hass.states.get(tieu_thu_entity_id)
            if tieu_thu_state is not None and tieu_thu_state.state not in ('unknown', 'unavailable', '0', '0.0'):
                try:
                    tieu_thu = float(tieu_thu_state.state)
                    if tieu_thu > 0:
                        tongtien, chi_tiet = tinhtiendien(tieu_thu)
                        self._attributes = {
                            "Tiêu thụ": tieu_thu,
                            "Chi tiết": chi_tiet
                        }
                        # Sao chép thuộc tính từ cảm biến tiêu thụ kỳ này
                        for key, value in tieu_thu_state.attributes.items():
                            if key not in self._attributes:
                                self._attributes[key] = value
                        return int(round(tongtien, 0)) if tongtien is not None else 0
                except (ValueError, TypeError):
                    pass
            # Phương pháp tính trực tiếp nếu không lấy được từ cảm biến
            _LOGGER.debug("Không thể lấy giá trị từ cảm biến tieu_thu_ky_nay, tính trực tiếp")
            # Tính tương tự như cảm biến tiêu thụ kỳ này
            chi_so_tam_chot, ngay_tam_chot = laychisongaygannhat(
                self._userevn, today.strftime("%Y-%m-%d"), reverse=True
            )
            _, _, _, prev_end_ky = tinhngaydauky(self._ngaydauky, today)
            chi_so_cuoi_ky = laychisongay(self._userevn, prev_end_ky.strftime("%Y-%m-%d"))
            if chi_so_cuoi_ky is None or chi_so_cuoi_ky <= 0:
                chi_so_cuoi_ky, ngay_cuoi_ky = laychisongaygannhat(
                    self._userevn,
                    prev_end_ky.strftime("%Y-%m-%d"),
                    reverse=False
                )
            else:
                ngay_cuoi_ky = prev_end_ky.strftime("%d-%m-%Y")
            if chi_so_tam_chot is not None and chi_so_cuoi_ky is not None:
                if chi_so_tam_chot > 0 and chi_so_cuoi_ky > 0 and chi_so_tam_chot > chi_so_cuoi_ky:
                    tieu_thu = chi_so_tam_chot - chi_so_cuoi_ky
                    tongtien, chi_tiet = tinhtiendien(tieu_thu)
                    self._attributes = {
                        "Tiêu thụ": tieu_thu,
                        "Chi tiết": chi_tiet,
                        "Chỉ số tạm chốt": chi_so_tam_chot,
                        "Chỉ số cuối kỳ trước": chi_so_cuoi_ky,
                        "Ngày bắt đầu": ngay_cuoi_ky,
                        "Ngày kết thúc": ngay_tam_chot
                    }
                    return int(round(tongtien, 0)) if tongtien is not None else 0
            self._attributes = {"Ghi chú": "Không đủ dữ liệu để tính tiền điện"}
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
                # Tính ngày cuối kỳ trước
                if self._ngaydauky == 1:
                    if today.month == 1:
                        end_prev = datetime(today.year - 1, 12, 31).date()
                    else:
                        last_day = (datetime(today.year, today.month, 1) - timedelta(days=1)).day
                        end_prev = datetime(today.year, today.month - 1, last_day).date()
                else:
                    end_prev = start_current - timedelta(days=1)
                # Tính ngày cuối kỳ trước nữa
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
                # Lấy chỉ số cuối kỳ trước
                chi_so_prev = laychisongay(self._userevn, end_prev.strftime("%Y-%m-%d"))
                # Nếu không có chỉ số cuối kỳ trước, tìm chỉ số gần nhất SAU ngày đó (tiến xuống)
                if chi_so_prev is None or chi_so_prev <= 0:
                    chi_so_prev, ngay_prev = laychisongaygannhat(
                        self._userevn,
                        end_prev.strftime("%Y-%m-%d"),
                        reverse=False  # Tìm chỉ số gần nhất SAU ngày cuối kỳ trước
                    )
                    end_prev_str = ngay_prev if chi_so_prev is not None else end_prev_str
                # Lấy chỉ số cuối kỳ trước nữa (đầu kỳ trước)
                chi_so_prev_prev = laychisongay(self._userevn, end_prev_prev.strftime("%Y-%m-%d"))
                # Nếu không có chỉ số cuối kỳ trước nữa, tìm chỉ số gần nhất TRƯỚC ngày đó (tiến lên)
                if chi_so_prev_prev is None or chi_so_prev_prev <= 0:
                    chi_so_prev_prev, ngay_prev_prev = laychisongaygannhat(
                        self._userevn,
                        end_prev_prev.strftime("%Y-%m-%d"),
                        reverse=True  # Tìm chỉ số gần nhất TRƯỚC ngày cuối kỳ trước nữa
                    )
                    end_prev_prev_str = ngay_prev_prev if chi_so_prev_prev is not None else end_prev_prev_str
                # Tính sản lượng nếu có đủ dữ liệu
                if chi_so_prev is not None and chi_so_prev_prev is not None and chi_so_prev > chi_so_prev_prev:
                    san_luong = chi_so_prev - chi_so_prev_prev
                    _LOGGER.debug(f"Tính tieu_thu_ky_truoc: {chi_so_prev} - {chi_so_prev_prev} = {san_luong}")
                    self._attributes.update({
                        "Tính theo chỉ số": True,
                        "Chỉ số đầu kỳ trước": format_kwh(chi_so_prev_prev),
                        "Chỉ số cuối kỳ trước": format_kwh(chi_so_prev),
                        "Ngày đầu kỳ trước": end_prev_prev_str,
                        "Ngày cuối kỳ trước": end_prev_str
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
                # Tính ngày cuối kỳ trước và ngày đầu kỳ trước
                start_current, _, end_current, _ = tinhngaydauky(self._ngaydauky, today)
                # Tính ngày cuối kỳ trước
                if self._ngaydauky == 1:
                    if today.month == 1:
                        end_prev = datetime(today.year - 1, 12, 31).date()
                    else:
                        last_day = (datetime(today.year, today.month, 1) - timedelta(days=1)).day
                        end_prev = datetime(today.year, today.month - 1, last_day).date()
                else:
                    end_prev = start_current - timedelta(days=1)
                # Tính ngày cuối kỳ trước nữa
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
                # Lấy chỉ số cuối kỳ trước
                chi_so_prev = laychisongay(self._userevn, end_prev.strftime("%Y-%m-%d"))
                # Nếu không có chỉ số cuối kỳ trước, tìm chỉ số gần nhất SAU ngày đó (tiến xuống)
                if chi_so_prev is None or chi_so_prev <= 0:
                    chi_so_prev, ngay_prev = laychisongaygannhat(
                        self._userevn,
                        end_prev.strftime("%Y-%m-%d"),
                        reverse=False  # Tìm chỉ số gần nhất SAU ngày cuối kỳ trước
                    )
                    end_prev_str = ngay_prev if chi_so_prev is not None else end_prev_str
                # Lấy chỉ số cuối kỳ trước nữa (đầu kỳ trước)
                chi_so_prev_prev = laychisongay(self._userevn, end_prev_prev.strftime("%Y-%m-%d"))
                # Nếu không có chỉ số cuối kỳ trước nữa, tìm chỉ số gần nhất TRƯỚC ngày đó (tiến lên)
                if chi_so_prev_prev is None or chi_so_prev_prev <= 0:
                    chi_so_prev_prev, ngay_prev_prev = laychisongaygannhat(
                        self._userevn,
                        end_prev_prev.strftime("%Y-%m-%d"),
                        reverse=True  # Tìm chỉ số gần nhất TRƯỚC ngày cuối kỳ trước nữa
                    )
                    end_prev_prev_str = ngay_prev_prev if chi_so_prev_prev is not None else end_prev_prev_str
                # Tính sản lượng nếu có đủ dữ liệu
                if chi_so_prev is not None and chi_so_prev_prev is not None and chi_so_prev > chi_so_prev_prev:
                    tieu_thu = chi_so_prev - chi_so_prev_prev
                    tien, tien_details = tinhtiendien(tieu_thu)
                    _LOGGER.debug(f"Tính tien_dien_ky_truoc theo công thức: {tieu_thu} kWh => {tien} VNĐ")
                    self._attributes.update({
                        "Tính theo công thức": True,
                        "Tiêu thụ": round(tieu_thu, 2),
                        "Chi tiết tính tiền": tien_details,
                        "Chỉ số đầu kỳ trước": format_kwh(chi_so_prev_prev),
                        "Chỉ số cuối kỳ trước": format_kwh(chi_so_prev),
                        "Ngày đầu kỳ trước": end_prev_prev_str,
                        "Ngày cuối kỳ trước": end_prev_str
                    })
                    return int(round(tien, 0)) if tien is not None else 0
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
            "manufacturer": "Smarthome Black",
            "model": "EVN VN",
            "sw_version": "2025.7.21",
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
