# ADR-0003 — Nhiên liệu đèn và luật thắng "sống tới bình minh" (Ticket-03)

Trạng thái: chấp nhận · Phase 3 · Thay thế luật "đèn sáng là xong" và "thắng ngay khi tất cả đèn sáng" của Phase 1–2.

## Bối cảnh
Người chơi giỏi thắp hết đèn rồi game kết thúc sớm. Nhà thiết kế muốn đèn tắt được và mục tiêu là giữ đảo sáng tới bình minh (Ticket-03, Contract v1.2).

## Quyết định
1. **Mô hình trạng thái đèn.** Từ nhị phân (`lit`) sang: `lit`, `fuel`, `ever_lit`, `relit_count`, `deposited`. Vòng đời: `chưa từng sáng → (10 đom đóm) sáng fuel=100 → hao 1/s → (≤ 0) tắt, ever_lit=true → (5 đom đóm) thắp lại`. Đèn sáng nhận dầu qua cùng phím Tương tác (`refuel`).
2. **Nhiên liệu là số nguyên đơn vị 1/60** (`fu`): hao 1 đơn vị/tick, hút 5 đơn vị/tick/Bóng Mực, mỗi đom đóm = 600 đơn vị. Chỉ chuyển sang giây (làm tròn 1 chữ số) khi xuất output. Lý do: ticket yêu cầu tránh sai số thực; so sánh `fuel < 30`, `≥ 30` và "đúng 30" trở nên chính xác (`fu >= 1800`).
3. **Vùng an toàn là hàm của dầu**, không phải của `lit`: `_zone(l) = lit and fu >= 1800`. Mọi chỗ trước đây hỏi `l["lit"]` cho vùng an toàn (chặn, đẩy ra, điểm sinh) đều gọi `_zone`. Đèn được châm lên ≥ 30 dùng lại cơ chế đẩy ra 30 tick của "vừa thắp" (một cơ chế duy nhất).
4. **Bóng Mực có trạng thái `drain`** (đứng yên, hút 5/s). Trạng thái `wander` giờ có mục tiêu: đèn sáng yếu gần nhất (< 30), nếu không có thì đèn tắt gần nhất; hết mục tiêu thì đi lang thang ngẫu nhiên như Phase 2. Trúng Tỏa Sáng khi đang drain: +15 tổng (thay cho +5).
5. **Luật thắng** chuyển từ "sự kiện" sang "kiểm tra tại bình minh": bỏ nhánh `all_lit`; ở tick hết giờ, thắng nếu còn sống và số đèn sáng ≥ `ceil(0.6 × tổng)`; `no_flames` luôn được xét trước. Dầu trừ ở bước 2 và đèn tắt ngay sau đó, nên đèn cạn đúng tick bình minh không được tính là sáng.
6. **Sức chứa** = `10 + 2 × successful_lights` (tối đa 20), đếm ở chỗ thắp thành công (kể cả thắp lại), không đếm đèn đặt sẵn bằng scenario.
7. **Điểm**: bảng mới trong `game.contract.json > score` (`per_mote` 5 áp dụng cho mọi lần nạp, `per_lantern` 100, `per_relight` 40, `per_stun_drain` 15, `per_lit_dawn` 50, `per_flame_left` 50; `per_second_left` = 0).

## Hệ quả
- Phá vỡ tương thích (xem `CHANGELOG.md`): thời gian Đêm, kết thúc Đêm, `game_over.reason`, điểm, snapshot đèn, sự kiện `lantern_lit` có thêm `relight`.
- Tổng điểm game, chơi lại: không đổi (cộng điểm các Đêm đã thắng).
- Test cũ bị thay thế bởi luật mới được sửa kèm lý do (xem phần "Test cũ" trong `CHANGELOG.md`), không có test bị skip.

## Phương án đã cân nhắc
- Lưu dầu bằng số thực: bỏ vì sai số ở ngưỡng 30 và ở tick hết dầu.
- Thêm cờ `weak` cho đèn: bỏ, vì dẫn xuất từ `fu` rẻ hơn và không thể lệch trạng thái.
