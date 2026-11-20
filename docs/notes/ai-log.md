# Nhật ký dùng AI (Phase 1)

Công cụ: Claude Code (Sonnet 5.5), một phiên làm việc. Token Phase 1: **ước tính** khoảng 150–200k (chủ yếu đọc tài liệu lab và sinh code; không dùng subagent). Đây là ước tính, không phải số đo.

Quyết định kiến trúc: Python stdlib cho `Sim` vì máy làm bài không có Node và Python chạy được trên macOS/Linux; server cục bộ chạy cùng `Sim` ở 60 Hz và client three.js chỉ vẽ → chỉ có **một** nơi chứa luật game, headless và bản chơi không thể lệch nhau.

Cách tiết kiệm token: đọc tài liệu một lần; test gom một file; tái dùng `Sim` cho server thay vì viết lại logic bằng JS; không để agent chạy vòng lặp dài.

Lỗi của AI và điều đã gặp:
1. Lệnh shell heredoc dài nhiều dấu nháy lỗi cú pháp (hai lần) → chuyển sang ghi file bằng công cụ Write.
2. Scenario thử đầu tiên sai khoảng cách (đi quá đèn): chạy thật thấy không có `deposit` rồi mới sửa input. Đây là lý do cần scenario chạy thật chứ không tin code.
3. Thử trình duyệt: người chơi đứng yên chết sau ~10 s (3 Bóng Mực) nên phép đo phím đầu thấy "không di chuyển". Nguyên nhân là ván đã kết thúc, không phải lỗi input; khởi động lại ván rồi đo lại (z 0.1 → 2.4 trong 1 s đồng hồ trình duyệt đang ẩn nên bị giảm tần số timer).
