import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_USERNAME
from homeassistant.helpers import selector
from typing import Any
import logging

_LOGGER = logging.getLogger(__name__)
CONF_NGAYDAUKY = "ngaydauky"

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
        """Xu ly buoc thiet lap ban dau."""
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
            step_id="user",
            data_schema=vol.Schema(schema_du_lieu),
            errors=loi,
        )

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
