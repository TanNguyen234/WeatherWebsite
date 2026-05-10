# WeatherApp

Ứng dụng thời tiết GIS xây dựng bằng Django.

## Tài liệu

- Hướng dẫn cài đặt đầy đủ: [Document/HUONG_DAN_CAI_DAT.md](Document/HUONG_DAN_CAI_DAT.md)
- Database & phân quyền chi tiết: [DATABASE_SETUP.md](DATABASE_SETUP.md)

## Cập nhật kiến trúc (03/2026)

- Đã dọn dẹp schema để chỉ giữ các thực thể đang dùng thực tế: `user_profile`, `user_location`, `route`.
- Đã loại bỏ các thành phần dư thừa/không được route tới (forecast flow cũ, script JS cũ, pipeline train ML thử nghiệm).
- Predict page ưu tiên model pre-trained thực tế `amazon/chronos-t5-tiny` (HuggingFace).
- Nếu môi trường máy chủ không đủ tài nguyên để nạp Chronos (ví dụ thiếu paging file cho `torch`), hệ thống tự fallback sang Open-Meteo forecast model (NWP) để vẫn trả kết quả dự đoán thực tế, không mock.
- API chính cho Predict: `POST /api/predict/` trả về `api_result`, `ai_result`, `comparison` (delta, score, confidence).

---

## Yêu cầu hệ thống

- Python 3.11 hoặc 3.12
- pip
- Virtualenv
- (Nếu sử dụng GIS / PostGIS)
  - PostgreSQL + PostGIS
  - GDAL cài ở mức hệ điều hành

---

## Cấu trúc project

WeatherApp/
├─ WeatherWeb/
│ ├─ WeatherWeb/
│ │ ├─ settings.py
│ │ ├─ urls.py
│ │ ├─ asgi.py
│ │ └─ wsgi.py
│ ├─ manage.py
│ └─ requirements.txt
├─ .gitignore
└─ README.md

---

## Setup database từ file backup

Tài liệu chi tiết kèm hình ảnh nằm trong [Document/HUONG_DAN_CAI_DAT.md](Document/HUONG_DAN_CAI_DAT.md). File backup mẫu được đặt tại [Document/weathergis_2026.backup](Document/weathergis_2026.backup).

Tóm tắt quy trình:

1. Tạo backup từ pgAdmin hoặc dùng file backup có sẵn.
2. Tạo database mới trong PostgreSQL.
3. Restore database từ file .backup bằng pgAdmin hoặc PowerShell.

---

## Cách chạy project (Windows)

### 1. Clone source

```bash
git clone https://github.com/TanNguyen234/WeatherWebsite.git
cd WeatherWebsite
```

### 2. Tạo và kích hoạt virtual environment

```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Cài dependency

```bash
pip install -r WeatherWeb/WeatherWeb/requirements.txt
```

### 4. Cài GDAL

```bash
pip install D:\Downloads\gdal-3.11.4-cp312-cp312-win_amd64.whl
```

### 5. Thiết lập biến môi trường

Tạo hoặc cập nhật file .env tại [WeatherWeb/.env](WeatherWeb/.env).

Nội dung tối thiểu:

```dotenv
SECRET_KEY=your-secret-key
DEBUG=True
DB_NAME=weather_app
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432
EMAIL_HOST_USER=your-email@example.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=your-email@example.com
```

### 6. Chạy migrate

```bash
python WeatherWeb/manage.py migrate
```

Lưu ý: bản refactor có migration dọn schema (`weather.0003_cleanup_unused_schema`) để xóa bảng/cột không dùng.

### 7. (Tuỳ chọn) Seed dữ liệu mẫu

```bash
python WeatherWeb/manage.py create_initial_data
```

### 8. Chạy server

```bash
python WeatherWeb/manage.py runserver
```

---

## AI Predict hoạt động thế nào

- Input: tọa độ từ map hoặc location đã lưu + `horizon_hours`.
- API hiện tại: lấy thời tiết real-time qua weather service.
- AI result: suy luận từ Chronos pre-trained (đầu vào là chuỗi lịch sử giờ từ Open-Meteo archive), không train runtime.
- Fallback runtime: dùng trực tiếp forecast pre-trained của Open-Meteo khi Chronos không khả dụng trên host.
- Comparison: trả về chênh lệch API vs AI, prediction score và confidence để hiển thị biểu đồ trên Predict page.

