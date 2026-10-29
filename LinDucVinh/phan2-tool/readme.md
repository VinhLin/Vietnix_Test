# Proxmox cluster load analyzer

CLI Python chỉ đọc snapshot JSON, tính tải mỗi node, báo dữ liệu lỗi và đề xuất các VM move có thể chứng minh an toàn theo ngưỡng. Tool **không** kết nối Proxmox, không phát lệnh migrate.

## Yêu cầu / chạy

- Python 3.10+; không cần package ngoài.
- Bảng terminal (mặc định):

```powershell
python .\cluster_load.py .\cluster-pve-hcm-c3.json
```

- JSON chuẩn cho pipe:

```powershell
python .\cluster_load.py .\cluster-pve-hcm-c3.json --format json | ConvertFrom-Json
```

- Test logic cốt lõi:

```powershell
python -m unittest discover -s .\tests -v
```

JSON lỗi/không đọc được trả exit code 2 và thông báo stderr; record thiếu trường/không hợp lệ được bỏ hoặc đánh dấu `unknown` kèm warning theo record, không crash.

## Công thức và giả định

- **CPU used (cores)** = tổng `vcpus × cpu_usage` của VM `running`. `cpu_usage` phải thuộc [0,1] theo đề; giá trị như `31.0` không tự suy luận là 31% mà làm CPU của node thành `unknown`.
- **RAM** = tổng `mem_used` của VM `running` / `nodes[].mem_total`. RAM unknown nếu có record không hợp lệ.
- **vCPU overcommit** = tổng vCPU cấp cho VM `running` / physical `cpu_cores`. VM stopped không tính.
- Ngưỡng mặc định: CPU >80%, RAM >85%, overcommit >2.5 vCPU/core. Chọn ngưỡng này để giữ headroom; chỉnh bằng CLI theo SLA/capacity policy của operator.
- Node offline không làm target. Node có dữ liệu capacity chưa đầy đủ không được dùng làm source hoặc target của plan. Các VM trùng `vmid` chỉ lấy bản ghi đầu; VM trỏ node chưa khai báo bị loại và cảnh báo.
- `mem_total <1 GiB` được đánh dấu implausible cho snapshot cluster máy chủ và metric RAM thành unknown. Đây là heuristic để tránh ra quyết định dựa trên field hỏng, không phải giới hạn phần cứng của Proxmox.
- Mỗi bước move phải làm giảm mức quá tải của node nguồn; node đích không được vượt ngưỡng sau move. Có thể cần nhiều bước để đưa nguồn xuống ngưỡng. `migration_complete=false` nếu còn node online overload hoặc chưa đủ dữ liệu. Hãy xác nhận storage compatibility, affinity/HA rules, bandwidth, migration window và tải live trước khi thực thi.

## Ví dụ output snapshot kèm theo

```text
NODE        CPU used         RAM used  vCPU/core  VMs  STATE
----------  ---------------  --------  ---------  ---  ----------
hcm-c3-n01  47.9/64 (74.9%)  81.7%     1.59x      13   normal
hcm-c3-n02  unknown          55.0%     1.25x      13   unknown
hcm-c3-n03  25.3/48 (52.7%)  62.0%     1.83x      12   normal
hcm-c3-n04  0.0/48 (0.0%)    0.0%      0.00x      0    offline
hcm-c3-n05  50.5/64 (78.9%)  unknown   1.12x      12   unknown
hcm-c3-n06  9.6/32 (30.0%)   unknown   2.94x      12   overloaded

Migration suggestions (not executed):
  status: partial / blocked by unresolved node data or overload
  VM 2008 db-ent-415: hcm-c3-n01 -> hcm-c3-n03 (source after CPU 74.9%, RAM 81.7%)
Overloaded: hcm-c3-n06
Unresolved online nodes: hcm-c3-n02, hcm-c3-n05, hcm-c3-n06
```

Snapshot validation found: CPU values `31.0`, `98.0`, `20.8` outside [0,1] on n02; missing `mem_used` on n05; `mem_total=262144` bytes on n06; duplicate VMID 2001; and VM 2390 on undeclared n07. Consequently the tool proposes the valid n01→n03 move, but does **not** claim the whole cluster is balanced: n06 is >2.5 vCPU/core and capacity data is unreliable; n02/n05 remain unknown. Correct/export fresh snapshot data before considering further migrations.
