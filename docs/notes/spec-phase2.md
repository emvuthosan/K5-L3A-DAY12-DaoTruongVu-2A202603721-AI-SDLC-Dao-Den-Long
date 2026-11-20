# Spec Phase 2 — Ticket-02 "Ba hòn đảo" (Contract v1.1)

Mỗi mục có tiêu chí nghiệm thu (AC) kiểm chứng được, và test/scenario chứng minh nó. Test: `tests/test_game.py` (class), scenario: `tests/scenarios/*.json`, chạy lại bằng `python3 tests/run_proof.py`.

## Số liệu chuẩn (Phần 1) và bản đồ (Phần 2)
- AC: mọi hằng số trong `game.contract.json` bằng số chuẩn; Đêm 1 có đèn L1..L5 đúng tọa độ, đảo bán kính 40; Đêm 2 hai đảo bán kính 28 + cầu tre; Đêm 3 ba tầng, 2 dốc, tháp. → `Contract`, `World.test_terrain_*`, `test_initial_motes_and_schedule`.
- Thứ tự tick và các bộ đếm theo đúng danh sách của ticket (ghi trong docstring `Sim.step`).

## Phần 3 — Tính năng mới
| # | Tính năng | Acceptance criteria | Bằng chứng |
|---|---|---|---|
| 1 | Lướt | Nhấn dash (cạnh lên): 14 m/s trong 12 tick, hồi chiêu 90 tick tính từ lúc bắt đầu (lướt lại được ở tick 91, không phải 90); không có input thì lướt theo hướng đang quay mặt; trên không giữ nguyên độ cao; phát sự kiện `dash {}` | `Movement.test_dash*`, scenario `dash` |
| 2 | Rơi khỏi đảo | Y < −10: đúng 1 lần −1 Ngọn Lửa, mất toàn bộ đom đóm (`player_hit by:"fall"` có `lost`), đứng yên 60 tick, hồi sinh ở điểm xuất phát với vận tốc 0 và bất tử 90 tick; hết lửa thì thua ngay | `test_fall_*`, scenario `fall` |
| 3 | Gió Lạc | Đêm 2–3, tối đa 2 con, sinh ở tick 1200k (id D1, D2…); idle→chase khi mang ≥5 và cách ≤15 m; chạm ≤1.2 m cướp min(3, mang) rồi flee 240 tick và biến mất; Tỏa Sáng trúng khi chase → flee không cướp, trúng khi flee có đồ → thả lại (`drifter_drop`); không mất Ngọn Lửa | `Drifters.*`, scenario `drifter_steal`, `drifter_pulse_drop` |
| 4 | Bùa Gió | Nhặt như đom đóm (`charm_picked`), 600 tick chạy 7.2 m/s và lướt không hồi chiêu (nhấn lại vẫn cần; đang lướt thì bỏ qua), nhặt lại làm mới; xuất hiện lại sau 2700 tick; vị trí đúng theo đêm | `Charms.*`, scenario `charm` |
| 5 | Bục nhảy | Đêm 2: bắn lên Y 14 và ngang 24 m/s về tâm đảo kia, đáp trong đảo đích; Đêm 3: Y 12 và ngang 8 m/s hướng −Z, đáp tầng 2; phím di chuyển không ghi đè | `test_launch_pads`, scenario `pad_night2`, `pad_night3` |
| 6 | Gió mạnh (Đêm 3) | Gió 5 s mỗi 30 s (tick 1800k, hướng ngẫu nhiên theo seed), đẩy 2 m/s; snapshot `wind {active, dir_deg}`; báo trước 2 s (client: lá bay + dòng chữ) | `test_wind`, scenario `wind` (dịch chuyển 9.999 m) |
| 7 | Chuỗi 3 Đêm | Menu → giới thiệu Đêm (lời Ông Đăng) → chơi → kết quả → Đêm kế; thắng Đêm 3 hiện Bình Minh + tổng điểm; thua thì chơi lại đúng Đêm đó; tổng điểm chỉ cộng các Đêm đã thắng | `game/server.py` (`Game`), kiểm tay trong trình duyệt (xem proof) |
| 8 | Tạm dừng | Esc/P: `sim_tick`, thời gian, hồi chiêu, spawn, TTL đứng yên; `tick` vẫn tăng; snapshot `state:"paused"`; sự kiện `paused`/`resumed`; menu Tiếp tục / Chơi lại Đêm / Cài đặt / Về menu | `Pause.test_pause_freezes`, scenario `pause`, kiểm tay |
| 9 | Cài đặt | Âm lượng và độ nhạy chuột lưu vào `localStorage`, giữ giữa các lần mở | kiểm tay (`ddl-settings` = `{"vol":33,"sens":77}`) |
| 10 | Âm thanh | Nhạc nền đêm + hiệu ứng: nhặt, thắp, tỏa sáng, bị đánh, nhảy, lướt, thắng, thua, Bóng Mực xuất hiện, đếm ngược 10 s cuối (tổng hợp bằng WebAudio, không asset ngoài) | **Chưa kiểm bằng tai**: đã nối sự kiện → âm thanh trong `main.js`, không có công cụ nghe trong phiên làm bài |
| 11 | HUD | Ngọn Lửa (trên trái), mm:ss (trên giữa, đỏ + nhấp nháy ≤30 s), đèn k/n + điểm (trên phải), thanh 10 ô, icon hồi chiêu Lướt/Tỏa Sáng (dưới phải), nhắc "E — Nạp ánh sáng (x/10)", mũi tên tới đèn chưa sáng gần nhất khi ngoài màn hình | ảnh `phase2-night2.jpg`, `phase2-night3.jpg` |
| 12 | Bảng màu + ánh sáng môi trường | Các màu chuẩn trong `main.js` (`PAL`); ambient = 0.15 + 0.55 × (đèn sáng / tổng đèn) | đọc mã (`PAL`, `ambient.intensity`); **chưa đo màu bằng công cụ** |

## Test Contract v1.1
- AC: `contract_version "1.1"`; `--night 1|2|3`; snapshot có `night`, `wind`, `player.{vel,grounded,invuln,dash_cd_s,pulse_cd_s,charm_s}`, mảng `motes/drifters/charms`; scenario nhận `invuln_ticks`, `dash_cd_ticks`, `pulse_cd_ticks`, `charm_ticks`, `shades[].{state,state_ticks_left}`, `drifters`, `charms`, `random_drifters`, `wind_enabled`; input có `dash`, `pause`; sự kiện mới đủ; trạng thái Bóng Mực ∈ {spawning, wander, chase, recoil, stunned}. → `Headless.test_format`, `test_bad_input_exit_2`.
- AC hiệu năng: một Đêm đầy đủ 21 600 tick ≤ 30 s. → đo được ≈1.4 s (xem `docs/proof/README.md`).
