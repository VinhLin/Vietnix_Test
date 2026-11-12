# Nhật ký làm bài

**Họ tên:** Vincent (xác nhận tên pháp lý trước khi nộp)  
**Nhận đề lúc:** Chưa xác định được từ folder. `DE-BAI.md` có timestamp 27/10/2026; folder được copy ngày 29/10/2026 14:03. Vincent điền thời điểm nhận đề theo email thực tế.  
**Nộp bài lúc:** Chưa nộp; điền sau khi thực sự gửi.  
**Tổng thời gian làm thật (ước tính):** Phần draft có AI hỗ trợ trong phiên 29/10/2026; cần Vincent bổ sung thời gian tự đọc/review/chỉnh sửa. Không tính thời gian này như thời gian Vincent tự làm.

## Các phiên làm việc

| Thời điểm | Thời lượng | Làm phần nào | Ghi chú (kẹt ở đâu, đã thử gì) |
|---|---:|---|---|
| 29/10/2026, bắt đầu theo timestamp tin nhắn khoảng 14:17 (+07) đến lúc hoàn tất bản draft | Phiên AI hỗ trợ; session status hiển thị khoảng 26 phút nhưng không khớp timestamp tin nhắn, nên Vincent cần xác minh và không tính thành giờ tự làm | Phân tích đề/log/snapshot; soạn Phần 1–3; viết tool Phần 2 và README | Không có access vào máy Vietnix/cluster thật. Tìm thấy logrotate typo, disk full, backup cùng filesystem; snapshot Proxmox có field bất thường nên tool chặn kết luận đầy đủ. |
| Vincent tự bổ sung | Điền sau khi review | Đọc lại, sửa theo hiểu biết/kinh nghiệm cá nhân, xác minh giả định và điền mốc nhận/nộp bài | Chưa thực hiện trong nhật ký này. |

## Giả định đã đặt ra

- Chọn đề A ở Phần 3 (MinIO so với Ceph RGW) theo yêu cầu bổ sung ngày 29/10/2026; bản nghiên cứu ban đầu theo đề B đã được thay thế.
- Tool dùng ngưỡng CPU 80%, RAM 85%, overcommit 2.5 vCPU/core; đây là default có thể cấu hình, không phải policy Vietnix.
- CPU usage chỉ hợp lệ trong [0,1] theo mô tả JSON; không diễn giải các giá trị 20.8/31/98 thành phần trăm vì không có schema xác nhận.
- VMID trùng lấy record đầu để tránh đếm đôi; node không khai báo bị loại. `mem_total` 256 KiB được xem là snapshot không đáng tin cho host 32 core. Do đó kế hoạch migrate chưa thể kết luận an toàn cho toàn cluster.
- Thông tin nhận đề, deadline và thời điểm nộp không có trong folder; cần đối chiếu email.

## Câu hỏi đã gửi cho người ra đề

- Chưa gửi câu hỏi nào.

## Dùng AI và công cụ

| Bước | Công cụ | Dùng để làm gì | Bạn đã kiểm tra, sửa lại gì |
|---|---|---|---|
| Đọc đề/snapshot | OpenAI Codex (Nyra), PowerShell | Trích nội dung Markdown, liệt kê file, xem snapshot và log | Đối chiếu chuỗi thời gian ở syslog, Nginx/PHP/MySQL, `df/du`, LB; không dùng nội dung không có bằng chứng làm kết luận. |
| Thống kê LB | Python | Đếm 4.718 dòng và status, xác định 502/504 đầu tiên và vhost | So lại với file log và thời gian ghi ở report. |
| Tool Proxmox | OpenAI Codex (Nyra), Python `unittest` | Viết analyzer, output table/JSON, validation và đề xuất migrate | Chạy 5 unit tests; chạy trên snapshot thật; kiểm tra cảnh báo CPU ngoài miền, RAM thiếu, VMID trùng, node thiếu; xác nhận đây là partial plan. |
| Nghiên cứu Phần 3 — bản cập nhật 29/10/2026, khoảng 14:43–14:47 (+07) | Firecrawl CLI, tài liệu chính thức MinIO/Ceph | Đối chiếu erasure coding/quorum MinIO, RGW/pool Ceph và monitor quorum | Chuyển từ đề B sang đề A theo yêu cầu Vincent; tính capacity chỉ là ước tính từ EC:4 và replication size=3, chưa POC/benchmark trên phần cứng mục tiêu. |

## Phần chưa xong hoặc chưa hài lòng

- Vincent chưa review hoặc chỉnh giọng văn/quan điểm cá nhân; cần làm trước khi nộp.
- Chưa có lab/phần cứng mục tiêu để kiểm tra storage, failure domain, tải degraded/healing, throughput hoặc khôi phục; sizing Phần 3 mới là ước tính trên tài liệu và cần POC.
- Log không đủ chứng minh bot là tác nhân khởi phát; báo cáo giữ kết luận này ở mức “chưa đủ bằng chứng”.
- Cần điền mốc nhận đề, thời gian Vincent thực làm, thời điểm nộp và thông tin cá nhân dựa trên thực tế.

## Nếu làm lại, bạn sẽ làm khác điều gì?

Đầu tiên xác minh ngưỡng overload và semantics của export Proxmox với team vận hành; sau đó thêm capacity/affinity constraints vào planner và kiểm tra restore backup trong lab. Với sự cố hosting, bổ sung trend dung lượng từng ngày và dữ liệu định danh request/crawler trước khi kết luận có bot abuse.
