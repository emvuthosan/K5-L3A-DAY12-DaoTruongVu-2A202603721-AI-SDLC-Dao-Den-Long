# Nhật ký dùng AI (Phase 1)

Công cụ: Claude Code (Sonnet 5.5), một phiên làm việc. Token Phase 1: **ước tính** khoảng 150–200k (chủ yếu đọc tài liệu lab và sinh code; không dùng subagent). Đây là ước tính, không phải số đo.

Quyết định kiến trúc: Python stdlib cho `Sim` vì máy làm bài không có Node và Python chạy được trên macOS/Linux; server cục bộ chạy cùng `Sim` ở 60 Hz và client three.js chỉ vẽ → chỉ có **một** nơi chứa luật game, headless và bản chơi không thể lệch nhau.

Cách tiết kiệm token: đọc tài liệu một lần; test gom một file; tái dùng `Sim` cho server thay vì viết lại logic bằng JS; không để agent chạy vòng lặp dài.

Lỗi của AI và điều đã gặp:
1. Lệnh shell heredoc dài nhiều dấu nháy lỗi cú pháp (hai lần) → chuyển sang ghi file bằng công cụ Write.
2. Scenario thử đầu tiên sai khoảng cách (đi quá đèn): chạy thật thấy không có `deposit` rồi mới sửa input. Đây là lý do cần scenario chạy thật chứ không tin code.
3. Thử trình duyệt: người chơi đứng yên chết sau ~10 s (3 Bóng Mực) nên phép đo phím đầu thấy "không di chuyển". Nguyên nhân là ván đã kết thúc, không phải lỗi input; khởi động lại ván rồi đo lại (z 0.1 → 2.4 trong 1 s đồng hồ trình duyệt đang ẩn nên bị giảm tần số timer).


# Phase 2 (Ticket-02)

Token Phase 2: **ước tính** 250–350k (viết lại sim, test, client, tài liệu; không dùng subagent). Là ước tính.

Quyết định: viết lại `sim.py` một lần thay vì vá (số liệu chuẩn đổi gần như mọi luật). Nhờ logic tách khỏi giao diện nên server/headless chỉ đổi rất ít. Dùng nhiều luồng RNG riêng (đom đóm/bóng/gió lạc/gió/rơi) để bật/tắt một tính năng không làm đổi kết quả của tính năng khác.

Lỗi của AI / lần sai trong phase này và cách phát hiện:
1. Chạy test lần đầu: 9 lỗi, gần hết là **test do tôi viết sai**, không phải sim sai: vị trí bóng ngoài vùng 12 m nên không đuổi; scenario đặt bóng trong vùng an toàn của đèn vừa thắp (đúng luật, bị vô hại); Đêm 1 chỉ có 24 điểm sinh đom đóm chứ không phải 30; bùa mặc định ở (35,0,0) làm lệch phép đo tốc độ cầu. Cách sửa: đối chiếu từng lỗi với đoạn ticket, sửa test hoặc luật, không nới lỏng assert.
2. Một lỗi thật: Gió Lạc sinh cả ở Đêm 1 khi bật cờ `random_drifters` (ticket: chỉ Đêm 2 và 3) → test `Drifters.test_spawn_schedule` bắt được, sửa trong `sim.py`.
3. Ticket không nói điểm xuất phát Đêm 3 và nhiều chi tiết khác: ghi vào `assumptions.md` thay vì đoán ngầm.
Harness chỉnh: AGENTS.md ghi rõ quy ước góc, luồng RNG và "một tính năng thêm không được đổi đầu ra headless"; skill `verify` chạy cả scenario phase 2.
