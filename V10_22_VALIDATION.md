# SonMap+ V10.22 - bộ cài đầy đủ

Nền mã ứng dụng: V10.21, commit effcdb07d16afe9e1ffbb1b9ce658c48b90ada23.
V10.22 bổ sung đóng gói/cài đặt, không thay thuật toán địa chính.

## Thành phần

- Một EXE Windows x64, đóng gói mã nguồn, hai mẫu xuất hồ sơ và ThanhTanApp.mvba.
- Python 3.12.10 x64 từ python.org, chữ ký Python Software Foundation hợp lệ.
- Shapely 2.0.7, NumPy 1.26.4, wheel CPython 3.12 Windows x64; đối chiếu SHA256 PyPI.
- Tạo môi trường riêng, lối tắt SonMap+, MicroStation V8i và khôi phục chương trình.
- VBA được cập nhật từ mã hiện hành khi xuất; bổ sung update_vba.ps1 ở đúng thư mục gốc.
- Khởi động V8i với cấu hình phiên làm việc, không yêu cầu workspace VietMapXM.
- Tài nguyên riêng chỉ lấy từ bản sao cục bộ: hai mẫu assets và project VBA.
  Không đóng gói DC101.dgn/DC101.mdb, settings, data, lịch sử chat hoặc vendor DLL.
  Không đưa tài nguyên riêng, bộ cài Python hoặc wheel lên GitHub.

## Đã kiểm tra trên Windows

- 109/109 kiểm thử Python/Tk đạt, gồm kiểm tra gói mã nguồn không có dữ liệu riêng.
- Tất cả PowerShell phân tích cú pháp thành công.
- EXE biên dịch .NET Framework 4, kiểm tra SHA256 bundle và giải nén đạt.
- Cài vào thư mục cô lập với -NoLaunch -IsolatedTest đạt. Tái sử dụng Python 3.12
  hiện có, tạo venv mới và cài Shapely/NumPy bằng --no-index từ wheel kèm gói.
- Tài nguyên đủ ba tệp; kiểm tra SHA256 trước khi cài. Cài lần hai giữ nguyên
  mẫu đã sửa, settings.json, dữ liệu thử và VBA đã tồn tại; sao lưu mã chương trình.
- Bộ cài Python kèm gói có chữ ký hợp lệ; nhánh cài Python khi máy chưa có Python
  chưa được thực thi trong máy ảo sạch. Không coi thử nghiệm tái sử dụng Python là
  xác minh đầy đủ lần cài đầu trên máy mới.
- Phát hiện được đường dẫn V8i trên máy kiểm thử bằng chế độ ProbeOnly.

## Giới hạn

Chưa nghiệm thu trên máy Windows sạch chỉ có V8i, chưa chạy xuất V8i/Jet với bộ
cài mới. Kết quả nghiệp vụ V10.21 vẫn xem V10_21_VALIDATION.md. Cần V8i có VBA
và Windows 64-bit. Không kèm MicroStation, Office, VietMapXM hoặc giấy phép của
các phần mềm này. Font và bố cục mẫu cần kiểm tra trên máy nhận trước khi in.
Các mẫu cũ được dùng lại từ bản sao của người dùng, không khẳng định đã cập nhật
theo quy định địa chính tại thời điểm mới. Không sửa DGN/MDB thật khi kiểm thử.

Tạo lại bộ cài: chạy installer/package_full.py với --output, --resources và
--prerequisites trỏ tới thư mục tài nguyên cục bộ. Không ghi đè gói đã có.
