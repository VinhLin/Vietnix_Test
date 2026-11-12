# Đề A — Object Storage S3 50 TB: MinIO hay Ceph RGW?

## Bài toán và giả định

Đề bài yêu cầu dịch vụ S3 cho khách doanh nghiệp, khoảng 50 TB dữ liệu, ban đầu 3–4 server và chịu lỗi tối thiểu một server. Chưa có số liệu về tăng trưởng, kích thước object, IOPS/throughput, RPO/RTO, loại ổ đĩa, mạng hay ngân sách; vì vậy khuyến nghị dưới đây là thiết kế khởi điểm để thử nghiệm, không phải sizing cuối cùng. “50 TB” được tính là dung lượng dữ liệu logic trước phiên bản, metadata và vùng trống vận hành.

## So sánh cho quy mô này

| Tiêu chí | MinIO | Ceph RGW |
|---|---|---|
| Vai trò | Object Storage phân tán, cung cấp API S3 trực tiếp; cấu hình và vận hành tập trung vào object storage. | RGW cung cấp object gateway S3 trên cụm Ceph; cùng nền Ceph có thể phục vụ thêm block/file tùy cấu hình. |
| Dung lượng và chịu lỗi | Erasure coding chia object thành data/parity shards. Tài liệu MinIO minh họa 4 node × 4 drive (16 shards), EC:4: một node mất làm còn 12 drive, đúng ngưỡng quorum để đọc/ghi. | Có thể dùng pool replicated hoặc erasure-coded. Nếu chọn replication size=3 để chịu mất một host, 50 TB logic cần khoảng 150 TB raw trước dự phòng; EC có thể tiết kiệm raw nhưng phải thiết kế failure domain và pool phù hợp. |
| Độ phức tạp | Ít thành phần hơn cho một cụm chỉ làm object storage; topology erasure set cần được quyết định từ đầu. | Nhiều khái niệm/vai trò hơn (MON, OSD, RGW, placement/pools); linh hoạt và phù hợp khi đã có năng lực vận hành Ceph hoặc cần một nền tảng storage đa giao thức. |
| Rủi ro chính | Khi mất một trong bốn node ở cấu hình EC:4/16 drive, cụm vừa đủ 12 shard quorum, không còn dư địa cho một drive lỗi khác trước khi heal xong. Phải giám sát healing, thay ổ nhanh và thử failure thực tế. | Replication size=3 tốn raw capacity; EC giảm overhead nhưng làm thiết kế, vận hành và khôi phục phức tạp hơn. Không nên coi số lượng daemon là thay thế cho failure-domain placement đúng theo host/rack. |

## Khuyến nghị

Với yêu cầu hiện tại, chọn **MinIO trên 4 server đồng cấu hình**, mỗi server có 4 drive dữ liệu tương đương, triển khai một topology 16-drive với EC:4; đặt mỗi nhóm shard/failure domain sao cho mất trọn một server vẫn còn 12 drive khả dụng. Tài liệu chính thức dùng chính topology này làm ví dụ: với EC:4, 12 drive là ngưỡng K để đọc và ghi, nên mất một node vẫn đạt quorum. Đây là mức tối thiểu theo đề, không phải thiết kế có thêm một host dự phòng.

Ước tính raw cho EC:4 trên 16 drive: hiệu suất dung lượng lý thuyết là 12/16 = 75%; do đó 50 TB logic cần khoảng **66.7 TB raw**. Nếu giữ thêm 20% raw làm headroom cho tăng trưởng/healing, nên dự trù xấp xỉ **83.3 TB raw** (66.7/0.8), chưa tính filesystem, metadata, versioning và khác biệt TB/TiB. Đây là phép tính từ tỷ lệ EC, không phải benchmark hay sizing đã kiểm chứng. Xác minh capacity usable trên đúng phiên bản/phần cứng trước khi chốt mua sắm.

Chọn **Ceph RGW** thay vào đó nếu Vietnix đã vận hành Ceph thành thạo, cần chung nền tảng với RBD/CephFS, hoặc muốn kiểm soát sâu placement và pool. Một phương án dễ hiểu để ước lượng là replicated size=3: khoảng 150 TB raw cho 50 TB logic, cộng headroom. EC có thể giảm con số này nhưng cần thử nghiệm placement, failure domain, hiệu năng và quy trình phục hồi; không nên quyết định chỉ từ tỷ lệ lưu trữ.

Trước production, cần POC trên đúng loại ổ/NIC và object-size mix; thử mất một server, mất thêm một drive khi đang degraded, khôi phục server/drive, node reboot, rebalance/heal và nâng cấp; đo throughput/latency khi bình thường lẫn degraded; kiểm thử tải đồng thời, IAM/TLS, versioning, backup/replication và cảnh báo. Chốt SLA, RPO/RTO, tăng trưởng 3 năm, spare-drive policy và năng lực on-call rồi mới khóa sizing. Không có benchmark Vietnix trong dữ liệu đầu bài nên báo cáo không tuyên bố hệ nào nhanh hơn.

## Nguồn chính thức

1. MinIO, [Erasure Coding](https://minio.community/community/minio-object-store/operations/concepts/erasure-coding.html) — topology 4×4, EC:4, read/write quorum, giới hạn thay đổi erasure set sau khi khởi tạo.
2. Ceph, [Ceph Object Gateway (RGW) service](https://docs.ceph.com/en/latest/cephadm/services/rgw/) — triển khai và quản lý RGW trong cụm Ceph.
3. Ceph, [Erasure code](https://docs.ceph.com/en/latest/rados/operations/erasure-code/) — so sánh cơ chế replicated và erasure-coded pools.
4. Ceph, [Monitor configuration reference](https://docs.ceph.com/en/squid/rados/configuration/mon-config-ref/) — monitor quorum cần đa số; dùng để lưu ý HA control-plane, không thay thế thiết kế chịu lỗi của dữ liệu.

Thông tin cấu hình và khả năng được đối chiếu theo tài liệu trên; các phép tính dung lượng được nêu rõ là ước tính. Chưa có POC, benchmark hoặc kiểm chứng failure trên phần cứng mục tiêu.
