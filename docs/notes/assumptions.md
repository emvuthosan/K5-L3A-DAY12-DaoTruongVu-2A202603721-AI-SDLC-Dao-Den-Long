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

---

# Phase 2 (Ticket-02, Contract v1.1): thay đổi và giả định mới

**Đổi hướng (lý do):** Ticket-02 thay toàn bộ số liệu tự chọn ở Phase 1 bằng số chuẩn (sức chứa 10, đèn cần 10, pulse tốn 3 / 5 m / hồi 3 s, Bóng Mực 4 m/s, đảo bán kính 40, điểm 10/100/5/2/50...). Đã viết lại `game/sim.py` và `game.contract.json`; các test Phase 1 tương ứng được **viết lại với số mới** (không tắt): đổi số, thêm kiểm tra theo ticket. Các mục Phase 1 sai theo luật mới: vùng an toàn 4 m → 6 m; bị đánh không còn rơi tại chỗ mà rơi ra vành 1.5–2.5 m; điểm tính khi *nạp* chứ không khi nhặt; tỏa sáng đẩy 4 m trong 15 tick thay vì 2 m tức thời; Bóng Mực đi tuần/đuổi theo ngưỡng 12/18 m. "Đom đóm vàng" (sáng tạo Phase 1) giữ nguyên, chỉ bật ở bản chơi.

Giả định thêm (chỗ ticket chưa nói):
| # | Chỗ mơ hồ | Giả định |
|---|---|---|
| 16 | Góc | `x = r cos a`, `z = r sin a` (khớp ticket: dốc 30°/150° và 20°–160° nằm ở nửa z > 0). |
| 17 | Điểm xuất phát | Đêm 1 và 2: (0,0,0) quay mặt +Z. Đêm 3: (0,0,−30) trên tầng 0 (tâm là tháp nên không thể xuất phát ở đó). |
| 18 | Tăng tốc | Đổi vận tốc tức thì (ticket cho phép ≤ 0.1 s). Đứng yên/quay mặt: facing giữ hướng cuối cùng khi di chuyển, ban đầu +Z. |
| 19 | Tick bất tử/choáng | Bộ đếm giảm ở bước 2 của tick sau: đặt 90 ở tick k thì tick k+90 hết bất tử (bị đánh được lại đúng 90 tick sau). Choáng 120 tick: choáng ở tick k..k+119. |
| 20 | Va chạm tầng | Vách đứng chặn nếu mặt đất đích cao hơn chân > 0.3 m; trượt theo trục khi bị chặn. Tháp: trụ bán kính 2 cao tới Y 14. Bóng Mực cũng bị vách/tháp chặn và không rơi khỏi đảo. |
| 21 | Bóng Mực wander | Đi theo hướng ngẫu nhiên (đổi mỗi 120 tick) tốc độ nửa tốc độ chạy. `spawning` kéo dài đúng 1 tick (tick sinh). Sau recoil/choáng về `wander`, tick đó xét lại 12 m để `chase`. |
| 22 | Điểm sinh Bóng Mực | Cách người chơi ≥ 15 m và ngoài vùng an toàn của đèn đã sáng (mọi Đêm); chọn ngẫu nhiên theo seed. Gió Lạc sinh trên các điểm sương = cùng bộ điểm Bóng Mực của Đêm đó. |
| 23 | Vùng an toàn | Bóng Mực trong vùng khi đèn vừa thắp (hoặc scenario đã sáng sẵn) được đẩy ra mép trong 30 tick, đồng thời vô hại; sau đó bị chặn ở mép 6 m. |
| 24 | Tỏa Sáng vs Gió Lạc | Gió Lạc cao hover = mặt đất + 1.5 m (dùng cho khoảng cách 3D). "Biến mất sau 120 tick" hiểu là Gió Lạc còn bay tối đa 120 tick nữa (đom đóm thả có TTL 480 như thường). `stunned_ids` chỉ gồm Bóng Mực. Điểm per_stun chỉ cho Bóng Mực. |
| 25 | Interact | Khoảng cách chỉ tính XZ (như Phase 1). Đang chờ hồi sinh thì không nhặt/tương tác/tỏa sáng/bị chạm. |
| 26 | Sự kiện `night_start` | Headless ghi `night_start` (tick 0) ngay sau snapshot tick 0; sự kiện thiết lập khác vẫn không có. |
| 27 | Nhiều thực thể mới | Trần 30 đom đóm tính cả đom đóm rơi; điểm trống = điểm sinh chưa có đom đóm ngẫu nhiên. `random_*` mặc định false nếu scenario cho danh sách tương ứng (`random_drifters` mặc định true từ Đêm 2). |
| 28 | Snapshot | `player.invuln` là số tick còn lại (nguyên); `*_s` là giây. Có thêm trường phụ (facing, pos của bùa, state_ticks_left). |
