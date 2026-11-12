# Bài test R&D Engineer — Vietnix

Bản nháp hỗ trợ hoàn thiện đề, tạo ngày 29/10/2026 từ dữ liệu trong folder. Nội dung kỹ thuật đã được viết; Vincent cần đọc lại, điền thông tin cá nhân/thời hạn thực tế và xác nhận nhật ký trước khi nộp. Chưa gửi email, tạo repo hay public nội dung.

## Deliverables

- `phan1-postmortem.md` — báo cáo điều tra dựa trên syslog, snapshot, service logs và load-balancer access log.
- `phan2-tool/` — tool Python, README sử dụng và unit tests.
- `phan3-nghien-cuu.md` — so sánh MinIO và Ceph RGW cho Object Storage S3 50 TB, chọn đề A và dẫn tài liệu chính thức.
- `phan4-nhat-ky.md` — nhật ký AI/công cụ và giả định; các thông tin không thể biết từ folder được đánh dấu để Vincent xác nhận.

## Chạy tool Proxmox

Cần Python 3.10+; không cần cài dependency ngoài. Từ thư mục này:

```powershell
python .\phan2-tool\cluster_load.py .\phan2-proxmox\cluster-pve-hcm-c3.json
python .\phan2-tool\cluster_load.py .\phan2-proxmox\cluster-pve-hcm-c3.json --format json
python -m unittest discover -s .\phan2-tool\tests -v
```

Tool chỉ phân tích snapshot và đề xuất; không gọi Proxmox API hoặc tự migrate VM. Mặc định ngưỡng là CPU >80%, RAM >85%, hoặc vCPU/core >2.5. Snapshot có record bất thường nên báo cáo chủ động đánh dấu node chưa đủ dữ liệu; kế hoạch hiện chỉ giảm tải an toàn cho một node, chưa phải kế hoạch cân bằng toàn cluster.

## Giả định và việc cần người làm bài xác nhận

- Chọn đề nghiên cứu A (MinIO so với Ceph RGW) theo yêu cầu bổ sung; sizing trong nghiên cứu là ước tính, cần POC trước production.
- Ngưỡng tải trong tool là giả định cấu hình, không phải policy Vietnix.
- Nhật ký không bịa thời điểm nhận/nộp đề, thời gian người dùng tự làm, hay câu hỏi đã gửi nhà tuyển dụng. Cần Vincent điền/kiểm tra trước khi nộp.
