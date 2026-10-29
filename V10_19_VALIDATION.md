# V10.19 — vị trí lỗi nhìn thấy được và giảm thời gian sửa ranh

Kiểm thử 29/10/2026 trên Windows, V8i SS3/V7, Python 3.12/Shapely 2.0.7.
Phiên bản trước 10.18, nhánh codex/sonmap-topology-ui. Các phép ghi dùng
bản sao trong data; không chạy thử sửa ranh trên DGN/MDB gốc.

## Tái hiện và nguyên nhân

- Bản ghi phân tích người dùng trên dc102 có 362 vùng, 25 thông báo nội bộ,
  24 dòng sau lọc thông báo đã tạo giao điểm. Thời gian prepare ghi trong
  job khoảng 3,13 giây, chưa gồm bước ghi sửa ranh.
- Bảng lỗi lớn che tâm view. Focus 10.18 không có dấu tạm riêng, giới hạn
  zoom sớm và không kiểm tra trường hợp không có view đang mở. Nếu V8i bị
  thu nhỏ, việc đặt view rồi trả thành công chưa bảo đảm người dùng thấy lỗi.
- Tại X=513042,2234; Y=1062311,2329, dữ liệu có các điểm cách nhau khoảng
  1,19e-7–3,98e-7 m, trong khi model báo 1.000 UOR/master unit với đơn vị m:
  độ phân giải 0,001 m. Không thể nhìn khe nhỏ như vậy bằng nét bản đồ ở
  tỷ lệ thông thường. Không tự kết luận đã hết lỗi hoặc ghi tọa độ làm tròn.

## Hiển thị và định vị

- Tìm/zoom tự chuyển sang bảng nhỏ ở góc; Danh sách khôi phục cửa sổ đầy đủ.
  Có bộ đếm, loại lỗi, tọa độ và Trước/Sau, zoom, xóa vòng đang chọn.
- Focus khôi phục cửa sổ V8i nếu bị thu nhỏ và đưa lên trước, sau đó đặt
  tâm/extents. Không có view mở thì báo lỗi, không trả thành công giả.
- Chữ thập vàng dùng TransientElementContainer, Overlay/DontIncludeInFit,
  không bật IncludeInPlot và không AddElement. Dọn khi đổi DGN/model, thay
  dấu khi chuyển lỗi; không tạo cell DGN. Đã nhìn trực tiếp dấu tại đúng
  vị trí người dùng gửi, không bị bảng lớn che.
- Cho zoom sâu hơn nhưng khống chế span tối thiểu theo UOR để không tạo
  view vượt khả năng biểu diễn. Chi tiết nút gần hiện khoảng cách, chú thích
  khi dưới độ phân giải; chỉ định dạng thông báo, không đổi số gốc.
- Thửa có lỗ lấy biên lỗ đầu tiên làm vị trí lỗi, thay vì chỉ vùng bao ngoài.
  Không thay quy tắc chặn thửa có lỗ hoặc tự xóa/hàn khe vì khó nhìn thấy.

## Tốc độ toàn bộ phần tìm/sửa ranh

Đo cùng cấu hình dc102 trên các bản sao độc lập, tự ẩn lớp bật:

| Đường xử lý | Phân tích | Ghi sửa ranh | Cộng hai bước |
| --- | ---: | ---: | ---: |
| 10.18 | 3,908 s | 27,496 s | 31,404 s |
| Ghi ranh trong V8i, còn chuẩn bị cũ | 3,339 s | 0,784 s | 4,123 s |
| 10.19, chuẩn bị và ghi trong V8i | 1,042 s | 0,886 s | 1,929 s |

Đây là các lượt đo trên laptop, đã có chi phí nạp riêng; không cam kết mọi
bản đồ cùng thời gian hoặc đồng nhất với toàn bộ tạo topology/cập nhật MDB.
Thông báo hoàn tất Sửa lỗi đo từ bắt đầu phân tích đến ghi xong, gồm thời
gian điều phối giao diện; không dùng riêng scan_seconds làm tổng thời gian.

Đọc lại hai DGN kết quả bằng đường Extract độc lập: **1.687 phần tử ranh**
có tọa độ và thuộc tính nét giống nhau hoàn toàn giữa cách ghi cũ/mới,
không dùng ID mới làm khóa so sánh vì thay ranh có thể cấp ID mới.

## Giao dịch, bảo toàn dữ liệu và thử lỗi

- Fast clean chỉ cho sửa ranh hiện tại không theo scope và không cập nhật
  MDB. Topology/MDB, scope và chế độ xuất bản sao giữ đường giao dịch cũ.
- Chốt DGN/model/2D, hash nguồn và bản phục hồi, lớp ranh/lỗi và phần tử
  chưa hỗ trợ được kiểm trước ghi. Chuẩn bị phần tử thay thế trước khi xóa
  ranh; tạo nút giữ double và nét nguồn. Đọc lại tọa độ phần tử sau Save theo
  độ phân giải native. Sửa API tạo lớp mới thành DesignFile.AddNewLevel.
- Lỗi sau thay đổi thử mở bản phục hồi, chép về nguồn rồi mở lại. Nếu bước
  phục hồi lỗi, cầu nối gửi rescue_required; coordinator giữ thư mục cứu hộ,
  không xóa vì file trên đĩa tình cờ còn hash cũ trong khi bộ nhớ đã thay đổi.
- Mẫu 4 vùng: vùng/diện tích giữ nguyên, USERERR và SMPARC giữ ID/thuộc tính.
  Chạy clean lần hai không đổi ID phần tử; style nguồn không tồn tại bị
  chặn trước ghi. Thử zoom ba mức không tăng phần tử hình học. V8i có thể tự lưu
  view nên không dùng hash toàn tệp làm bằng chứng duy nhất cho zoom.
  Việc khôi phục cửa sổ có lần tạo metadata ViewGroup (type 96); không
  nhầm metadata view với ranh/cell hình học hoặc khẳng định mọi phần tử kể
  cả metadata đều bất biến khi đổi view.
- Ẩn lớp hai lần giữ snapshot đầu, khôi phục dọn tệp trạng thái; không lưu
  DGN trong riêng thao tác ẩn/hiện. Có kiểm tra tương thích state 10.18.
- Các phép thử cuối lưu snapshot gốc trước/sau trên Level 1–63 và đối chiếu
  khớp. Lần thăm dò đầu có so sánh không khớp sau mở lại và không dùng để
  nghiệm thu bảo toàn; không lấy snapshot cũ ghi đè dữ liệu người dùng.
  Việc V8i ghi lại tệp/view khi đổi bản vẽ có thể đổi hash; không khẳng định
  mọi byte DGN gốc giữ nguyên. Không có thao tác ghi MDB gốc trong thử clean.

## Tự động, giao diện và giới hạn

- 102 kiểm thử Python/Tk đạt ở lượt kiểm tra trước đóng gói: thêm kiểm tra
  bảng nhỏ/khôi phục danh sách, khoảng cách dưới UOR không sửa tọa độ và
  giữ cứu hộ khi cầu nối báo phục hồi lỗi. I/O trong phần unit test được
  mô phỏng riêng với các thử V8i thật nói trên.
- Chưa cưỡng bức lỗi sau Save trên V8i thật để kiểm mọi nhánh phục hồi C#;
  đã kiểm việc giữ cứu hộ ở coordinator bằng lỗi mô phỏng. Không suy rộng
  mẫu này thành nghiệm thu mọi lỗi ghi đĩa, model hoặc kiểu phần tử.
- Các package/tag cũ giữ nguyên; gói mới kiểm CRC ZIP và SHA256 manifest.
  Source chỉ lên nhánh phát triển hiện có, không gói DLL Bentley, DGN/MDB,
  runtime, settings hoặc data. Trình cập nhật giữ backup/rollback chương trình.

## C?i ??t tr?n laptop

- ?? c?i 10.19 b?ng tr?nh c?p nh?t, x?c nh?n VERSION v? APP_TITLE t?i th? m?c
  c?i, ??i chi?u byte c?c m?-?un c?u n?i/giao di?n/quy tr?nh v?i m? ?? ki?m th?.
- B?n ch??ng tr?nh 10.18 ???c gi? trong Backups/before-10.19-ecc995d9df224ffa9418812cc0ddbee9.
  Tr?nh c?p nh?t t?i s? d?ng runtime v? gi? nguy?n data/settings/assets.
- C?u n?i t? th? m?c c?i ?? n?p v?o V8i, ??c 1.694 ph?n t? ranh c?a dc102
  v? ??nh v? th?nh c?ng ?i?m X=513042,2234407789; Y=1062311,232865322.
  Quan s?t tr?c ti?p ch? th?p v?ng t?i t?m view; kh?ng ch?y s?a ranh tr?n b?n g?c.
- L??t ki?m th? Python cu?i sau thay ??i hi?n th?: 102/102 ??t.
