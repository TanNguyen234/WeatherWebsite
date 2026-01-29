# WeatherApp

Django project cho ứng dụng thời tiết.

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

## Cách chạy project

### 1. Clone source

- git clone <repository-url>
- cd WeatherApp
  
### 2. Tạo và kích hoạt virtual environment

python -m venv venv
venv\Scripts\activate

### 3. Cài dependency

pip install -r WeatherWeb/requirements.txt

### 4. Thiết lập biến môi trường

- Tạo file .env tại thư mục: WeatherWeb/WeatherWeb/.env

Nội dung mẫu của file .env:

SECRET_KEY=your-secret-key
DEBUG=True
DB_NAME=weather_app
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432

### 5. Chạy migrate

python WeatherWeb/manage.py migrate

### 6. Chạy server

python WeatherWeb/manage.py runserver

