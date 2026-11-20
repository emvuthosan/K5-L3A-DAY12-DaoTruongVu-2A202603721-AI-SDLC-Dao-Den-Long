---
name: verify
description: Chạy kiểm chứng đầy đủ (unit test + 20 scenario headless + tính tất định 3 Đêm + đo thời gian 1 Đêm) và lưu bằng chứng vào docs/proof. Dùng sau mỗi thay đổi luật game, trước khi gắn tag phase.
---

1. `python3 -m unittest discover -s tests -q` — phải xanh.
2. `python3 tests/run_proof.py` — in PASS/FAIL cho từng scenario (fuel_out_relight, refuel, drain, dawn_win/lose, capacity, dash, pause, fall, tiers_ramp, pad_night2/3, wind, charm, drifter_*, pulse, safe_zone, win/lose), tính tất định cả 3 Đêm và thời gian Đêm dài nhất 18.000 tick (≤ 30 s). Ghi jsonl vào `docs/proof/phase3/`.
3. Cập nhật bảng truy vết trong `docs/proof/README.md` (yêu cầu -> bằng chứng -> kết quả). Yêu cầu chưa đạt/chưa kiểm ghi "chưa đạt/chưa kiểm" + lý do.
4. Với thay đổi giao diện: chạy `python3 -m game.server --night N`, mở trình duyệt, chụp ảnh, kiểm console không lỗi.
5. Không sửa tay file output. Nếu test đỏ do luật mới, sửa test kèm lý do trong `docs/notes/`.
