# Khảo sát sửa lỗi và topology VietMapXM — 29/10/2026

## Bổ sung sau khi người dùng hướng dẫn trên dc101

Phần này cập nhật bằng chứng mới hơn; các giới hạn thử demo bên dưới chỉ áp
dụng giai đoạn khảo sát trước khi người dùng trình diễn trên bản đồ dc101.

Người dùng kẻ một đường cắt qua nhiều thửa và gửi ảnh kết quả:

- Tìm lỗi: thời gian giao diện báo 211 mili giây, có 2 lỗi cần sửa.
- Bảng vị trí lỗi hiển thị lỗi 1/2, loại đỉnh treo. Chưa xác minh cả hai vị trí.
- Tạo topology: báo thành công 329 thửa trong 1 giây 111 mili giây; lớp
  10,23,32, tờ 101, chế độ Cập nhật từ CSDL cũ, bật Bỏ qua lỗi topology.

Sau đó đã trực tiếp vào cửa sổ `dc101.dgn [2D - V8 DGN]`, mở Thông Tin
Topology Thửa Đất và Quản Lý Dữ Liệu Thửa Đất, chỉ xem dữ liệu:

- Thanh trạng thái ghi tổng 329 thửa, xóa 29 thửa, thêm mới 58 thửa.
  Số liệu phù hợp với 29 thửa bị chia thành 58 phần; không diễn giải chữ
  "xóa" này thành mất thông tin ngoài ý muốn. Nếu chỉ có delta này thì số
  lượng trước thao tác suy ra là 300, nhưng chưa có snapshot trước để xác minh.
- Bảng thống kê topology xác nhận tổng 329 thửa.
- Bảng dữ liệu hiển thị 329 thửa, có các cặp cùng số hiệu 9, 10, 11, 12,
  cùng tên chủ và loại đất trên hai dòng, diện tích khác nhau.
- Ví dụ quan sát: số 9 có 4.957,6 và 7.705,5 m²; số 10 có 12.487,8 và
  2.081,6 m²; số 11 có 14.656,6 và 1.628,8 m²; số 12 có 830,2 và 7.373,4 m².
  Những dòng này phù hợp hành vi giữ số thửa/thông tin cũ cho các phần mới.
  Chưa đối chiếu toàn bộ 58 phần với hình học và bản ghi cha trước cập nhật,
  chưa xác minh ID riêng hoặc mọi cột MDB.

Hai thời gian phần mềm báo cộng thành 1,322 giây. Đây là thời gian trong
giao diện do người dùng cung cấp, chưa đo độc lập từ đầu đến cuối, không gồm
thời gian xem/di chuyển qua các hộp thoại. Không so sánh tỷ lệ tăng tốc với
SonMap trên dữ liệu dc144 khác. Các thao tác quan sát tiếp nối không chạy lại
sửa lỗi/tạo topology hoặc bấm lưu thuộc tính trên dữ liệu đang mở.

Bằng chứng này thay thế nhận định thiếu kết quả chạy thật trên dc101.
Nó cho thấy luồng thực tế có thể cập nhật nhiều thửa bị cắt rất nhanh và vẫn
trả vùng khi bật bỏ qua lỗi. Cần phân biệt lỗi đỉnh treo của đường dư với vùng
khép hợp lệ, thay vì mặc định mọi đỉnh treo đều làm vô hiệu toàn bộ bản đồ.
Đây là yêu cầu thiết kế cần nghiên cứu cho SonMap; chưa thay đổi mã ứng dụng.

## Phạm vi

Mở VietMapXM cài tại `C:\VietMapXM` trong MicroStation V8i, workspace
VietMapXM. Thanh công cụ hiện `3.6.433.0725.447686460`. DGN thử là bản sao
demo dc24 tại `data/vietmap-study-20261029/demo.dgn`, kèm MDB cùng tên.
Không sửa mã SonMap hoặc phát hành phiên bản mới; VERSION vẫn 10.17.

Đã mở trực tiếp BẢN ĐỒ → Tạo Topology → Tự Động Tìm Và Sửa Lỗi.
Lần bấm chạy bị công cụ điều khiển từ chối vì điểm bấm không thuộc cửa sổ
đích; tiếp đó phát hiện thao tác người dùng và hộp mở DGN. Vì vậy phiên này
**không có lần chạy sửa lỗi/topology được xác nhận và không có số đo tốc độ
VietMap**. Không dùng thời gian click/chụp màn hình làm benchmark.

Quan sát chạy thật ngày 27/10 nằm ở `VIETMAPXM_STUDY.md`: làm sạch báo thành
công nhưng bước topology vẫn phát hiện lỗi; không suy diễn thành kết quả lần này.

## Bảng tự sửa lỗi quan sát được

- Trùng đè: đang chọn Xóa; có lớp/màu dành cho phương thức xử lý khác.
- Phá vỡ Arc và ComplexShape: đang bật.
- Báo đoạn ngắn dưới 0,001 m và vùng nhỏ dưới 0,3 m²: đang bật.
- Kết nối LineString, báo đoạn thẳng dư, kiểm tra nút gần: đang tắt.
- Khoảng cách nút gần 0,1 m; sai số tiếp xúc 0,01 m.
- Lớp tham gia: 10. Cell báo lỗi Level 60, màu 3, bán kính 0,01.
- Có tab danh sách file chạy đồng loạt.

Đây là trạng thái UI trên demo, không phải mặc định toàn sản phẩm hoặc ngưỡng
đúng cho mọi bản đồ. Đặc biệt, checkbox báo lỗi không chứng minh tự sửa lỗi đó.

## Bằng chứng mới về lõi dựng vùng

REA đọc tĩnh PE/CLI, không nạp DLL vào CLR hoặc thực thi mã phân tích.
`VietMap.CleanUp.dll` và `VietMap.DLBD.dll` có metadata giải mã được nhưng
thân các entry point khảo sát báo `Unsupported method body header`; coverage
member là partial. Chưa khôi phục được toàn bộ điều phối sửa lỗi và ghi MDB.

Tuy nhiên `VietMapDC.dll` cho phép đọc CIL với coverage complete trong phạm vi
các type đã chọn. Hai DLL giao diện có MemberRef tới các lớp hình học này.
Đây là bằng chứng về thành phần được tham chiếu và mã thư viện có sẵn, chưa
chứng minh mọi lựa chọn UI đều đi qua cùng một đường chạy.

### Dựng polygon từ đồ thị cạnh

Type `CADTOOLS.MyMap.Operation.Poligonize.Polygonizer`, method token
`0x06000864`, có thứ tự lời gọi trong CIL:

1. Kiểm tra trường kết quả `polyList` và đồ thị `graph`.
2. Offset IL 62: `PolygonizeGraph.DeleteDangles`, lưu vào `dangles`.
3. Offset IL 79: `DeleteCutEdges`, lưu vào `cutEdges`.
4. Offset IL 95: `GetEdgeRings`.
5. Offset IL 127: helper `0x06000865`; helper kiểm tra `EdgeRing.IsValid`,
   tách vòng hợp lệ và LineString vòng lỗi.
6. Offset IL 135: helper `0x06000866`; dùng `EdgeRing.IsHole` phân loại
   `holeList` và `shellList`.
7. Offset IL 153: helper `0x06000867` duyệt các lỗ, gọi helper gán lỗ.
8. Offset IL 204: lấy `EdgeRing.Polygon`, thêm vào `polyList`.
9. Giữ danh sách node/cạnh có hướng từ đồ thị để truy cập sau.

`DeleteDangles` token `0x0600084d` dùng `FindNodesOfDegree` và Stack Push/Pop,
duyệt các cạnh kề và đánh dấu cạnh, tiếp tục xét nút liên quan. Đây là xử lý
đồ thị trong thư viện; tên Delete không phải bằng chứng xóa phần tử DGN.

Nhận định: bộ dựng vùng phân loại cạnh không tạo vùng và vòng lỗi riêng trước
khi trả polygon. Mô hình này tương đồng với nhóm kết quả `polygonize_full`
SonMap đang sử dụng; chưa có cơ sở quy tốc độ VietMap cho một thuật toán
dựng vùng hoàn toàn khác.

### Tạo nút giao có chỉ mục không gian

Type `CADTOOLS.MyMap.Noding.MCQuadtreeNoder` có CIL cho thấy:

- `Node` duyệt SegmentString, gọi helper tạo chuỗi rồi helper tìm giao,
  sau đó gọi `Noder.GetNodedEdges`.
- Helper `0x060006b9`: `SegmentString.Coordinates` →
  `MonotoneChainBuilder.GetChains` → lấy Envelope → `ISpatialIndex.Insert`.
- Helper `0x060006b8`: lấy Envelope → `ISpatialIndex.Query` → so sánh Id
  chuỗi → `MonotoneChain.ComputeOverlaps` cho các ứng viên.

Như vậy có triển khai lọc ứng viên bằng vùng bao và chuỗi đơn điệu trong
thư viện, giảm nhu cầu xét mọi cặp đoạn. Chưa xác minh entry point sửa lỗi
VietMap hiện tại có gọi noder này hay dùng đường xử lý khác; không quy kết
đây là nguyên nhân tốc độ đã đo.

### Giao tiếp MicroStation

CleanUp tham chiếu Bentley interop `ElementScanCriteria`, `ExcludeAllLevels`,
`IncludeLevel`, `ExcludeAllTypes`, `IncludeType`, `ModelReference.Scan`,
`VertexList.GetVertices` và `Element.Rewrite`. Có khai báo P/Invoke MDL
`mdlElmdscr_setProperties`. Những tham chiếu/khai báo này chưa chứng minh
số lần gọi COM, tốc độ hoặc thứ tự ghi khi chạy thật.

## Đối chiếu SonMap+ 10.17

Nguồn hiện tại: `VERSION`, `CHANGELOG.md`, `PROJECT.md`,
`V10_17_VALIDATION.md`, `topology.py`, `topology_workflow.py`,
`dgn_interop.ps1`. Không dùng mô tả thiếu chức năng ở các bản cũ làm trạng
thái hiện tại.

| Nội dung | SonMap hiện tại | Điều cần kiểm tra tiếp |
| --- | --- | --- |
| Chỉ mục không gian | STRtree cho đỉnh gần và tra thuộc tính đoạn sau tạo nút | Đo trên cùng dữ liệu; không thay chỉ mục chỉ vì VietMap có Quadtree |
| Dựng vùng | unary_union tạo mạng nút, polygonize_full phân loại lỗi | Đo chất lượng cùng bộ lỗi có chủ đích |
| Nối khe hở | Chỉ nối hai đầu mút cô lập duy nhất và đối xứng trong dung sai | Chưa có sửa endpoint gần giữa cạnh/T-junction; cần thiết kế riêng và xem trước |
| Thửa có lỗ | Báo HOLE_UNSUPPORTED, chặn ghi | Lõi VietMap có shell/hole; khả năng lưu/xuất hồ sơ của UI chưa xác minh |
| Quét V8i | Interop C# có kiểu, lọc Level từ V8i | Đo riêng khởi động PowerShell, Add-Type, COM, serialize và I/O |
| Ghi bản vẽ | Có lọc phần tử, ghi theo lô; chỉ sửa ranh khi thay đổi | Đếm số tiến trình và lượt quét/đọc lại trên cùng tác vụ |

Theo nghiệm thu V10.17, một lần phân tích dc144 mất 22,20 giây: bước chuẩn
bị/quét 21,86 giây, dựng vùng 0,29 giây. Tên `scan_seconds` trong mã bao gồm
cả chuẩn bị, ẩn lớp/lưu nếu bật, hash, tiến trình PowerShell và xuất JSON;
không được diễn giải toàn bộ 21,86 giây là riêng lệnh Scan của Bentley.

Ưu tiên tối ưu đề xuất: đo chi tiết các phần trên, giảm khởi tạo PowerShell/
Add-Type lặp lại, cân nhắc cầu nối thường trú trong V8i và tái sử dụng snapshot
khi đã xác minh DGN/model/Level không đổi. Giữ kiểm tra xung đột, đọc lại dữ
liệu và khả năng phục hồi khi ghi lỗi. Đây là hướng triển khai độc lập,
**chưa được triển khai hoặc chứng minh tăng tốc trong phiên khảo sát**.

## Bằng chứng, nhận dạng và giới hạn

Các trích xuất bằng chứng tĩnh, giữ nguyên token và CIL anchor, lưu tại
`data/vietmap-study-20261029/static-evidence.json` (dữ liệu cục bộ, không đưa
DLL hoặc nội dung phân tích bên thứ ba vào gói SonMap). Đây không phải bundle
Evidence đầy đủ; các bản ghi đầy đủ vẫn được REA giữ theo các ID dưới đây.

- CleanUp SHA256: `975cc3ff216fb60876b6ebcf9bb13e2a8b815cc24230ff92d7872fa0088dc718`.
  Identity: `ev_1cbc82388fe622caa725dca243f1a90a7ba8331944f4e0049fb82a6e6a270970`.
- CleanUp entry point/member references:
  `ev_eb75d02c9fda3db3aa223392a9325dd612714b88ffb0e54e8f6d5ce08de98602`.
- DLBD SHA256: `db294625c60149526d7a808cdb5fcc3308b44ff5e37e7367719a1f1267938e39`.
  Member references: `ev_798f28bef1d4f4b613d53e394593f8d1b2a7ecacfaf2d4ff5a2f8ea4954d99db`.
- VietMapDC member inventory:
  `ev_8c99d166b19efc85cafd732af0960b3f0df819012df00d10466092d94685c095`.
- CIL Polygonizer/PolygonizeGraph/MCQuadtreeNoder:
  `ev_88b4a46b51dae9f1b1d976d0a775a8ab7bcf78bf55ee79e1002b1e369bc3ebd1`.
- Giải tên token noder:
  `ev_ef0b03367106a0d7b1f31fa6f57ac8ce609f5919ebfd372c90f859236679a6fc`.
- Giải tên EdgeRing:
  `ev_3b0afb5fd34fcf2004a93f4d2ab46a34bc6f5e032bd512d3f497bc839e0c15e9`.

Không suy ra hãng dùng nguyên một thư viện mã nguồn mở chỉ từ tên type.
Không xác nhận thuật toán chọn thuộc tính cũ, sửa trùng đè, endpoint-to-edge,
tính nguyên tử ghi DGN/MDB hay tốc độ VietMap khi chưa có bằng chứng tương ứng.
Không sửa DLL, bản quyền hoặc cấu hình bảo vệ phần mềm.

Đối chiếu cuối khảo sát: hash demo gốc DGN
`0893f97d60376ae1afdf6be52927d5f4da441b7f51b9cb77a2cef2bc2e06ff08`, MDB
`e48b053919f73b63702c7aef96114249d7551be988a5729d216447385b9a7379`
vẫn khớp trước thử. Không chạy test ứng dụng vì chỉ bổ sung báo cáo nghiên cứu.
