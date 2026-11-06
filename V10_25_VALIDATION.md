# SonMap+ V10.25

- Tự lấy số tờ từ tên DGN dạng dc188, DC00116, to/tb/sheet; khi tên không xác
  định, dùng ToBD duy nhất trong MDB. Không đoán tờ 1. Ô số tờ chỉ đọc.
- Chọn thửa dùng IPrimitiveCommandEvents trong V8i thay cho GetInput ngoài
  tiến trình. Một DataPoint hoàn tất, Reset hủy; kiểm tra DGN/model/MDB.
- Bỏ Số tạm khỏi form, giữ nguyên dữ liệu cột MDB. Không gán ID làm nhãn tâm.
- Đọc mẫu CENTRD thực tế ở lớp 11. Giữ tâm có sẵn trong thửa, bỏ tâm trùng
  trong cùng vùng và sao cấu trúc CENTRD cho vùng mới. Nếu không có mẫu, tạo
  ký hiệu độc lập gồm vòng tròn, hình thoi và cross, không có nhãn ID.
- 113 kiểm thử Python/Tk đạt; interop và picker C# biên dịch thành công với
  thư viện V8i đã cài. Không đóng gói DLL Bentley hoặc DGN/MDB riêng.
- Thử tạo tâm trên bản sao mở nền bằng OpenDesignFileForProgram bị V8i chặn:
  Operation requires the active design file. Chưa nghiệm thu ghi tâm hoặc
  thao tác chuột thực tế bằng V10.25 trên bản sao đang hoạt động.
- Chưa coi kiểm thử/biên dịch là bằng chứng đầy đủ cho nghiệp vụ V8i/Jet.
