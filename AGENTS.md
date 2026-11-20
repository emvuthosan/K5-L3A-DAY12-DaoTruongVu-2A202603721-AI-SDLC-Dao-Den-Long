# AGENTS.md — Đảo Đèn Lồng

Game 3D (web client) + mô phỏng tất định bằng Python stdlib. Không có phụ thuộc ngoài.

## Lệnh
- Chạy game: `python3 -m game.server` rồi mở http://localhost:8000
- Test: `python3 -m unittest discover -s tests -q` (phải xanh trước khi kết thúc việc)
- Bằng chứng: `python3 tests/run_proof.py` (ghi lại `docs/proof/phaseN/`)
- Headless: `python3 -m game.headless --seed 1 --night 1 --ticks 600 --out out.jsonl`

## Quy ước
- Mọi luật game nằm trong `game/sim.py` (không I/O, không đọc đồng hồ). Server và headless dùng chung `Sim`.
- Số liệu cân bằng chỉ ở `game.contract.json`; không hard-code lại trong code/test.
- Test Contract v1.0 là bắt buộc: 60 tick/s, làm tròn 3 chữ số, lỗi file đầu vào -> exit 2.
- Phần "sáng tạo" chỉ bật qua `Sim(extras=True)` (server), dùng RNG riêng; headless không bao giờ bật.
- Đổi luật => cập nhật test + `docs/notes/assumptions.md` cùng commit. Không tắt test âm thầm.
- Không commit `.env`/khóa. Không viết lại lịch sử sau khi gắn tag.
