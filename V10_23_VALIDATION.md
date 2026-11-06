# SonMap+ V10.23

Sửa cấu hình khởi động và chẩn đoán lỗi, không thay đổi thuật toán địa chính.

- 111 kiểm thử Python/Tk/PowerShell đạt trên Windows, gồm kiểm tra tạo workspace
  trong đường dẫn có dấu cách và lỗi thiếu quyền thay thế MDB.
- Tất cả tệp PowerShell phân tích cú pháp thành công.
- Workspace SonMap nằm trong thư mục ứng dụng, được tạo lại khi mở V8i qua
  start_v8i.ps1; lối tắt cài đặt trỏ tới trình khởi động này.
- Lỗi COM khi V8i chưa mở/không truy cập được có hướng dẫn mở V8i cùng tài khoản
  và mức quyền. Không tự chạy lại thao tác ghi. Đây không phải cách sửa mọi lỗi COM.
- Lỗi quyền MDB báo tên tệp và yêu cầu Modify. Không tự thay đổi ACL của dữ liệu.
- Lỗi topo lưu traceback tại data/topology-error.log.

Chưa nghiệm thu ghi topology thực tế trên DGN/MDB bằng V10.23 hoặc kiểm thử máy
Windows sạch. Không coi kiểm thử mô phỏng quyền và workspace là nghiệm thu V8i.
Giữ nguyên giới hạn nghiệp vụ và bộ cài V10.22 trong V10_22_VALIDATION.md.
