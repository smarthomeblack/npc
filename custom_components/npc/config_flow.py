import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_USERNAME
from homeassistant.helpers import selector
from typing import Any
import logging

_LOGGER = logging.getLogger(__name__)
CONF_NGAYDAUKY = "ngaydauky"
CONF_PHUONG_THUC = "phuong_thuc"

TRUONG_MA_KHACH_HANG = (
    lambda data: {
        vol.Required(CONF_USERNAME): selector.TextSelector(
            selector.TextSelectorConfig(
                type=selector.TextSelectorType.TEXT,
                autocomplete="username"
            )
        )
    }
    if (data.get(CONF_USERNAME) is None)
    else {
        vol.Required(CONF_USERNAME, default=data.get(CONF_USERNAME)): selector.TextSelector(
            selector.TextSelectorConfig(
                type=selector.TextSelectorType.TEXT,
                autocomplete="username"
            )
        )
    }
)

TRUONG_NGAY_DAU_KY = {
    vol.Required(CONF_NGAYDAUKY, default=1): selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=1,
            max=31,
            mode=selector.NumberSelectorMode.SLIDER,
            step=1
        )
    ),
}


class CauHinhEVN(config_entries.ConfigFlow, domain="npc"):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Bước chọn phương thức thiết lập."""
        errors = {}
        
        if user_input is not None:
            phuong_thuc = user_input[CONF_PHUONG_THUC]
            
            if phuong_thuc == "auto":
                # Kiểm tra lại có mã nào khả dụng không trước khi chuyển sang auto
                available_codes = await self._lay_danh_sach_ma_khach_hang_tu_database()
                if not available_codes:
                    # Nếu không còn mã nào khả dụng, chuyển sang manual
                    return await self.async_step_manual()
                return await self.async_step_auto()
            else:  # manual
                return await self.async_step_manual()
        
        # Kiểm tra có customer codes từ database không
        customer_codes = await self._lay_danh_sach_ma_khach_hang_tu_database()
        has_data = len(customer_codes) > 0
        
        # Build description dựa trên trạng thái database
        if has_data:
            description = f"""
### 🎉 Đã phát hiện dữ liệu EVN VN Addon!

✅ **Database EVN**: Đã thấy có dữ liệu !
📊 **Mã khách hàng**: {len(customer_codes)} mã khả dụng !
🔗 **Đường dẫn**: `/config/evnvn/evndata.db`

**Chọn phương thức thiết lập:**
            """
        else:
            description = """
### ⚠️ Chưa phát hiện dữ liệu EVN VN

🔍 **Database**: Chưa có dữ liệu hoặc chưa cài EVN VN Addon !
💡 **Gợi ý**: Cài đặt EVN VN Addon hoặc nhập thủ công, hoặc kiểm tra xem Addon EVN VN có chạy không !

**Chọn phương thức thiết lập:**
            """
        
        # Build options với trạng thái enabled/disabled
        options = [
            {
                "value": "auto",
                "label": (f"🤖 Thêm Tự Động ({len(customer_codes)} mã khả dụng)"
                          if has_data else "🤖 Thêm Tự Động (Không tìm thấy Mã Khách Hàng)")
            },
            {"value": "manual", "label": "✏️ Nhập Thủ Công"}
        ]
        
        schema = {
            vol.Required(CONF_PHUONG_THUC): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=options,
                    mode=selector.SelectSelectorMode.LIST
                )
            )
        }
        
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(schema),
            errors=errors,
            description_placeholders={"method_info": description}
        )

    async def async_step_auto(self, user_input: dict[str, Any] | None = None):
        """Bước tự động - chọn từ dropdown customer codes."""
        errors = {}
        
        if user_input is not None:
            ma_khach_hang = user_input[CONF_USERNAME]
            ngay_dau_ky = user_input[CONF_NGAYDAUKY]
            
            # Validation
            kiem_tra_ton_tai = await self._kiem_tra_ma_khach_hang_ton_tai(ma_khach_hang)
            if not kiem_tra_ton_tai:
                errors[CONF_USERNAME] = "customer_not_found"
            
            if not errors:
                await self.async_set_unique_id(ma_khach_hang)
                
                # Check already configured
                if self._async_current_entries():
                    for entry in self._async_current_entries():
                        if entry.unique_id == ma_khach_hang:
                            return self.async_abort(
                                reason="already_configured",
                                description_placeholders={"title": ma_khach_hang}
                            )
                
                return self.async_create_entry(
                    title=ma_khach_hang,
                    data={
                        CONF_USERNAME: ma_khach_hang,
                        CONF_NGAYDAUKY: ngay_dau_ky
                    }
                )
        
        # Get customer codes from database
        customer_codes = await self._lay_danh_sach_ma_khach_hang_tu_database()
        
        if not customer_codes:
            # Fallback to manual if no data found
            return await self.async_step_manual()
        
        # Build dropdown options
        options = [
            {"value": code, "label": f"📊 {code}"}
            for code in sorted(customer_codes)
        ]
        
        schema_du_lieu = {
            vol.Required(CONF_USERNAME): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=options,
                    mode=selector.SelectSelectorMode.DROPDOWN
                )
            )
        }
        schema_du_lieu.update(TRUONG_NGAY_DAU_KY)
        
        description = f"""
### 🤖 Thiết lập Tự Động

✅ **Đã tìm thấy {len(customer_codes)} mã khách hàng**
📊 **Nguồn dữ liệu**: EVN VN Addon Database
🔄 **Đồng bộ**: Tự động cập nhật từ addon

**Chọn mã khách hàng và ngày đầu kỳ:**
        """
        
        return self.async_show_form(
            step_id="auto",
            data_schema=vol.Schema(schema_du_lieu),
            errors=errors,
            description_placeholders={"auto_info": description}
        )

    async def async_step_manual(self, user_input: dict[str, Any] | None = None):
        """Bước thủ công - nhập manual như hiện tại."""
        loi = {}
        if user_input is not None:
            ma_khach_hang = user_input[CONF_USERNAME].strip().upper()
            if not (ma_khach_hang.startswith('P') or ma_khach_hang.startswith('S')) or len(ma_khach_hang) < 11:
                loi[CONF_USERNAME] = "invalid_evn_code"
            else:
                kiem_tra_ton_tai = await self._kiem_tra_ma_khach_hang_ton_tai(ma_khach_hang)
                if not kiem_tra_ton_tai:
                    loi[CONF_USERNAME] = "customer_not_found"
            if not loi:
                await self.async_set_unique_id(ma_khach_hang)
                
                # Kiem tra xem ma khach hang da duoc cau hinh chua
                if self._async_current_entries():
                    for entry in self._async_current_entries():
                        if entry.unique_id == ma_khach_hang:
                            return self.async_abort(
                                reason="already_configured",
                                description_placeholders={"title": ma_khach_hang}
                            )
                
                return self.async_create_entry(
                    title=ma_khach_hang,
                    data={
                        CONF_USERNAME: ma_khach_hang,
                        CONF_NGAYDAUKY: user_input[CONF_NGAYDAUKY]
                    }
                )
        schema_du_lieu = {}
        schema_du_lieu.update(TRUONG_MA_KHACH_HANG({}))
        schema_du_lieu.update(TRUONG_NGAY_DAU_KY)

        return self.async_show_form(
            step_id="manual",
            data_schema=vol.Schema(schema_du_lieu),
            errors=loi,
        )

    async def _lay_danh_sach_ma_khach_hang_tu_database(self) -> list[str]:
        """Lấy danh sách mã khách hàng từ database EVN VN (chỉ những mã chưa được cấu hình)."""
        try:
            import sqlite3
            import os

            db_path = "/config/evnvn/evndata.db"
            if not os.path.exists(db_path):
                _LOGGER.debug(f"Database file không tồn tại: {db_path}")
                return []

            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Lấy tất cả customer codes từ cả 2 bảng (giống như Go code)
            cursor.execute("""
                SELECT DISTINCT userevn
                FROM daily_consumption
                WHERE userevn IS NOT NULL AND trim(userevn) != ''
                UNION
                SELECT DISTINCT userevn
                FROM monthly_bill
                WHERE userevn IS NOT NULL AND trim(userevn) != ''
                ORDER BY userevn
            """)

            all_codes = [row[0] for row in cursor.fetchall()]
            conn.close()

            # Lọc ra những mã đã được cấu hình trong Home Assistant
            configured_codes = set()
            if self._async_current_entries():
                for entry in self._async_current_entries():
                    if entry.unique_id:
                        configured_codes.add(entry.unique_id)

            # Chỉ trả về những mã chưa được cấu hình
            available_codes = [code for code in all_codes if code not in configured_codes]

            _LOGGER.info(f"Tìm thấy {len(all_codes)} mã tổng cộng, "
                         f"{len(configured_codes)} đã cấu hình, "
                         f"{len(available_codes)} khả dụng")
            return available_codes

        except Exception as ex:
            _LOGGER.error(f"Lỗi lấy danh sách từ database: {ex}")
            return []

    async def _kiem_tra_ma_khach_hang_ton_tai(self, ma_khach_hang: str) -> bool:
        try:
            import sqlite3
            import os
            db_path = "/config/evnvn/evndata.db"
            if not os.path.exists(db_path):
                _LOGGER.warning(f"Database file khong ton tai: {db_path}")
                return True  # Allow through if DB file doesn't exist
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM daily_consumption WHERE userevn=? LIMIT 1",
                (ma_khach_hang,)
            )
            count = cursor.fetchone()[0]
            conn.close()
            _LOGGER.debug(f"Tim thay {count} ban ghi cho userevn: {ma_khach_hang}")
            return count > 0
        except Exception as ex:
            _LOGGER.error(f"Loi kiem tra database: {ex}")
            return True

    @staticmethod
    def async_get_options_flow(config_entry):
        """Lay options flow cho handler nay."""
        return XuLyTuyChon()


class XuLyTuyChon(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        loi = {}
        ngay_dau_ky_hien_tai = self.config_entry.options.get(
            CONF_NGAYDAUKY,
            self.config_entry.data.get(CONF_NGAYDAUKY, 1)
        )
        if user_input is not None:
            try:
                ngay_dau_ky = int(user_input[CONF_NGAYDAUKY])
                if 1 <= ngay_dau_ky <= 31:
                    tuy_chon = {CONF_NGAYDAUKY: ngay_dau_ky}
                    return self.async_create_entry(title="", data=tuy_chon)
                else:
                    loi[CONF_NGAYDAUKY] = "invalid_day"
            except (ValueError, KeyError) as ex:
                _LOGGER.error(f"Loi xu ly tuy chon: {ex}")
                loi["base"] = "unknown"
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(
                    CONF_NGAYDAUKY,
                    default=ngay_dau_ky_hien_tai
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1,
                        max=31,
                        mode=selector.NumberSelectorMode.BOX
                    )
                )
            }),
            errors=loi
        )
