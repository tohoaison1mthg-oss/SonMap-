# Phiên bản SonMap+

## V10.4

- Bảng chính gọn: Sửa lỗi, Tạo topology, Kết nối CSDL; hộp thoại riêng.
- Xử lý ranh trên bản sao, tạo vùng/tâm, gán nhãn và sửa thuộc tính thửa.
- Tạo/đọc MDB theo cấu trúc SonMap; tạo DGN và MDB mới từ topology.
- Sửa cách nhận model mặc định khi bản sao DGN không dùng tên hiển thị Default.
- Tự tìm Python 3.12 64-bit, khắc phục lỗi trình chạy chỉ in dòng đầu traceback.
- Gói cài/cập nhật theo người dùng, tạo lối tắt và sao lưu mã cũ.
- Công cụ khôi phục bản đã cài; giữ cả bản cũ và bản mới bằng backup và tag GitHub.
- Công cụ đọc cấu hình CAD tại C:\VietMapXM và chẩn đoán kết nối V8i, không sửa cấu hình gốc.
- Phiên bản hiển thị lấy từ VERSION; không dùng tên dev-v1/v2 thay phiên bản app.

Phần hình học/giao diện được kiểm thử cloud. Cầu nối V8i, Jet và trình cài
mới cần xác minh trên Windows thực; không coi các kiểm thử mô phỏng là bằng chứng
DGN/MDB của người dùng đã chạy thành công.

## V10.3

Mã nguồn ban đầu được đưa vào GitHub, có kiểm thử Python và các công cụ xuất
hồ sơ Windows/V8i. Tài nguyên runtime, VBA và mẫu hồ sơ đầy đủ được giữ riêng.
