# Bằng chứng kiểm chứng

> Phase 1 (tag `phase-1`) dùng Contract v1.0 và số liệu cũ; phần Phase 1 bên dưới mô tả bản ở tag đó, `docs/proof/phase1/` là đầu ra của tag đó. Phase 2 thay luật (xem `docs/notes/assumptions.md`), bằng chứng hiện hành nằm ở mục Phase 2 và `docs/proof/phase2/`.

Tái tạo: `python3 -m unittest discover -s tests -q` và `python3 tests/run_proof.py` (đầu ra jsonl trong `docs/proof/phase1/` do chương trình sinh, không sửa tay). Máy: Windows 10, Python 3.11.9.

## Phase 1

| Yêu cầu | Cách kiểm chứng | Bằng chứng | Kết quả |
|---|---|---|---|
| contract `game.contract.json` đủ trường | `tests/test_game.py::Contract` | 21/21 test xanh | Đạt |
| Di chuyển, chuẩn hóa chéo, quy đổi `cam_yaw_deg`, nhảy | `Movement` | unit test | Đạt |
| Nhặt đom đóm (bán kính, sức chứa, điểm) | `Lanterns` | unit test | Đạt |
| Nạp ánh sáng, thắp đèn, thắng + điểm | `test_light_all_and_win_score`, scenario `win_two_trips` | `phase1/win_two_trips.jsonl` (end: won, score 439) | Đạt |
| Bóng Mực: chạm, rơi ánh sáng, bất tử, thua hết lửa | `Shades` | unit test | Đạt |
| Tỏa sáng: tốn ánh sáng, cooldown, choáng, đẩy lùi, điểm | `test_pulse*` | unit test | Đạt |
| Vùng an toàn quanh đèn sáng | `test_safe_zone` | unit test | Đạt |
| Thua khi bình minh | `test_lose_dawn`, scenario `lose_dawn` | `phase1/lose_dawn.jsonl` | Đạt |
| Headless: định dạng, nhịp snapshot, dừng khi game over | `Headless` | unit test | Đạt |
| Tính tất định (cùng seed -> cùng đầu ra) | chạy seed 42 hai lần, so SHA-256 | `run_proof.py`: `15848cdbfd1b` = `15848cdbfd1b` | Đạt |
| File đầu vào hỏng -> exit 2 + stderr | `test_bad_files_exit_2` | unit test | Đạt |
| Bản chơi 3D: render, HUD, di chuyển bằng phím | Chạy server, mở trình duyệt, chụp ảnh | [phase1-gameplay.jpg](phase1-gameplay.jpg) (Mây, đom đóm, Bóng Mực, đèn, HUD); phím W làm z tăng 0.1 -> 2.4 | Đạt (một phần, xem dưới) |
| Chơi hết một ván thắng trên giao diện | — | — | **Chưa kiểm** bằng tay: mới xác nhận qua scenario headless |
| Chơi lại sau thắng/thua | Nút/phím R gọi `/restart` | gọi `/restart` thủ công trong phiên thử, ván mới bắt đầu tick 0 | Đạt (không chụp riêng nút) |

Giới hạn trung thực: các con số hiệu năng chưa đo (Phase 1 không yêu cầu); `dash` và sự kiện rơi không có (ghi trong README). Ảnh chụp lấy từ commit làm Phase 1; client chưa được điều chỉnh sau đó.


## Phase 2 (Contract v1.1)

Máy: Windows 10, Python 3.11.9, trình duyệt trong app Claude Code. Tái tạo: `python3 -m unittest discover -s tests -q` (46 test) và `python3 tests/run_proof.py` (đầu ra jsonl trong `docs/proof/phase2/`, sinh bởi chương trình, không sửa tay; hash SHA-256 rút gọn in cùng kết quả). Spec và AC: [../notes/spec-phase2.md](../notes/spec-phase2.md).

| Yêu cầu | Cách kiểm chứng | Bằng chứng | Kết quả |
|---|---|---|---|
| Số liệu chuẩn trong contract v1.1 | `Contract.test_v11_values` | unit test | Đạt |
| Di chuyển 6 m/s, nhảy chỉ khi chạm đất | `Movement` | unit test | Đạt |
| Lướt 14 m/s × 12 tick, hồi 90 tick từ lúc bắt đầu, giữ độ cao | `test_dash*`, scenario `dash` | `phase2/dash.jsonl` | Đạt |
| Rơi khỏi đảo (1 lần, mất đồ, chờ 60, hồi sinh, bất tử 90, hết lửa thì thua) | `test_fall_*`, scenario `fall` | `phase2/fall.jsonl` | Đạt |
| Nhặt (1.0 m, chênh cao 1.5), sức chứa 10, điểm tính khi nạp | `Lanterns.*` | unit test | Đạt |
| Đèn: nạp min(mang, thiếu), gần nhất/ID, +100, thắng 2/giây + 50/lửa, thắng đúng tick hết giờ | `Lanterns.*`, `win_two_trips` | `phase2/win_two_trips.jsonl` (won, 948) | Đạt |
| Tỏa Sáng: 3 đom đóm, tâm +0.8 m, 3D ≤ 5, choáng 120, đẩy 4 m/15 tick, làm mới, +5/con, hồi 180 | `Pulse.*`, `pulse_shade` | unit test + jsonl | Đạt |
| Bóng Mực: 4/4.5 m/s, 12/18 m, hit/recoil 2 m/60 tick, 1 hit mỗi tick, bất tử, lịch sinh 3 Đêm, spawn ≥ 15 m | `Shades.*` | unit test | Đạt |
| Vùng an toàn 6 m, đẩy ra ≤ 30 tick vô hại | `test_safe_zone_blocks`, `test_expel_*`, `safe_zone` | `phase2/safe_zone.jsonl` (z tối đa 19.0) | Đạt |
| Đom đóm: 20 điểm khác nhau, +1 mỗi 240 tick tới trần 30 / hết điểm bỏ lượt, TTL 480 | `World.*` | unit test | Đạt |
| Địa hình: cầu không lan can, vách tầng, dốc, tháp, rơi xuống tầng dưới | `test_terrain_*`, `tiers_ramp` | `phase2/tiers_ramp.jsonl` (y = 3.0) | Đạt |
| Bục nhảy Đêm 2/3 | `test_launch_pads`, `pad_night2`, `pad_night3` | landed (51.4, 13.0); tầng 2 y = 6.0 | Đạt |
| Gió mạnh Đêm 3 | `test_wind`, `wind` | dịch chuyển 9.999 m (kỳ vọng 10) | Đạt |
| Gió Lạc | `Drifters.*`, `drifter_steal`, `drifter_pulse_drop` | unit test + jsonl | Đạt |
| Bùa Gió | `Charms.*`, `charm` | `phase2/charm.jsonl` | Đạt |
| Tạm dừng | `Pause`, scenario `pause` | `sim_tick = tick − 30` | Đạt |
| Contract: định dạng, `--night`, exit 2, tính tất định | `Headless.*`, `run_proof.py` | seed 42 chạy hai lần: hash trùng cả 3 Đêm | Đạt |
| 1 Đêm đầy đủ ≤ 30 s | `test_full_night_under_30s`, `run_proof.py` | 21 600 tick: 1.45 s | Đạt |
| Hồi quy Phase 1 | scenario `win_two_trips` + `lose_dawn` (viết lại theo số chuẩn) | PASS | Đạt (với số chuẩn) |
| Chuỗi 3 Đêm, menu, tạm dừng, cài đặt trên giao diện | Chạy server, thao tác trong trình duyệt | tạm dừng đóng băng `sim_tick`, tiếp tục chạy; `ddl-settings` lưu `{"vol":33,"sens":77}`; Đêm 2/3 hiển thị: [phase2-night2.jpg](../proof/phase2-night2.jpg), [phase2-night3.jpg](../proof/phase2-night3.jpg) | Đạt một phần (xem dưới) |
| FPS ≥ 30 ở 1280×720 | đo rAF 2 s ở 1280×720 | ≈ 180 FPS (bản chơi Đêm 3, máy làm bài) | Đạt |

**Chưa kiểm / chưa đạt (trung thực):**
- Chưa chơi hết một ván thắng ba Đêm bằng tay trên giao diện, nên màn kết quả, "Đêm kế tiếp" và màn Bình Minh chưa được quan sát; logic chuyển Đêm nằm trong `Game.command` nhưng chưa có test tự động.
- Âm thanh/nhạc chưa nghe được trong phiên làm bài (chỉ nối sự kiện → WebAudio).
- Bảng màu chuẩn có trong mã (`PAL`) nhưng chưa đo màu pixel bằng công cụ; ánh sáng môi trường theo công thức nhưng chưa đo.
- Nhiều chi tiết ticket không nói rõ đã được tự giả định (xem `assumptions.md` #16–28); bộ test ẩn có thể chọn khác (ví dụ điểm xuất phát Đêm 3, `night_start` ở headless).
