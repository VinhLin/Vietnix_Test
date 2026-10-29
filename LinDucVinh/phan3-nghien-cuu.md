## So sánh giữa MinIO và Ceph RGW

Tiêu chí	|		MinIO			|		Ceph RGW		|
----------------|---------------------------------------|---------------------------------------|
Kiến trúc cốt lõi| Chuyên biệt cho Object Storage (Được viết bằng Go, tối ưu hóa hiệu năng trực tiếp trên ổ cứng/filesystem). | Tích hợp sâu trong hệ thống Ceph Distributed Storage (Viết bằng C++, thông qua tầng RADOS).|
Khả năng mở rộng (Scale)| Rất linh hoạt, mở rộng theo mô hình Distributed (Erasure Coding trên các node độc lập).| Cực kỳ lớn, mở rộng theo cụm hạ tầng phần cứng của Ceph (OSD, Monitor, RGW instances).|
Độ phức tạp vận hành| Thấp – Trung bình. Dễ triển khai qua Docker Compose hoặc Kubernetes (Operator chuẩn).| Cao. Yêu cầu hiểu sâu về kiến trúc Ceph (MON, OSD, PG, CRUSH map) để tune hiệu năng và xử lý sự cố.|
Hiệu năng (Performance)| Rất cao (Ultra-fast), đặc biệt tối ưu cho các workload AI/ML, Big Data, đọc/ghi file dung lượng lớn hoặc hàng triệu file nhỏ với tốc độ cực nhanh.| Tốt, nhưng độ trễ (latency) thường cao hơn MinIO một chút do phải đi qua nhiều tầng chuyển đổi của Ceph RADOS. |

## Khuyến nghị

### Ngắn hạn
- MinIO đã dần chuyển sang phiên bản [Enterprise](https://github.com/minio/minio) *(bản miễn phí sẽ không cập nhật các bán vá nữa)*
- MinIO dễ vận hành, tài liệu và hướng dẫn cũng nhiều
> *Do đó nếu doanh nghiệp muốn triển khai nhanh, dễ vận hành thì bản miễn phí đã có thể đáp ứng.* </br>

### Dài hạn
- Nếu muốn phát triển lớn mạnh về dịch vụ Object Storage S3, thì **Ceph RGW** sẽ tốt hơn.
- Vì hiện tại **Ceph RGW** vẫn đang là dự án mã nguồn mở, có khả năng tích hợp sâu vào hạ tầng.
- Điều này đi kèm với sự phức tạp trong vận hành.

## Benchmark MinIO
```
warp mixed --host=192.168.100.123:9000 --access-key=<user> --secret-key=<pass> --autoterm
```
Kết quả:
- **Về mặt khả năng đáp ứng**: Hệ thống hoạt động hoàn toàn ổn định (không lỗi), xử lý tốt các tác vụ đọc (`GET`), kiểm tra (`STAT`) và xóa (`DELETE`).
- **Về mặt hiệu năng ghi (PUT)**: Hệ thống đang bị nghẽn nặng ở thao tác ghi file. Độ trễ lên tới gần 10 giây cho một request `PUT` cho thấy hạ tầng lưu trữ vật lý bên dưới (có thể là tốc độ ghi của ổ cứng, băng thông mạng nội bộ, hoặc cấu hình phân bổ tài nguyên phần cứng cho cụm) chưa được tối ưu cho việc ghi dữ liệu dưới tải đồng thời.








