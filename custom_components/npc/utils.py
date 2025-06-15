import logging
import sqlite3
from datetime import datetime, timedelta
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Đường dẫn DB cho Home Assistant (dùng đường dẫn động để tương thích mọi môi trường)
DB_PATH = "/config/evnvn/evndata.db"


def set_lancapnhapcuoi(hass, userevn, dt=None):
    if dt is None:
        dt = datetime.now()
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
    if userevn not in hass.data[DOMAIN]:
        hass.data[DOMAIN][userevn] = {}
    hass.data[DOMAIN][userevn]['lancapnhapcuoi'] = dt


def get_lancapnhapcuoi(hass, userevn):
    try:
        return hass.data[DOMAIN][userevn]['lancapnhapcuoi']
    except Exception:
        return None


def tinhkytruoc(ngaydauky, today=None, ky_offset=1):
    """
    Trả về (ngày đầu kỳ, ngày cuối kỳ, tháng, năm) của kỳ trước hoặc kỳ trước nữa.
    """
    if today is None:
        today = datetime.now().date()
    elif hasattr(today, 'date'):
        today = today.date()
    # Tính ngày đầu kỳ hiện tại
    start_current, _, _, _ = tinhngaydauky(ngaydauky, today)
    prev_start = start_current
    for _ in range(ky_offset):
        if prev_start.month == 1:
            prev_month = 12
            prev_year = prev_start.year - 1
        else:
            prev_month = prev_start.month - 1
            prev_year = prev_start.year
        try:
            prev_start = prev_start.replace(year=prev_year, month=prev_month, day=ngaydauky)
        except ValueError:
            from calendar import monthrange
            last_day = monthrange(prev_year, prev_month)[1]
            day_to_use = min(ngaydauky, last_day)
            prev_start = prev_start.replace(year=prev_year, month=prev_month, day=day_to_use)
    # Ngày đầu kỳ
    start = prev_start
    # Ngày đầu kỳ tiếp theo (để tính ngày cuối kỳ)
    if start.month == 12:
        next_month = 1
        next_year = start.year + 1
    else:
        next_month = start.month + 1
        next_year = start.year
    try:
        next_start = start.replace(year=next_year, month=next_month, day=ngaydauky)
    except ValueError:
        from calendar import monthrange
        last_day = monthrange(next_year, next_month)[1]
        day_to_use = min(ngaydauky, last_day)
        next_start = start.replace(year=next_year, month=next_month, day=day_to_use)
    end = next_start - timedelta(days=1)
    return start, end, start.month, start.year

# Hàm xác định ngày đầu kỳ, cuối kỳ


def tinhngaydauky(ngaydauky, today=None):
    if today is None:
        today = datetime.now()
    day = today.day
    month = today.month
    year = today.year

    if ngaydauky == 1:
        start = today.replace(day=1)
    else:
        if day < ngaydauky:
            if month == 1:
                start = today.replace(year=year-1, month=12, day=ngaydauky)
            else:
                start = today.replace(month=month-1, day=ngaydauky)
        else:
            start = today.replace(day=ngaydauky)
    end = today
    if start.month == 12:
        next_month = 1
        next_year = start.year + 1
    else:
        next_month = start.month + 1
        next_year = start.year
    try:
        next_start = start.replace(year=next_year, month=next_month, day=ngaydauky)
    except ValueError:
        last_day_next_month = (start.replace(year=next_year, month=next_month+1, day=1) - timedelta(days=1)).day
        next_start = start.replace(year=next_year, month=next_month, day=last_day_next_month)
    end_ky = next_start - timedelta(days=1)
    prev_end_ky = start - timedelta(days=1)
    return start, end, end_ky, prev_end_ky

# Hàm tính tiền điện bậc thang
# Trả về: tổng tiền đã gồm thuế, dict chi tiết


def tinhtiendien(kwh):
    if kwh is None or kwh <= 0:
        return None, {}
    tiers = [
        {"limit": 50, "price": 1984}, {"limit": 50, "price": 2050}, {"limit": 100, "price": 2380},
        {"limit": 100, "price": 2998}, {"limit": 100, "price": 3350}, {"limit": float("inf"), "price": 3460}
    ]
    total_cost = 0
    remaining_kwh = kwh
    tier_details = []
    for i, tier in enumerate(tiers, 1):
        kwh_in_tier = min(remaining_kwh, tier["limit"])
        cost = kwh_in_tier * tier["price"]
        total_cost += cost
        tier_details.append({f"Bậc thang {i}": {"VNĐ/kWh": tier["price"], "kWh": kwh_in_tier, "Tính Tiền": cost}})
        remaining_kwh -= kwh_in_tier
        if remaining_kwh <= 0:
            break
    tax = total_cost * 0.08
    total_with_tax = total_cost + tax
    return total_with_tax, {"Tiền trước thuế": total_cost, "Thuế 8%": tax, "Chi tiết bậc thang": tier_details}

# Hàm truy vấn dữ liệu từ SQLite


def dinhdangngay(date_str):
    # Chuyển yyyy-mm-dd -> dd-mm-yyyy nếu đúng định dạng
    if isinstance(date_str, str) and len(date_str) == 10 and date_str[4] == "-":
        y, m, d = date_str.split("-")
        return f"{d}-{m}-{y}"
    return date_str


def laychisongay(userevn, date_str):
    date_str = dinhdangngay(date_str)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT chi_so FROM daily_consumption WHERE userevn=? AND ngay=?",
        (userevn, date_str)
    )
    row = cursor.fetchone()
    conn.close()
    _LOGGER.debug(f"laychisongay({userevn}, {date_str}) => {row}")
    if not row or row[0] is None or str(row[0]).strip().lower() == "không có dữ liệu":
        return None
    try:
        return float(row[0])
    except (TypeError, ValueError):
        return None


def laydientieuthungay(userevn, date_str):
    date_str = dinhdangngay(date_str)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT dien_tieu_thu_kwh FROM daily_consumption WHERE userevn=? AND ngay=?",
        (userevn, date_str)
    )
    row = cursor.fetchone()
    conn.close()
    _LOGGER.debug(f"laydientieuthungay({userevn}, {date_str}) => {row}")
    if not row or row[0] is None or str(row[0]).strip().lower() == "không có dữ liệu":
        return None
    try:
        return float(row[0])
    except (TypeError, ValueError):
        return None


def laydientieuthuthang(userevn, month, year):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT tien_dien, san_luong_kwh FROM monthly_bill WHERE userevn=? AND thang=? AND nam=?",
        (userevn, month, year)
    )
    row = cursor.fetchone()
    conn.close()
    _LOGGER.debug(f"laydientieuthuthang({userevn}, {month}, {year}) => {row}")
    if row:
        return float(row[0]) if row[0] is not None else None, float(row[1]) if row[1] is not None else None
    return None, None


def laychisongaygannhat(userevn, date_str, reverse=False):
    date_str = dinhdangngay(date_str)
    # Lấy ngày, tháng, năm từ date_str
    if isinstance(date_str, str) and len(date_str) == 10 and date_str[2] == "-":
        d, m, y = date_str.split("-")
    else:
        return None, None
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Ưu tiên lấy ngày gần nhất trong tháng/năm hiện tại, nếu không có thì trả về None
    query = (
        "SELECT ngay, chi_so FROM daily_consumption "
        "WHERE userevn=? AND ngay<=? "
        "AND substr(ngay,4,2)=? AND substr(ngay,7,4)=? "
        "AND chi_so IS NOT NULL AND chi_so != '' AND lower(chi_so) != 'không có dữ liệu' "
        "ORDER BY ngay DESC LIMIT 1"
    )
    cursor.execute(query, (userevn, date_str, m, y))
    row = cursor.fetchone()
    conn.close()
    _LOGGER.debug(f"laychisongaygannhat({userevn}, {date_str}, reverse={reverse}) => {row}")
    if row and row[1] is not None:
        try:
            ngay = row[0]
            # Nếu ngày là yyyy-mm-dd thì chuyển về dd-mm-yyyy
            if isinstance(ngay, str) and len(ngay) == 10 and ngay[4] == "-":
                y2, m2, d2 = ngay.split("-")
                ngay = f"{d2}-{m2}-{y2}"
            return float(row[1]), ngay
        except (TypeError, ValueError):
            return None, None
    return None, None


def laykhoangtieuthukynay(userevn, start_date, end_date):
    start_date = dinhdangngay(start_date)
    end_date = dinhdangngay(end_date)
    from datetime import datetime
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT ngay, chi_so, dien_tieu_thu_kwh FROM daily_consumption WHERE userevn=? ORDER BY ngay ASC",
        (userevn,)
    )
    rows = cursor.fetchall()
    conn.close()
    result = []
    try:
        start_dt = datetime.strptime(start_date, "%d-%m-%Y").date()
        end_dt = datetime.strptime(end_date, "%d-%m-%Y").date()
    except Exception:
        _LOGGER.error(f"laykhoangtieuthukynay: Lỗi chuyển đổi ngày {start_date} hoặc {end_date}")
        return []
    for row in rows:
        try:
            ngay_dt = datetime.strptime(row[0], "%d-%m-%Y").date()
            if start_dt <= ngay_dt <= end_dt:
                result.append(row)
        except Exception:
            continue
    _LOGGER.debug(f"laykhoangtieuthukynay({userevn}, {start_date}, {end_date}) => {result}")
    return result


def layhoadon(userevn, year):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT thang, tien_dien, san_luong_kwh FROM monthly_bill WHERE userevn=? AND nam=? ORDER BY thang ASC",
        (userevn, year)
    )
    rows = cursor.fetchall()
    conn.close()
    _LOGGER.debug(f"layhoadon({userevn}, {year}) => {rows}")
    return rows


def laylichcatdien(userevn):
    """Lấy lịch cắt điện từ database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT ngay_bat_dau, ngay_ket_thuc, thoi_gian_bat_dau,
               thoi_gian_ket_thuc, ly_do, khu_vuc
        FROM power_outage_schedule
        WHERE userevn=?
        ORDER BY ngay_bat_dau DESC
        """,
        (userevn,)
    )
    rows = cursor.fetchall()
    conn.close()
    _LOGGER.debug(f"laylichcatdien({userevn}) => {rows}")
    result = []
    for row in rows:
        if row[0]:
            result.append({
                "Ngày": row[0],
                "Thời gian từ": row[2],
                "Thời gian đến": row[3],
                "Lý do": row[4],
                "Khu vực": row[5]
            })
    return result
