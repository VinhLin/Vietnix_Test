## Vị trí "R&D Engineer (Infrastructure & Automation)" tại "CÔNG TY CỔ PHẦN GIẢI PHÁP VÀ CÔNG NGHỆ VIETNIX"
- Ngày 16/10/2026 nộp CV qua ứng dụng TopCV *(Quên lưu lại cái JD cho vị trí này)*.
- Ngày 29/10/2026, nhận được bài thi đợt 2.
- Hôm nay ngày 12/11/2026, kết quả fail, với lý do **chưa phù hợp với tiêu chí chuyên môn và định hướng hiện tại của đội ngũ**.
- Dẫu sao cũng có nhiều cái hay ho, mình sẽ note lại vài điểm.

## Nhận xét đề
- Đề cũng không quá khó, lúc đọc câu 1 và đọc log là đã tạm có kết luận nguyên nhân của vấn đề rồi. **Tại sao chỉ đọc log và biết nguyên nhân?**
> *Vì mình đã từng bị vấn đề tương tự, hệ thống SIEM của mình nhận quá nhiều log, service vẫn chạy, nhưng app lại crash.* </br>
> *Mất cả buổi debug mới biết nguyên nhân là do **đầy ổ cứng**, xóa bớt log và restart lại là xong* </br>

- Sau đó mình thử đưa nguyên cái đề này cho OpenClaw giải thử, mục tiêu là có một góc nhìn khác xem về cách giải quyết vấn đề. 
- Nó mất chưa đến nửa tiếng là giải xong *(thư mục `OpenClaw_Process` là kết quả xử lý của OpenClaw)*
- Mình phải kiểm tra lại và mất hơn **5 tiếng** để biên soạn lại, cũng như trình bày lại.

### Học được gì từ Câu 1?
- Đọc file readme của Claw, mình ngạc nhiên. Nó tìm đc nguyên nhân gốc rể của vấn đề luôn.
- **File config bị sai, nên dẫn đến tình trạng bị đầy ổ cứng** *(Mình có thử nhờ Gemini kiểm chứng lại file config, kết quả nó cũng báo là config bị sai)*. Quá hay
- Tuy nhiên khi đọc đến phần giải pháp của nó, thì mình thấy **quá rườm rà, đi hơi xa**.
- Để xử lý nhanh thì chỉ cần sửa file script, cho xóa bớt dung lượng ổ đĩa là xong.
- Hơn nữa, còn 1 điều mà mình học được từ câu 1 này, đó là **trình tự và cú pháp kiểm tra** khi xảy ra sự cố. Thật sự rất hữu ích.

### Học được gì từ Câu 2?
- Phần này thì con AI nó làm gần hết, vả lại hệ thống mình đang dùng là **ESXi free**, chứ không phải Proxmox.
- Mình thì dùng Zabbix để monitor con ESXi này, không biết là hệ thống họ dùng gì để monitor con Proxmox?
> *Zabbix thì mình có thể lấy được tất cả các VM trong ESXi, nhưng mình chưa biết cách export ra file `json` giống trong đề. Để nào có time chắc cũng ngâm cứu thử* </br>

### Học được gì từ Câu 3?
**Đề B**:
- Có vẻ hơi chua, vả lại mình cũng chưa hiểu lắm cách ngăn chặn.
- Mình thì cũng có public một trang web **HTTP/80**, cũng bị scan nhiều á. Nhưng giải pháp của mình là build một **WAF**
- Mặc dù là open-source, nhưng mà nó cũng giúp mình chặn được kha khá thứ, như **HTTP Flood**, **các IP độc hại**,...

**Đề A**:
- Con Claw làm xong đề A rồi, nhưng khi đọc vào mình thấy có vẻ không ổn lắm, mình đọc vào cũng không hiểu hết =]]
- Thế là phải đi tra lại các thông tin, đưa nhận định và **góc nhìn cá nhân** *(với tư cách là một người đã từng làm R&D về sản phẩm phần cứng)*. Mất khá nhiều thời gian.
- Một lý do nữa mà mình chọn đề A, là vì mình đã build MinIO trên hạ tầng của mình, và có ứng dụng nó cho giao thức **File Transfer over MQTT**.
- Có một điều khá thú vị mình học được là **benchmark**, trước giờ mình chưa từng nghĩ đến việc đo *benchmark cho MinIO*.
- Tận dụng cơ hội này, mình tiến hành cài công cụ **warp** để test thử.
> *Test xong mới biết, con MinIO mình build đang bị nghẽn về mặt phần cứng. Thì cũng đúng, do mình dùng **HDD** để chứa VM mà.* </br>
> *Đo benchmark của MinIO đúng là ý tưởng hay để mình biết vấn đề hạ tầng của bản thân nằm ở đâu* </br>

## Thú vị
- Đây là một trải nghiệm thú vị.
- Mong là mình sẽ gặp được những bài test thú vị như vậy. =]]
