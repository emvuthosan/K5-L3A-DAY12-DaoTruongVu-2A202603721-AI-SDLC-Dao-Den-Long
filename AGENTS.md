# AGENTS.md — Đảo Đèn Lồng

Game 3D (web client, three.js) + mô phỏng tất định bằng Python stdlib. Không có phụ thuộc ngoài. Đang ở Phase 4 / v1.0.0 (Contract v1.3: benchmark, soak, bảng xếp hạng, đổi phím).

## Lệnh
- Chạy game: `python3 -m game.server` rồi mở http://localhost:8000 (`--night 2` để thử Đêm khác)
- Test: `python3 -m unittest discover -s tests -q` (phải xanh trước khi kết thúc việc)
- Bằng chứng: `python3 tests/run_proof.py` (chạy 20 scenario + tính tất định + đo Đêm dài nhất, ghi `docs/proof/phase3/`)
- Benchmark: `python3 -m game.bench --seed 42 --duration 30 --out bench.json` (cần Chrome/Chromium/Edge; mở cửa sổ thật)
- Soak: `python3 -m game.soak --seed 7 --nights 10 --out soak.json`
- Xuất bảng xếp hạng: `python3 -m game.server --export-leaderboard out.json`
- Headless: `python3 -m game.headless --seed 1 --night 1|2|3 --ticks 600 --out out.jsonl [--scenario f --inputs f]`

## Quy ước
- Mọi luật nằm trong `game/sim.py` (không I/O, không đồng hồ). Server và headless dùng chung `Sim`; client chỉ vẽ và gửi input.
- Số liệu chuẩn chỉ ở `game.contract.json`; không hard-code lại trong test (đọc từ contract) trừ khi test kiểm đúng số chuẩn của ticket.
- Thứ tự xử lý trong một tick theo ticket (xem docstring `Sim.step`). Đổi thứ tự = đổi hành vi, phải có test.
- Đèn: dầu là **số nguyên đơn vị 1/60** (`fu`); vùng an toàn luôn hỏi `Sim._zone(l)` (lit và fuel ≥ 30), không hỏi `l["lit"]`. Không có thắng sớm: thắng/thua chỉ ở bước 11 (xem ADR-0003).
- Góc: `x = r cos a`, `z = r sin a`. Bộ đếm giảm ở bước 2 của tick sau khi đặt (xem assumptions #19).
- Mỗi tính năng ngẫu nhiên dùng luồng RNG riêng (`r_mote`, `r_shade`, `r_drift`, `r_wind`, `r_drop`, `r_x`): bật/tắt một tính năng không được làm đổi đầu ra tính năng khác.
- Cảnh benchmark/soak: `Sim(bench=True)` và `extras=False`; không thêm gì vào cảnh đó. Bảng xếp hạng ở `data/` (đã gitignore), đổi chỗ bằng `DDL_DATA_DIR`.
- Phần "sáng tạo" chỉ bật qua `Sim(extras=True)` (server). Headless không bao giờ bật; đầu ra headless không được đổi.
- Test Contract: 60 tick/s, làm tròn 3 chữ số, file đầu vào hỏng -> exit 2, một Đêm đầy đủ headless ≤ 30 s.
- Đổi luật => cập nhật test + `docs/notes/assumptions.md` (+ spec phase) cùng commit. Không tắt test âm thầm.
- Không commit `.env`/khóa. Không viết lại lịch sử sau khi gắn tag. Không push khi chưa được phép.
