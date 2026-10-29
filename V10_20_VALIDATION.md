# V10.20 — bảng lỗi nhỏ, vòng tròn và bỏ qua sai lệch nhỏ

Kiểm thử trên laptop Windows/V8i SS3 ngày 29/10/2026. Kế thừa đường ghi và
tốc độ 10.19; phiên bản này thay giao diện và phân loại cảnh báo.

- Bảng mặc định 270 × 205, sáu nút, loại lỗi và bộ đếm; không hiện tọa độ,
  khoảng cách hay đoạn giải thích. Danh sách đầy đủ còn qua chuột phải.
- Dấu focus là ellipse transient, không AddElement, không ghi vòng tạm vào DGN.
  Các cell SMERR và thao tác xóa một/xóa tất cả giữ nguyên.
- Sai số bỏ qua mặc định 0,001 m, chỉnh được. Chỉ ẩn cảnh báo về nút gần,
  đoạn ngắn và dangle thỏa ngưỡng. Với dangle dài, mọi đầu tự do phải gần
  một cạnh khác, không tính cạnh nối trực tiếp vào chính đầu đó. Không dùng
  một đầu tiếp xúc để bỏ qua đầu còn lại đang hở xa. Không ẩn CUT_EDGE,
  INVALID_RING, HOLE_UNSUPPORTED hoặc NO_PARCELS.
- So sánh snapshot dc102 nghiêm ngặt và ngưỡng 1 mm: 10 NEAR_NODE và 10 DANGLE
  nhỏ được bỏ qua; còn 1 DANGLE và 3 HOLE_UNSUPPORTED. Giữ đúng 362 vùng,
  toàn bộ parcel và noded_lines giống hệt trước/sau phân loại. Không sửa DGN
  thật để thử tính năng. Chi tiết chẩn đoán cục bộ ở data/v1020-analysis.json.
- Không dùng việc ẩn cảnh báo để xác nhận đã khép vùng. Chuỗi dangle dài bị
  ẩn theo sai số vẫn chặn export_rows trước ghi MDB, tránh xuất thiếu vùng.
- 104 kiểm thử Python/Tk đạt, gồm ngưỡng 0, giữ ranh/diện tích, đầu hở thật,
  chặn xuất thiếu vùng và các thao tác điều hướng/xóa cũ. I/O của unit test
  được mô phỏng; không coi đó là kiểm thử Jet thực tế.
- V8i thật trên bản sao mẫu 4 vùng: clean 0,152 s; vùng/diện tích, USERERR,
  SMPARC giữ nguyên; clean lần hai giữ ID; style sai bị chặn trước ghi;
  focus ba mức không thêm hình học DGN. Ẩn/khôi phục lớp không Save, snapshot
  gốc trước/sau khớp. Không viết MDB trong đợt kiểm tra này.
  Báo cáo: data/v1020-validation-3a38756e5d6f4c10ba4f4cd5537b7389/report.json.
- Không cần mở gCadas: lỗi người dùng đã được tái hiện trực tiếp trên dc102,
  xác định khoảng hở nhỏ và kiểm chứng cách bỏ qua mà không đổi tọa độ.

Giữ nguyên các giới hạn giao dịch C# nêu ở V10_19_VALIDATION.md. Kiểm tra
CRC và SHA256 từng gói; giữ package/tag cũ và backup chương trình khi cập nhật.

## Xác minh cài đặt

- Đã cài SonMap+ V10.20 vào thư mục App hiện có, đối chiếu byte các mô-đun
  Python và interop với mã kiểm thử. Runtime/data/settings được giữ lại.
- Bản 10.19 được lưu tại Backups/before-10.20-57666803a039400799bae8638cd182c4.
- Bản đã cài đọc dc102, dựng 362 vùng và bỏ 20 cảnh báo nhỏ; focus trả FOCUSED.
  Đã nhìn trực tiếp vòng tròn đỏ quanh điểm đang chọn, không còn chữ thập.
  Cửa sổ ứng dụng mang tiêu đề SonMap+ V10.20.
- 104/104 kiểm thử Python/Tk cuối đạt sau thay đổi giao diện cuối cùng.
