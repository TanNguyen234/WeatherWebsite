# HƯỚNG DẪN CÀI ĐẶT

## Chương 1: Setup database từ file backup

### Bước 1: Chọn database cần backup, nhấn chuột phải và chọn Backup.

![Bước 1 - Backup database](docs/images/image1.png)

### Bước 2: Nhấn vào icon ở mục Filename -> chọn folder chứa file backup -> tại mục save as type chọn BACKUP File .backup -> Nhấn Save.

### Bước 3: Chạy lệnh SQL sau để tiến hành tạo database mới:

![Bước 3 - Tạo database mới](docs/images/image2.png)

### Bước 4: Mở Windows PowerShell và chạy lệnh sau để thực hiện phục hồi dữ liệu (backup):

![Bước 4 - Lệnh pg_restore](docs/images/image3.png)

Giải thích lệnh: Trong đó postgres là tên user, recover_database là tên database vừa tạo ở Bước 3, và phần cuối là đường dẫn đến file .backup đã tạo ở Bước 2.

Cách khác: Bạn có thể chuột phải vào database mới tạo, chọn Restore và trỏ đến file .backup.

![Cách khác - Restore từ pgAdmin](docs/images/image4.png)

## Chương 2: Setup dự án

### Bước 1: Chuẩn bị môi trường:

- Cài đặt Python 3.12.4 và kết nối vào VS Code.
- Tải file thư viện gdal-3.11.4-cp312-cp312-win_amd64.whl.
- Cài đặt PostgreSQL (lưu ý nhớ mật khẩu đăng nhập).

### Bước 2: Sử dụng Terminal trong VS Code, chạy lệnh git clone để lấy mã nguồn:

Bash
```bash
git clone https://github.com/TanNguyen234/WeatherWebsite.git
```

![Bước 2 - Git clone](docs/images/image5.png)

### Bước 3: Di chuyển vào thư mục dự án vừa tải về:

Bash
```bash
cd WeatherWebsite
```

![Bước 3 - Di chuyển thư mục](docs/images/image6.png)

### Bước 4: Tạo môi trường ảo (virtual environment) để quản lý thư viện:

Bash
```bash
python -m venv venv
```

![Bước 4 - Tạo venv](docs/images/image7.png)

### Bước 5: Kích hoạt môi trường ảo vừa tạo:

Bash
```bash
venv\Scripts\activate
```

![Bước 5 - Kích hoạt venv](docs/images/image8.png)

### Bước 6: Cài đặt các thư viện cần thiết từ file requirements:

Bash
```bash
pip install -r WeatherWeb/WeatherWeb/requirements.txt
```

![Bước 6 - Cài đặt requirements](docs/images/image9.png)

### Bước 7: Cài đặt thư viện GDAL (Lưu ý sửa lại đường dẫn file .whl cho đúng với nơi bạn đã lưu ở Bước 1):

Bash
```bash
pip install D:\Downloads\gdal-3.11.4-cp312-cp312-win_amd64.whl
```

![Bước 7 - Cài đặt GDAL](docs/images/image10.png)

### Bước 8: Tạo file .env tại đường dẫn WeatherWeb/WeatherWeb/.env với các nội dung cấu hình sau:

![Bước 8 - File .env](docs/images/image11.png)

Hướng dẫn điền thông tin file .env:

- SECRET_KEY: Điền một chuỗi ký tự ngẫu nhiên bất kỳ (khuyến nghị trên 20 ký tự).
- DB_NAME: Tên database bạn đã tạo trong PostgreSQL.
- DB_USER: Tên người dùng database (thường là postgres).
- DB_PASSWORD: Mật khẩu của người dùng database đó.
- EMAIL_HOST_USER: Email dùng để gửi tin nhắn tự động từ hệ thống.
- EMAIL_HOST_PASSWORD: Mật khẩu ứng dụng (App Password) của email trên.
- DEFAULT_FROM_EMAIL: Có thể điền giống với EMAIL_HOST_USER.

### Bước 9: Chạy dự án bằng lệnh:

Bash
```bash
python WeatherWeb/manage.py runserver
```

![Bước 9 - Runserver](docs/images/image12.png)
