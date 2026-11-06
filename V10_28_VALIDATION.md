# SonMap+ V10.28

Đầu ranh được chiếu lên cạnh xiên có thể lệch chính cạnh đó một ULP. Bản cũ
chỉ thay đầu ranh, chưa tách cạnh đích ở cùng tọa độ, nên GEOS vẫn thấy ranh hở.
Bản mới chèn chính đỉnh đã chọn trên cả hai cạnh và giữ thuộc tính nguồn.

- Tái hiện bằng dữ liệu tổng hợp tọa độ lớn, hai đầu đường chia gần cạnh xiên.
  Kiểm tra tạo hai vùng kín, tổng diện tích, bậc nút chung và xuất dữ liệu.
- Tắt nối ranh thì vẫn chặn dữ liệu hở. Các kiểm thử khe hở ngoài ngưỡng giữ nguyên.
- Dựng lại snapshot DC113 chỉ trong bộ nhớ: trước 212 vùng và 2 DANGLE ẩn,
  export_rows bị chặn; sau vẫn 212 vùng, không DANGLE ẩn và export_rows đạt.
- Chưa chạy ghi V8i/Jet thực tế bằng bản này. Không sửa DGN/MDB gốc khi chẩn đoán.
