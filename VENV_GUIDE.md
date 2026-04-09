# Hướng dẫn thiết lập môi trường ảo

## Kích hoạt môi trường ảo

### Trên Windows:
```cmd
venv\Scripts\activate
```

### Trên macOS/Linux:
```bash
source venv/bin/activate
```

## Cài đặt dependencies

Sau khi kích hoạt môi trường ảo, chạy:
```bash
pip install -r requirements.txt
```

## Kiểm tra môi trường ảo đang hoạt động

Đảm bảo bạn thấy `(venv)` ở đầu dòng lệnh:
```
(venv) D:\Projects_IT\AetherTutor>
```

## Thoát khỏi môi trường ảo

```bash
deactivate
```

## Nâng cấp pip

```bash
python -m pip install --upgrade pip
```
