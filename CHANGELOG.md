# Phiên bản SonMap+

Phiên bản ứng dụng hiện tại lấy từ [VERSION](VERSION). Các mục dưới đây ghi
lịch sử từng bản, bao gồm hành vi sao lưu và giới hạn tại thời điểm phát hành;
không dùng mô tả bản cũ làm quy ước phát triển hiện hành. Quy ước lâu dài nằm
trong [AGENTS.md](AGENTS.md); thông tin dự án và dẫn chiếu nghiệm thu nằm trong
[PROJECT.md](PROJECT.md). Cập nhật tài liệu quy ước không tạo bản phát hành mới.

## V10.16

- Sửa lỗi dừng topology vì so sánh Double tuyệt đối khi MDB đọc lại lệch vài ULP (trường DienTich, ID 111). Chỉ dung sai sai số biểu diễn số thực; ID, văn bản và Geometry vẫn kiểm tra chính xác, diện tích hiển thị một chữ số thập phân.
- Quét ranh bằng interop có kiểu và lọc lớp ngay trong V8i; không chuyển hàng nghìn phần tử ngoài lớp topo sang PowerShell. Chỉ đọc lớp nhãn khi được chọn, đọc bổ sung khi đổi lớp gán nhãn.
- Chế độ cập nhật hiện tại không tạo before-save.dgn hoặc thư mục bản sao DGN cạnh bản đồ. Phục hồi giao dịch dùng tệp tạm, tự dọn sau thành công hoặc sau khi phục hồi được; chỉ giữ tệp cứu hộ nếu không tự phục hồi được. Theo yêu cầu người dùng, không giữ thêm backup DGN/MDB mỗi lần sửa lỗi/topo; các backup cũ được giữ nguyên.
- Giữ nguyên hình học/diện tích MDB và bỏ ghi lại các bản ghi không thay đổi; topology chỉ viết lại ranh khi cần tạo nút/nối/chia cung hoặc loại đoạn trùng. Bộ nhớ đệm lớp giảm số lần gọi COM khi ghi tâm/ranh.
- Sửa kiểm tra hash trong PowerShell 32-bit bằng SHA256 .NET. Kiểm thử Windows/V8i/Jet trên bản sao tạm của dc144: 181 → 182 thửa, ID 164 → hai ID 181/182, 177 bản ghi giữ nguyên, đọc lại đủ vùng và tâm thửa. Phân tích 17 giây, cập nhật 26 giây trên laptop này; tệp người dùng mở lại với hash DGN/MDB không đổi.

## V10.15

- Sửa đường mở từ MicroStation/VBA cũ vẫn gọi ThanhTanApp/app.py và hiện V10.3 dù đã cài SonMap mới. Trình cập nhật chuyển điểm mở cũ sang SonMapPlus/App hiện đang cài, dùng Python riêng của bản đó; tiêu đề tiếp tục đọc VERSION.
- Sao lưu nguyên mã khởi động cũ trước sửa; sửa lặp lại không chèn trùng. Có khôi phục điểm mở cũ và lưu bản đang thay để hoàn tác khôi phục. Không sửa DGN/MDB, settings, runtime hoặc tài nguyên riêng.
- Mẫu VBA khởi động ưu tiên thư mục cài SonMap hiện tại thay vì đường dẫn máy phát triển cũ. Giữ nguyên các gói/tag V10.12–V10.14, không hạ bản đang cài.

## V10.14

- Thu gọn ba bảng Sửa lỗi, Tạo topology và Sửa thông tin thửa theo bố cục mẫu; bỏ các dòng mô tả kỹ thuật và tab toàn bộ cột MDB khỏi bảng sửa thửa.
- Chỉ hiện các thuộc tính địa chính được yêu cầu: số tờ/thửa/tạm, diện tích, đất ở, diện tích pháp lý, mục đích/đối tượng sử dụng, địa chỉ, chủ/vợ chồng, thông tin giấy tờ và ghi chú. Cột kỹ thuật, ID, tọa độ và cột bổ sung khác được giữ trong MDB, không đưa lên form.
- Diện tích tại các ô, danh sách thửa và báo lỗi luôn hiển thị một chữ số sau dấu phẩy (568,7). Không làm tròn dữ liệu lưu; chọn một ô diện tích chưa sửa cũng giữ nguyên độ chính xác gốc.
- Giữ chức năng pick trong thửa, chọn từng trường để lưu, sao lưu và kiểm tra MDB; thuộc tính chưa có trong cấu trúc MDB hiển thị trống, không tự tạo cột.
- Kiểm thử Python/Tk và toàn vẹn gói cài đạt. Đây là thay đổi giao diện/định dạng; không sửa thuật toán COM/V8i/Jet đã kiểm thử ở V10.13. Giữ gói/tag/bản cài V10.13 để khôi phục.

## V10.13

- Làm gọn bản vẽ chỉ ẩn các lớp không tham gia; có khôi phục đúng trạng thái hiển thị từng view, không xóa phần tử.
- Sửa ranh tạo giao điểm thực, giữ lớp/màu/độ đậm/kiểu nét; giữ đoạn dư và ranh hở để báo lỗi, không tự xóa đoạn dư hay nối khe hở mặc định.
- Báo lỗi có Trước/Sau, tìm vị trí trên DGN, ghi dấu lỗi có sao lưu và kiểm tra lại sau sửa thủ công.
- Bảng thông tin thửa có nút con trỏ pick bên trong, pick lại nhiều thửa, tùy chọn zoom; hủy pick không cho lưu nhầm thửa trước.
- Đọc toàn bộ thuộc tính MDB; chỉnh các trường văn bản/số/logic có sẵn, chọn riêng trường ghi và xóa nội dung bằng giá trị trống. ID, hình học và diện tích đo chỉ đọc; không tự thêm/xóa cột cơ sở dữ liệu.
- Ghi thuộc tính trên MDB tạm, kiểm tra lại toàn bộ bản ghi trước khi thay tệp, giữ bản sao lưu và các bảng/cột khác.
- Sửa lỗi tạo MDB nhiều thửa trong PowerShell 32-bit. Giữ V10.12, các gói/tag cũ và dữ liệu riêng để phục hồi.
- Kiểm thử Python/Tk và kiểm tra gói đạt; đã thử Windows/V8i V7/Jet trên dữ liệu tổng hợp trong bản sao seed: ẩn/khôi phục lớp không đổi phần tử/tệp, ghi giao điểm giữ nét, giữ đoạn dư, ghi dấu lỗi không trùng lặp, sửa thuộc tính Unicode không đổi thửa bên cạnh/hình học. DGN người dùng mở lại, hash không đổi. Chi tiết nghiệm thu trong V10_13_VALIDATION.md.

## V10.12

- Thửa con tạm kế thừa số thửa và thông tin thửa cũ; mỗi vùng vẫn có ID MDB riêng và diện tích/hình học riêng.
- Cho phép số thửa trùng tạm trong MDB; chọn bằng điểm trên DGN vẫn phân biệt theo hình học và ID.
- Bảng thông tin trên DGN có ô Số thửa để đổi riêng số thửa, tên và địa chỉ chủ sử dụng; sao lưu trước khi lưu.
- Sao chép các cột thuộc tính khác của thửa cha vào thửa con, giữ cấu trúc MDB và bản ghi ngoài phạm vi.
- Giữ V10.11 và các bản sao dữ liệu để phục hồi.
- Kiểm thử Windows/Jet thực trên bản sao đã xác nhận số trùng tạm, kế thừa cả cột bổ sung, đổi riêng số/tên một thửa con và giữ nguyên thửa còn lại; 71 kiểm thử Python đạt.

## V10.11

- Nút Thông tin thửa trên DGN: nhấp bên trong thửa trong V8i để mở bảng thông tin theo ID MDB và hình học.
- Sửa tên, địa chỉ chủ sử dụng và lưu trực tiếp vào MDB bằng câu lệnh có tham số, transaction, đọc lại kiểm tra và sao lưu trước ghi.
- Chặn điểm trên ranh, vùng chồng lấn, ID trùng và dữ liệu MDB đã thay đổi trong lúc mở bảng; chuột phải để hủy chọn.
- Không thay ranh, diện tích, số thửa hoặc các bản ghi khác khi sửa chủ sử dụng. Giữ V10.10 để phục hồi.
- Đã thử chọn điểm trong V8i thật và mở đúng bảng thửa; Jet ghi/đọc Unicode trên MDB bản sao đạt, giữ nguyên dữ liệu gốc. 66 kiểm thử Python và kiểm thử PowerShell đạt.

## V10.10

- Cột Diện tích trong danh sách thửa luôn hiển thị một chữ số thập phân, dùng dấu phẩy: 682,7; 918,3; 100,0.
- Áp dụng khi đọc, lọc và cập nhật dòng; giữ nguyên độ chính xác của giá trị MDB và dữ liệu xuất.
- Giữ V10.9 và sao lưu mã trước cập nhật để phục hồi.

## V10.9

- Cập nhật cục bộ thửa tách đã khép kín và phủ đủ thửa MDB cũ khi lỗi topology nằm ngoài phạm vi đó.
- Dừng nếu lỗi chạm phạm vi thửa tách, thiếu diện tích, có phần tử ranh chưa hỗ trợ hoặc đã nối ranh.
- Giữ nguyên đường ranh DGN và các thửa MDB ngoài phạm vi; chỉ thay tâm SonMap trong vùng và cập nhật delta của thửa tách.
- Mở/khôi phục DGN bằng chế độ V7 Workmode rõ ràng, giữ định dạng và quyền chỉnh sửa thay vì hiện hộp thoại nâng cấp/chỉ đọc.
- Kiểm thử Windows/V8i/Jet trên bản sao thực đã đạt: MDB tăng một bản ghi, hai tâm mới đúng vị trí, đường ranh không đổi.
- Đã áp dụng và đọc lại cặp DGN/MDB hiện tại trên laptop: hai thửa con đúng hình học/tâm, mọi bản ghi ngoài phạm vi giữ nguyên; có sao lưu trước ghi.
- Giữ V10.8, bản sao dữ liệu trước cập nhật và các gói nguồn để phục hồi.

## V10.8

- Đọc/ghi Point3d, Matrix3d và ID qua interop V8i đã cài trên laptop; sửa lỗi COM khiến đường lớp 10/23/32 bị coi là phần tử không hỗ trợ.
- Giữ ID thửa không đổi khi hình học MDB và DGN lệch ở mức sai số số thực; hỗ trợ ID 0 có sẵn trong MDB cũ.
- Kiểm tra quét V8i phải đọc được tọa độ đường, không chỉ đếm phần tử. Giữ lỗi COM gốc khi dọn bản sao thất bại.
- Đã thử Windows/V8i thật: đọc 68 ranh trên bản sao, tạo 13 vùng từ MDB 12 thửa; Jet ghi/đọc lại bản sao đạt. Kiểm thử đối tượng hình học rời đạt.
- Chưa xác nhận cập nhật cặp DGN/MDB người dùng đang mở. Ghi bản sao DGN V7 còn lỗi Bad modelRef, đang điều tra; không coi đây là bản đã nghiệm thu.

## V10.7

- Chế độ mặc định ghi DGN hiện tại và cập nhật MDB đang kết nối, có sao lưu trước thay đổi.
- Sau tách vùng, cập nhật và nạp lại danh sách MDB; giữ thửa ngoài phạm vi, ID/thuộc tính của vùng không đổi.
- Thửa con mới có ID mới; số thửa chính thức để chờ nếu không có nhãn được gán.
- Cập nhật delta trên bản sao đầy đủ MDB để giữ các bảng/cột khác; phát hiện ràng buộc không hỗ trợ sẽ dừng.
- Hiển thị số phần tử đọc theo lớp và số vùng tạo được; vẫn có lựa chọn tạo bản riêng.
- Gói workspace cho laptop, lối mở Codex local trong VS Code, đồng bộ mã qua GitHub và lưu lịch sử.

Cần xác minh DGN/Jet thật trên laptop. Các kiểm thử cloud chỉ xác nhận logic và mô phỏng I/O.

## V10.6

- Sửa lệnh quét DGN từ COM ngoài V8i: tạo ElementScanCriteria qua ứng dụng rồi truyền rõ vào Scan.
- Áp dụng cho cả đọc ranh và quét các phần tử cần thay trên bản sao.
- Tách chẩn đoán thành tạo tiêu chí, bắt đầu quét, chuyển phần tử và lấy phần tử hiện tại.
- Trình cài thử quét trực tiếp trên V8i đang mở, so với bản sao chỉ đọc và ghi báo cáo; không coi lỗi hoặc số phần tử 0 là kiểm thử đạt.
- Không đổi cách nhập nhiều lớp: 10,23,32 vẫn hợp lệ; giữ V10.5 để phục hồi.

Cần chạy xác minh trên V8i thực tế; kiểm thử đối tượng giả không thay thế COM thật.

## V10.5

- Phân biệt Python đã cài và Python phù hợp với thư viện SonMap; báo rõ 3.15/32-bit/thiếu thành phần.
- Probe Python có giới hạn 15 giây, không che mất lý do kiểm tra thất bại.
- Khi cài mới mà thiếu 3.12, tự tải bộ cài chính thức, kiểm tra chữ ký hợp lệ của Python Software Foundation.
- Cài Python 3.12 riêng cho SonMap, giữ các Python khác và không đổi PATH/liên kết tệp.
- Giữ gói, tag và nguồn V10.4 để phục hồi.

Cài tự động vẫn cần được xác minh trên Windows thật; kiểm thử cloud không thay thế thao tác này.

## V10.4

- Bảng chính gọn: Sửa lỗi, Tạo topology, Kết nối CSDL; hộp thoại riêng.
- Xử lý ranh trên bản sao, tạo vùng/tâm, gán nhãn và sửa thuộc tính thửa.
- Tạo/đọc MDB theo cấu trúc SonMap; tạo DGN và MDB mới từ topology.
- Sửa cách nhận model mặc định khi bản sao DGN không dùng tên hiển thị Default.
- Tự tìm Python 3.12 64-bit, khắc phục lỗi trình chạy chỉ in dòng đầu traceback.
- Gói cài/cập nhật theo người dùng, tạo lối tắt và sao lưu mã cũ.
- Công cụ khôi phục bản đã cài; giữ cả bản cũ và bản mới bằng backup và tag GitHub.
- Công cụ đọc cấu hình CAD tại C:\VietMapXM và chẩn đoán kết nối V8i, không sửa cấu hình gốc.
- Phiên bản hiển thị lấy từ VERSION; không dùng tên dev-v1/v2 thay phiên bản app.

Phần hình học/giao diện được kiểm thử cloud. Cầu nối V8i, Jet và trình cài
mới cần xác minh trên Windows thực; không coi các kiểm thử mô phỏng là bằng chứng
DGN/MDB của người dùng đã chạy thành công.

## V10.3

Mã nguồn ban đầu được đưa vào GitHub, có kiểm thử Python và các công cụ xuất
hồ sơ Windows/V8i. Tài nguyên runtime, VBA và mẫu hồ sơ đầy đủ được giữ riêng.
