# SonMap+ — Sửa lỗi, Tạo topology và Kết nối CSDL

## Chạy trên Windows

Cần Python 3.12 **64-bit** có Tcl/Tk và pip. Giải nén gói mã vào một thư mục
riêng, nhấp đúp **start_topology.cmd**. Script tự tìm Python qua PATH, Registry
và thư mục cài thông dụng; không bắt buộc có lệnh `py`. Lần đầu cần Internet để
cài Shapely. Không cần cài lại Python nếu bản 3.12 64-bit đang hoạt động.

Nếu báo lỗi, xem **data/topology-startup.log**. Nếu thiếu Python, dùng
[bộ cài chính thức 3.12.10 64-bit](https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe).
Có thể chỉ định đường dẫn Python bằng biến `SONMAP_PYTHON`.

Đọc/ghi DGN cần MicroStation V8i đang chạy. Đọc/ghi MDB cần Windows PowerShell
32-bit, Microsoft Jet OLEDB 4.0 và ADOX. Chương trình tự gọi PowerShell trong
SysWOW64; Python xử lý hình học vẫn dùng 64-bit. Tạo/đọc CSDL không đòi hỏi V8i
đang mở, nhưng làm việc với bản vẽ và xuất hồ sơ thì có.

## Bảng chính

Ba nút chính mở ba hộp thoại độc lập, bố cục theo nhóm tham số:

- **Sửa lỗi**: tùy chọn ranh trùng, phá Arc/Complex, LineString, báo đoạn ngắn,
  vùng nhỏ và nút gần; ngưỡng nối đầu hở; lớp, màu, bán kính cell báo lỗi.
- **Tạo topology**: lớp tạo vùng, số tờ, thuộc tính cell tâm và báo lỗi tạo vùng.
  Có nút Gán nhãn, Thông tin thửa và Báo lỗi.
- **Kết nối CSDL**: Đọc/kết nối MDB, Tạo MDB trống mới hoặc Tạo DGN + MDB có dữ
  liệu từ topology. Có thể mở lại dự án đã lưu ở đây.

Các nút xuất trích lục, GCN và Mẫu 03 cũ được thu gọn dưới **Xuất hồ sơ ▾**.
Danh sách thửa có nút mở riêng; không trải tất cả tham số ra bảng chính.

## Quy trình với DGN chưa có MDB

1. Mở đúng DGN và model 2D trong V8i, lưu bản vẽ trước khi xử lý. Chương trình
   dùng dữ liệu đã lưu trên đĩa, không lấy các sửa đổi chưa lưu hoặc Reference.
2. Bấm **Sửa lỗi**, chọn các lớp ranh đúng với bản vẽ. Lớp 10 là gợi ý ban đầu.
   Trong **Đơn vị / sai số cung**, đặt số mét trên một đơn vị DGN (DGN dùng mét:
   nhập 1). Các ngưỡng chiều dài nhập bằng mét, diện tích bằng m².
3. Bấm **Thực hiện**: phân tích và ghi ranh đã xử lý lên một bản sao mới. Đoạn
   trùng chính xác và đoạn dài 0 được loại bỏ; giao cắt/chồng đoạn được node.
   Nếu bật nối đầu hở, chỉ nối cặp đầu mút cô lập có duy nhất một đối tác trong
   ngưỡng. Không tự kéo đầu ranh tới cạnh hoặc nối qua các ngã ba mơ hồ.
4. **Báo lỗi** mở danh sách cảnh báo; **Ghi cell báo lỗi** tạo bản sao có vòng tròn
   `SMERR` trên lớp lỗi. Phần tử không đọc được có thể chỉ báo trong danh sách.
   Nếu còn đầu hở/đường thừa, sửa trên bản sao trong V8i, lưu và xử lý lại từ bản
   sao đó. Dữ liệu nguyên gốc được giữ lại.
5. Bấm **Tạo topology**, chọn lớp ranh và số tờ rồi **Thực hiện**. Khi ranh hợp lệ,
   chương trình tạo DGN mới với vùng và cell tâm `SMPARC`. Điểm tâm nằm bên trong
   thửa, kể cả thửa lõm. Tâm chưa có số thửa ghi `ID:<mã>` tạm, không tự đánh số
   thửa chính thức.
6. Bấm **Gán nhãn** để chọn lớp chữ cho số thửa, loại đất, tên chủ, xứ đồng. Có
   thể đặt trước khi tạo topology hoặc gán lại từ bản chụp dữ liệu đã lưu sau đó.
   Mỗi nhãn cần có điểm chèn nằm hẳn trong một vùng. Nhãn trên ranh hoặc nhiều
   nhãn cùng trường được báo để kiểm tra. Không suy đoán cách tách nhãn nhiều
   dòng/ghép số thửa-diện tích. Có thể để trống lớp và nhập tay.
7. Mở **Thông tin thửa**, chọn một dòng; đánh dấu các trường muốn thay đổi, sửa
   rồi bấm **Lưu**. Các trường bỏ chọn được giữ nguyên. Diện tích đo được tính
   từ ranh, không dùng để thay diện tích pháp lý. Gán lại nhãn giữ các trường
   đã sửa tay. Việc lưu này cập nhật dự án, chưa ghi vào MDB cũ.
8. Mở **Kết nối CSDL → Tạo DGN + MDB từ topology**. Cần hết lỗi ranh chặn, số tờ
   và số thửa nguyên dương, không trùng số thửa. Mỗi lần xuất tạo thư mục
   `result_<mã riêng>` có DGN/MDB cùng tên, không ghi đè kết quả cũ.
9. Chỉ kết quả xuất DGN + MDB có **receipt.json** với `status: verified` mới được
   đọc lại để kiểm tra mọi trường MDB, hình học, từng vùng và tâm DGN. Nếu lỗi
   giữa chừng, không coi các tệp dở dang là dữ liệu đã xác minh.
10. Mở DGN kết quả trong V8i để SonMap tự nhận MDB cùng tên cạnh bản vẽ.

Mỗi lần phân tích lưu `project.json`, snapshot và DGN gốc sao chép vào thư mục
`<tên>_SonMap_<mã riêng>`. Dùng **Kết nối CSDL → Mở dự án** để tiếp tục làm việc.
Đổi DGN sẽ bỏ dữ liệu dự án cũ khỏi phiên làm việc để tránh gán nhầm bản đồ.

## Tạo hoặc đọc MDB trực tiếp

- **Tạo MDB mới** tạo CSDL trống có bảng `ThuaDat` theo cấu trúc SonMap. Chọn tên
  chưa tồn tại; chương trình từ chối ghi đè MDB cũ. CSDL trống chưa có thửa hoặc
  hình học; cần tạo topology/gán thuộc tính để xuất MDB có dữ liệu.
- **Đọc / kết nối MDB** chọn tệp có cấu trúc bảng phù hợp với `read_mdb.ps1`.
  Chương trình đọc trên bản sao tạm để tránh đặt sidecar Jet bên cạnh nguồn.
  Sau khi đọc thành công sẽ kết nối vào bảng chính; mở Danh sách thửa để xem.
- Có thể kết nối MDB khác tên với DGN. Liên kết này chỉ áp dụng trong phiên làm
  việc và cho bản vẽ tương ứng; chuyển sang bản đồ khác sẽ ngắt liên kết cũ.
- Đây không phải bản sao đầy đủ cấu trúc MDB riêng của VietMap. Các trường không
  có trên bản vẽ không thể tự sinh thành dữ liệu thật.

## Lỗi kết nối V8i

Lỗi **Value does not fall within expected range** trong ảnh là ngoại lệ của cầu
nối COM, chưa đủ dữ liệu để quy về hỏng bản đồ. Bản cập nhật không dùng tên model
hay số lớp làm chỉ số danh sách: tìm model theo tên, lớp theo số thực tế.
Khi lỗi, thông báo mới ghi bước đang chạy và dòng mã; nội dung đầy đủ ở
**data/dgn-topology-last.log**. Gửi file này nếu vẫn không đọc được DGN.

## Phạm vi và giới hạn kiểm chứng

- Phần hình học và tương tác giao diện có kiểm thử trên cloud. Kết nối Windows,
  Jet và V8i vẫn cần xác minh trên máy thực; thử giao diện dùng mô phỏng I/O.
- Xử lý model 2D, Line, LineString, Shape, ComplexString/ComplexShape và chữ
  Text/TextNode. Complex được phân rã theo lớp cha khi bật tùy chọn. Arc/Ellipse
  được chia theo sai số dây cung nếu API V8i đọc được; trường hợp không đọc được
  ghi lỗi chặn, không bỏ ranh để tạo MDB.
- Ranh trong Cell cần Drop trên bản sao trước. Không tự suy diễn B-spline, 3D
  hoặc ranh trong Reference. Một lần phân tích giới hạn 30.000 nút.
- Đoạn ngắn/vùng nhỏ là cảnh báo, không tự xoá thửa. Đầu hở, đường thừa, vòng lỗi,
  thửa có lỗ hoặc phần tử ranh không hỗ trợ chặn xuất MDB.
- Ranh kết quả dùng lớp ranh đầu tiên đã chọn. Màu/nét riêng của từng đường nguồn
  không được bảo toàn khi dựng lại ranh. Cell lỗi và tâm ở các lớp riêng.
- Chưa hỗ trợ hàng loạt, cập nhật ranh từ MDB cũ, bỏ qua lỗi để xuất MDB, CCCD,
  thông tin vợ chồng, đất lâm nghiệp hoặc toàn bộ quy trình pháp lý trong VietMap.
- Xuất MDB hiện yêu cầu DGN dùng mét để tương thích bộ xuất SonMap hiện có.
  Bộ cài đầy đủ và xuất hồ sơ cũ vẫn cần các tài nguyên Windows/VBA/mẫu riêng.

## Kiểm thử

```sh
python -m pip install -r requirements-topology.txt
python -m unittest test_upgrade.UpgradeTests test_topology test_topology_ui test_release -v
```

Kiểm thử giao diện cần màn hình Tk; khi chạy cloud không có DISPLAY sẽ được ghi
rõ là skipped. Kiểm thử cũ vẫn chạy độc lập không cần Shapely:

```sh
python -m unittest test_upgrade.UpgradeTests -v
```

## Gói cập nhật V10.4

Giải nén toàn bộ SonMapPlus_V10_4_Update.zip rồi chạy Cai_dat.cmd. Trình cài
không cần quyền quản trị; dùng Python 3.12 64-bit đã cài, tạo môi trường riêng và
lối tắt Desktop. Cần Internet lần đầu để cài thư viện. Đóng bản SonMap đã cài
trước khi cập nhật. Bản cũ trong thư mục Downloads vẫn còn nguyên; sau cài hãy
mở bằng lối tắt SonMap+ mới và kiểm tra tiêu đề V10.4.

Vị trí cài: %LOCALAPPDATA%\SonMapPlus\App. Nhật ký ở SonMapPlus\Logs; sao lưu
mã trước khi cập nhật ở SonMapPlus\Backups. Không ghi đè data, assets, runtime,
settings.json hoặc DGN/MDB cũ. Nếu bản ThanhTanApp cũ có assets/VBA, trình cài
sao chép chúng sang khi đích chưa có; không tải/cung cấp các tài nguyên riêng.

Gói là ZIP có trình cài Cai_dat.cmd/Cai_dat.ps1, không phải EXE độc lập. Đã kiểm
tra cấu trúc gói, checksum và cú pháp; cài đặt Windows/V8i vẫn cần chạy thực tế.

## Phục hồi và phát triển trên máy khác

Mỗi nâng cấp tăng phiên bản; các gói mang số cũ không bị ghi đè. Khi đã cài và
cập nhật ít nhất một lần, lối tắt **SonMap+ - Khoi phuc** cho chọn bản cũ trong
Backups. Khôi phục chỉ thay file chương trình, giữ data/settings/assets và
DGN/MDB. Bản đang dùng cũng được sao lưu trước khi khôi phục để có thể quay lại.
Lần đầu cài vào thư mục mới chưa có bản trước đó để khôi phục tại thư mục này.

Các mốc mã cũ/mới được giữ trên GitHub bằng tag phiên bản. Đăng nhập trên máy
khác, mở repository và chọn đúng nhánh/tag để tiếp tục; không tự tăng số phiên
bản từ một checkout cũ khi GitHub đã có bản mới hơn.

Để kiểm tra laptop: mở V8i và DGN rồi chạy Kiem_tra_V8i.cmd trong gói cài.
Công cụ đọc các thiết lập CAD cho phép trong C:\VietMapXM và cấu hình User Bentley,
không đọc nội dung bản đồ hoặc sửa cấu hình/DLL/giấy phép. Báo cáo ở
`%LOCALAPPDATA%\SonMapPlus\App\data\vietmapxm-diagnostic.json`.

## V10.5 — máy có Python 3.15

Python 3.15 không đáp ứng yêu cầu 3.12 của môi trường SonMap hiện tại. Khi
chạy Cai_dat.cmd V10.5, trình cài dùng lại bản 3.12 phù hợp nếu có; nếu chưa có,
tải bộ cài 3.12.10 chính thức qua HTTPS và chỉ chạy khi chữ ký hợp lệ của Python
Software Foundation. Python này được cài riêng trong SonMapPlus/Python312,
không gỡ 3.15 hay đổi PATH. Cần Internet và chứng thư hệ thống hoạt động. Nếu
đã có đăng ký Python 3.12 nhưng thiếu thành phần, chương trình báo cần Modify/Repair
bản đó thay vì tự ghi đè. Probe có giới hạn 15 giây để tránh treo vô hạn.
