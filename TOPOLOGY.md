# SonMap+ V10.20 — làm trực tiếp trên laptop

Phiên bản lấy từ [VERSION](VERSION), lịch sử và giới hạn nghiệm thu từng bản
ở [CHANGELOG.md](CHANGELOG.md). Quy ước phát triển nằm trong [AGENTS.md](AGENTS.md).

## Cài hoặc nâng cấp ứng dụng

Giải nén SonMapPlus_V10_20_Update.zip, đóng SonMap cũ và chạy Cai_dat.cmd.
Lối tắt SonMap+ dùng chương trình ở `%LOCALAPPDATA%\SonMapPlus\App`.
Trình cài giữ các phiên bản trước, sao lưu mã cũ và có công cụ Khôi phục.
Nếu thiếu CPython 3.12 64-bit phù hợp, chuẩn bị bản riêng cho SonMap từ bộ cài
chính thức có chữ ký hợp lệ. Python 3.15 và PATH được giữ nguyên.

## Làm trên DGN/MDB đang mở

Mặc định **Tự ẩn lớp không tham gia trước khi chạy** được bật ở cả Sửa lỗi và
Tạo topology. Thao tác này chỉ làm gọn hiển thị, không xóa phần tử. Bấm
**Hiện lại lớp** để khôi phục trạng thái trước lần ẩn đầu tiên; có thể chạy
nhiều lần mà vẫn khôi phục được. Có thể bỏ chọn tự ẩn nếu cần giữ cách xem hiện tại.
**Sửa ranh** tạo giao điểm thật, giữ nét, có dữ liệu phục hồi tạm. Đoạn dư/hở được giữ để
báo lỗi và sửa thủ công. Mở **Báo lỗi** để tìm từng lỗi trên DGN, ghi dấu và kiểm
tra lại sau khi sửa. Chỉ tạo topology khi đã kiểm tra ranh hoặc phạm vi cập nhật hợp lệ.

Bấm **Xóa dấu lỗi** để xóa các vòng tròn SMERR của SonMap trong model hiện tại,
kể cả sau khi đã chỉnh sửa ranh thủ công. Nút có ở Sửa lỗi, Tạo topology và
danh sách lỗi; không xóa toàn bộ Level báo lỗi hoặc vòng tròn do người dùng vẽ.
Xóa dấu không xác nhận đã sửa hết lỗi. Chạy lại Sửa lỗi/Tạo topology hoặc
**Kiểm tra lại sau sửa tay** để có danh sách lỗi mới.

Trong **Báo lỗi**, chọn một dòng rồi bấm **Tìm trên DGN**; dùng **Trước/Sau**
để chuyển lỗi, bộ đếm cho biết vị trí hiện tại. **Phóng to + / Thu nhỏ −**
giữ tâm tại lỗi đang chọn. Với đầu ranh hở, tâm là chính đầu hở, không phải
giữa đoạn dài. **Xóa vòng đang chọn** chỉ dọn SMERR tại vị trí đó; **Xóa dấu lỗi**
dọn toàn bộ SMERR trong model. Danh sách vẫn giữ để tiếp tục tìm vị trí sau
khi xóa vòng; cần kiểm tra lại ranh trước khi ghi kết quả phân tích mới.

Báo lỗi mặc định mở bảng **Tìm vị trí lỗi** nhỏ ở góc, chỉ có loại lỗi, bộ đếm
và sáu nút thu/phóng, trước/sau, xóa một/xóa tất cả. Chuột phải chọn
**Danh sách chi tiết** để xem thêm khi cần. Vòng tròn tạm chỉ vị trí được chọn,
không thêm phần tử vào DGN; đổi bản vẽ/model sẽ dọn dấu tạm. Giữ vòng SMERR
được ghi bằng Ghi dấu lỗi. Xóa dấu không có nghĩa là đã sửa ranh.

Trong **Sửa lỗi**, ô **Bỏ qua sai lệch ≤** mặc định `0.001` m (1 mm).
Không báo nút gần/đoạn ngắn và đầu hở trong ngưỡng này; nhập 0 để kiểm tra nghiêm
ngặt. Chỉ bỏ cảnh báo, không đổi tọa độ hoặc nối ranh. Đầu hở thật ngoài ngưỡng,
cạnh thừa, vòng không hợp lệ và thửa có lỗ vẫn báo. Ranh dài chưa khép vùng
dù tiếp xúc trong sai số vẫn cần nối thực sự trước khi xuất MDB.

V10.19 chuyển bước ẩn lớp/lưu và ghi sửa ranh trực tiếp vào V8i, giữ tệp phục
hồi tạm và kiểm tra tọa độ sau ghi. Thông báo hoàn tất Sửa lỗi hiện tổng thời
gian gồm phân tích và ghi; tránh nhầm tốc độ đọc ranh với toàn bộ công việc.

V10.18 đọc ranh và zoom qua cầu nối SonMap bên trong V8i. Lần đầu tự biên
dịch từ mã nguồn bằng các thư viện Bentley đã cài trên máy; không đóng gói
DLL Bentley. Chỉ bổ sung đường tìm tiện ích trong phiên V8i hiện tại, không
sửa cấu hình workspace trên đĩa. Đóng các hộp thoại V8i đang chặn lệnh nếu
chương trình báo chưa nhận được kết quả. Khởi động/nạp lần đầu có chi phí
riêng; số đo bước đọc ranh không phải thời gian ghi DGN/MDB hoàn chỉnh.

**Thông tin thửa trên DGN** mở bảng có nút con trỏ **↖** và nút **Chọn**. Nhấp một nút,
sau đó nhấp bên trong thửa; chuột phải hủy. Bảng nạp thuộc tính theo hình học và ID,
không dùng số thửa làm khóa. Sửa giá trị sẽ đánh dấu trường cần ghi; có thể bỏ dấu
để giữ giá trị cũ. Để trống trường đã chọn để xóa nội dung nếu kiểu dữ liệu cho phép.
Diện tích hiển thị đúng một chữ số sau dấu phẩy; dữ liệu lưu giữ độ chính xác gốc.
Bảng chỉ hiển thị các thuộc tính địa chính cần dùng theo mẫu, không hiện cột kỹ thuật.
Thuộc tính chưa có trong MDB để trống và vô hiệu hóa. Nút pick dùng lại để chuyển sang thửa khác; các chỉnh sửa
chưa lưu được nhắc trước khi bỏ. Chương trình giữ nguyên cấu trúc cột MDB.

1. Mở đúng DGN trong MicroStation V8i. SonMap tự nhận MDB cùng tên; hoặc chọn
   Kết nối CSDL → Đọc/kết nối MDB để chọn CSDL khác.
2. Trong Sửa lỗi/Tạo topology, nhập lớp ranh, ví dụ `10,23,32`. Chỉ chọn lớp ranh.
3. Mặc định **ghi DGN hiện tại** được bật. Chương trình lưu nét đang mở rồi
   phân tích lại, dùng tệp tạm để phục hồi giao dịch khi ghi lỗi. Không kẻ thêm/sửa bản vẽ trong khi
   tác vụ đang chạy. Bỏ chọn nếu muốn xuất bản riêng như các phiên bản trước.
4. Sửa lỗi chuẩn hóa ranh và báo đoạn ngắn, vùng nhỏ, đầu hở/cạnh thừa. Nó không
   tự tạo thêm bản ghi thửa; dùng Tạo topology sau khi ranh hợp lệ.
5. Tạo topology dựng lại vùng, tâm thửa và cập nhật MDB đang kết nối. Kết quả
   được ghi vào **tên DGN/MDB hiện tại**, không giữ thêm backup sau thành công.
   Giao diện hiển thị số phần tử theo lớp, số vùng, số thửa MDB trước/sau.
6. Một đường phân chia khép đúng hai đầu vào ranh của một thửa phải tạo hai
   vùng. Nếu tách một thửa từ MDB có 12 thửa, kết quả dự kiến là 13 bản ghi.
   Thửa không thay đổi giữ ID/thuộc tính; phần ngoài phạm vi được giữ nguyên.
7. Thửa con mới có ID riêng; tạm kế thừa số thửa và thuộc tính của thửa cha.
   Số được nhập chủ động hoặc gán từ nhãn được ưu tiên. Thửa mới không có nguồn
   số hiển thị **Chờ số**; không tự bịa số thửa pháp lý. Mở
   Thông tin thửa, nhập số rồi lưu; dùng Cập nhật MDB hiện tại trong Kết nối CSDL
   để ghi các thuộc tính sửa tay. Xuất hồ sơ bị chặn khi thiếu số thửa.
8. Không có MDB kết nối thì chỉ cập nhật DGN; tạo/kết nối CSDL trước nếu cần
   danh sách thửa được cập nhật. Đổi DGN sẽ bỏ liên kết CSDL của bản đồ cũ.

Cập nhật MDB áp dụng delta trên bản sao đầy đủ, giữ các bảng/cột khác và kiểm
tra dữ liệu đọc lại trước khi thay tệp. Tệp chờ thay được tạo cạnh MDB đích để
hỗ trợ dữ liệu khác ổ đĩa với thư mục tạm Windows. Khóa MDB được kiểm tra trước
khi ghi DGN; nếu không đổi bản ghi thì không thay MDB. MDB bị khóa hoặc có ràng buộc chèn/xóa
không hỗ trợ sẽ báo lỗi; không phá ràng buộc hoặc xóa bảng khác để ép cập nhật.
Nếu ghi thất bại, chương trình thử phục hồi; chỉ giữ và nêu vị trí tệp cứu hộ
khi chưa tự phục hồi được. Sau thành công, thông tin người dùng đã xác nhận
không bị tự hoàn nguyên. Các
phần mềm khác không nên đồng thời sửa MDB trong lúc SonMap đang cập nhật.

## Giới hạn đã biết

Model 2D; Line/LineString/Shape, Complex được phân rã khi bật tùy chọn. Arc được
chia theo sai số dây cung nếu API V8i hỗ trợ. Không tự suy diễn ranh trong
Reference, Cell hoặc B-spline. Ranh hở, đường thừa, vòng lỗi và thửa có lỗ chặn
cập nhật topology/MDB. Không biến cảnh báo polygon thành cam kết sạch bản đồ.

Các ngưỡng chiều dài tính bằng mét, diện tích bằng m². DGN dùng mét nhập hệ số 1;
ghi MDB hiện yêu cầu hệ số này để tương thích xuất hồ sơ. Ranh dựng lại giữ
lớp, màu, độ đậm và kiểu nét theo nguồn. Không làm tròn tọa độ/MDB theo giá trị hiển thị.

Phần xuất hồ sơ cũ vẫn cần mẫu/VBA riêng. Không sửa DLL hoặc giấy phép VietMap.

## Phát triển tại laptop và gửi mã lên GitHub

Dùng SonMapPlus_V10_7_Laptop_Workspace.zip:

1. Cần Git for Windows; nếu thiếu, có thể cài bằng
   `winget install --id Git.Git -e --source winget`.
2. Giải nén gói, chạy Bat_dau_lam_viec.cmd để tạo `%USERPROFILE%\SonMap-Dev`
   từ lịch sử Git đóng gói. Workspace cũ không bị ghi đè.
3. Lam_viec_laptop.cmd chạy ứng dụng từ mã tại laptop. Đóng ứng dụng bản cũ trước.
4. Để trợ lý có terminal/COM ngay trên laptop, mở Mo_Codex_laptop.cmd trong
   Visual Studio Code, cài extension OpenAI Codex được đề xuất (`openai.chatgpt`),
   đăng nhập tại máy và bắt đầu phiên local. Yêu cầu: “Đọc CONTINUE.md và AGENTS.md,
   kiểm tra SonMap với MicroStation V8i đang mở, tham khảo C:\VietMapXM”.
   Phiên cloud hiện tại không tự biến thành phiên điều khiển laptop.
5. Làm xong chạy Gui_len_GitHub.cmd, đăng nhập GitHub qua trình quản lý thông tin
   đăng nhập của Git. Script chỉ gửi mã, tăng phiên bản khi có thay đổi và giữ
   lịch sử; không gửi DGN/MDB/runtime/assets/khóa. Snapshot mã chưa qua kiểm chứng
   Windows không được coi là bộ cài đã kiểm thử.
6. Nếu GitHub có nhánh khác phát triển đồng thời, mã laptop được gửi vào nhánh
   laptop/snapshot-<SHA> để không ghi đè. Mang link nhánh được in về cloud để làm
   tiếp. Lay_ban_moi_tu_GitHub.cmd lấy bản mới khi workspace sạch.

Không gửi token/mật khẩu vào chat. Dữ liệu bản đồ giữ trên laptop; chỉ chia sẻ
mẫu đã ẩn thông tin cá nhân khi cần kiểm tra ngoài máy.

## Kiểm chứng và chẩn đoán

Kiểm thử Python/Tk kiểm tra logic và luồng giao diện, trong đó có I/O mô phỏng.
Kết quả Windows/V8i/Jet thật trên bản sao được ghi riêng tại
[V10_17_VALIDATION.md](V10_17_VALIDATION.md). Các mẫu thử này không chứng minh
mọi bản đồ hoặc mọi lỗi topology đã được xử lý; kiểm tra bản sao dữ liệu trước khi dùng chính thức.

Kiem_tra_V8i.cmd đọc cấu hình CAD cho phép từ C:\VietMapXM và trạng thái COM.
Kiem_tra_quet_DGN.cmd thử quét bản đang mở và bản sao chỉ đọc, ghi data/v8i-scan-*.json.
Các lỗi thao tác đầy đủ ở data/dgn-topology-last.log. Không coi kết quả quét đạt
là bằng chứng cập nhật MDB hoặc xuất hồ sơ đã đúng.

```sh
python -m pip install -r requirements-topology.txt
python -m unittest test_upgrade.UpgradeTests test_topology test_release test_python_probe test_database_topology -v
```

Thêm test_topology_ui nếu có màn hình Tk. Tạo gói cài bằng
`python installer/package_update.py --output <thư-mục-mới>`, gói workspace bằng
`python -m installer.package_workspace --output <thư-mục-mới>` sau khi commit sạch.
