# Phiên bản SonMap+

## V10.6

- Sửa lệnh quét DGN từ COM ngoài V8i: tạo ElementScanCriteria qua ứng dụng rồi truyền rõ vào Scan.
- Áp dụng cho cả đọc ranh và quét các phần tử cần thay trên bản sao.
- Tách chẩn đoán thành tạo tiêu chí, bắt đầu quét, chuyển phần tử và lấy phần tử hiện tại.
- Trình cài thử quét trực tiếp trên V8i đang mở, so với bản sao chỉ đọc và ghi báo cáo; không coi lỗi hoặc số phần tử 0 là kiểm thử đạt.
- Không đổi cách nhập nhiều lớp: 10,23,32 vẫn hợp lệ; giữ V10.5 để phục hồi.

Cần chạy xác minh trên V8i thực tế; kiểm thử đối tượng giả không thay thế COM thật.

## V10.5

- Phân biệt Python đã cài và Python phù hợp với thư viện SonMap; báo rõ 3.15/32-bit/thiếu thành phần.
- Probe Python có giới hạn 15 giây, không che mất lý do kiểm tra thất bại.
- Khi cài mới mà thiếu 3.12, tự tải bộ cài chính thức, kiểm tra chữ ký hợp lệ của Python Software Foundation.
- Cài Python 3.12 riêng cho SonMap, giữ các Python khác và không đổi PATH/liên kết tệp.
- Giữ gói, tag và nguồn V10.4 để phục hồi.

Cài tự động vẫn cần được xác minh trên Windows thật; kiểm thử cloud không thay thế thao tác này.

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
