# SonMap+ V10.21 — nghiệm thu sửa bốn luồng

- 109/109 kiểm thử Python/Tk đạt trên Windows, gồm mở form từ ID dòng đang
  chọn, trùng số nhưng khác ID, polygon nhiều vòng, pick vùng có lỗ, nối đầu
  vào cạnh và giữ lỗi ngoài ngưỡng. Không coi unit test là xác minh Jet.
- Dữ liệu dc102 thực: đọc đủ 363 bản ghi, gồm 3 polygon có vòng trong.
  Bộ đọc kiểm tra số vòng, chiều dài blob, vòng kín, tọa độ hữu hạn và tính
  hợp lệ toàn polygon. Không bỏ vòng trong khi đối chiếu, tính diện tích hay pick.
- Kiểm thử V8i/Jet ghi trên bản sao dc102: 363 → 365 vùng; hai vùng đã có ranh
  chia trong DGN được tách theo hình học, giữ thuộc tính cha. Các vùng chỉ lệch
  trong 1 mm giữ ID, Geometry và diện tích MDB gốc. Chạy lần hai không đổi
  ranh và không đổi bản ghi MDB. Không ghi sửa DGN/MDB thật.
- Đầu ranh được nối thật trong ngưỡng mặc định 0,01 m, thay cho chỉ bỏ cảnh báo.
  Nút lệch dưới 1 mm được gom theo nhóm có giới hạn khoảng cách giữa mọi cặp;
  không gom nối tiếp làm trôi tọa độ. Nối hình chiếu chỉ khi có vị trí duy nhất.
  Có thể tắt nối hoặc chỉnh ngưỡng trong Sửa lỗi; ranh ngoài ngưỡng vẫn báo.
- Sáu lần xuất V8i đạt: Trích lục / GCN / Mẫu 03 cho thửa 102/1/0 và thửa
  có lỗ 102/2007/340. Đọc lại DGN xác minh cả vòng ngoài và vòng trong trong
  ngưỡng 0,00001 m. Vòng trong có nhãn riêng; Trích lục/Mẫu 03 có bảng bổ sung
  ngoài khung chính, GCN có chiều dài cạnh. Chưa nghiệm thu bố cục in giấy
  cho bảng vòng trong hoặc mọi loại mẫu/font của người dùng.
- Định dạng bảng xuất: tọa độ 3, cạnh 2, diện tích 1 chữ số sau dấu phẩy.
  Không dùng giá trị đã định dạng để ghi ngược dữ liệu gốc.
- Xuất dùng khóa tờ/thửa/ID, không tự đổi số trùng và không chặn thửa đã chọn
  vì thửa khác chưa có số. Thửa được chọn chưa có số vẫn yêu cầu nhập số.
- Báo cáo chi tiết cục bộ:
  `data/v1021-validation-6a57a7aa9a44451fb0c16f877772bbd7/report.json`.
  DGN/MDB gốc kiểm tra hash trước/sau không đổi. Kiểm thử xuất chỉ bỏ hộp
  thoại thông báo thành công trong module thử, giữ nguyên đường ghi/kiểm tra.
- Gói cập nhật kiểm tra CRC và SHA256 từng tệp; không chứa dữ liệu riêng,
  assets hay runtime. Giữ gói/tag cũ và sao lưu chương trình trước cập nhật.
