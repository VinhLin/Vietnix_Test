# Postmortem: web-hcm-07 trả 502/504 ngày 20/10/2026

## 1. Tóm tắt sự cố

Từ 01:33 ngày 20/10, nhiều website trên `web-hcm-07` bắt đầu trả 502/504; access log của load balancer ghi nhận 2.775 lỗi 502/504 trên 4.718 request trong khung 00:50–02:25. Nguyên nhân gốc là log Nginx không được rotate từ sau lần sửa cấu hình ngày 13/10 (`dailly` sai chính tả), làm `access.log` phình tới 37 GB; backup hằng đêm lại ghi thêm vào cùng phân vùng `/` và giữ bản backup cũ cho đến khi backup mới thành công. Phân vùng hết chỗ lúc backup còn dang dở, khiến Nginx không ghi được log/body, MySQL không ghi được binary log, PHP không ghi được session và worker PHP-FPM cạn. Đây là sự cố dung lượng đĩa, không phải thiếu CPU/RAM; log hiện có chưa đủ chứng minh một cuộc tấn công là tác nhân khởi phát.

## 2. Timeline

| Thời điểm (+07) | Dấu hiệu / sự kiện |
|---|---|
| 13/10 17:42 | `syslog`: tài khoản `hieunv` dùng `vim /etc/logrotate.d/nginx`; 17:44 reload Nginx. Đây là thay đổi liên quan sớm nhất trong dữ liệu. |
| 14/10 00:00 | `syslog`: logrotate báo `unknown option 'dailly'` và `skipping` `/var/log/nginx/*.log`. Lỗi lặp lại mỗi ngày đến 20/10. |
| 14–18/10 | Disk-check tăng từ 57% lên 77%; log Nginx không được rotate. Backup ngày vẫn hoàn thành, kích thước tăng dần 17,6 → 18,8 GB. |
| 19/10 00:30 | Disk-check cảnh báo `/` dùng 82%. Backup 19,1 GB hoàn thành lúc 01:42. |
| 20/10 00:00 | Logrotate tiếp tục bỏ qua Nginx log. 00:30 disk-check cảnh báo `/` dùng 87%. |
| 20/10 01:00 | Script bắt đầu nén `/home` vào `/var/backups/sites-20261020.tar.gz` ngay trên phân vùng `/`; backup 19/10 còn nguyên cho đến khi lần chạy mới thành công. |
| 20/10 01:32:57–01:33:04 | `tar` ghi dở (chỉ 4.096/10.240 byte ở lần ghi cuối) rồi lỗi; MySQL báo `OS errno 28 - No space left on device`. Nginx lúc 01:32:59 lỗi `pwrite()` errno 28 và 01:33:01 không ghi được access log. |
| 20/10 01:33:05 | LB ghi nhận 504 đầu tiên (`rt=60.587s`); 01:33:09 ghi nhận 502 đầu tiên (`rt=0.002s`). Lỗi xuất hiện trên nhiều host. |
| 20/10 01:34 trở đi | PHP-FPM báo session không ghi được vì hết chỗ và `pm.max_children` đạt 50; MySQL lỗi kéo dài. LB tiếp tục ghi 502/504 đến hết cửa sổ log. |
| 20/10 02:21–02:23 | On-call SSH vào; `df -h` xác nhận `/dev/sda2` 118/118 GB, 0 khả dụng. Snapshot thấy Nginx `access.log` 37 GB, `error.log` 641 MB, backup cũ 19 GB và backup mới dở 16 GB. |

## 3. Nguyên nhân gốc và chuỗi hệ quả

1. **Logrotate Nginx bị hỏng:** `/etc/logrotate.d/nginx` (snapshot) có `dailly` ở dòng 3 thay vì `daily`. `syslog` ghi lỗi parser và bỏ qua toàn bộ `/var/log/nginx/*.log` từ 14/10. Vì thế access log không được luân chuyển; đến snapshot lúc 02:23 ngày 20/10, `access.log` là 37 GB và `error.log` 641 MB (`snapshot/du-var.txt`).
2. **Dung lượng không được cô lập:** `snapshot/backup-sites.sh` nén `/home` thẳng vào `/var/backups`, cùng filesystem `/`; chỉ xóa backup hôm trước sau khi backup mới thành công. Backup thường 17–19 GB. Ngày 20/10, `/` đã ở 87% trước giờ chạy backup, trong khi log Nginx vẫn tăng. Backup mới đạt 16 GB nhưng thất bại; file backup 19 GB hôm trước vẫn còn. Đây là yếu tố làm đầy đĩa nhanh hơn, trên nền log đã không được rotate và thiếu headroom.
3. **Filesystem đầy làm hỏng nhiều tầng cùng lúc:** log Nginx ghi lỗi `pwrite(.../var/lib/nginx/body/...) failed (28)` lúc 01:32:59 và không ghi được `access.log` lúc 01:33:01. MySQL ghi `Disk is full writing './binlog.000187' (errno 28)` từ 01:33:04. PHP-FPM lúc 01:33:06 không tạo được session vì `No space left on device`; sau đó pool đạt `pm.max_children=50`. Nginx không kết nối được socket PHP-FPM (`EAGAIN`) hoặc chờ upstream quá 60 giây, tạo 502/504.
4. **Phạm vi:** trong file LB có 4.718 request: 1.914 mã 200, 29 mã 404, 1.231 mã 502 và 1.544 mã 504. Lỗi xuất hiện trên cả `tintuc24h.net`, `noithatmoc.com`, `site42.vn`, `phongkhamanbinh.vn`, `shop.anhduongfood.vn`. Đây là ảnh hưởng diện rộng trên node shared hosting, không chỉ một website.

## 4. Giả thuyết đã loại trừ / chưa đủ bằng chứng

- **Thiếu CPU/RAM:** không phù hợp với snapshot. `top` lúc 02:23:53 báo CPU idle 94,9%, I/O wait 0,6%; `free -m` có 22.053 MiB available và swap dùng 12 MiB. Đây không loại trừ mọi vấn đề tải ứng dụng, nhưng không giải thích được errno 28.
- **MySQL hỏng là nguyên nhân gốc:** bị loại. MySQL báo không ghi được binlog vì filesystem đầy, sau khi backup và Nginx đã lỗi ghi. Các lỗi MySQL greeting sau đó là hệ quả làm request PHP kéo dài.
- **Bot/DDoS là nguyên nhân đã xác minh:** chưa đủ bằng chứng. LB có nhiều IP/UA và request đến nhiều host; dữ liệu này không đủ xác nhận danh tính crawler hoặc một đợt tấn công. Dù có traffic bất thường, nó không giải thích việc logrotate lỗi nhiều ngày và backup cùng filesystem.
- **Lỗi cấu hình Nginx/PHP upstream đơn thuần:** các lỗi upstream là triệu chứng sau khi hệ thống không còn ghi được file và PHP pool bão hòa; chưa có bằng chứng cấu hình upstream thay đổi trước đó.

## 5. Khắc phục tức thời tại 02:23

Mục tiêu là phục hồi dung lượng mà không xóa/sửa file website, database hay source của khách. Cần một volume cứu hộ riêng (không nằm trên `/`) còn ít nhất 40 GB; giữ nguyên bản backup dở 20/10 để điều tra. Trước tiên xác nhận mount cứu hộ là filesystem khác và đủ chỗ:

```bash
findmnt -T /mnt/incident
findmnt -T /
df -h / /mnt/incident
ls -lh /var/log/nginx/access.log /var/backups/sites-20261019.tar.gz /var/backups/sites-20261020.tar.gz
```

Nếu `/mnt/incident` là volume riêng, sao lưu access log ra đó trước; dừng Nginx trong lúc chụp để file không tiếp tục đổi. Chỉ giải phóng log cục bộ sau khi hai bản trùng hash. Backup dở vẫn được giữ nguyên tại `/var/backups`:

```bash
sudo systemctl stop nginx
sudo install -d -m 0700 /mnt/incident/web-hcm-07-20261020
sudo cp --sparse=always /var/log/nginx/access.log /mnt/incident/web-hcm-07-20261020/access.log
sudo sha256sum /var/log/nginx/access.log /mnt/incident/web-hcm-07-20261020/access.log
# Chỉ tiếp tục nếu hai SHA-256 giống nhau:
sudo truncate -s 0 /var/log/nginx/access.log
sudo chown www-data:adm /var/log/nginx/access.log
sudo chmod 0640 /var/log/nginx/access.log
sudo sed -i 's/^\s*dailly\s*$/\tdaily/' /etc/logrotate.d/nginx
sudo logrotate -d /etc/logrotate.conf
sudo nginx -t && sudo systemctl start nginx
sudo df -h /
sudo systemctl --no-pager --full status nginx php8.1-fpm mysql
```

Nếu không có volume cứu hộ, không đoán lệnh sửa partition khi chưa biết layout; ưu tiên mở rộng filesystem `/` theo hypervisor/storage runbook. Không xóa file nào trong `/home`, không xóa database/binlog, không xóa backup cũ/dở. Sau khi có headroom: kiểm tra MySQL ghi binlog trở lại, PHP-FPM còn worker, chạy health-check các vhost; ghi nhận khoảng log bị lưu ngoài volume; xác nhận lịch logrotate hôm sau tạo file rotated. Không tăng `pm.max_children` khi chưa đo memory-per-child và nguyên nhân slow query.

## 6. Phòng ngừa

- Sửa và kiểm tra cấu hình logrotate trong CI/config management (`logrotate -d`), cảnh báo khi job lỗi hoặc log active vượt ngưỡng; dùng `logrotate -f` chỉ trong bảo trì đã kiểm tra.
- Đưa backup ra filesystem/object storage riêng; tính retention và headroom trước khi chạy; dùng lock để ngăn overlap, kiểm checksum/restore định kỳ, không xóa bản gần nhất trước khi bản mới được xác minh.
- Giám sát dung lượng theo thời gian: cảnh báo ở 70/80/90%, theo dõi tốc độ tăng của `/var/log/nginx`, `/var/backups`, inode và free bytes; cảnh báo Zabbix hiện tại bị “not supported: Cannot write to log file” khi chính disk đầy, nên cần agent/alert path không phụ thuộc vào node đang lỗi.
- Thu thập log ra hệ thống ngoài node; giới hạn retention và bảo vệ dữ liệu log. Dashboard theo dõi 502/504, upstream latency, PHP-FPM active/max children, socket backlog, MySQL binlog write errors và disk I/O.
- Dùng rate-limit L7 theo endpoint/vhost và L4 baseline tại edge khi có bằng chứng traffic; triển khai dry-run/canary để tránh chặn nhầm crawler hoặc người dùng shared NAT. Rate-limit không thay thế capacity planning, log rotation hay backup isolation.

## Evidence được dùng

- `phan1-su-co/syslog`: thay đổi logrotate 13/10; lỗi `dailly` và disk-check; backup; errno 28; Zabbix mất khả năng ghi log.
- `phan1-su-co/snapshot/logrotate-nginx.conf`, `backup-sites.sh`, `df-h.txt`, `du-var.txt`, `free-m.txt`, `uptime-top.txt`, `ss-summary.txt`.
- `phan1-su-co/nginx/error.log`, `php/php8.1-fpm.log`, `mysql/error.log`.
- `phan1-su-co/lb/access-lb-hcm-01.log`: 4.718 dòng; thống kê mã HTTP nêu trên, thời gian đầu tiên 502/504 và các vhost bị ảnh hưởng.
