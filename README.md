# 🔌 NPC Electricity MQTT Bridge

Công cụ tự động đăng nhập vào website CSKH NPC (miền Bắc), lấy dữ liệu điện tiêu thụ & tiền điện, và gửi qua MQTT về Home Assistant.

- ✅ Không cần đăng nhập thủ công
- ✅ Hỗ trợ MQTT Discovery (Home Assistant nhận dạng tự động)

---

## 🚀 Cách sử dụng

### 1. Tạo thư mục cấu hình

Tạo file `config.txt` trong thư mục lưu trữ bạn muốn với nội dung mẫu:

```ini
makhachhang=điền mã điểm đo
mqtt_server=
mqtt_port=1883
mqtt_username=
mqtt_password=
mqtt_topic_prefix=homeassistant
usernpc=tài khoản npc
passnpc=mật khẩu npc
gemini_api_key=key api gemini
gemini_model=gemini-2.0-flash

```

> Bạn cần có tài khoản [Google Gemini](https://makersuite.google.com/app/apikey) để lấy `gemini_api_key`.

---

### 2. Tạo file `docker-compose.yml`

```yaml

services:
  npc:
    image: ghcr.io/smarthomeblack/npc:2025.5.31
    container_name: npc_container
    restart: unless-stopped
    network_mode: host
    volumes:
      - ./npc:/app/data
      - ./npc/config.txt:/app/config.txt
```

---

### 3. Chạy dịch vụ

```bash
docker compose up -d
```

---

## 📡 Kết quả

Sau khi khởi chạy, các cảm biến sẽ xuất hiện trong Home Assistant nhờ MQTT Discovery:

- `NPC Tieu Thu Hom Nay`
- `NPC Tien Dien Thang Truoc`
- `NPC Chi So Cuoi Ky`
- Và nhiều cảm biến khác

---

## 🛠 Cập nhật

Để cập nhật image mới nhất:

```bash
docker compose pull
docker compose up -d
```

---

## 📦 Image Docker

- Public GHCR: [ghcr.io/smarthomeblack/npc](https://ghcr.io/smarthomeblack/npc)
- Không yêu cầu clone mã nguồn
- Người dùng tự cấu hình bằng `config.txt`

---

## ❓ Câu hỏi thường gặp

#### Q: Có cần tài khoản NPC không?
> A: Cần. Bạn phải đăng ký tài khoản tại: https://cskh.npc.com.vn

#### Q: Dữ liệu có tự động cập nhập không?
> A: Có, dữ liệu sẽ tự động thu thập & gửi dữ liệu mỗi 120 phút.

#### Q: Có log không?
> A: Có. Bạn có thể xem bằng `docker logs -f npc_container`.

---

## ❤️ Đóng góp

Nếu bạn có câu hỏi hoặc muốn cải tiến, hãy mở [Issue](https://github.com/smarthomeblack/npc/issues) hoặc gửi PR.

---

## 📜 License

MIT License.
