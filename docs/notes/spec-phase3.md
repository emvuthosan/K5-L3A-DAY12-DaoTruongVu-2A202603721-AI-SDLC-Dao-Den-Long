# Spec Phase 3 — Ticket-03 "Đèn cạn dầu" (Contract v1.2)

Quyết định thiết kế: [ADR-0003](ADR-0003-fuel-and-dawn-rule.md). Thay đổi phá vỡ: [CHANGELOG.md](../../CHANGELOG.md). Test: `tests/test_phase3.py` (+ các test Phase 1-2 đã cập nhật), scenario `tests/scenarios/`, chạy `python3 tests/run_proof.py`.

| # | Mục | Acceptance criteria | Bằng chứng |
|---|---|---|---|
| 1 | Nhiên liệu | Thắp = fuel 100; hao đúng 1/s tính bằng 1/60 nguyên (tick 6000 tắt chính xác); hết dầu → tắt, `deposited=0`, `ever_lit=true`, sự kiện `lantern_out`; thắp lại 5 đom đóm (chưa từng sáng: 10); đèn đặt `lit:true` không có `fuel` thì 100 | `Fuel.test_decay_exact_and_out`, `test_relight_*`, `test_out_then_relight_cycle`, scenario `fuel_out_relight` |
| 2 | Châm dầu | `used = min(mang, ceil((100−fuel)/10))`, fuel `min(100, +10·used)`, +5/đom đóm; đèn đầy dầu không được chọn, không sự kiện, không điểm; chọn đèn nhận được gần nhất, hòa thì id nhỏ | `Fuel.test_refuel_formula`, `test_full_lantern_not_selected`, `test_nearest_receiver_tie_by_id`, scenario `refuel` |
| 3 | Vùng an toàn theo dầu | Đúng 30 vẫn còn vùng, < 30 mất; đèn yếu cho Bóng Mực vào; đèn châm lên ≥ 30 đẩy các con trong 6 m ra ≤ 30 tick, vô hại | `test_safe_zone_threshold`, `test_weak_lantern_lets_shades_in_strong_blocks`, `Drain.test_refuel_expels_harmlessly` |
| 4 | Bóng Mực hút dầu | Chỉ `wander` chọn đèn yếu gần nhất (hòa: id nhỏ), không có thì đèn tắt gần nhất; ≤ 2 m → `drain` đứng yên, 5/s cộng dồn; `fuel_drain` mỗi 60 tick; drain→chase khi Mây trong 6 m, →stunned khi trúng Tỏa Sáng (+15 tổng), →wander khi đèn tắt / fuel ≥ 30 / cách > 2 m | `Drain.*`, scenario `drain` |
| 5 | Luật thắng mới | Đêm 240/270/300 s; không thắng sớm; thắng = sống + sáng ≥ ceil(0.6n) (3/5, 4/6, 5/7), reason `dawn_survived`; thua `dawn` hoặc `no_flames`; `no_flames` xét trước ở tick bình minh; đèn cạn đúng tick bình minh không được tính | `Win.*`, `test_no_early_win_and_dawn_win`, scenario `dawn_win`, `dawn_lose` |
| 6 | Sức chứa | `10 + 2·successful_lights` ≤ 20; tính cả thắp lại, không tính đèn đặt sẵn và châm dầu; nhặt theo sức chứa; HUD đang mang/sức chứa | `Capacity.*`, scenario `capacity` |
| 7 | Điểm | +5 mỗi đom đóm nạp, +100 thắp đầu, +40 thắp lại, +5/+15 Tỏa Sáng, bình minh +50+floor(fuel)/đèn sáng và +50/lửa, bỏ thưởng thời gian | `Win.test_dawn_score`, `test_no_time_bonus_when_all_lit`, `Score` |
| 8 | Hiển thị | Thanh dầu, nhấp nháy 1 Hz khi < 30, đèn tắt xẹp 20% + vết rách | ảnh `docs/proof/phase3-fuel-hud.jpg` |
| 9 | Chế độ mù màu | Cài đặt lưu được; viền/mắt Bóng Mực `#00B3FF`; cảnh báo `#FFFFFF` + ⚠ | kiểm tay: `--danger` = `#FFFFFF`, `ddl-settings.cb = true` (⚠ trên HUD chưa quan sát) |
| 10 | Contract v1.2 | `contract_version "1.2"`, tuning mới, snapshot `fuel/ever_lit/relit_count/capacity`, scenario mới, sự kiện mới, `lantern_lit.relight`, lỗi file → exit 2 | `Contract.test_v12_values`, `test_phase3.Headless.*` |
