# Giả định Phase 1 (PRD-0 + Test Contract v1.0)

Các con số khai báo trong `game.contract.json`. Chỗ PRD/contract chưa quy định, tôi tự chọn:

| # | Chỗ mơ hồ | Giả định |
|---|---|---|
| 1 | Hình dạng đảo | Đĩa tròn bán kính 30 m. Người chơi và Bóng Mực bị giữ trong đảo (bờ là tường mềm). `fall_enabled=false`: không có rơi; sự kiện `player_hit` với `by:"fall"` không bao giờ phát. |
| 2 | Vị trí đèn | L1..L5 trên vòng bán kính 16 m, cách nhau 72°; L_i tại (16 sin((i-1)·72°), 0, 16 cos((i-1)·72°)), tức L1 = (0,0,16). Cố định, không phụ thuộc seed. |
| 3 | "Ánh sáng" | Mỗi đom đóm = 1 đơn vị. `carry_capacity`=5, `lantern_cost`=10 (cần ≥2 chuyến mỗi đèn). Cho phép nạp góp nhiều lần (`deposited` tích lũy). |
| 4 | Interact | Cạnh false→true; nạp vào đèn **chưa sáng gần nhất** trong `interact_radius` (hòa: ID nhỏ hơn). Không mang gì thì không có sự kiện. |
| 5 | Tỏa sáng (pulse) | Tốn `pulse_cost`=1 ánh sáng đang mang, cooldown 1.5 s. Mọi Bóng Mực trong `pulse_radius` bị choáng 3 s và đẩy lùi 2 m; `per_stun` tính cho mỗi con. Không đủ ánh sáng hoặc đang cooldown thì không có sự kiện. |
| 6 | Bóng Mực | Đuổi thẳng người chơi 3.5 m/s. Choáng: đứng yên và vô hại. Quanh đèn **đã sáng** bán kính `safe_radius`=4 m chúng bị đẩy ra (trạng thái `repelled`). Trạng thái: chase / stunned / repelled. |
| 7 | Bị chạm | Trong `shade_hit_radius` và không bất tử: -1 ngọn lửa, rơi `floor(carried*0.5)` ánh sáng (thành đom đóm bán kính 2 m quanh người), bất tử 1.5 s. Hết lửa -> thua `no_flames`. |
| 8 | Sinh ngẫu nhiên | Mặc định: 60 đom đóm, 3 Bóng Mực lúc đầu, +1 Bóng Mực mỗi 20 s (tối đa 6, sự kiện `shade_spawned`). Nếu scenario có `motes`/`shades`, danh sách thay mặc định và `random_*` mặc định `false` (đặt `true` để thêm ngẫu nhiên). |
| 9 | Điểm | +1/đom đóm nhặt, +100/đèn thắp, +5/Bóng Mực bị choáng; khi thắng: +1 × giây còn lại (làm tròn xuống) + 50 × ngọn lửa còn lại. |
| 10 | Thứ tự trong 1 tick | đầu vào -> di chuyển/nhảy -> nhặt -> interact -> pulse -> Bóng Mực -> sinh -> va chạm -> điều kiện kết thúc (hết lửa > thắng > bình minh). |
| 11 | Hết giờ | `night1_duration_s`=180; thua `dawn` khi `time_left_s` về 0. Scenario đặt `time_left_s` thì dùng giá trị đó. |
| 12 | `dash` | Không có -> bỏ qua (ghi trong README). |
| 13 | Snapshot cuối | Không thêm snapshot ngoài lịch `--snapshot-every`; bản ghi `end` mang trạng thái cuối. |
| 14 | Nhảy | 8 m/s, trọng lực 20 m/s²; chỉ nhảy khi chạm đất; khoảng cách chỉ tính trên XZ nên nhảy không né được va chạm. |
| 15 | Camera/cam_yaw | Camera client nhìn về +Z ở yaw 0; contract quy đổi x' = x cosθ + z sinθ nên phím D gửi x = -1. |
