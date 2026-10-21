# Demo chuẩn bị môi trường: lệnh và giải thích

Hướng dẫn chạy lại các kiểm tra trong recording **20/10/2026**, theo thứ tự của [session log](../docs/screenshots/00-environment-setup/vmware-2026-10-20/logs/session-readable.txt). Mỗi khối lệnh đi kèm mục đích và kết quả cần quan sát. Đây là demo **setup môi trường**, chưa phải bốn workload chính của seminar.

Chạy trong Bash trên VM Ubuntu Server dành cho seminar, bằng tài khoản có sudo, từ thư mục gốc repo. Repo đã clone theo [commands.md](commands.md#1-cài-đặt-lần-đầu). Dùng một terminal xuyên suốt để giữ các biến; chỉ thực hiện khi các instance demo chưa được dùng để đo bài khác. Mốc video dưới đây là gần đúng, dựa trên [chỉ mục recording](../docs/screenshots/00-environment-setup/vmware-2026-10-20/README.md#recording).

## 1. Chuẩn bị lưu log

Tạo thư mục log riêng ngoài repo để không ghi đè minh chứng cũ. Đây là bước chuẩn bị trước nội dung demo.

```bash
export EVIDENCE="$(mktemp -d "$HOME/redis-setup-XXXXXX")"
printf 'Evidence directory: %s\n' "$EVIDENCE"
script -q -f -c bash "$EVIDENCE/session.txt"
```

`script` mở một Bash con để lưu lệnh và output vào `session.txt`; biến `EVIDENCE` đã được export nên vẫn dùng được trong shell này. Tiếp tục các bước dưới đây trong shell vừa mở.

```bash
set -o pipefail
```

`pipefail` giúp nhận biết lỗi của lệnh đứng trước `tee`, công cụ vừa hiển thị output vừa ghi log. Sau mỗi bước, nếu exit code khác `0` hoặc output không đúng kỳ vọng thì xử lý lỗi trước khi tiếp tục; xem [troubleshooting.md](troubleshooting.md).

## 2. Giới thiệu VM và phiên bản repo

**Video: khoảng 00:00–00:25.** Chụp settings VMware riêng để thể hiện allocation RAM/CPU; lệnh trong guest chỉ cho biết tài nguyên mà Ubuntu nhìn thấy.

```bash
date -Is
cat /etc/os-release
uname -r
free -h
git branch --show-current
git rev-parse HEAD
```

Các lệnh lần lượt hiển thị thời gian, hệ điều hành, kernel, RAM/swap, branch và commit. Recording dùng thêm `fastfetch` để trình bày thông tin máy; công cụ đó không bắt buộc vì các lệnh chuẩn ở trên cung cấp thông tin cần thiết. Giữ phiên bản thực tế của lần chạy, không sao chép số phiên bản từ minh chứng cũ.

## 3. Chạy setup và kiểm tra service mặc định

**Video: từ phần cài đặt đến khoảng 02:50.** Setup cài Redis, Python/venv, tạo thư mục dữ liệu và bật Redis mặc định ở port 6379.

```bash
sudo bash linux/setup.sh 2>&1 | tee "$EVIDENCE/setup.txt"
echo "SETUP_EXIT=$?"
```

`2>&1` đưa cả output lỗi vào log. Chờ lệnh hoàn tất; kỳ vọng cuối setup có `PONG`, phiên bản Redis/Python và `SETUP_EXIT=0`. Không chạy setup chồng lên một lượt cài đặt chưa kết thúc.

```bash
dpkg-query -W redis-server redis-tools python3
systemctl is-enabled redis-server
systemctl is-active redis-server
systemctl status redis-server --no-pager -l
redis-cli -e -p 6379 PING
```

`dpkg-query` hiển thị phiên bản gói đã cài; hai lệnh tiếp theo cần trả `enabled` và `active`. `status` cho biết trạng thái service, còn `PING` cần trả `PONG`. Đây mới là service mặc định, chưa phải các instance demo.

## 4. Khởi động năm instance và chạy checker

**Video: phần chuẩn bị trước checker, đến khoảng 04:10.** Kiểm tra cú pháp hai script và xem các port demo có đang được dùng không:

```bash
bash -n linux/setup.sh && bash -n linux/check.sh
echo "SHELL_SYNTAX_EXIT=$?"
sudo ss -lntp | grep -E ':638[0-4]\b'
```

Kỳ vọng syntax exit `0`. Lệnh xem port có thể không in gì nếu chưa có instance. Nếu đã có process ở 6380–6384, xác định nó trước khi start thêm. Hai script được kiểm tra riêng; trong session cũ, lệnh `bash -n script1 script2` chỉ kiểm tra script đầu.

Khởi động các instance ở chế độ nền để tiếp tục thao tác trong cùng terminal, theo cách dùng trong recording:

```bash
for demo in rdb aof eviction data-structures cache-aside; do
  redis-server "redis/redis-$demo.conf" \
    --daemonize yes \
    --logfile "/tmp/redis-seminar/$demo/server.log"
done
```

Mỗi instance đọc file config riêng và ghi log vào thư mục riêng. Chờ các server sẵn sàng nhận kết nối:

```bash
for port in 6380 6381 6382 6383 6384; do
  echo "Waiting for port $port"
  for attempt in {1..20}; do
    redis-cli -e -p "$port" PING && break
    sleep 0.5
  done
done
```

Phải thấy `PONG` cho cả năm port; nếu port nào không trả lời thì dừng tại đây để kiểm tra. Sau đó chạy checker chỉ đọc:

```bash
bash linux/check.sh 2>&1 | tee "$EVIDENCE/check.txt"
echo "CHECK_EXIT=$?"
```

Kỳ vọng cuối output có `PASS` và `CHECK_EXIT=0`. Checker kiểm tra cả service 6379, năm instance demo và các giá trị cấu hình chung. Đối chiếu [ảnh port](../docs/screenshots/00-environment-setup/vmware-2026-10-20/screenshots/05-ports.png) và [ảnh checker](../docs/screenshots/00-environment-setup/vmware-2026-10-20/screenshots/06-config-pass.png).

## 5. Chứng minh cách ly và key hết hạn

**Video: khoảng 04:10–05:15.** Tạo một key thử có tên riêng để tránh trùng dữ liệu, đặt thời hạn tồn tại 5 giây trên port 6383:

```bash
probe="env:vmcheck:$(date +%s):$$"
echo "Probe key: $probe"
redis-cli -e -p 6383 SET "$probe" vm-test EX 5
redis-cli -p 6383 GET "$probe"
redis-cli -p 6384 EXISTS "$probe"
redis-cli -p 6383 TTL "$probe"
sleep 6
redis-cli -p 6383 EXISTS "$probe"
redis-cli -p 6383 TTL "$probe"
```

`SET` cần trả `OK`, `GET` trên 6383 trả `vm-test`. `EXISTS` trên 6384 trả `0`, chứng minh key không được dùng chung giữa hai instance. `TTL` là số giây còn lại trước khi key hết hạn: ban đầu tối đa 5, sau chờ 6 giây thì `EXISTS=0` và `TTL=-2` (key không tồn tại). Chạy liên tiếp khối lệnh để quan sát được key trước khi hết hạn. Đối chiếu [ảnh cách ly/TTL](../docs/screenshots/00-environment-setup/vmware-2026-10-20/screenshots/07-isolation-ttl.png).

## 6. Kiểm tra dữ liệu sau khởi động lại bình thường

**Video: khoảng 05:15–06:45.** Port 6380 lưu bản dữ liệu RDB bằng lệnh `SAVE`; port 6381 ghi thay đổi vào nhật ký AOF; port 6383 tắt lưu dữ liệu xuống đĩa. Ghi cùng một key vào ba instance:

```bash
persist_probe="env:restart:$(date +%s):$$"
echo "Restart probe: $persist_probe"
redis-cli -e -p 6380 SET "$persist_probe" rdb-ok
redis-cli -e -p 6380 SAVE
redis-cli -e -p 6381 SET "$persist_probe" aof-ok
redis-cli -e -p 6383 SET "$persist_probe" temporary
```

Kỳ vọng bốn lệnh Redis trả `OK`. Dừng bình thường cả ba instance:

```bash
redis-cli -e -p 6380 SHUTDOWN
redis-cli -e -p 6381 SHUTDOWN
redis-cli -e -p 6383 SHUTDOWN
```

`SHUTDOWN` kết thúc server và có thể không in output khi thành công. Khởi động lại bằng đúng các config cũ, rồi chờ kết nối:

```bash
for demo in rdb aof data-structures; do
  redis-server "redis/redis-$demo.conf" \
    --daemonize yes \
    --logfile "/tmp/redis-seminar/$demo/server.log"
done

for port in 6380 6381 6383; do
  for attempt in {1..20}; do
    redis-cli -e -p "$port" PING && break
    sleep 0.5
  done
done
```

Khi cả ba port trả `PONG`, đọc lại dữ liệu:

```bash
redis-cli -p 6380 GET "$persist_probe"
redis-cli -p 6381 GET "$persist_probe"
redis-cli -p 6383 EXISTS "$persist_probe"
```

Kỳ vọng lần lượt `rdb-ok`, `aof-ok`, `0`. Hai instance có lưu đĩa nạp lại key, còn 6383 không giữ key sau restart. Đây là **normal restart**, không phải thử nghiệm crash hay mất điện. Đối chiếu [ảnh restart](../docs/screenshots/00-environment-setup/vmware-2026-10-20/screenshots/08-normal-restart.png) và session log để xem output sau đó.

Xóa riêng key thử; lưu lại RDB sau khi xóa để key không quay lại từ bản cũ:

```bash
redis-cli -e -p 6380 DEL "$persist_probe"
redis-cli -e -p 6380 SAVE
redis-cli -e -p 6381 DEL "$persist_probe"
```

Kỳ vọng `1`, `OK`, `1`. Không cần xóa toàn bộ dữ liệu của instance.

## 7. Kiểm tra Python và kiểm tra môi trường lần cuối

**Video: từ khoảng 06:45.** Tạo môi trường Python riêng cho dependency ứng dụng và kiểm tra interpreter/pip:

```bash
python3 -m venv .venv
echo "VENV_EXIT=$?"
.venv/bin/python --version
.venv/bin/python -m pip --version
```

Kỳ vọng `VENV_EXIT=0` cùng phiên bản Python/pip. Bước này chưa cài dependency hoặc chạy ứng dụng của từng demo.

```bash
bash linux/check.sh 2>&1 | tee "$EVIDENCE/check-final.txt"
echo "FINAL_CHECK_EXIT=$?"
free -h
```

Kỳ vọng `PASS`, `FINAL_CHECK_EXIT=0`; `free -h` ghi lại RAM/swap ở cuối lượt kiểm tra.

## 8. Thu log và kết thúc

**Video: phần cuối, đến khoảng 08:27.** Lưu log service, kernel và các instance trước khi dừng server:

```bash
sudo journalctl -u redis-server -b --no-pager \
  > "$EVIDENCE/redis-service.txt"
sudo journalctl -k -b --no-pager \
  > "$EVIDENCE/kernel.txt"
mkdir -p "$EVIDENCE/instance-logs"
for demo in rdb aof eviction data-structures cache-aside; do
  cp "/tmp/redis-seminar/$demo/server.log" \
    "$EVIDENCE/instance-logs/$demo.log"
done
```

Dừng năm instance demo; giữ service mặc định 6379:

```bash
for port in 6380 6381 6382 6383 6384; do
  redis-cli -e -p "$port" SHUTDOWN
done
exit
```

`exit` đóng shell do `script` mở và hoàn tất `session.txt`. Có thể dùng `ss -lnt | grep -E ':638[0-4]\b'` để xác nhận không còn port demo lắng nghe; bước xác nhận này bổ sung cho lần chạy lại, chưa có trong session gốc.

Thư mục `$EVIDENCE` chứa log của lượt chạy mới. Minh chứng đã review của recording nằm trong [docs/screenshots/00-environment-setup/](../docs/screenshots/00-environment-setup/README.md); không ghi đè log/ảnh cũ. Chuỗi lệnh ở đây đã bỏ phần input lặp do terminal echo, không thay đổi bản session gốc.
