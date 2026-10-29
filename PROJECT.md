# SonMap+ — thông tin dự án

## Nguồn thông tin hiện hành

- Phiên bản thực tế lấy từ [VERSION](VERSION); tại lần cập nhật tài liệu này là
  **10.16**. Lịch sử thay đổi và phạm vi từng bản nằm trong [CHANGELOG.md](CHANGELOG.md).
  Không suy ra phiên bản từ README cũ hoặc tiêu đề bàn giao lịch sử.
- Quy ước phát triển lâu dài nằm trong [AGENTS.md](AGENTS.md), mục
  **Development principles**. Khi hướng dẫn cũ khác quy ước hiện hành, áp dụng
  quy ước này và đối chiếu changelog/báo cáo nghiệm thu của phiên bản liên quan.
- Dữ liệu địa chính do người dùng nhập và xác nhận có thể thay đổi hợp lệ.
  Không tự hoàn nguyên chủ sử dụng/thuộc tính sau cập nhật thành công. Chỉ phục
  hồi giao dịch kỹ thuật bị lỗi, chưa hoàn tất; không tạo thêm backup DGN/MDB
  sau mỗi lần chỉnh lý thành công, vẫn bảo đảm phục hồi khi ghi lỗi giữa chừng.
- Diện tích hiển thị và xuất hồ sơ theo dạng **568,7 m²**; giữ độ chính xác
  tính toán hình học, tọa độ và dữ liệu MDB, không tự ghi ngược số đã làm tròn.
- Ba ưu tiên: topology chính xác (tách/hợp thửa, giao điểm, ranh Level 10, 23,
  32); thao tác nhanh trên V8i (chọn thửa, sửa thuộc tính, cập nhật MDB trực
  tiếp); tự động xuất trích lục, phiếu đo đạc chỉnh lý, bảng tọa độ và biểu mẫu.
  Đây là định hướng, không phải xác nhận các chức năng đã hoàn tất.
- Giữ chức năng ổn định; chỉ thay quy trình, giao diện hoặc cấu trúc MDB khi
  cần thiết cho yêu cầu. Cập nhật quy ước bằng tài liệu không làm tăng VERSION.
- Kết quả nghiệm thu V10.16 được ghi trong
  [V10_16_VALIDATION.md](V10_16_VALIDATION.md) và changelog. Phân biệt kiểm thử
  Python/cloud với xác minh Windows/MicroStation V8i/Jet thực tế.

## Yêu cầu nền tảng từ bàn giao V10.3

- Giữ dữ liệu DGN/MDB của người dùng; kiểm thử sửa trên bản sao. Khi người dùng
  chủ động cập nhật dữ liệu thật, tuân thủ quy tắc giao dịch trong AGENTS.md.
  Hỗ trợ nguồn V7 qua Workmode=3.
- Mẫu ưu tiên: Phiếu đo đạc chỉnh lý thửa đất / Mẫu 03/CLBĐ.
- MDB lấy cùng tên/cùng thư mục DGN, không cho người dùng phải chọn đường dẫn thủ công.
- Kết quả cạnh DGN: Trich luc, In GCN, Phieu do dac chinh ly. Không tự tạo CSV hàng loạt.
- Địa chỉ: Xudong + xã/phường + tỉnh/thành, không có cấp huyện; dùng danh sách chọn địa bàn và nhớ theo thư mục.
- Màu đen bảng màu đầu ra đổi trắng để xem trên nền V8i đen.
- Tên SonMap+; phiên bản lấy từ VERSION, tăng thành phần minor mỗi nâng cấp
  ứng dụng theo AGENTS.md; không dùng ngày hoặc nhãn dev-v1/v2 làm phiên bản.
- Icon lông chim + địa cầu; Danh sách thửa mặc định thu gọn.
- Bỏ nút Đọc lại, Lưu dòng, Cập nhật VBA; vẫn tự chuẩn bị/lưu/cập nhật trong luồng xuất.
- Ánh xạ gắn Reference nguồn tại tọa độ thế giới, đúng tỷ lệ, không gắn trùng; bấm tiếp để ẩn/hiện và lưu DisplayFlag.

## Kiến trúc ghi nhận ở bàn giao V10.3

app.py: Tk GUI, nạp MDB snapshot, sinh VBA, receipt worker, theo DGN active. quality.py: hình học/kiểm tra/tra cứu/chỉnh tay theo nguồn. workflow.py: đường dẫn, địa chỉ, icon. bridge.bas và mau03_engine.bas: xuất hồ sơ và khôi phục tọa độ thế giới, AssertWorldParcel trước receipt OK. reference_map.ps1: AddCoincident1 flags=7, Display toggle. Installer C# chứa payload và PowerShell sao lưu/cập nhật.

## Kiểm chứng và giới hạn lịch sử V10.3

Phần này giữ bằng chứng và giới hạn tại thời điểm V10.3, không mô tả đầy đủ
khả năng hiện tại. Đối chiếu CHANGELOG.md và báo cáo nghiệm thu mới hơn trước
khi kết luận một chức năng chưa có hoặc chưa được kiểm chứng.

Đã chạy trực tiếp V8i trên bản sao dc86 V7, thửa 86/16/11 (15 đỉnh): cả ba loại hồ sơ mở lại khớp MDB với ngưỡng 0,00001 m; Reference giữ đúng nguồn, tỷ lệ 1 và Display. Kiểm tra tắt/bật trên bản sao giữ trạng thái và không tăng số Reference. Đây là mẫu thử có giới hạn; chưa kiểm chứng in giấy, đầy đủ font/bố cục hay mọi loại geometry. Danh sách hành chính trích từ nguồn Chính phủ năm 2025 chưa đầy đủ các xã giữ nguyên.

Chưa hoàn thiện tự sửa ranh/tạo topology trên DGN. Không được suy diễn kiểm tra polygon MDB là kiểm tra sạch toàn bản đồ. Dữ liệu thật và API Windows không có trong gói cloud-ready này.

## Workspace

SonMap.ucf giữ thiết lập V7/tài nguyên nhưng không nạp VietMap.Init.dll, giúp tránh khởi tạo mạng của plugin khi chỉ dùng SonMap. VietMapXM.ucf cũ giữ nguyên; không sửa DLL/khóa hoặc bỏ kiểm tra bản quyền. Thông báo Error2 của VietMap vẫn có thể có khi dùng workspace VietMapXM.
