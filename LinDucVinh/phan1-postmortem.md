# Postmortem: web-hcm-07 trả 502/504 ngày 20/10/2026

## 1. Tóm tắt sự cố

Ngày 20/10 (khoảng 01:00), nhiều website trên `web-hcm-07` bắt đầu trả 502/504; access log của load balancer ghi nhận 2.775 lỗi 502/504 trên 4.718 request trong khung 00:50–02:25. 

Nguyên nhân gốc là do file cấu hình `logrotate-nginx.conf` *(`dailly` sai chính tả)*, khiến log tăng nhanh chóng làm đầy ổ cứng, dẫn đến crash database và sập web. 

Đây là sự cố dung lượng đĩa, không phải thiếu CPU/RAM; log hiện có chưa đủ chứng minh một cuộc tấn công là tác nhân khởi phát.

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
- Trong file `mysql/error.log`:
```
2026-10-14T03:00:12.551203+07:00 0 [Warning] [MY-010055] [Server] IP address '10.20.1.31' could not be resolved: Name or service not known
```
- Cái này là lỗi liên quan đến **DNS**, câu hỏi là **Có phải DNS-Server đang có vấn đề gì không?** -> Chưa có thông tin gì thêm
- Các dòng còn lại cho thấy ổ cứng bị full, tại sao lại full?
```
2026-10-20T01:33:04.118842+07:00 14 [ERROR] [MY-000035] [Server] Disk is full writing './binlog.000187' (OS errno 28 - No space left on device). Waiting for someone to free space... Retry in 60 secs. Further messages will be issued every 10 minutes.
```
- File `df -h.txt`, cũng cho thấy ổ `/dev/sda2` bị full.
- File `dmesg-tail.txt`, firewall UFW đã block IP `103.97.125.71`, check trên virustotal -> **IP sạch, có thể loại trừ trường hợp bị malware**.
- **Kết luận tạm thời:** Việc website bị sự cố có thể là do dung lượng ổ cứng đầy, là crash sql dẫn đến treo website.

## 5. Khắc phục tức thời tại 02:23

Mục tiêu là phục hồi dung lượng mà không xóa/sửa file website, database hay source của khách. Cần một volume cứu hộ riêng (không nằm trên `/`) còn ít nhất 40 GB; giữ nguyên bản backup dở 20/10 để điều tra. Trước tiên xác nhận mount cứu hộ là filesystem khác và đủ chỗ:

File script `backup-sites.sh`, chức năng của file này là back-up log và xóa log cũ của ngày hôm qua.

### Kiểm tra folder `/var/backups`
```
ls -lah /var/backups
```
- Tạo file script `clean_old_backup-sites.sh`, **xóa đi các file backup cũ hơn 3 ngày** để giải phóng nhanh dung lượng.
```
#!/bin/bash

set -o pipefail
DEST=/var/backups
TODAY=$(date +%Y%m%d)

logger -t backup-sites "start backup /home -> $DEST/sites-$TODAY.tar.gz"

if tar -czf "$DEST/sites-$TODAY.tar.gz" /home 2>&1 | logger -t backup-sites; then
    SIZE=$(du -h "$DEST/sites-$TODAY.tar.gz" | cut -f1)
    logger -t backup-sites "backup done size=$SIZE"
else
    logger -t backup-sites "ERROR backup failed exit=$?, keep old backups"
fi

# Clean old file backup (older 3 days)
find "$DEST" -name "sites-*.tar.gz" -mtime +3 -exec rm -f {} \; \
    && logger -t backup-sites "cleaned up backup files older than 3 days"
```
- Run:
```
cd /home
sudo chmod +x clean_old_backup-sites.sh
sudo ./clean_old_backup-sites.sh
```

## 6. Phòng ngừa

- Dùng Zabbix để monitor dung lượng ổ đĩa *(cái này hình như hệ thống đã có)*
- Đẩy syslog sang SIEM, và tạo rule khi có sự thay đổi về các file config trên host, notifi qua Telegram.
- Chạy thêm crontab file `clean_old_backup-sites.sh` để tránh bị đầy dung lượng.
