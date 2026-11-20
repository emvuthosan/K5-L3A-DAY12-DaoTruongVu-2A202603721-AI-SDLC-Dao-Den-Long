# Changelog

## Phase 3 — "Đèn cạn dầu" (Contract v1.2, tag `phase-3`)

### Thay đổi phá vỡ tương thích (breaking)
- **Luật thắng:** bỏ "thắng khi tất cả đèn sáng" (`game_over.reason = all_lit` không còn dùng). Thắng = còn sống ở bình minh và số đèn sáng ≥ `ceil(0.6 × tổng)` (`dawn_survived`); thua = `no_flames` hoặc `dawn`.
- **Thời gian Đêm:** 300/330/360 s → **240/270/300 s** (`night*_duration_s`).
- **Đèn có dầu:** `fuel` 100, hao 1/s, tắt khi hết; thắp lại chỉ cần 5 đom đóm; đèn sáng nhận đom đóm để châm dầu. Vòng đời đèn từ 2 trạng thái thành chu trình (chưa sáng → sáng → tắt → sáng lại).
- **Vùng an toàn:** không còn "đèn sáng = có vùng". Chỉ đèn sáng có `fuel ≥ 30` mới có vùng.
- **Bóng Mực:** thêm trạng thái `drain`; `wander` nay đi tới đèn yếu/đèn tắt thay vì chỉ lang thang ngẫu nhiên.
- **Điểm:** thay toàn bộ (nạp +5/đom đóm, thắp lần đầu +100, thắp lại +40, Tỏa Sáng +5 hoặc +15 nếu đang drain, bình minh +50 + floor(fuel) mỗi đèn sáng và +50 mỗi Ngọn Lửa; bỏ thưởng thời gian).
- **Sức chứa:** cố định 10 → `10 + 2 × successful_lights` (tối đa 20); `player.capacity` mới trong snapshot.
- **Contract v1.2:** thêm tuning `fuel_max, fuel_decay_per_s, fuel_per_mote, relight_cost, win_ratio, drain_per_s, low_fuel_threshold, capacity_max`; snapshot đèn thêm `fuel, ever_lit, relit_count`; Bóng Mực thêm `target_lantern_id`; sự kiện mới `refuel, lantern_out, fuel_drain`; `lantern_lit.relight`; scenario nhận `fuel, ever_lit, relit_count, successful_lights, target_lantern_id`.
- Một Đêm headless dài nhất giờ là 18 000 tick (Đêm 3, 300 s).

### Thêm mới (client)
- Thanh dầu trên đèn, nhấp nháy 1 Hz khi `fuel < 30`, đèn tắt bị xẹp 20% và có vết rách, nhắc "Châm dầu", HUD `đang mang/sức chứa`, "Đèn sáng k/n (cần m)".
- Cài đặt "Bảng màu dễ phân biệt" (lưu được): viền và mắt Bóng Mực `#00B3FF`, màu cảnh báo `#FFFFFF` kèm ⚠.

### Test cũ bị luật mới làm sai (đã sửa/thay, không skip)
| Test cũ | Lý do | Xử lý |
|---|---|---|
| `Contract.test_v11_values` | số liệu chuẩn đổi (thời gian Đêm, bảng điểm, tuning mới) | đổi thành `test_v12_values`, giá trị mới |
| `Lanterns.test_win_score_and_exact_last_tick` | thắng sớm khi đủ đèn bị bỏ | thay bằng `test_no_early_win_and_dawn_win` (+ `Win.*` trong `tests/test_phase3.py`) |
| `Lanterns.test_deposit_score_and_range`, `test_partial_and_min` | +10/đom đóm → +5 | cập nhật số điểm kỳ vọng |
| `Headless.test_phase1_scenario_still_wins` | thắng khi đủ đèn → thắng ở bình minh | scenario `win_two_trips` đặt `time_left_s=6`, kỳ vọng thắng tại tick 360 |
| `Headless.test_full_night_under_30s` | Đêm 3 còn 300 s | kỳ vọng 18 000 tick |
| `lose_dawn`, các test Phase 2 khác | không bị ảnh hưởng | giữ nguyên, vẫn pass |

## Phase 2 — "Ba hòn đảo" (Contract v1.1, tag `phase-2`)
Số liệu chuẩn, 3 bản đồ, lướt, rơi khỏi đảo, Gió Lạc, Bùa Gió, bục nhảy, gió mạnh, tạm dừng, cài đặt, âm thanh, HUD đầy đủ.

## Phase 1 — Đêm 1 (Contract v1.0, tag `phase-1`)
Lõi game, headless theo Test Contract v1.0.
