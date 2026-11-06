# SonMap+ V10.27

## Kiểm thử

- 120 kiểm thử Python/Tk/PowerShell đạt, gồm native commit/rollback, không tự
  chạy lại lệnh ghi, khôi phục nguồn Reference và giao diện một nút mỗi loại hồ sơ.
- C# biên dịch bằng interop V8i cục bộ; native topology đã chạy thực tế trên
  các bản sao DGN/MDB với MicroStation V8i và Jet trên Windows.
- 250 thửa chạy lại: V10.26 37,158 giây; V10.27 3,077 giây.
- Thêm cùng một ranh tách trên hai bản sao, 250 → 251 thửa: V10.26 50,040 giây;
  V10.27 3,076 giây. MDB đầu ra của cặp cũ/mới có hash dữ liệu logic giống nhau,
  bao gồm Geometry, thuộc tính và ID; thời gian ghi DGN 47,409 → 0,368 giây.
- Đối chiếu tâm chỉ đọc: 250 thửa/250 tâm, 2,620 → 0,019 giây, cùng danh sách cell.
- Reference thử trên bản sao hồ sơ: gắn TrueScale/CoincidentWorld thành công,
  bật → tắt → bật lại thành công. Mở lại DGN gốc sau thử nghiệm.
- SHA256 DGN/MDB gốc không đổi sau toàn bộ phép thử.

## Giới hạn

Đây là số đo trên một bộ dữ liệu và một đường tách, không cam kết 3 giây cho mọi
bản đồ. Cập nhật phạm vi cục bộ còn dùng đường ghi cũ. Luồng chọn DGN cho cả ba
loại hồ sơ dùng cùng quy trình xuất; chưa nghiệm thu lại đủ ba loại bằng thao
tác chuột thực tế trong bản này. Không thay đổi thuật toán hình học địa chính.
