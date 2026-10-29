## Bài test interview
- Ứng tuyển vị trí R&D Engineer (Infrastructure & Automation) tại Vietnix
- Làm bài test tại nhà theo file đính kèm. Thời hạn: 72 giờ kể từ khi nhận email này. Thời gian làm thực tế khoảng 4 đến 6 giờ.

### `phan1-su-co`
- Ngó sơ một lượt tất cả file, mình để ý nhanh đến `mysql/error.log`:
```
2026-10-14T03:00:12.551203+07:00 0 [Warning] [MY-010055] [Server] IP address '10.20.1.31' could not be resolved: Name or service not known
```
- Cái này là lỗi liên quan đến **DNS**, câu hỏi là **Có phải DNS-Server đang có vấn đề gì không?**
- Các dòng còn lại cho thấy ổ cứng bị full, tại sao lại full?
```
2026-10-20T01:33:04.118842+07:00 14 [ERROR] [MY-000035] [Server] Disk is full writing './binlog.000187' (OS errno 28 - No space left on device). Waiting for someone to free space... Retry in 60 secs. Further messages will be issued every 10 minutes.
```
- File `df -h.txt`, cũng cho thấy ổ `/dev/sda2` bị full.
- File `dmesg-tail.txt`, firewall UFW đã block IP `103.97.125.71`, check trên virustotal. IP sạch
- **Kết luận tạm thời:** Việc website bị sự cố có thể là do dung lượng ổ cứng đầy, là crash sql và treo website.
- Dựa trên `syslog`, thì:
	- Ngày 12/10, dung lượng ổ cứng: 55% *(`Oct 12 00:30:02 web-hcm-07 disk-check: OK / usage 55%`)*
	- Ngày 13/10, dung lượng ổ cứng: 56% *(`Oct 13 00:30:02 web-hcm-07 disk-check: OK / usage 56%`)*	
	- Ngày 14/10, dung lượng ổ cứng: 57% *(`Oct 14 00:30:02 web-hcm-07 disk-check: OK / usage 57%`)*
	- Ngày 15/10, dung lượng ổ cứng: 62% *(`Oct 15 00:30:02 web-hcm-07 disk-check: OK / usage 62%`)*	
	- Ngày 16/10, dung lượng ổ cứng: 67% *(`Oct 16 00:30:02 web-hcm-07 disk-check: OK / usage 67%`)*
	- Ngày 13/10, dung lượng ổ cứng: 72% *(`Oct 17 00:30:02 web-hcm-07 disk-check: OK / usage 72%`)*
	- Ngày 13/10, dung lượng ổ cứng: 77% *(`Oct 18 00:30:02 web-hcm-07 disk-check: OK / usage 77%`)*
	- Ngày 13/10, dung lượng ổ cứng: 82% *(`Oct 19 00:30:02 web-hcm-07 disk-check: WARN / usage 82%`)*
	- Ngày 13/10, dung lượng ổ cứng: 87% *(`Oct 20 00:30:02 web-hcm-07 disk-check: WARN / usage 87%`)*
- Tại sao lại đầy? Trong khi thấy vẫn đã có **remove** sau mỗi lần backup.
- Nhờ AI overview lại nội dung trong folder `phan1-su-co`. Có một số phát hiện nổi bật:
```
13/10 17:42
syslog: tài khoản hieunv dùng vim /etc/logrotate.d/nginx; 17:44 reload Nginx. Đây là thay đổi liên quan sớm nhất trong dữ liệu.

14/10 00:00
syslog: logrotate báo unknown option 'dailly' và skipping /var/log/nginx/*.log. Lỗi lặp lại mỗi ngày đến 20/10.
```
- Vậy nguyên nhân gốc rễ là do sai config.

### `phan2-proxmox`
- Phần này đưa yêu cầu và nhờ AI viết code để đọc file `json`.
- Kiểm chứng lại code trên môi trường linux:
```
python3 --version
python3 cluster_load.py cluster-pve-hcm-c3.json
python3 cluster_load.py cluster-pve-hcm-c3.json --format json | jq .
```

### Phần 3
Chọn đề A, và lúc này mình sẽ add thêm vài tiêu chí cá nhân khi lựa chọn công cụ:
```
Chi phí
Đối tượng/Mục tiêu
Vận hành
```



