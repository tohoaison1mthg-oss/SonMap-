# SonMap+ V10.14 — giao diện theo mẫu người dùng

Ngày 27/10/2026. Nâng từ V10.13, giữ nhánh `codex/sonmap-topology-ui`.

- Bảng sửa lỗi và topology được chia nhóm, đặt ô nhập và nút thao tác theo bố cục ảnh mẫu. Các công cụ phụ vẫn ở Tùy chọn để giữ luồng gán nhãn và xem thửa dự án.
- Bảng sửa thửa chỉ có các thuộc tính trong mẫu: tờ/thửa/tạm, diện tích/đất ở/pháp lý, MĐSD/ĐTSD, địa chỉ, chủ sử dụng/vợ chồng, giấy tờ và ghi chú. Gộp bí danh cột theo cấu trúc MDB, không hiện đồng thời LRD/MaLD hay địa chỉ thửa/xứ đồng thành các dòng trùng. Các cột ID, tọa độ và cột nội bộ khác không lên bảng và không bị xóa khỏi MDB.
- Diện tích trong ô, danh sách và báo lỗi hiển thị một chữ số sau dấu phẩy: `568,7`, `0,0`. Ô diện tích đo chỉ đọc. Diện tích pháp lý chưa sửa nhưng được chọn vẫn gửi lại giá trị gốc, tránh làm tròn âm thầm dữ liệu lưu.
- Thuộc tính chưa có trong MDB để trống/vô hiệu hóa, không tạo cột giả hoặc ghi vào cột khác. Nút con trỏ và Chọn đều dùng lại luồng pick trong thửa; giữ kiểm tra DGN/model và sao lưu trước ghi.

Đã chạy **81 kiểm thử Python/Tk trên Windows: đạt**, bao gồm giới hạn các trường trên form, không hiện cột kỹ thuật, định dạng diện tích và giữ nguyên độ chính xác khi lưu. Kiểm thử cấu trúc/hash gói cài nằm trong bộ kiểm thử.

Đã mở và quan sát riêng cả ba bảng bằng Computer Use, kiểm tra ô nhập/nút nằm trong cửa sổ. Dữ liệu hiển thị để kiểm tra là dữ liệu tổng hợp. Không ghi DGN/MDB người dùng trong phiên chỉnh giao diện.

Đây là thay đổi giao diện và định dạng hiển thị. Các phép toán hình học và cầu nối COM/V8i/Jet không đổi; bằng chứng chạy thật trên V7/Jet và pick/lưu của nền V10.13 được ghi trong `V10_13_VALIDATION.md`, không ghi thành một lần nghiệm thu mới trên dữ liệu địa chính thật.

Gói cài và nguồn V10.14 lưu riêng trong `data/releases/V10.14`. Giữ các gói/tag V10.13 và bản sao chương trình trước cập nhật; updater không thay dữ liệu riêng.
