# Bằng chứng kiểm chứng

> Mỗi mục Phase mô tả bản ở tag tương ứng. Phase 3 thay một số luật của Phase 1–2 (xem `CHANGELOG.md`); bằng chứng về luật nằm ở mục **Phase 3** (`docs/proof/phase3/`), số đo và bảng xếp hạng/trợ năng nằm ở mục **Phase 4** (`docs/proof/phase4/`).

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


## Phase 3 (Contract v1.2) — hiện hành

Máy: Windows 10, Python 3.11.9. Tái tạo: `python3 -m unittest discover -s tests -q` (77 test) và `python3 tests/run_proof.py` (20 scenario + tính tất định 3 Đêm + đo thời gian; đầu ra jsonl trong `docs/proof/phase3/`, sinh bởi chương trình). Spec/AC: [../notes/spec-phase3.md](../notes/spec-phase3.md). ADR: [../notes/ADR-0003-fuel-and-dawn-rule.md](../notes/ADR-0003-fuel-and-dawn-rule.md).

| Yêu cầu | Cách kiểm chứng | Bằng chứng | Kết quả |
|---|---|---|---|
| Dầu hao 1/s theo đơn vị nguyên, tắt đúng tick 6000, `lantern_out`, ever_lit | `Fuel.test_decay_exact_and_out` | unit test | Đạt |
| Thắp lại 5 đom đóm (+40), chưa từng sáng 10 (+100), `lantern_lit.relight` | `test_relight_cost_and_score`, scenario `fuel_out_relight` | `phase3/fuel_out_relight.jsonl` (out tại tick 180, relight, điểm 65) | Đạt |
| Châm dầu: công thức `ceil`, đèn đầy không được chọn, hòa theo id | `Fuel.test_refuel_formula`, `test_full_lantern_not_selected`, `refuel` | `phase3/refuel.jsonl` (6 đom đóm, fuel 100.0) | Đạt |
| Vùng an toàn: đúng 30 còn, < 30 mất | `test_safe_zone_threshold`, `test_weak_lantern_*` | unit test | Đạt |
| Bóng Mực hút dầu: chọn mục tiêu, drain cộng dồn, `fuel_drain`, các chuyển trạng thái, +15 | `Drain.*`, `drain` | `phase3/drain.jsonl` (đèn tắt tại tick 234) | Đạt |
| Đẩy ra vô hại khi châm ≥ 30 | `test_refuel_expels_harmlessly` | unit test | Đạt |
| Luật thắng: ngưỡng 3/5, 4/6, 5/7; không thắng sớm; `no_flames` ưu tiên; đèn cạn tick bình minh | `Win.*`, `dawn_win`, `dawn_lose` | `phase3/dawn_win.jsonl` (won, dawn_survived), `dawn_lose.jsonl` | Đạt |
| Thời gian Đêm 240/270/300 | `Win.test_durations` | unit test | Đạt |
| Sức chứa 10 + 2·lần thắp ≤ 20 | `Capacity.*`, `capacity` | 10 → 12 sau một lần thắp | Đạt |
| Điểm mới (5/100/40/5/15, bình minh 50+floor(fuel), 50/lửa, bỏ thưởng thời gian) | `Win.test_dawn_score`, `Score` | unit test | Đạt |
| Contract v1.2: tuning, snapshot, scenario, exit 2 | `Contract`, `test_phase3.Headless.*` | unit test | Đạt |
| Tính tất định (seed 42 × 2, cả 3 Đêm) | `run_proof.py` | hash trùng | Đạt |
| Đêm dài nhất (18 000 tick) headless ≤ 30 s | `run_proof.py` | 2.64 s | Đạt |
| Hồi quy Phase 1–2 không bị thay thế | toàn bộ test Phase 1–2 còn lại + 14 scenario cũ | PASS | Đạt |
| Giao diện: thanh dầu, vùng an toàn, "Đèn sáng k/n (cần m)", đang mang/sức chứa | chạy server với đèn đặt sẵn dầu 91.8/41.9/3.9, chụp ảnh | [phase3-fuel-hud.jpg](phase3-fuel-hud.jpg) | Đạt một phần |
| Chế độ mù màu | bật checkbox trong trình duyệt | `--danger` đổi thành `#FFFFFF`, cài đặt lưu `cb:true` | Đạt một phần |

**Chưa kiểm / chưa đạt (trung thực):**
- Nhấp nháy 1 Hz, đèn xẹp 20% + vết rách, biểu tượng ⚠ và màu `#00B3FF` của viền/mắt Bóng Mực có trong mã nhưng chưa quan sát trực tiếp (ảnh chụp chỉ thấy thanh dầu, vùng an toàn và HUD).
- Chưa chơi trọn một Đêm bằng tay tới bình minh trên giao diện (màn kết quả mới "Bình minh! giữ được k đèn" chưa được xem).
- Một số chi tiết ticket để ngỏ đã tự giả định (`assumptions.md` #29–36); test ẩn có thể chọn khác (ví dụ tốc độ `wander` có mục tiêu).


## Phase 4 (Contract v1.3, v1.0.0)

Máy: Windows 10, Python 3.11.9, Chrome 157, NVIDIA GeForce RTX 3050 Laptop GPU. Spec/AC: [../notes/spec-phase4.md](../notes/spec-phase4.md). Số đo do chính lệnh `bench`/`soak` sinh ra (không sửa tay) và được commit: [phase4/bench.json](phase4/bench.json), [phase4/soak.json](phase4/soak.json). Đây là số đo trên máy làm bài, **không phải máy chấm**.

| Yêu cầu | Cách kiểm chứng | Bằng chứng | Kết quả |
|---|---|---|---|
| Benchmark: cảnh chuẩn 200 Bóng Mực wander + 100 đom đóm + L1–L3 sáng fuel 100; tắt sinh thêm/sát thương/nhặt/hao dầu/kết thúc; Bóng Mực vẫn wander | `BenchScene.*` | unit test | Đạt |
| Benchmark: công thức `avg_fps`, `p1_low_fps` (k = max(1, ceil(0.01N))), `frame_ms_p95` | `BenchMetrics.test_definitions` | unit test | Đạt |
| Benchmark chạy thật, thoát mã 0, đủ trường | `python3 -m game.bench --seed 42 --duration 30 --out bench.json` | avg 643.6 FPS, p1-low 211.8 FPS, p95 2.3 ms, 19 309 khung, load 903 ms, bộ nhớ đỉnh 690 MB (cây tiến trình Chrome) | Đạt (ngưỡng 60 / 30 / 10 000 ms đạt trên máy làm bài) |
| Soak 10 Đêm trong một tiến trình: `crashes = 0`, `mem_end ≤ 1.2 × mem_start` | `python3 -m game.soak --seed 7 --nights 10 --out soak.json`; `Soak.*` (tất định) | 0 crash, RSS 22.1 → 22.1 MB, 1.4 s; cả 10 Đêm thua (người chơi ngẫu nhiên) | Đạt |
| Bảng xếp hạng: luật tên, top 10, thứ tự và hòa, lưu bền, xuất `--export-leaderboard`, lưu một lần mỗi lần kết thúc | `Leaderboard.*` | unit test (gồm tiến trình riêng đọc lại file) | Đạt |
| Bảng xếp hạng: nhập tên trên giao diện, màn hình từ menu | — | — | **Chưa kiểm bằng tay trọn vẹn**: ván thử đứng yên không thua nên không tới màn nhập tên; mới kiểm logic lưu và API |
| Đổi phím: 9 hành động, báo trùng, khôi phục mặc định, lưu | thao tác trong trình duyệt | gán Nhảy → W bị từ chối với cảnh báo "đã dùng cho Đi lên"; gán → J được và lưu `KeyJ`; "Khôi phục mặc định" trả về Space | Đạt |
| Giảm chuyển động, chữ lớn ×1.25 | thao tác trong trình duyệt | gốc 18 px → 22.5 px khi bật chữ lớn; cài đặt lưu `rm`, `big`; rung/chớp được bỏ qua khi `rm` (đọc mã, chưa quan sát bằng mắt) | Đạt một phần |
| Chữ UI ≥ 18 px ở 1280×720 | đo `getComputedStyle` mọi phần tử có chữ | lần đo đầu thấy 13.3 px ở nút/ô nhập ngoài `.screen`; đã sửa bằng `button,input{font-size:1rem}` | Đã sửa; **chưa đo lại toàn bộ** sau sửa (chỉ kiểm CSS) |
| Phụ đề/chỉ báo hình ảnh (Bóng Mực xuất hiện + mũi tên, gió sắp thổi, 10 s cuối, đèn < 30) | chạy game | ảnh [phase4-gameplay.jpg](phase4-gameplay.jpg) (⚠ chế độ mù màu, viền xanh của Bóng Mực, dòng báo Bóng Mực xuất hiện); các chỉ báo khác đọc mã | Đạt một phần |
| Đóng gói: README đủ mục, CHANGELOG 4 phase, CREDITS, LICENSE, zip phát hành | `scripts/make_release.py` | `dist/dao-den-long-v1.0.0.zip` | Đạt (zip chưa đăng lên GitHub Release: máy không có `gh`) |
| Clone sạch → 2 lệnh → chơi được | — | — | **Chưa thử trên máy sạch/macOS/Linux** |
| Hồi quy Phase 1–3 còn hiệu lực | 89 test + 20 scenario | PASS | Đạt |
| Video demo `.mp4` < 5 phút | — | kịch bản [../demo/DEMO.md](../demo/DEMO.md) | **Chưa đạt** (không quay được trong phiên làm bài) |

**Hạn chế đã biết:** `vsync_off` được ghi theo cờ trình duyệt đã truyền, không kiểm chứng được từ trang web; FPS đo bằng `requestAnimationFrame` kèm chờ GPU (`readPixels`) nên không bị phóng đại nhưng vẫn phụ thuộc trình duyệt/GPU của máy chấm.
