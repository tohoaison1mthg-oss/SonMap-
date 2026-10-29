# V10.17 — kiểm thử sửa lỗi/topology, MDB khác ổ đĩa và xóa dấu lỗi

Kiểm thử ngày 29/10/2026 trên laptop Windows, MicroStation V8i V7 Workmode=3,
Jet 32-bit và Python 3.12/Shapely 2.0.7. Các thao tác ghi dưới đây chạy trên
bản sao hoặc mẫu tổng hợp, không áp dụng kết quả thử lên DGN/MDB gốc.

## Lỗi thay MDB đã tái hiện

- Windows trả **WinError 17** khi dùng `os.replace` từ tệp tạm ở ổ C sang
  MDB đích ở ổ D. V10.16 quy mọi OSError ở bước này thành thông báo MDB bị
  khóa, khiến người dùng nhận sai nguyên nhân và phải chờ phục hồi DGN.
- V10.17 sao chép MDB đã kiểm chứng sang tệp chờ thay cùng thư mục đích,
  đối chiếu SHA256 rồi thay tệp. Phục hồi MDB dùng cùng cơ chế. Thử thật C → D
  đã tái hiện lỗi cũ và xác nhận cách mới thành công.
- Kiểm tra Windows sharing bằng DELETE access trước khi ghi DGN; kiểm thử
  với handle đọc thật xác nhận phát hiện khóa và không đổi nội dung tệp.
  Không ép đóng handle của phần mềm khác. Cơ sở kiểm tra sharing theo
  [tài liệu CreateFile của Microsoft](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew).
  Khóa phát sinh sau kiểm tra vẫn được xử lý bằng giao dịch phục hồi hiện có.

## Topology trên dữ liệu thật, dùng bản sao

- Cặp dc144 được sao chép vào thư mục thử ở ổ D, giao dịch tạm ở ổ C.
  MDB 181 → 182 bản ghi; đọc lại đủ 182 vùng và tâm/số thửa. Diện tích hình
  học từng vùng khớp ở độ chính xác kiểm tra 0,00001 m²; 177 bản ghi không
  thay đổi được đối chiếu toàn bộ cột và giữ nguyên.
- Lần chạy cuối: phân tích 22,20 giây (quét 21,86; dựng vùng 0,29), cập nhật
  23,52 giây. Lần chạy trước trong phiên: 17,64 và 25,67 giây tương ứng.
  Các số này phụ thuộc trạng thái máy/V8i; chưa có bằng chứng toàn bộ tác vụ
  nhanh hơn theo cùng tỷ lệ của riêng bước quét.
- Chạy lại khi MDB đã khớp, giữ một handle đọc MDB đang mở: cập nhật thành
  công, 182 → 182 bản ghi và SHA256 MDB không đổi; bước cập nhật 19,00 giây.
  Không chạy Jet trên bản tạm hoặc thay MDB khi không có delta.
- Phép đo riêng bước quét phục vụ ghi trên dc159: bộ quét cũ duyệt 761 phần
  tử mất 2,91 giây; bộ lọc interop trả 64 phần tử cần xét mất 0,52 giây.
  Đây không phải thời gian phân tích hay tạo topology toàn bộ.
- Không tạo SonMap_backups hoặc để lại tệp `.sonmap-pending-*` sau thành công.
  Mở lại dc159 gốc; SHA256 của các cặp DGN/MDB gốc dc159 và dc144 không đổi.
  Các báo cáo chi tiết có dữ liệu riêng chỉ nằm trong `data/`, không đưa vào Git.

## Mẫu tổng hợp Level 10, 23, 32 trên V8i thật

- Ranh trên ba Level tạo 4 vùng; giao điểm trung tâm được ghi thành 4 đầu
  đoạn thực. Giữ đúng lớp, màu và độ đậm từng nguồn. Ranh dư được giữ và báo
  lỗi, không tự xóa để ép tạo topology.
- Ẩn lớp hai lần liên tiếp không đổi phần tử hoặc byte DGN trên đĩa; Hiện lại
  khôi phục đúng trạng thái hiển thị đã lưu của từng view/level.
- Sửa ranh, ghi dấu lỗi hai lần không tăng dấu trùng. Sau khi sửa thủ công
  ranh dư và lưu DGN, Xóa dấu lỗi vẫn hoạt động dù hash phân tích cũ đã thay đổi.
- Chỉ xóa SMERR. Đường trên Level 50 và đường người dùng trên Level 60 vẫn
  giữ nguyên. Sau phân tích lại hết lỗi chặn, tạo đúng 4 tâm SMPARC; xóa dấu
  lần nữa không đổi ranh hoặc 4 tâm này.
- Mẫu sửa lần hai có `boundary_changed=False`; không viết lại ranh đã ổn định.
  DGN gốc được mở lại và kiểm tra hash không đổi.

## Python, PowerShell, giao diện và gói cài

- **94 kiểm thử Python/Tk đạt**. Các bài I/O mô phỏng kiểm tra riêng với
  Windows/V8i/Jet thật nêu trên: khác ổ đĩa, không giữ tệp chờ thay, lỗi khóa
  trước ghi DGN, phục hồi khi thay MDB thất bại, giữ MDB khi không có delta,
  nút xóa dấu sau sửa tay, tùy chọn tự ẩn và kích thước hộp thoại.
- `test_dgn_models.ps1`, `test_dgn_scan.ps1` đạt với đối tượng giả;
  `test_dgn_interop.ps1` đạt trên V8i thật, chỉ tạo đối tượng rời.
- Kiểm tra trực quan hai bảng mới ở mức DPI hiện tại: các nút/ô không bị
  cắt, nền sáng và tiêu đề xanh đậm, có thanh tiến trình và nút Hiện lại lớp.
- Kiểm thử gói cài đối chiếu VERSION, CRC ZIP và SHA256 từng tệp trong payload;
  không đóng gói DGN/MDB, runtime, assets, settings hoặc dữ liệu riêng.

## Giới hạn

Không coi các mẫu trên là bằng chứng mọi lỗi topology đã hết. Ranh hở, đoạn dư,
cell trên lớp ranh, kiểu hình học chưa hỗ trợ và thửa có lỗ vẫn cần xử lý theo
báo cáo; không tự nối/xóa hoặc đổi cấu trúc MDB. Xóa vòng tròn chỉ dọn dấu lỗi,
phải kiểm tra lại để xác nhận ranh. Thử nghiệm này không nghiệm thu toàn bộ
luồng xuất/in hồ sơ, mọi model hoặc mọi dữ liệu bản đồ.

Trình cập nhật chương trình tiếp tục bảo lưu phiên bản cũ và dữ liệu riêng theo
cơ chế có sẵn; không đồng nhất backup chương trình với tệp phục hồi DGN/MDB tạm.
