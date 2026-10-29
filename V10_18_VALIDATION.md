# V10.18 — tăng tốc đọc ranh, zoom lỗi và xóa từng vòng báo lỗi

Kiểm thử ngày 29/10/2026 trên Windows, MicroStation V8i SS3, Python 3.12,
Shapely 2.0.7 và Jet 32-bit. Phiên bản trước là 10.17 trên nhánh
`codex/sonmap-topology-ui`; không hợp nhất sang main.

## Kết quả tốc độ và phạm vi số đo

- Đối chiếu hai đường đọc cùng bản đồ dc101 đang mở, cùng 1.408 phần tử ranh
  Level 10,23,32, cùng lựa chọn đọc nhãn/cung/complex. Hai lượt PowerShell
  riêng mất 24,76 và 24,88 giây. Cầu nối trong V8i mất 0,895 giây ở lượt
  đầu của phiên đo, sau đó 0,110 và 0,099 giây. Snapshot JSON giống nhau
  toàn bộ, bao gồm tọa độ, thuộc tính nét và ID nguồn; hash DGN không đổi
  trong phép đo chỉ đọc. Các lượt thăm dò trước có thời gian khác theo
  trạng thái máy; không dùng một tỷ lệ tăng tốc cho mọi bản đồ.
- Giữ PowerShell chạy sẵn đơn thuần vẫn mất 14,78–20,56 giây để đọc cùng
  1.408 phần tử. Do đó đường đọc chính chuyển vào add-in V8i, không chỉ đổi
  cách mở PowerShell. Worker 32-bit vẫn dùng cho thao tác giao dịch.
- Lõi dựng vùng không đổi. Cùng snapshot ở phép đo trên tạo 310 vùng bằng
  SonMap; không đồng nhất với ảnh VietMap 329 thửa ở thời điểm trước đó,
  hoặc coi đây là nghiệm thu tương đương toàn bộ topology của hai sản phẩm.
- Trên mẫu tổng hợp 4 vùng V7, prepare gồm lưu/quét/dựng vùng mất 0,428 rồi
  0,202 giây khi đã nạp cầu nối và không tự ẩn lớp; cập nhật DGN/MDB thử mất
  1,605 giây, đọc lại đủ 4 bản ghi Jet. Zoom tại lỗi mất 0,112–0,125 giây.
  Xóa một vòng mất 2,274 giây ở lượt đầu có nạp interop ghi, xóa toàn bộ mất
  0,522 giây ở lượt tiếp theo. Không dùng số đo đọc ranh làm thời gian toàn
  bộ quy trình sửa lỗi/tạo topology/cập nhật MDB.

## Cầu nối và kiểm tra giao dịch

- Add-in C# chạy trên luồng giao diện V8i, chỉ chấp nhận Extract và Focus.
  Kiểm tra đúng đường dẫn DGN/model và từ chối model 3D. Cùng nguồn interop
  với đường đọc trước, không chuyển đơn vị hoặc làm tròn tọa độ.
- Tự biên dịch bằng Bentley assemblies của máy, lưu DLL sinh ra trong
  `data/cad-bridge`, không phân phối DLL Bentley. Thư mục tìm add-in được
  bổ sung bằng ActiveWorkspace.AddConfigurationVariable trong phiên chạy;
  không sửa UCF/PCF hoặc thiết lập bảo vệ phần mềm.
- Task ID/DLL theo hash mã và thư mục ứng dụng, tách bản phát triển với bản
  đã cài. Kiểm tra PID/thời điểm khởi động của V8i trước mỗi yêu cầu để
  không dùng endpoint cũ khi V8i khởi động lại. Request/response có ID và
  công bố tệp bằng rename; hết thời gian không xác nhận thành công.
- PowerShell 32-bit dùng lại trong một phiên, nhưng script có scope riêng,
  đối số truyền qua JSON/hashtable có tên, giữ switch và Unicode. Kiểm thử
  thật xác minh exit code lỗi, throw, tái sử dụng type tĩnh, script ghi
  Console không có newline, và process bị dừng không tự phát lại yêu cầu.
- Các thao tác ghi tiếp tục có bản phục hồi tạm, kiểm tra hash/model và
  đọc lại. Không bỏ các chốt kiểm tra để đạt số đo nhỏ hơn.

## Vòng báo lỗi và giao diện

- Tạo hai SMERR trong bản sao mẫu, kèm cell USERERR cùng vị trí và tâm
  SMPARC. Xóa riêng điểm thứ nhất còn đúng một SMERR; ID/type/level/name
  toàn bộ phần tử không phải SMERR giữ nguyên. Xóa toàn bộ không còn SMERR,
  vẫn giữ các phần tử đối chứng. Kiểm tra quét lại trước khi báo thành công.
- Chặn sai model trước khi lưu hoặc xóa; DGN bản sao không đổi khi bị chặn.
  Cho phép dọn vòng sau sửa ranh thủ công bằng snapshot phục hồi mới, không
  dùng hash phân tích cũ để chặn nhầm hoặc phục hồi nét người dùng đã sửa.
- Danh sách có Trước/Sau, bộ đếm, Tìm trên DGN, Phóng to/Thu nhỏ và Xóa
  vòng đang chọn. Xóa vòng vẫn giữ danh sách để định vị, nhưng bỏ project
  có thể ghi; cần phân tích lại trước lần cập nhật tiếp theo. Đổi DGN bỏ
  cả danh sách định vị cũ. Zoom DANGLE lấy đầu hở, không lấy giữa đoạn dài.
- Đã xem trực tiếp bảng lỗi trên Windows ở DPI hiện tại: hai hàng nút và
  bộ đếm đầy đủ, không cắt chữ hoặc che nút thao tác.

## Dữ liệu gốc và giới hạn

Các thao tác tạo/xóa phần tử và ghi Jet chạy trên bản sao/mẫu trong `data/`.
MDB dc101 gốc giữ nguyên hash. Khi chuyển khỏi rồi mở lại dc101, V8i ghi
lại tệp nên hash DGN thay đổi; không báo hash gốc giữ nguyên hoặc tự chép
snapshot cũ đè dữ liệu hiện hành. Đã so sánh snapshot tất cả Level 1–63,
gồm nhãn, hình học đọc được, ID và thuộc tính nét trước/sau: hoàn toàn khớp.
Đối chiếu này không thay thế kiểm tra byte mọi loại phần tử DGN.

Không mặc định bỏ qua đỉnh treo hoặc mọi lỗi topology như tùy chọn VietMap
đã quan sát; không thay quy tắc kế thừa MDB, chức năng xuất hồ sơ hoặc cấu
trúc MDB. Không xóa vòng do VietMap hay người dùng tạo chỉ vì cùng Level.
Chưa nghiệm thu mọi kiểu geometry, model, bản đồ lớn hoặc bộ in/xuất hồ sơ.

## Kiểm tra tự động và gói chương trình

- 100 kiểm thử Python/Tk đạt, gồm kiểm thử transport PowerShell thật và
  kiểm thử giao diện có mô phỏng I/O. PowerShell model/scan đạt với đối
  tượng giả; interop Point3d/marker đạt trên V8i thật bằng phần tử rời.
- Gói cập nhật kiểm CRC ZIP và SHA256 từng mục payload, VERSION và nguồn
  tiêu đề; không chứa data, DGN/MDB, settings, runtime, DLL hoặc tài nguyên
  riêng. Trình cập nhật/rollback chương trình giữ cơ chế sao lưu bản bị thay.
- Đã chạy trình cập nhật trên laptop với NoLaunch, cài V10.18 vào
  `%LOCALAPPDATA%/SonMapPlus/App`, tái sử dụng Python/venv có sẵn. Chương
  trình V10.17 được lưu dưới Backups/before-10.18-…; cập nhật startup VBA
  báo không cần sửa thêm. Không hạ phiên bản hoặc ghi đè gói/tag cũ.
- Kiểm tra từ đúng thư mục chương trình đã cài: tiêu đề SonMap+ V10.18;
  đọc 1.408 phần tử mất 0,592 giây lần đầu của tiến trình kiểm tra, rồi
  0,157 và 0,108 giây. Hash DGN giữ nguyên trong phép thử chỉ đọc này.
- Kết quả đo và bản sao dữ liệu nằm trong `data/vietmap-study-20261029/`,
  không đưa lên GitHub. Hướng dẫn Add-in của Bentley đã được đối chiếu với
  API đang cài: [Learning MicroStation Addins Step by Step](https://bentleysystems.service-now.com/community?id=community_blog&sys_id=34d1e3c71b394e50dc6db99f034bcb5e).
