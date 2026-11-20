---
name: verify
description: Chạy kiểm chứng đầy đủ (unit test + scenario headless + tính tất định) và lưu bằng chứng vào docs/proof. Dùng sau mỗi thay đổi luật game, trước khi gắn tag phase.
---

1. `python3 -m unittest discover -s tests -q` — phải xanh.
2. `python3 tests/run_proof.py` — in PASS/FAIL, ghi jsonl vào `docs/proof/phase1/`.
3. Cập nhật bảng truy vết trong `docs/proof/README.md` (yêu cầu -> bằng chứng -> kết quả). Yêu cầu chưa đạt ghi "chưa đạt" + lý do.
4. Không sửa tay file output. Nếu test đỏ do luật mới, sửa test kèm lý do trong `docs/notes/`.
