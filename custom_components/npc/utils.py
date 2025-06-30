import logging
import sqlite3
from datetime import datetime, timedelta
from .const import DOMAIN
import os

_LOGGER = logging.getLogger(__name__)
DB_PATH = "/config/evnvn/evndata.db"
PDF_PATH = "/config/evnvn"


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


def chuyen_doi_so(value):
    """Chuyển đổi số từ format Việt Nam (dấu phẩy) sang format Python (dấu chấm)"""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        # Loại bỏ khoảng trắng và chuyển dấu phẩy thành dấu chấm
        value = value.strip().replace(',', '.')
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    return None


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
    return chuyen_doi_so(row[0])


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
    return chuyen_doi_so(row[0])


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
        return chuyen_doi_so(row[0]), chuyen_doi_so(row[1])
    return None, None


def laychisongaygannhat(userevn, date_str, reverse=False):
    """
    Lấy chỉ số điện ngày gần nhất trong tháng/năm của date_str
    - userevn: mã khách hàng
    - date_str: ngày dạng yyyy-mm-dd hoặc dd-mm-yyyy
    - reverse: nếu True thì lấy ngày xa nhất, False thì lấy ngày gần nhất
    """
    # Fix lỗi date_str là None hoặc không đúng định dạng
    if not date_str or not isinstance(date_str, str) or len(date_str) != 10:
        _LOGGER.error(f"laychisongaygannhat: date_str không hợp lệ: {date_str}")
        return None, None
    # Tạo db_date (dd-mm-yyyy) từ date_str
    if date_str[4] == '-':  # yyyy-mm-dd
        y, m, d = date_str.split('-')
        date_str_db = f"{d}-{m}-{y}"
        _LOGGER.debug(f"laychisongaygannhat: Chuyển từ yyyy-mm-dd ({date_str}) -> dd-mm-yyyy ({date_str_db})")
    elif date_str[2] == '-':  # dd-mm-yyyy
        date_str_db = date_str
        _LOGGER.debug(f"laychisongaygannhat: Giữ nguyên dd-mm-yyyy: {date_str_db}")
    else:
        _LOGGER.error(f"laychisongaygannhat: Định dạng date_str không đúng: {date_str}")
        return None, None
    # Lấy các thành phần ngày, tháng, năm
    try:
        d, m, y = date_str_db.split("-")
        _LOGGER.debug(f"laychisongaygannhat: Trích xuất d={d}, m={m}, y={y} từ {date_str_db}")
    except Exception as e:
        _LOGGER.error(f"laychisongaygannhat: Lỗi tách date_str_db: {date_str_db}, lỗi: {str(e)}")
        return None, None
    # Thực hiện truy vấn DB
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        order_direction = "ASC" if reverse else "DESC"
        order_by_clause = (
            f"ORDER BY substr(ngay,7,4) {order_direction}, "
            f"substr(ngay,4,2) {order_direction}, "
            f"substr(ngay,1,2) {order_direction}"
        )
        query = (
            "SELECT ngay, chi_so FROM daily_consumption "
            "WHERE userevn=? "
            "AND substr(ngay,4,2)=? AND substr(ngay,7,4)=? "
            "AND chi_so IS NOT NULL AND chi_so != '' "
            "AND lower(chi_so) != 'không có dữ liệu' AND chi_so != 'Khôngcódữliệu' "
            f"{order_by_clause} LIMIT 1"
        )
        # Thực hiện truy vấn
        _LOGGER.debug(f"laychisongaygannhat: SQL query: {query}")
        _LOGGER.debug(f"laychisongaygannhat: Params: userevn={userevn}, thang={m}, nam={y}")
        cursor.execute(query, (userevn, m, y))
        row = cursor.fetchone()
        _LOGGER.debug(f"laychisongaygannhat: Kết quả truy vấn: {row}")
        # Nếu không tìm thấy, thử mở rộng tìm kiếm
        if not row:
            _LOGGER.debug("laychisongaygannhat: Thử tìm không giới hạn ngày")
            query_alt = (
                "SELECT ngay, chi_so FROM daily_consumption "
                "WHERE userevn=? "
                "AND chi_so IS NOT NULL AND chi_so != '' "
                "AND lower(chi_so) != 'không có dữ liệu' AND chi_so != 'Khôngcódữliệu' "
                f"{order_by_clause} LIMIT 1"
            )
            cursor.execute(query_alt, (userevn,))
            row = cursor.fetchone()
            _LOGGER.debug(f"laychisongaygannhat: Kết quả truy vấn mở rộng: {row}")
            # Vẫn không tìm thấy, kiểm tra xem có bản ghi nào trong DB không để debug
            if not row:
                cursor.execute("SELECT COUNT(*) FROM daily_consumption WHERE userevn=?", (userevn,))
                count_row = cursor.fetchone()
                _LOGGER.debug(f"laychisongaygannhat: Tổng số bản ghi cho {userevn}: {count_row[0] if count_row else 0}")
                # Kiểm tra một số bản ghi đầu tiên để xem dạng dữ liệu
                cursor.execute(
                    "SELECT ngay, chi_so FROM daily_consumption WHERE userevn=? LIMIT 5",
                    (userevn,)
                )
                sample_rows = cursor.fetchall()
                _LOGGER.debug(f"laychisongaygannhat: Mẫu dữ liệu: {sample_rows}")
        conn.close()
        if row and row[1] is not None:
            try:
                ngay = row[0]
                # Kiểm tra thêm một lần nữa để đảm bảo không lấy dữ liệu không hợp lệ
                if row[1] == "Khôngcódữliệu" or row[1].lower() == "không có dữ liệu":
                    _LOGGER.debug(f"laychisongaygannhat: Bỏ qua dữ liệu không hợp lệ {row[1]}")
                    return None, None
                chi_so = chuyen_doi_so(row[1])
                if chi_so is None:
                    _LOGGER.error(f"laychisongaygannhat: Lỗi chuyển đổi chỉ số: {row[1]}")
                    return None, None
                _LOGGER.debug(f"laychisongaygannhat: Thành công, ngày={ngay}, chỉ số={chi_so}")
                return chi_so, ngay
            except (TypeError, ValueError) as e:
                _LOGGER.error(f"laychisongaygannhat: Lỗi chuyển đổi chỉ số: {row[1]}, lỗi: {str(e)}")
                return None, None
        else:
            _LOGGER.debug(f"laychisongaygannhat: Không tìm thấy dữ liệu cho {userevn}, tháng={m}, năm={y}")
            return None, None
    except Exception as e:
        _LOGGER.error(f"laychisongaygannhat: Lỗi truy vấn DB: {str(e)}")
        try:
            conn.close()
        except Exception:
            pass
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


def export_pdf_from_db(userevn, db_path=None, pdf_dir=None):
    db_file = db_path or DB_PATH
    out_dir = pdf_dir or PDF_PATH
    try:
        now = datetime.now()
        current_year = now.year
        current_month = now.month
        if not os.path.exists(out_dir):
            os.makedirs(out_dir, exist_ok=True)
        file_infos = []
        for m in range(1, current_month + 1):
            file_path = os.path.join(out_dir, f"hoadon_{userevn}_{m}_{current_year}.pdf")
            info = {"month": m, "year": current_year, "file": file_path, "downloaded": False}
            if not os.path.exists(file_path):
                conn = sqlite3.connect(db_file)
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT pdf FROM hoadon_pdf WHERE userevn=? AND thang=? AND nam=? ORDER BY id DESC LIMIT 1",
                    (userevn, m, current_year)
                )
                row = cursor.fetchone()
                conn.close()
                if row and row[0]:
                    with open(file_path, "wb") as f:
                        f.write(row[0])
                    info["downloaded"] = True
            else:
                info["downloaded"] = False
            file_infos.append(info)
        return file_infos
    except Exception:
        return []
