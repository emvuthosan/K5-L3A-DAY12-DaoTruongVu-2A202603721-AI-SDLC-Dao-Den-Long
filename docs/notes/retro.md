# Đánh giá và retro

## Phase 1 — đánh giá
- **Đạt:** luật lõi PRD-0 (nhặt, nạp, thắp, Bóng Mực, tỏa sáng, thắng/thua, điểm), headless theo Test Contract v1.0, tính tất định, exit 2 khi file hỏng. Bằng chứng: `docs/proof/README.md`.
- **Chưa kiểm / chưa có:** chưa chơi hết một ván thắng bằng tay trên giao diện; chưa có video; chưa đo hiệu năng; `dash` và sự kiện rơi không có.
- **Hỏng phase trước:** không áp dụng (phase đầu).
- **Cần chỉnh:** nếu Phase 2 đổi luật, sửa test kèm lý do trong `docs/notes/`.
- Token Phase 1: ước tính 150–200k (xem `ai-log.md`).

## Phase 2 — đánh giá
- **Đạt:** toàn bộ số liệu chuẩn, 3 bản đồ, lướt, rơi, Gió Lạc, Bùa Gió, bục nhảy, gió, tạm dừng, contract v1.1; 46 test + 14 scenario; một Đêm headless 1.45 s (ngưỡng 30 s).
- **Chưa kiểm:** ván thắng ba Đêm bằng tay trên giao diện, âm thanh bằng tai, màu pixel (xem `docs/proof/README.md`).
- **Hỏng phase trước:** không hỏng ngoài ý muốn; các luật Phase 1 bị ticket thay thế đã được viết lại kèm lý do (`assumptions.md`). Test Phase 1 cũ được đổi số chứ không tắt.
- **Cần chỉnh:** thêm test tự động cho chuỗi Đêm của server; chơi thử toàn bộ trước khi tag.
- Token Phase 2: ước tính 250–350k.

## Phase 3 — đánh giá
- **Đạt:** nhiên liệu đèn, châm dầu, thắp lại, Bóng Mực hút dầu, luật thắng bình minh, sức chứa tăng dần, điểm mới, chế độ mù màu (một phần quan sát), contract v1.2; 77 test và 20 scenario; một Đêm dài nhất 2.64 s.
- **Chưa kiểm:** các hiệu ứng thị giác (nhấp nháy, xẹp, ⚠), một Đêm trọn vẹn bằng tay (xem `docs/proof/README.md`).
- **Hỏng phase trước:** chỉ những luật bị ticket thay thế; các test đó được sửa kèm lý do trong `CHANGELOG.md`, không có test bị skip. Phần còn lại của Phase 1–2 vẫn pass.
- **Cần chỉnh:** giả định #31 (tốc độ wander có mục tiêu) là chỗ dễ lệch với bản chuẩn.
- Token Phase 3: ước tính 150–250k. Tiết kiệm nhờ vá có kiểm assert thay vì viết lại.

## Phase 4
Chưa thực hiện (ticket chưa phát hành). Không có tag `phase-4` và Release `v1.0.0`.

## Retro tạm thời
- Hiệu quả: một `Sim` dùng chung cho headless và bản chơi; viết test trước khi tin code; scenario chạy thật bắt được lỗi scenario của chính mình.
- Khó: môi trường không có Node nên chọn Python; lệnh shell dài dễ lỗi.
- Nếu làm lại: chơi thử bằng tay sớm hơn, thêm snapshot kiểm tra giao diện tự động.
