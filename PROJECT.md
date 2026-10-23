# Bàn giao SonMap+ V10.3

## Yêu cầu đã chốt

- Giữ DGN/MDB gốc; thử sửa trên bản sao. Hỗ trợ nguồn V7 qua Workmode=3.
- Mẫu ưu tiên: Phiếu đo đạc chỉnh lý thửa đất / Mẫu 03/CLBĐ.
- MDB lấy cùng tên/cùng thư mục DGN, không cho người dùng phải chọn đường dẫn thủ công.
- Kết quả cạnh DGN: Trich luc, In GCN, Phieu do dac chinh ly. Không tự tạo CSV hàng loạt.
- Địa chỉ: Xudong + xã/phường + tỉnh/thành, không có cấp huyện; dùng danh sách chọn địa bàn và nhớ theo thư mục.
- Màu đen bảng màu đầu ra đổi trắng để xem trên nền V8i đen.
- Tên SonMap+, đánh số V10 → V10.1 → V10.2 → V10.3; không dùng ngày làm phiên bản.
- Icon lông chim + địa cầu; Danh sách thửa mặc định thu gọn.
- Bỏ nút Đọc lại, Lưu dòng, Cập nhật VBA; vẫn tự chuẩn bị/lưu/cập nhật trong luồng xuất.
- Ánh xạ gắn Reference nguồn tại tọa độ thế giới, đúng tỷ lệ, không gắn trùng; bấm tiếp để ẩn/hiện và lưu DisplayFlag.

## Kiến trúc

app.py: Tk GUI, nạp MDB snapshot, sinh VBA, receipt worker, theo DGN active. quality.py: hình học/kiểm tra/tra cứu/chỉnh tay theo nguồn. workflow.py: đường dẫn, địa chỉ, icon. bridge.bas và mau03_engine.bas: xuất hồ sơ và khôi phục tọa độ thế giới, AssertWorldParcel trước receipt OK. reference_map.ps1: AddCoincident1 flags=7, Display toggle. Installer C# chứa payload và PowerShell sao lưu/cập nhật.

## Kiểm chứng và giới hạn

Đã chạy trực tiếp V8i trên bản sao dc86 V7, thửa 86/16/11 (15 đỉnh): cả ba loại hồ sơ mở lại khớp MDB với ngưỡng 0,00001 m; Reference giữ đúng nguồn, tỷ lệ 1 và Display. Kiểm tra tắt/bật trên bản sao giữ trạng thái và không tăng số Reference. Đây là mẫu thử có giới hạn; chưa kiểm chứng in giấy, đầy đủ font/bố cục hay mọi loại geometry. Danh sách hành chính trích từ nguồn Chính phủ năm 2025 chưa đầy đủ các xã giữ nguyên.

Chưa hoàn thiện tự sửa ranh/tạo topology trên DGN. Không được suy diễn kiểm tra polygon MDB là kiểm tra sạch toàn bản đồ. Dữ liệu thật và API Windows không có trong gói cloud-ready này.

## Workspace

SonMap.ucf giữ thiết lập V7/tài nguyên nhưng không nạp VietMap.Init.dll, giúp tránh khởi tạo mạng của plugin khi chỉ dùng SonMap. VietMapXM.ucf cũ giữ nguyên; không sửa DLL/khóa hoặc bỏ kiểm tra bản quyền. Thông báo Error2 của VietMap vẫn có thể có khi dùng workspace VietMapXM.
