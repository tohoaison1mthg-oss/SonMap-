# V10.15 — sửa mở nhầm bản V10.3

## Nguyên nhân đã xác minh trên laptop

- Mã ở tag V10.12 và thư mục SonMapPlus/App V10.14 đều lấy tiêu đề từ VERSION.
- ThanhTanApp/app.py cũ vẫn ghi cứng `SonMap+ V10.3`.
- ThanhTanApp/LH_KhoiDong.bas đã sinh đường gọi trực tiếp app.py cũ bằng runtime/pythonw.exe. Vì vậy sửa riêng nhãn shortcut không giải quyết đường mở từ VBA.

## Kiểm tra trên Windows

- 84 kiểm thử Python/Tk đạt, gồm ba kiểm thử đường mở cũ, khôi phục hai chiều, bảo toàn dữ liệu riêng và từ chối backup hỏng.
- Kiểm thử gọi cả app.py và launch.py cũ xác nhận yêu cầu mở được chuyển sang Python và launch.py thuộc SonMapPlus/App; không chạy thân ứng dụng V10.3. Đây là kiểm thử có giả lập Popen, không phải tự động bấm VBA trong V8i.
- Kiểm tra cú pháp PowerShell updater/restore và phân biệt tiến trình chạy bản cài với workspace dùng chung Python đạt.
- Kiểm thử gói xác minh mọi SHA256 trong payload, VERSION, tên ZIP và loại trừ DGN/MDB/runtime/assets/settings/data.
- Không thay thuật toán topology, giao điểm hoặc Jet ở phiên bản này; không coi các kiểm thử khởi động là nghiệm thu lại các thuật toán đó.

## Khôi phục điểm mở cũ

Trình cập nhật lưu nguyên ThanhTanApp/app.py và biên nhận SHA256 trong `ThanhTanApp/SonMap_startup_backups/<id>/` trước khi sửa. Chạy lại không chèn thêm đầu chuyển hướng. Chỉ bản có tiêu đề V10.3 đã nhận diện mới được sửa.

Muốn khôi phục, dùng Python của SonMap chạy `legacy_startup.py --legacy-root <ThanhTanApp> --restore <thư mục backup>`. Mã hiện tại cũng được lưu thành backup mới trước khi khôi phục. Phục hồi bản chương trình bằng shortcut Khôi phục vẫn giữ bộ chuyển hướng tới phiên bản thực tế đang cài; nếu bản cài không còn đủ file khởi động thì phần chương trình cũ được giữ nguyên bên dưới để chạy lại.

Giữ các bản/tag/gói trước đó. DGN/MDB, cấu hình, tài nguyên và runtime riêng không thuộc danh sách thay thế của bản sửa này.
