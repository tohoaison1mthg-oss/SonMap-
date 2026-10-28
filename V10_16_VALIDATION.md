# V10.16 — tốc độ topo và lỗi diện tích

## Lỗi đã tái hiện

MDB tạm của lần chạy bị lỗi chứa diện tích ID 111 là 431.9326793858611; kế hoạch là 431.93267938586115. Chênh lệch 5.684341886080802e-14 m². So sánh tuyệt đối làm dừng trước bước ghi DGN/thay MDB.

Bản sửa cho phép tối đa 8 ULP đối với Double. Không dùng ngưỡng hiển thị 0,1 m²; sai lệch diện tích thực vẫn bị chặn trước khi ghi DGN. Các thuộc tính và Geometry khác vẫn được kiểm tra.

## Đo trên Windows/V8i/Jet thật

- dc144 đọc bằng bộ quét interop toàn bộ: 78,38 giây; bộ quét lọc lớp 10,23,32: 16,45 giây. Hai kết quả có cùng 938 phần tử ranh có thuộc tính/hình học tương ứng; bộ lọc không đưa các lớp khác vào tạo vùng. Đây là phép đo bước quét, không phải toàn bộ thời gian tạo topo.
- Cặp DGN/MDB được sao chép vào thư mục tạm để nghiệm thu. Phân tích đầy đủ: 17,04 giây (quét 16,66; dựng vùng 0,32). Cập nhật và kiểm tra MDB: 25,54 giây.
- MDB 181 → 182 bản ghi. ID 164 được chia thành hai vùng với ID 181 và 182; giữ số thửa và thuộc tính kế thừa theo cơ chế hiện có. Có 177 bản ghi giữ nguyên mọi cột. Các vùng khác có hình học thay đổi theo ranh hiện tại được đối chiếu riêng, không coi số lượng bản ghi là bằng chứng duy nhất.
- Đọc lại DGN sau lưu: đủ 182 vùng, diện tích hình học từng vùng khớp ở độ chính xác kiểm tra 0,00001 m²; từng tâm/số thửa có tọa độ đúng. Không tạo SonMap_backups trong thư mục thử. Thư mục giao dịch tạm tự dọn.
- Mở lại dc144 gốc; SHA256 cả DGN và MDB không đổi. Kết quả ghi thực nêu trên thuộc bản sao tạm, không phải tuyên bố đã thay dữ liệu gốc.
- 87 kiểm thử Python/Tk đạt, bao gồm sai số Double, chặn diện tích sai thực, rollback khi MDB khóa, không giữ backup sau thành công và nhận diện khi nào cần viết lại ranh. Kiểm thử record interop V8i thực đạt; không thêm phần tử hay lưu DGN ở kiểm thử record. Kiểm tra toàn vẹn gói phải đạt trước phân phối.

## Phạm vi và phục hồi

Chế độ cập nhật trực tiếp vẫn kiểm tra đúng DGN/model/hash, xác minh mọi bản ghi trước khi thay MDB và phục hồi khi lỗi. Theo yêu cầu người dùng, không giữ backup mới khi chạy thành công. Tệp cứu hộ chỉ được giữ nếu phục hồi thất bại. Không xóa các backup cũ. Sao lưu phiên bản chương trình của trình cài vẫn được giữ riêng để có thể quay lại V10.15.

Phần tử tham gia theo lớp của phần tử cấp ngoài được V8i Scan lựa chọn; cell trên lớp ranh vẫn báo chưa hỗ trợ, không tự phá cell chứa ranh. Cung chỉ được chia khi bật tùy chọn. Các lỗi ranh hở/đoạn dư vẫn chặn topo và có báo vị trí, không tự nối hoặc xóa chúng.
