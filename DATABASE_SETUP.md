# WeatherGIS – Database & Authentication Setup

## 1. Tổng quan

Tài liệu này mô tả toàn bộ schema database, cấu trúc model Django, dữ liệu khởi tạo, và hệ thống phân quyền của **WeatherGIS**.

**Nguyên tắc cốt lõi:**
- Database chỉ lưu **dữ liệu không gian do người dùng tạo ra** (điểm, vùng, tuyến đường)
- Dữ liệu thời tiết **KHÔNG BAO GIỜ** được lưu vào database — luôn fetch on-demand
- Thiết kế tối giản, sẵn sàng nâng cấp lên PostGIS

---

## 2. Cấu hình kết nối Database

**File:** `.env` tại `WeatherWeb/.env`

```dotenv
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=123
DB_HOST=localhost
DB_PORT=5432
```

**Engine:** `django.contrib.gis.db.backends.postgis` (settings.py)

> OSGEO_PATH phải trỏ đúng vào GDAL trong venv dự án:
> `OSGEO_PATH=D:\Projects\WeatherWebsite\venv\Lib\site-packages\osgeo`

---

## 3. Schema SQL (đầy đủ)

> Các bảng dưới đây được tạo tự động bởi Django migrations.
> SQL thuần dùng để tham khảo hoặc kiểm tra.

### 3.1 `user_profile` – Hồ sơ người dùng

```sql
CREATE TABLE user_profile (
    id                BIGSERIAL PRIMARY KEY,
    user_id           INTEGER      NOT NULL UNIQUE
                          REFERENCES auth_user(id) ON DELETE CASCADE,
    role              VARCHAR(20)  NOT NULL DEFAULT 'user',
                      -- 'user' | 'admin'
    bio               TEXT         NOT NULL DEFAULT '',
    avatar_url        VARCHAR(500) NOT NULL DEFAULT '',
    default_latitude  DOUBLE PRECISION,         -- NULL = dùng mặc định hệ thống
    default_longitude DOUBLE PRECISION,
    default_zoom      SMALLINT     NOT NULL DEFAULT 6,   -- 1–18
    show_temperature  BOOLEAN      NOT NULL DEFAULT TRUE,
    show_rain         BOOLEAN      NOT NULL DEFAULT TRUE,
    show_wind         BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at        TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
```

### 3.2 `user_location` – Địa điểm

```sql
CREATE TABLE user_location (
    id           BIGSERIAL PRIMARY KEY,
    user_id      INTEGER          NOT NULL REFERENCES auth_user(id)   ON DELETE CASCADE,
    name         VARCHAR(255),                     -- tuỳ chọn
    description  TEXT             NOT NULL DEFAULT '',
    latitude     DOUBLE PRECISION NOT NULL,        -- [-90,  90]
    longitude    DOUBLE PRECISION NOT NULL,        -- [-180, 180]
    address      VARCHAR(500)     NOT NULL DEFAULT '',  -- reverse-geocoded
    is_favourite BOOLEAN          NOT NULL DEFAULT FALSE,
    created_at   TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_user_location_lat_lng  ON user_location (latitude, longitude);
CREATE INDEX idx_user_location_user_fav ON user_location (user_id, is_favourite);

-- PostGIS upgrade:  latitude + longitude  →  POINT SRID 4326
```

### 3.3 `area` – Vùng phân tích tròn

```sql
CREATE TABLE area (
    id                 BIGSERIAL PRIMARY KEY,
    user_id            INTEGER          NOT NULL REFERENCES auth_user(id)     ON DELETE CASCADE,
    center_location_id INTEGER          NOT NULL REFERENCES user_location(id) ON DELETE CASCADE,
    name               VARCHAR(255)     NOT NULL DEFAULT '',
    radius_km          DOUBLE PRECISION NOT NULL,   -- [0.1, 500]
    notes              TEXT             NOT NULL DEFAULT '',
    created_at         TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- PostGIS upgrade:  ST_Buffer(center.point, radius_km * 1000)
```

### 3.4 `location_group` – Nhóm địa điểm

```sql
CREATE TABLE location_group (
    id          BIGSERIAL PRIMARY KEY,
    user_id     INTEGER      NOT NULL REFERENCES auth_user(id) ON DELETE CASCADE,
    name        VARCHAR(255) NOT NULL,
    description TEXT         NOT NULL DEFAULT '',
    color       VARCHAR(7)   NOT NULL DEFAULT '#3b82f6',   -- hex colour
    created_at  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
```

### 3.5 `location_group_item` – Thành viên nhóm (junction)

```sql
CREATE TABLE location_group_item (
    id            BIGSERIAL PRIMARY KEY,
    group_id      INTEGER NOT NULL REFERENCES location_group(id)  ON DELETE CASCADE,
    location_id   INTEGER NOT NULL REFERENCES user_location(id)   ON DELETE CASCADE,
    display_order SMALLINT NOT NULL DEFAULT 0,
    UNIQUE (group_id, location_id)
);
```

### 3.6 `route` – Tuyến đường

```sql
CREATE TABLE route (
    id                BIGSERIAL PRIMARY KEY,
    user_id           INTEGER          NOT NULL REFERENCES auth_user(id)     ON DELETE CASCADE,
    name              VARCHAR(255)     NOT NULL,
    start_location_id INTEGER          NOT NULL REFERENCES user_location(id) ON DELETE CASCADE,
    end_location_id   INTEGER          NOT NULL REFERENCES user_location(id) ON DELETE CASCADE,
    distance_km       DOUBLE PRECISION,    -- điền sau khi gọi OSRM
    duration_minutes  DOUBLE PRECISION,
    notes             TEXT             NOT NULL DEFAULT '',
    created_at        TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- PostGIS upgrade:  (start + end)  →  LINESTRING SRID 4326
```

### 3.7 `interaction_log` – Nhật ký tương tác (analytics)

```sql
CREATE TABLE interaction_log (
    id          BIGSERIAL PRIMARY KEY,
    user_id     INTEGER REFERENCES auth_user(id) ON DELETE SET NULL,
    action_type VARCHAR(50) NOT NULL,
    -- 'map_click' | 'save_location' | 'save_route'
    -- 'analyze_area' | 'login' | 'register'
    detail      JSONB,        -- context tuỳ chọn, KHÔNG chứa dữ liệu thời tiết
    ip_address  INET,
    created_at  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX interaction_log_action_idx  ON interaction_log (action_type);
CREATE INDEX interaction_log_created_idx ON interaction_log (created_at);
```

---

## 4. Django Models (weather/models.py)

### Model: `UserProfile`

| Trường | Kiểu | Mô tả |
|--------|------|-------|
| `user` | OneToOneField → auth_user | Liên kết 1-1 với User |
| `role` | CharField(20) | `'user'` hoặc `'admin'` |
| `bio` | TextField | Giới thiệu ngắn |
| `avatar_url` | URLField | URL ảnh đại diện |
| `default_latitude/longitude` | FloatField, nullable | Trung tâm bản đồ mặc định |
| `default_zoom` | SmallIntegerField (1–18) | Zoom mặc định |
| `show_temperature/rain/wind` | BooleanField | Ưu tiên hiển thị lớp |

### Model: `UserLocation`

| Trường | Kiểu | Mô tả |
|--------|------|-------|
| `user` | ForeignKey → auth_user | Chủ sở hữu |
| `name` | CharField(255), nullable | Tên hiển thị |
| `description` | TextField | Ghi chú chi tiết |
| `latitude/longitude` | FloatField | Toạ độ thực |
| `address` | CharField(500) | Địa chỉ reverse-geocoded |
| `is_favourite` | BooleanField | Đánh dấu yêu thích |

### Model: `Area`

| Trường | Kiểu | Mô tả |
|--------|------|-------|
| `user` | ForeignKey → auth_user | Chủ sở hữu |
| `center` | ForeignKey → UserLocation | Tâm vùng |
| `radius_km` | FloatField (0.1–500) | Bán kính km |
| `name` | CharField(255) | Tên vùng |
| `notes` | TextField | Ghi chú |

### Model: `LocationGroup` + `LocationGroupItem`

| Trường | Kiểu | Mô tả |
|--------|------|-------|
| `name` | CharField(255) | Tên nhóm |
| `description` | TextField | Mô tả |
| `color` | CharField(7) | Mã hex màu nhóm |
| `items` (reverse) | → LocationGroupItem | Các địa điểm trong nhóm |

### Model: `Route`

| Trường | Kiểu | Mô tả |
|--------|------|-------|
| `start_location` | ForeignKey → UserLocation | Điểm xuất phát |
| `end_location` | ForeignKey → UserLocation | Điểm đích |
| `distance_km` | FloatField, nullable | Khoảng cách OSRM |
| `duration_minutes` | FloatField, nullable | Thời gian OSRM |
| `notes` | TextField | Ghi chú |

### Model: `InteractionLog`

| Trường | Kiểu | Mô tả |
|--------|------|-------|
| `user` | ForeignKey, nullable | Người dùng (có thể ẩn danh) |
| `action_type` | CharField(50) | Loại hành động |
| `detail` | JSONField | Context JSON (không chứa thời tiết) |
| `ip_address` | GenericIPAddressField | IP người dùng |

---

## 5. Migrations

### Thứ tự migrations

```
weather/migrations/
├── 0001_initial.py           – Schema đầy đủ (tất cả models mới)
└── 0002_new_models_and_fields.py – RunSQL thêm bảng/cột vào DB cũ
```

### Chạy migrations lần đầu (database trống)

```bash
python manage.py migrate
```

### Chạy migrations trên database cũ (có bảng cũ)

```bash
# 1. Fake initial (Django nhận biết bảng đã tồn tại)
python manage.py migrate --fake weather 0001

# 2. Áp dụng migration mới (tạo bảng/cột còn thiếu)
python manage.py migrate
```

---

## 6. Dữ liệu khởi tạo

### Chạy lệnh seed

```bash
python manage.py create_initial_data
```

Lệnh sẽ tạo:

| Tài khoản | Mật khẩu | Loại | Điều hướng sau login |
|-----------|----------|------|----------------------|
| `admin` | `admin123` | Superuser / role=admin | `/panel/dashboard/` |
| `testuser` | `user123` | Regular user / role=user | `/map/` |

Và 3 địa điểm mẫu gắn với `testuser`:
- Hà Nội – Hoàn Kiếm (21.0285, 105.8542)
- TP. HCM – Bến Thành (10.7769, 106.7009)
- Đà Nẵng – Sơn Trà (16.0544, 108.2022)

### Làm mới dữ liệu (reset)

```bash
python manage.py create_initial_data --reset
```

---

## 7. Hệ thống phân quyền

### Quy tắc điều hướng sau đăng nhập

```
Đăng nhập thành công
    ├── user.is_staff == True   →  /panel/dashboard/
    ├── user.is_superuser == True  →  /panel/dashboard/
    ├── profile.role == 'admin' →  /panel/dashboard/
    └── (còn lại)               →  /map/
```

### Bảo vệ Admin Panel (`/panel/`)

`AdminBaseView` kiểm tra mọi request:

```python
# weather/views/auth.py – hàm _redirect_after_login()
# adminpanel/views.py   – AdminBaseView._is_admin()
```

- Chưa đăng nhập → redirect `GET /login/?next=/panel/...`
- Đã đăng nhập nhưng không phải admin → redirect `/map/`
- DEBUG mode **không còn bypass** auth (đã sửa)

### Tạo admin mới bằng shell

```bash
python manage.py createsuperuser
# Sau đó set profile:
python manage.py shell -c "
from weather.models import UserProfile
from django.contrib.auth import get_user_model
u = get_user_model().objects.get(username='your_new_admin')
UserProfile.objects.update_or_create(user=u, defaults={'role': 'admin'})
"
```

---

## 8. Trang quản trị Django (`/admin/`)

Các model đã đăng ký trong `weather/admin.py`:

| Model | Tính năng |
|-------|-----------|
| `UserProfile` | Sửa role trực tiếp từ danh sách, lọc theo role |
| `UserLocation` | Xem toạ độ, tìm kiếm theo tên/địa chỉ/user |
| `Area` | Xem vùng phân tích, bán kính |
| `LocationGroup` | Inline thêm/xoá địa điểm trong nhóm, xem màu |
| `Route` | Xem khoảng cách OSRM, thời gian di chuyển |
| `InteractionLog` | **Read-only** – không cho tạo/xoá log (trừ superuser) |

---

## 9. Nâng cấp lên PostGIS (tương lai)

Khi đã cài PostGIS extension:

```sql
-- Bật extension
CREATE EXTENSION IF NOT EXISTS postgis;

-- Nâng cấp user_location
ALTER TABLE user_location ADD COLUMN point GEOMETRY(Point, 4326);
UPDATE user_location SET point = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326);

-- Nâng cấp route (cần xây dựng linestring từ OSRM geometry)
ALTER TABLE route ADD COLUMN path GEOMETRY(LineString, 4326);
```

**Không cần thêm bảng mới** – chỉ đổi kiểu cột. Logic application không thay đổi.

---

## 10. Bảng bị cấm (không được tạo)

| Tên bảng | Lý do |
|----------|-------|
| `weather` / `forecast` / `hourly_weather` | Dữ liệu thời tiết luôn fetch on-demand |
| `city` / `country` | GIS dùng toạ độ thực, không fix điểm |
| `api_response_cache` | Không cache API response |
| `sensor` / `station` | Ngoài phạm vi dự án |
