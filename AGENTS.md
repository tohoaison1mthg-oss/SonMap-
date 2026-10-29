# SonMap+ versioning

## Development principles

Các nguyên tắc dưới đây áp dụng lâu dài cho phát triển SonMap+. Đây là quy ước
phát triển, không phải tuyên bố rằng mọi chức năng ưu tiên đã được triển khai
hoặc nghiệm thu. Các mô tả phiên bản cũ là lịch sử, không thay thế quy ước này.

1. Dữ liệu địa chính thường xuyên thay đổi do tách thửa, hợp thửa, chuyển quyền,
   tặng cho và chỉnh lý. Người sử dụng chịu trách nhiệm nhập và xác nhận thông
   tin địa chính mới. Không coi thay đổi tên chủ, số thửa, diện tích hoặc thuộc
   tính là lỗi khi đó là thao tác được người dùng chủ động thực hiện. Kiểm tra
   kỹ thuật phải phân biệt thay đổi được yêu cầu với ghi sai hoặc thay đổi ngoài
   phạm vi; không mặc định dữ liệu cũ luôn là dữ liệu đúng.
2. Diện tích địa chính hiển thị trên giao diện và xuất hồ sơ dùng một chữ số
   sau dấu phẩy, ví dụ **568,7 m²**. Đây là quy tắc định dạng đầu ra; giữ độ
   chính xác cần thiết cho tính toán hình học và tọa độ. Không tự làm tròn tọa
   độ hoặc ghi đè độ chính xác gốc trong MDB nếu chưa có yêu cầu cụ thể; không
   ghi ngược giá trị hiển thị đã làm tròn vào dữ liệu lưu khi người dùng chưa sửa.
3. Ưu tiên phát triển ba nhóm chức năng:
   - Topology chính xác: tách thửa, hợp thửa, tạo giao điểm, kiểm tra và xử lý
     ranh Level 10, 23, 32.
   - Thao tác nhanh trên MicroStation V8i: chọn thửa, sửa thuộc tính và cập nhật
     MDB trực tiếp.
   - Tự động xuất hồ sơ: trích lục, phiếu đo đạc chỉnh lý, bảng tọa độ và các
     biểu mẫu địa chính.
4. Không tự khôi phục thông tin chủ sử dụng hoặc thuộc tính cũ sau khi người
   dùng đã xác nhận cập nhật thành công. Chỉ phục hồi dữ liệu khi giao dịch kỹ
   thuật bị lỗi và chưa hoàn tất; không dùng snapshot cũ để đảo ngược một cập
   nhật đã hoàn tất hợp lệ.
5. Không tạo thêm các bản backup DGN/MDB sau mỗi lần chỉnh lý thành công. Vẫn
   phải có khả năng phục hồi an toàn khi ghi lỗi giữa chừng: dùng transaction
   hoặc tệp tạm phù hợp, kiểm tra kết quả ghi trước khi xác nhận thành công,
   dọn tệp phục hồi tạm sau thành công hoặc sau khi phục hồi được. Chỉ giữ tệp
   cứu hộ khi chưa phục hồi được; không xóa backup cũ của người dùng. Quy tắc
   này không thay thế việc sao lưu tệp chương trình khi cập nhật/rollback phần mềm.
6. Giữ nguyên những chức năng đã chạy ổn định. Không tự ý thay đổi quy trình
   nghiệp vụ, giao diện hoặc cấu trúc MDB khi chưa cần thiết cho yêu cầu đang
   thực hiện. Kiểm thử thao tác ghi trên bản sao dữ liệu, bảo vệ dữ liệu thật.
7. Đồng bộ tài liệu hướng dẫn với phiên bản thực tế: ưu tiên `VERSION` và
   `CHANGELOG.md`, không lấy phiên bản từ README cũ. Đọc `PROJECT.md` cùng các
   báo cáo nghiệm thu của phiên bản liên quan; không coi giới hạn hoặc kết quả
   kiểm thử lịch sử là trạng thái hiện tại nếu đã có bằng chứng mới hơn.

## Release and update rules

The user requires a new version number for every user-visible upgrade, including
work continued on another computer. Read VERSION, CHANGELOG.md and current Git
branches/tags before releasing. Increment the minor component once per upgrade
(e.g. 10.3 -> 10.4 -> 10.5); do not reuse informal dev-v1/v2 labels as app versions.
VERSION is the source of truth for the application title, installer, shortcut
and package filename. Record each release in CHANGELOG.md. Do not lower a newer
installed version or discard work made on another branch/computer.

Documentation-only updates to development principles do not require a VERSION
bump, a release package or a release tag. Commit them separately from algorithm
or application behavior changes. Keep existing release history intact.

Run the relevant Python tests and package integrity checks before distribution.
Distinguish cloud tests from Windows/V8i/Jet validation. Preserve user DGN/MDB,
settings, runtime, assets and data during updates. Keep source on the existing
GitHub development branch unless the user asks to merge/publish it elsewhere.

Keep both old and new releases: never overwrite a versioned package or Git tag.
Create immutable tags for release commits and retain old source archives. Push
release commits/tags to the existing repository so another computer can resume.
The laptop updater must back up replaced program files, preserve private data,
and offer program rollback while also saving the version being rolled back.
