# SonMap+ V10.13 — nghiệm thu ngày 27/10/2026

## Thay đổi đã hoàn thành

- Làm gọn bằng ẩn lớp và khôi phục trạng thái hiển thị từng view. Thao tác này không xóa hay sửa phần tử.
- Sửa ranh tạo nút tại giao cắt và tiếp giáp chữ T, giữ lớp và thuộc tính nét của ranh nguồn; giữ đoạn dư/hở để báo và sửa thủ công. Không tự bù ranh còn thiếu khi chưa có chỉ định.
- Duyệt lỗi Trước/Sau, tìm/zoom đến lỗi trên DGN, ghi dấu lỗi có sao lưu và kiểm tra lại sau sửa tay. Tạo topology tiếp tục chặn lỗi ảnh hưởng phạm vi cập nhật.
- Bảng thông tin thửa có nút con trỏ pick bên trong, chọn lại thửa, tùy chọn zoom, checkbox trường ghi và tab toàn bộ thuộc tính. Hủy pick vô hiệu hóa lưu thửa cũ.
- Đọc các cột sẵn có của MDB. Cho điền/sửa/xóa nội dung văn bản, số và logic theo kiểu cột; ID, geometry và diện tích đo chỉ đọc. Các kiểu chưa hỗ trợ vẫn hiển thị ở tab toàn bộ thuộc tính. Không tự thêm/xóa cột cơ sở dữ liệu.
- Ghi trên bản sao MDB, dùng tham số, transaction và kiểm tra tất cả bản ghi trước khi thay tệp. Giữ các trường không chọn, thửa khác, bảng/cột khác và sao lưu trước ghi. Kiểm tra lại DGN/model đang mở trước khi lưu.
- Sửa lỗi đọc mảng nhiều thửa khi tạo MDB bằng PowerShell 5.1/Jet 32-bit.

## Kiểm thử

**78 kiểm thử Python/Tk đạt** bằng môi trường CPython 3.12 đang dùng cho SonMap trên Windows. Bao gồm phân tích hình học, cập nhật thửa tách, chọn thửa, kiểu dữ liệu, lỗi đọc lại, hủy pick, chặn ghi khi đổi DGN, giao diện và cấu trúc/checksum gói cài. Các lần thử Tk trong sandbox không truy cập được Tcl; chạy ngoài sandbox xác nhận Tcl 8.6.15 hoạt động. Không thay hay cài lại Tcl/Python.

Đã thử **Windows/MicroStation V8i SS3, V7 workmode, Jet 32-bit** trên bản sao seed 2D, với hai vùng khép kín, ranh chia lớp khác, một đoạn dư và một phần tử ngoài lớp ranh:

- Ẩn lớp giữ nguyên danh sách phần tử và hash DGN trên đĩa; khôi phục đúng trạng thái lớp của các view.
- Hai vùng được phát hiện; giao điểm ghi thành đầu đoạn thực. Lớp/màu/độ đậm được giữ; phần tử ngoài lớp ranh và đoạn dư không bị xóa.
- Ghi dấu lỗi, rồi ghi lại không làm tăng số dấu lỗi cũ. Đưa khung nhìn đến vị trí lỗi/thửa; kiểm tra tâm khung nhìn sau đặt.
- Jet ghi thuộc tính Unicode và đổi số thửa theo ID; đọc lại đúng, thửa còn lại và hình học/diện tích không đổi; có bản sao lưu.
- Thử thêm cột ghi chú MEMO dài hơn 255 ký tự, số thực dùng dấu phẩy thập phân, số nguyên và cờ logic trên MDB thử riêng. Ghi/đọc lại đúng; xóa nội dung ghi chú và giá trị số cho phép NULL không đổi thửa còn lại hay cờ chưa chọn.
- Thử **chuột thật qua UI**: mở bảng SonMap, bấm nút con trỏ, nhấp bên trong thửa thử số 102; bảng nạp đúng tờ 185, diện tích 100,0 m² và thông tin MDB. Nhập riêng loại đất `ODT`, bấm Lưu, đọc lại thấy `ODT`; checkbox được bỏ dấu sau lưu. Dữ liệu này là tổng hợp, không phải thửa người dùng.
- Đóng phiên thử và mở lại DGN người dùng; kiểm tra hash gốc không đổi. Chưa áp dụng sửa ranh hay đổi thuộc tính vào DGN/MDB gốc của người dùng.

Lần dựng fixture ban đầu từ bản vẽ đầy đủ gặp `Bad modelRef` khi cố bỏ các phần tử điều khiển nội bộ. Bản gốc được mở lại và hash giữ nguyên; fixture tiếp theo dùng seed độc lập. Đây là lỗi của cách dựng fixture, không được ghi thành một ca sửa bản vẽ thành công.

Kết quả runtime riêng tư lưu dưới `data/v1013-validation-*`, không nằm trong gói cài hay GitHub. Kiểm thử tổng hợp không thay thế nghiệm thu toàn bộ dữ liệu địa chính thực tế, mọi loại đường cong/kiểu nét tùy biến và cấu trúc MDB ngoài các kiểu đã hỗ trợ.

## Phát hành và khôi phục

Phiên bản ứng dụng lấy từ VERSION: **10.13**. Nhánh giữ nguyên `codex/sonmap-topology-ui`; không gộp sang main. Gói V10.13 và nguồn lưu riêng trong `data/releases/V10.13`, không ghi đè V10.12 hay tag cũ.

Updater hiện có sao lưu các tệp chương trình bị thay, giữ DGN/MDB, data, assets, settings, runtime và môi trường Python. Công cụ rollback giữ lại cả phiên bản đang được thay ra. Trạng thái cài lên laptop và mã commit/tag được báo riêng sau khi hoàn tất kiểm tra gói.
