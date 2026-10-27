# Nghiên cứu VietMapXM trên Windows — 27/10/2026

Ghi chú tiếp nối: các cải tiến SonMap theo nghiên cứu này đã được thực hiện ở V10.13;
xem [nghiệm thu V10.13](V10_13_VALIDATION.md). Phần dưới lưu nguyên kết quả giai đoạn nghiên cứu trước nâng cấp.

## Phạm vi và phiên bản

- GitHub: `tohoaison1mthg-oss/SonMap-`, nhánh `codex/sonmap-topology-ui`, `VERSION=10.12` đã đọc qua kết nối GitHub. Checkout hiện tại commit `30138f0`, tag `v10.12`, ban đầu sạch.
- VietMap đang chạy trong MicroStation V8i SS3, thanh công cụ hiển thị `3.6.433.0725.447686460`.
- Chỉ nghiên cứu; chưa sửa mã ứng dụng hay phát hành SonMap mới. VERSION giữ 10.12.
- Dữ liệu thử: sao chép `C:\VietMapXM\Demo\ChayGCN\dc24\dc24.dgn` và `dc24.mdb` thành `data/vietmap-study-20261027/demo.dgn`, `demo.mdb`. Không chạy sửa lỗi/tạo topology trên DGN người dùng ban đầu đang mở (`dc171.dgn`).
- Bộ demo có cảnh báo thiếu reference khi mở. Kết quả dưới đây chỉ áp dụng bản demo và các lớp đã chọn, không dùng làm kết luận chất lượng dữ liệu địa chính thực tế.

## Kết quả quan sát và chạy thật

### 1. Tự động tìm và sửa lỗi

Đường dẫn menu: **BẢN ĐỒ → Tạo Topology → Tự Động Tìm Và Sửa Lỗi**.

Bảng có phương thức xử lý trùng đè, phá vỡ Arc/ComplexShape, báo đoạn ngắn, vùng nhỏ, đoạn dư, nối LineString, kiểm tra nút gần, sai số tiếp xúc, chọn lớp và thuộc tính cell báo lỗi. Có tab chạy đồng loạt nhiều file.

Giá trị quan sát trên bản vẽ ban đầu: lớp `10,23,32`, đoạn ngắn `0.001 m`, vùng nhỏ `0.3 m²`, khoảng cách nút gần `0.1 m`, sai số tiếp xúc `0.01 m`, cell báo lỗi lớp 60, màu 3, bán kính 0.01. Đây là cấu hình đang hiển thị, không phải khuyến nghị áp dụng cho mọi bản đồ.

Trên demo, lớp hiển thị là `10`. Bấm Thực hiện, ứng dụng báo **“Làm sạch bản vẽ thành công! Bản vẽ đã sẵn sàng cho việc tạo topology.”** Danh sách file ghi **“Có thể tạo topology luôn”**.

### 2. Tạo topology

Đường dẫn menu: **BẢN ĐỒ → Tạo Topology → Tạo Topology Thửa Đất**.

Lần đầu bị chặn do cấu trúc MDB cũ. Dùng **HỆ THỐNG → Cập Nhật Cấu Trúc Dữ Liệu Mới → Thêm file hiện thời**; danh sách xác nhận duy nhất MDB bản sao trong thư mục nghiên cứu. Bấm Cập nhật, ứng dụng báo cập nhật thành công cho 1 file.

Bảng topology sau cập nhật có:

- Lớp tạo vùng; số tờ bản đồ.
- Chế độ **Cập nhật từ CSDL cũ** và **Tạo mới, xoá CSDL cũ**.
- Các ô giữ/cập nhật thuộc tính cũ khi ranh thay đổi: diện tích, thông tin chủ sử dụng, số hiệu thửa, loại đất, địa chỉ/xứ đồng, gán tên chủ UBND xã.
- Cell tâm thửa: lớp 11, màu 3, tỷ lệ 1 trong lần quan sát.
- Báo lỗi tạo vùng: lớp 63, màu 59, bán kính 2 trong lần quan sát.
- Ô **Bỏ qua lỗi topology** đang được đánh dấu khi bảng mở.

Đã bỏ dấu **Bỏ qua lỗi topology**, giữ chế độ cập nhật từ CSDL cũ và chạy trên demo. VietMap báo bản vẽ vẫn còn lỗi topology và đề nghị xem lỗi. Chọn xem, công cụ **Tìm vị trí lỗi** hiển thị **1/4**, loại hiện tại **Lỗi đỉnh treo**; có nút tiến/lùi và phóng to/thu nhỏ.

**Chưa tạo topology thành công trong lần thử này.** Thông báo làm sạch thành công không chứng minh bộ tạo topology đã kiểm tra đạt. Chưa kiểm tra cả bốn lỗi nên không kết luận cả bốn đều cùng loại. Không bật bỏ qua lỗi để ép ghi dữ liệu.

### 3. Thông tin thửa đất

Đường dẫn menu: **BẢN ĐỒ → Quản Lý Dữ Liệu Bản Đồ**.

Đã mở **Quản Lý Dữ Liệu Thửa Đất**: demo có **362 thửa**, bảng hiển thị số hiệu, mã loại đất/mục đích sử dụng, diện tích, chủ sử dụng, tên vợ/chồng, địa chỉ thửa/chủ và các cột bổ sung. Có lệnh tìm kiếm, hiển thị thửa trên bản đồ, gán/xuất dữ liệu, tạo hồ sơ và sửa thông tin.

Đã mở **Sửa thông tin thửa**. Bảng có tab Thông tin thửa, Nhập đa MĐSD, BĐ Lâm Nghiệp; các trường số tờ, số thửa, số tạm, đất ở, diện tích, diện tích pháp lý, MĐSD, ĐTSD, địa chỉ, chủ sử dụng, vợ/chồng, giấy tờ và ghi chú. Có ô chọn riêng trường cần áp dụng, **Sử dụng Fence**, **Zoom đến tâm thửa khi pick bên trong**, nút Chọn/Lưu. Các ô thông tin lúc quan sát còn trống, trạng thái yêu cầu chọn tâm thửa.

**Chưa chọn và ghi thử thuộc tính một thửa VietMap.** Không coi việc mở bảng là bằng chứng đã đọc/ghi đúng bản ghi. Điều khiển cửa sổ này có các lần timeout; bước ghi và đọc lại chưa được xác minh.

## Bảng lệnh từ tài nguyên cài đặt

Đọc trực tiếp XML đi kèm phần mềm, không suy đoán tên lệnh:

| Lệnh key-in | Hàm đích trong XML |
| --- | --- |
| `VIETMAP DULIEU LamSachBanVe` | `VietMap.CleanUp.KeyinCommands.LamSachBanVe` |
| `VIETMAP DULIEU SuaLoiTaoVung` | `VietMap.CleanUp.KeyinCommands.SuaLoiTaoVung` |
| `VIETMAP DULIEU TAO_TOPOLOGY` | `BuildTopology.KeyinCommands.TaoVung` |
| `VIETMAP DULIEU ThongTinTopology` | `BuildTopology.KeyinCommands.ThongTinTopology` |
| `VIETMAP DULIEU SUANHANTHUA` | `BuildTopology.KeyinCommands.SuaNhanThua` |
| `VIETMAP DULIEU SUABANGNHAN` | `BuildTopology.KeyinCommands.SuaBangNhan` |
| `VIETMAP DULIEU TIMKIEMTHUADAT` | `BuildTopology.KeyinCommands.TimKiemThuaDat` |

Nguồn: `C:\VietMapXM\XMLCOMMANDS\VietMap.CleanUp.Commands.xml`, `VietMapXM.DLBD.Commands.xml`. Các thao tác chạy thật ở trên đi qua menu; chưa thử nhập trực tiếp từng chuỗi key-in.

## Những gì SonMap có thể học theo

Đây là đề xuất triển khai độc lập từ hành vi quan sát, không phải kết luận về thuật toán bên trong VietMap.

| Nội dung | SonMap 10.12 hiện tại | Hướng phát triển |
| --- | --- | --- |
| Làm sạch rồi kiểm tra khép vùng | `topology.py` đã xử lý trùng đoạn/đoạn 0, nối đầu mút có điều kiện, polygonize và phân loại lỗi | Giữ kiểm tra topology độc lập; thông báo tách rõ làm sạch xong và đủ điều kiện ghi |
| Duyệt lỗi trên bản vẽ | Có danh sách lỗi và dữ liệu vị trí | Thêm Trước/Sau, số thứ tự/tổng số, zoom và đánh dấu lỗi đang chọn |
| Chọn phạm vi/lớp | Có nhập nhiều lớp, chặn lớp ranh/tâm/lỗi trùng nhau | Hiện số phần tử mỗi lớp và phạm vi trước khi chạy |
| Kế thừa dữ liệu khi đổi ranh | 10.12 đã kế thừa số thửa cha và thuộc tính, ID thửa con riêng | Thêm chọn từng nhóm thuộc tính, bản xem trước trước/sau và giải thích bản ghi sẽ đổi |
| Thông tin từng thửa | `parcel_info.py` chọn điểm trong polygon theo hình học và ID; sửa số/tên/địa chỉ có kiểm tra MDB thay đổi và backup | Mở rộng loại đất/địa chỉ thửa/ghi chú có lựa chọn trường ghi, kiểm tra kiểu và đọc lại |
| Kiểm tra cấu trúc MDB | Có kiểm tra dữ liệu/cấu trúc phục vụ thao tác hiện có | Bổ sung màn hình báo cột thiếu và khả năng tương thích; chỉ nâng cấu trúc trên bản sao có rollback |

Không sao chép tùy chọn bỏ qua mọi lỗi thành mặc định của SonMap. Cần tiếp tục chặn lỗi chạm phạm vi đang cập nhật, giữ các thửa ngoài phạm vi, DGN/MDB gốc và dữ liệu riêng.

## Bằng chứng phân tích tĩnh và giới hạn

REA đọc `C:\VietMapXM\VietMap.CleanUp.dll`: SHA-256 `975cc3ff216fb60876b6ebcf9bb13e2a8b815cc24230ff92d7872fa0088dc718`, MVID `334f1e6c-d337-4b67-bf85-a50032a9fce7`, .NET Framework 4.0, CIL. Metadata assembly có phiên bản 1.0.0.0; đây không phải phiên bản sản phẩm hiển thị trên thanh công cụ.

- Identity evidence: `ev_8d2cee33264eb1d5f7b7bac818587f2c793936012f1ba11182503b8c9a074957`.
- Member evidence: `ev_1538450f11720029c9e5c50a863006e699b330d6efdba61576326c5a9dd26ddc`.
- Có type `VietMap.CleanUp.KeyinCommands`; nhiều tên type khác bị làm rối. Coverage giải mã member/CIL được công cụ ghi là **partial**.
- Chưa khôi phục thuật toán sửa lỗi, ghép vùng hay quy tắc kế thừa của VietMap. Không được suy ra thuật toán từ tên DLL hoặc chỉ từ các checkbox.

## Kiểm thử SonMap trong phiên này

Dùng Python của môi trường ứng dụng đã cài: `%LOCALAPPDATA%\SonMapPlus\App\.venv-topology\Scripts\python.exe`.

`-m unittest test_topology test_database_topology test_parcel_info test_release -q`: **52 tests, OK**, bao gồm kiểm tra cấu trúc gói; không phân phối hay ghi đè gói phát hành cũ.

Thử thêm `test_parcel_info_ui`: 54 tests tổng, 2 lỗi khởi tạo Tk do không tìm thấy Tcl sử dụng được. Đây là lỗi môi trường kiểm thử chưa xử lý trong phạm vi nghiên cứu, không đánh dấu kiểm thử giao diện đạt. Lần chạy ban đầu bằng Python312 nền thiếu Shapely; đã chuyển sang venv có sẵn, không cài thêm thư viện.

Các test Python không thay thế nghiệm thu COM/V8i/Jet. Windows runtime VietMap đã quan sát như trên; chưa có lần chạy ghi/đọc lại SonMap trên DGN/MDB mới trong phiên này.

SHA-256 bản sao trước thử: DGN `0893f97d60376ae1afdf6be52927d5f4da441b7f51b9cb77a2cef2bc2e06ff08`; MDB `e48b053919f73b63702c7aef96114249d7551be988a5729d216447385b9a7379`. Bản demo gốc vẫn giữ ở thư mục cài VietMap. Dữ liệu thử và cây UI lưu trong `data/`, không đưa lên GitHub.

Kiểm tra cuối phiên: hash hai file demo gốc vẫn khớp trước thử. DGN bản sao đã đổi thành `c11ab1f3b11bff31e2cbb7a67b032a94ce687e2e1dacac4f03b862b163889d76`. MDB bản sao đang bị VietMap khóa nên chưa lấy được hash cuối. Bảng sửa thửa demo vẫn có thể đang mở do lần đóng bị timeout; chưa bấm Lưu. Báo cáo là tệp mới tại workspace, chưa commit/push; không có release mới.
