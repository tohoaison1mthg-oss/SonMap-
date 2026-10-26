# Tiếp tục phát triển SonMap+ trên máy khác

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
đóng gói. Phiên bản hiện tại là V10.4; lần nâng cấp kế tiếp tăng lên V10.5 nếu
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
