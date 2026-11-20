# Spec Phase 4 — Ticket-04 "Bình minh: phát hành v1.0.0" (Contract v1.3)

Tiêu chí nghiệm thu (AC) và bằng chứng. Test: `tests/test_phase4.py`; số đo: `docs/proof/phase4/bench.json`, `soak.json`.

| # | Mục | Acceptance criteria | Bằng chứng |
|---|---|---|---|
| 1 | Benchmark | `python3 -m game.bench --seed 42 --duration 30 --out bench.json`: cảnh chuẩn (Đêm 1, 200 Bóng Mực wander rải đều, 100 đom đóm, L1–L3 sáng fuel 100, Mây đứng yên (0,0,0), camera quay (30,15,0) ngược chiều kim đồng hồ, 15 s/vòng, 1280×720, tắt vsync/giới hạn FPS); 3 s khởi động không đo rồi đo đúng `--duration`; tắt sinh thêm/sát thương/nhặt/hao dầu/kết thúc; xuất đủ các trường theo định nghĩa của ticket; thoát mã 0 | `BenchScene.*`, `BenchMetrics.test_definitions`, `bench.json` |
| 2 | Soak | `python3 -m game.soak --seed 7 --nights 10 --out soak.json`: 10 Đêm xoay vòng 1→2→3 trong một tiến trình, seed 7+i, input ngẫu nhiên theo seed (đổi hướng mỗi 30 tick; 5% nhảy, 3% lướt, 2% tỏa sáng, 10% tương tác); `crashes = 0`, `mem_end ≤ 1.2 × mem_start` | `Soak.test_runs_and_is_deterministic`, `soak.json` |
| 3 | Bảng xếp hạng | Nhập tên 3–12 ký tự `[A-Za-z0-9_]` (chữ Việt có dấu được chấp nhận) sau Bình Minh hoặc sau khi thua bất kỳ Đêm nào; lưu `name, score, nights_won, achieved_at (ISO 8601 + múi giờ), seed`; top 10, điểm giảm dần, bằng điểm thì ai đạt trước đứng trên; lưu trên đĩa, còn sau khi mở lại; màn Bảng xếp hạng ở menu; `--export-leaderboard out.json` ra `{"entries": [...]}` đúng thứ tự | `Leaderboard.*` |
| 4 | Đổi phím | Đủ 9 hành động (4 hướng, nhảy, lướt, tương tác, tỏa sáng, tạm dừng); báo trùng phím; "Khôi phục mặc định"; lưu | kiểm tay trong trình duyệt (xem proof) |
| 5 | Phụ đề/chỉ báo | Bóng Mực xuất hiện (chữ + mũi tên tím chỉ hướng ở mép màn hình), gió sắp thổi, 10 s cuối, đèn fuel < 30 (chữ cảnh báo) | `main.js` (`timedCues`, `edgeArrow`), kiểm tay |
| 6 | Giảm chuyển động | Tắt rung camera và chớp màn hình khi bật | `main.js` (`settings.rm`) |
| 7 | Cỡ chữ | Mọi chữ UI ≥ 18 px ở 1280×720 (`1rem = 18px`); "Chữ lớn" ×1.25 | đo bằng JS trong trình duyệt (xem proof) |
| 8 | Đóng gói | Clone sạch → 2 lệnh → chơi được; README đủ mục; CHANGELOG 4 phase; CREDITS; LICENSE; bản phát hành chạy được | README, `dist/` (zip), CHANGELOG |
| 9 | Contract v1.3 | `contract_version "1.3"`, `bench_cmd`, `soak_cmd`; mọi yêu cầu v1.0–v1.2 giữ nguyên | `Contract13.test_version_and_commands`, toàn bộ test cũ |
| 10 | Retro | 1–2 trang tổng hợp 4 phase | `docs/notes/retro.md` |
| 11 | Video demo | `.mp4` < 5 phút | **chưa làm** (xem `docs/demo/DEMO.md`) |
