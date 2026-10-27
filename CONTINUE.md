# Tiếp tục phát triển SonMap+ trên máy khác

## V10.12

Theo yêu cầu người dùng, tách 1 thành nhiều thửa phải tạm giữ cùng số thửa
và thông tin cũ. ID MDB luôn riêng; diện tích/hình học tính theo vùng mới.
`reconcile` cho phép số tờ/thửa trùng tạm khi ghi MDB, nhưng vẫn chặn ID trùng.
Khi chèn thửa con, `update_mdb_topology.ps1` sao chép các cột thuộc tính của
thửa cha trước khi xóa cha; không làm mất cột ngoài danh sách SonMap biết.
`parcel_info_ui.py` có ô Số thửa; ghi số/tên/địa chỉ bằng ID duy nhất. Chọn
thửa trùng số bằng điểm/hình học. Xuất hồ sơ vẫn kiểm tra số chính thức.
Giữ bản V10.11; nâng cấp kế tiếp là V10.13 nếu chưa có bản cao hơn.
71 kiểm thử Python đạt; kiểm thử Jet thật trên bản sao xác minh kế thừa số
và các cột ngoài schema SonMap, đổi riêng số/tên con và bảo toàn thửa còn lại.
Các thửa con từ lần tách trước nếu còn trống số được điền lại số cha từ bản
sao lưu đã xác minh, có kiểm tra hình học và giữ nguyên thông tin đã sửa.

## V10.11

`parcel_info.py`, `parcel_info_ui.py`, `pick_dgn_point.ps1` và
`update_parcel_owner.ps1` cung cấp nút chọn điểm trong thửa DGN và bảng sửa
tên/địa chỉ chủ ghi trực tiếp MDB. Bắt điểm qua GetInput có đủ bốn tham số,
đọc Point3d bằng interop; chuột phải hủy. Không đoán thửa bằng số nhãn.
Ghi theo ID, kiểm tra SHA nguồn, sao lưu đầy đủ trước transaction và đọc lại.
Không ghi tọa độ, số thửa/diện tích từ bảng sửa chủ. Không tự điền thông tin
chủ giả vào dữ liệu gốc khi kiểm thử: dùng MDB bản sao để thử thay đổi nội dung.
Phiên bản kế tiếp là V10.12 nếu chưa có bản cao hơn trên GitHub/laptop.
Đã kiểm tra chọn điểm thật trong V8i và hiện đúng thông tin thửa. Ghi tên/địa
chỉ Unicode, dấu nháy trên MDB bản sao bằng Jet đạt; kiểm tra backup, hình học,
bản ghi khác và chặn SHA cũ đạt. 66 kiểm thử Python cùng kiểm thử PowerShell
model/scan/interop đạt. Nội dung chủ của MDB gốc không bị thay bằng dữ liệu thử.

## V10.10

Cột Diện tích trên danh sách chính dùng `app.format_area`: một chữ số thập
phân với dấu phẩy, chỉ định dạng hiển thị; không làm tròn giá trị MDB/dữ liệu
xuất. Áp dụng cả đọc/lọc/sửa dòng. Giữ bản V10.9; nâng cấp kế tiếp là V10.11
nếu chưa có bản cao hơn trên GitHub/laptop.

## Trạng thái mới nhất: V10.9 trên Windows laptop

V10.8 đã sửa COM record Point3d/Matrix3d/ID bằng thư viện interop của V8i
đã cài, không đóng gói DLL Bentley. V10.9 bổ sung `scope_splits` trong
database_topology.py: khi bản đồ có lỗi ở xa, chỉ cập nhật các vùng tách kín
phủ đủ thửa MDB cũ. Lỗi chạm phạm vi, ranh chưa hỗ trợ, hoặc ranh đã được nối
sẽ chặn chế độ này. Giữ nguyên mọi đường ranh DGN và bản ghi ngoài phạm vi.
Thông báo kết quả vẫn nêu số lỗi ngoài phạm vi chưa xử lý.

Đã kiểm thử thực V8i/Jet trên bản sao, sau đó áp dụng lên DGN/MDB hiện tại:
đọc lại các vùng/tâm, so sánh toàn bộ đường ranh, xác minh bản ghi ngoài phạm
vi không đổi và có sao lưu trước ghi. Báo cáo dữ liệu thực chỉ nằm
trong data/ bị Git bỏ qua. Không đưa các báo cáo/snapshot/DGN/MDB lên GitHub.
Kết quả Python hiện có 60 kiểm thử đạt, cộng kiểm thử PowerShell model/scan
và `test_dgn_interop.ps1` trên V8i thật. Cloud không thay thế các kiểm thử này.

Khi gọi OpenDesignFile từ COM, truyền MsdV7Action.Workmode (=3) rõ ràng để
giữ định dạng V7 và mở chỉnh sửa. Bỏ tham số này sẽ hiện hộp thoại hỏi nâng cấp
hoặc mở chỉ đọc. Không tự chuyển dữ liệu gốc sang V8. Ghi file V7 qua model
nền không được hỗ trợ: dùng bản vẽ đang hoạt động, có backup/rollback.

Nhánh vẫn là codex/sonmap-topology-ui. Giữ các tag/gói cũ; bản tiếp theo sau
V10.9 là V10.10 nếu GitHub/bản cài chưa có bản cao hơn. Các ghi chú V10.7 trở
xuống bên dưới là lịch sử, bao gồm trạng thái chưa kiểm chứng ở các bản cũ.

## Mã và điểm tiếp tục

Giao diện chính đã có Sửa lỗi, Tạo topology, Kết nối CSDL; các công cụ xuất hồ sơ
cũ nằm dưới nút Xuất hồ sơ. Mã xử lý hình học: topology.py; giao diện:
topology_ui.py; điều phối Windows: topology_workflow.py; cầu nối V8i/Jet:
dgn_topology.ps1. Xem TOPOLOGY.md để chạy trên Windows.

Lỗi thực tế gần nhất từ máy người dùng: `select-model: Default / Model not found
in this DGN: Default`. Bản sửa mới dùng vai trò DefaultModelReference của file
nguồn khi đọc bản sao, thay vì yêu cầu tên hiển thị phải trùng. Vai trò này được
lưu trong snapshot và project, dùng lại lúc ghi/kiểm tra DGN. File dgn_models.ps1
chứa phần tìm model; test_dgn_models.ps1 dùng fake objects, không cần V8i.

**Chưa xác minh bản sửa model trên Windows/V8i thật.** Không khẳng định DGN của
người dùng đã đọc hoặc MDB đã tạo thành công. Bước tiếp theo: chạy lại Sửa lỗi
hoặc Tạo topology từ DGN nguồn trên máy có V8i. Nếu lỗi, lấy
`data/dgn-topology-last.log`, không chỉ dòng thông báo đầu tiên.

## Cloud/Linux

Cloud hỗ trợ phát triển và kiểm thử Python; không chạy được COM/Jet/V8i thực tế.
Không cần dữ liệu địa chính riêng để chạy các kiểm thử tổng hợp.

```sh
cd /workspace/SonMap-
python3 -m venv /workspace/sonmap-cloud-venv
/workspace/sonmap-cloud-venv/bin/python -m pip install -r requirements-topology.txt
/workspace/sonmap-cloud-venv/bin/python -m unittest test_upgrade.UpgradeTests test_topology -v
```

Nếu có màn hình Tk, thêm test_topology_ui. Trong cloud không có DISPLAY, các kiểm
thử Tk được ghi rõ là skipped. Trên Windows có PowerShell, có thể chạy thêm:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File test_dgn_models.ps1
```

Mỗi cloud task đã được cô lập. Dùng checkout hiện có; không tạo worktree trừ khi
người dùng yêu cầu. Không đưa DGN/MDB thật, thông tin cá nhân, khóa hoặc runtime
bên thứ ba lên Git. Không chạy `python test_upgrade.py` trên cloud vì phần main
của file đó yêu cầu data/source.json riêng.

## Quy tắc nâng cấp

Người dùng đã xác nhận nhánh codex/sonmap-topology-ui là đúng bản giao diện cần
đóng gói. Phiên bản hiện tại là V10.7; lần nâng cấp kế tiếp tăng lên V10.8 nếu
chưa có bản cao hơn trên GitHub. Đọc AGENTS.md, VERSION và CHANGELOG.md trước khi
phát hành. Không dùng dev-v1/v2 thay số phiên bản app.

Gói cập nhật laptop: `python installer/package_update.py --output <thu-mục-mới>`.
Giải nén và chạy Cai_dat.cmd; cài theo người dùng, không cần quyền quản trị,
tạo lối tắt Desktop, sao lưu mã cũ và giữ dữ liệu riêng. Bộ cài không kèm Python,
MicroStation hoặc tài nguyên xuất hồ sơ riêng. Kiểm thử cloud không thay thế
kiểm chứng cài đặt và COM/V8i/Jet trên Windows thật.

Người dùng cho phép thao tác trên MicroStation ở laptop và tham khảo C:\VietMapXM,
nhưng phiên cloud không có công cụ điều khiển laptop. Không được tuyên bố đã
thao tác Windows. Kèm Kiem_tra_V8i.cmd/check_connection.ps1 để người dùng chạy
tại máy, lấy báo cáo data/vietmapxm-diagnostic.json; chỉ đọc các cấu hình CAD.

V10.5 sửa trường hợp laptop chỉ có Python 3.15: bản này không tương thích yêu
cầu 3.12 của thư viện đã ghim. python_probe.py báo rõ phiên bản/bit/thành phần;
python_setup.ps1 có timeout và chuẩn bị Python 3.12 riêng nếu được trình cài gọi.
Chỉ thực thi bộ cài có chữ ký hợp lệ của Python Software Foundation; không tắt
TLS/chữ ký. Không gỡ bản 3.15 hay đổi PATH. Nếu đã có 3.12 hỏng/thiếu thành phần,
báo sửa bản đó thay vì tự ghi đè. Chưa xác minh trên Windows thật.

V10.6 xử lý lỗi người dùng gửi: scan-model / Index was outside the bounds of the
array khi lớp 10,23,32. Lớp nhập đúng. dgn_scan.ps1 tạo ElementScanCriteria trong
V8i, truyền tham số Scan rõ ràng cho COM; giữ tham chiếu tiêu chí tới hết lượt
quét. Các bước tạo/bắt đầu/MoveNext/Current được báo riêng. Chưa được chạy trên
V8i thật; nếu vẫn lỗi phải đọc dgn-topology-last.log, không coi bản đồ rỗng.

## V10.7: làm trực tiếp và đồng bộ mã

Người dùng xác nhận ranh mới đã dính nhưng danh sách MDB không tăng; bản cũ chỉ
xuất bản sao, không cập nhật MDB. Yêu cầu mới là sửa ngay DGN/MDB đang dùng, có
sao lưu. apply_current và database_topology.reconcile tạo delta trên bản sao
MDB, giữ các bảng/cột không liên quan, đọc lại kiểm tra rồi cập nhật. Tách thửa
có ID mới, chờ số hiệu chính thức nếu nhãn không có; không tự bịa số pháp lý.
Nếu MDB có ràng buộc/schema không hỗ trợ chèn/xóa, dừng và giữ sao lưu. Chưa
kiểm chứng COM/Jet thực; phải thử trên laptop trước khi khẳng định thành công.

Gói Laptop_Workspace được tạo bằng installer/package_workspace.py từ Git đã
commit sạch. Bat_dau_lam_viec.cmd tạo %USERPROFILE%/SonMap-Dev từ Git bundle,
không ghi đè workspace cũ. Lam_viec_laptop.cmd chạy ứng dụng tại máy. Để một
trợ lý thực sự dùng terminal/COM trên laptop, mở Mo_Codex_laptop.cmd trong
VS Code có extension OpenAI Codex (openai.chatgpt), đăng nhập tại laptop và
bắt đầu phiên local; cloud chat này không tự truy cập laptop. Đọc file này và
AGENTS.md trước, dùng SysWOW64 PowerShell cho COM V8i/Jet, tham khảo C:\VietMapXM
chỉ theo phạm vi người dùng cho phép, không sửa DLL/giấy phép. Có Kiem_tra_quet_DGN.cmd
và các báo cáo ở data để kiểm chứng thật.

Khi xong, Gui_len_GitHub.cmd chỉ gửi mã nguồn, tăng VERSION khi có thay đổi;
không tải DGN/MDB/assets/runtime/keys lên GitHub. Đăng nhập qua Git credential
manager trên laptop, không gửi token vào chat. Khi nhánh cloud đã có thay đổi
khác, upload sang laptop/snapshot-<SHA> thay vì force-push. Mang link nhánh đó
về cloud để tiếp tục, không tự thay main hay ghi đè các tag cũ.
