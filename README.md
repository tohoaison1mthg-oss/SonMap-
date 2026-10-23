# SonMap+

Phần mềm địa chính cho Windows + MicroStation V8i. Phiên bản hiện tại: **V10.3**.

Tự nhận DGN đang mở và MDB cùng tên; tìm thửa, kiểm tra hình học, xuất trích lục/In GCN/Mẫu 03; địa chỉ từ Xudong + xã/phường + tỉnh; Reference tọa độ thực, bật/tắt bằng nút Ánh xạ. Giao diện gọn, danh sách thửa mở/thu gọn riêng. Có workspace SonMap V7 độc lập.

## Kiểm thử thuần Python (có thể chạy trên cloud)

`python -m unittest test_upgrade.UpgradeTests -v`

Không cần cài thư viện ngoài cho nhóm kiểm thử này. GUI, Jet MDB, COM, VBA và xuất DGN phải kiểm thử trên Windows có V8i; không coi kiểm thử cloud là bằng chứng V8i chạy đúng.

## Tài nguyên chạy thực tế trên Windows

Cần bổ sung riêng runtime Python Windows (thư mục runtime), project VBA ThanhTanApp.mvba, các mẫu hợp lệ vào assets, và bộ dữ liệu kiểm thử đã ẩn thông tin cá nhân. Không đưa bản đồ/MDB cá nhân, khóa, runtime/vendor DLL hoặc lịch sử chat lên repo này. Bản đầy đủ trên máy cũ và bộ cài SonMapPlus_V10_3_Setup.exe vẫn được giữ nguyên.

`installer/build.py` tạo payload sau khi bổ sung các tài nguyên. Build Setup.cs bằng csc .NET Framework x86, tham chiếu Windows.Forms, Drawing, IO.Compression và IO.Compression.FileSystem, nhúng payload.zip và install.ps1. Không có bộ cài hoàn chỉnh tự dựng được từ source-only khi thiếu các tài nguyên riêng.

## Tiếp tục phát triển

Đọc PROJECT.md trước. Gói này chỉ giữ mã và mô tả dự án; không sao chép các câu hỏi ngoài luồng. Repository mã nguồn: https://github.com/tohoaison1mthg-oss/SonMap-. Môi trường Codex Cloud cần được cấu hình riêng với repository này.
