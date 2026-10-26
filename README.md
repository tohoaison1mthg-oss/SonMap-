# SonMap+

Phần mềm địa chính cho Windows + MicroStation V8i. Phiên bản hiện tại: **V10.7**.

Tự nhận DGN đang mở và MDB cùng tên; tìm thửa, kiểm tra hình học, xuất trích lục/In GCN/Mẫu 03; địa chỉ từ Xudong + xã/phường + tỉnh; Reference tọa độ thực, bật/tắt bằng nút Ánh xạ. Giao diện gọn, danh sách thửa mở/thu gọn riêng. Có workspace SonMap V7 độc lập.

## Kiểm thử thuần Python (có thể chạy trên cloud)

`python -m unittest test_upgrade.UpgradeTests -v`

Không cần cài thư viện ngoài cho nhóm kiểm thử này. GUI, Jet MDB, COM, VBA và xuất DGN phải kiểm thử trên Windows có V8i; không coi kiểm thử cloud là bằng chứng V8i chạy đúng.

## Tài nguyên chạy thực tế trên Windows

Cần bổ sung riêng runtime Python Windows (thư mục runtime), project VBA ThanhTanApp.mvba, các mẫu hợp lệ vào assets, và bộ dữ liệu kiểm thử đã ẩn thông tin cá nhân. Không đưa bản đồ/MDB cá nhân, khóa, runtime/vendor DLL hoặc lịch sử chat lên repo này. Bản đầy đủ trên máy cũ và bộ cài SonMapPlus_V10_3_Setup.exe vẫn được giữ nguyên.

`installer/build.py` tạo payload sau khi bổ sung các tài nguyên. Build Setup.cs bằng csc .NET Framework x86, tham chiếu Windows.Forms, Drawing, IO.Compression và IO.Compression.FileSystem, nhúng payload.zip và install.ps1. Không có bộ cài hoàn chỉnh tự dựng được từ source-only khi thiếu các tài nguyên riêng.

## Tiếp tục phát triển

Đọc PROJECT.md trước. Gói này chỉ giữ mã và mô tả dự án; không sao chép các câu hỏi ngoài luồng. Repository mã nguồn: https://github.com/tohoaison1mthg-oss/SonMap-. Môi trường Codex Cloud cần được cấu hình riêng với repository này.

## Chức năng mới: tạo dữ liệu từ DGN chưa có MDB

Ba nút **Sửa lỗi**, **Tạo topology** và **Kết nối CSDL** mở các hộp thoại riêng để xử lý ranh trên bản sao, tạo tâm thửa, gán nhãn, sửa thuộc tính, tạo hoặc đọc MDB tương thích SonMap. Xem [hướng dẫn và giới hạn](TOPOLOGY.md). Phần hình học có kiểm thử cloud; cầu nối Windows/V8i mới chưa được xác minh thực tế.

## Cài/cập nhật V10.7 trên laptop

Giải nén **SonMapPlus_V10_7_Update.zip**, đóng SonMap cũ rồi nhấp đúp
**Cai_dat.cmd**. Trình cài tái sử dụng Python 3.12 64-bit, chuẩn bị thư viện,
cài vào `%LOCALAPPDATA%\SonMapPlus\App` và tạo lối tắt **SonMap+** trên Desktop.
Mã cũ được sao lưu, dữ liệu DGN/MDB và các thư mục riêng không bị ghi đè.
Gói cài không kèm Python, MicroStation hoặc tài nguyên xuất hồ sơ riêng.

Để tạo gói từ mã nguồn: `python installer/package_update.py --output <thu-muc-moi>`.
Phiên bản lấy từ VERSION; lần nâng cấp kế tiếp phải tăng số theo AGENTS.md.

## V10.5 — Python trên máy khác

Trình cài ghi rõ phiên bản Python tìm thấy. Nếu máy chỉ có Python 3.15 hoặc
không có CPython 3.12 64-bit phù hợp, Cai_dat.cmd tải bộ cài chính thức, xác minh
chữ ký Python Software Foundation rồi cài Python riêng vào SonMapPlus/Python312.
Không gỡ Python 3.15, không đổi PATH hoặc liên kết tệp. Lần đầu cần Internet.

## Làm trực tiếp và tiếp tục trên laptop

V10.7 mặc định ghi DGN hiện tại và cập nhật MDB kết nối, có sao lưu. Thửa con
chưa có số chính thức hiển thị Chờ số; xuất hồ sơ cần gán số trước. Có gói
Laptop_Workspace để chạy Codex local trong VS Code rồi gửi mã lên GitHub.
Xem TOPOLOGY.md; thao tác COM/Jet trực tiếp vẫn cần kiểm chứng trên Windows thật.
