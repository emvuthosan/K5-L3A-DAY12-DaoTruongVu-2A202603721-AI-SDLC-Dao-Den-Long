# Đánh giá và retro

## Phase 1 — đánh giá
- **Đạt:** luật lõi PRD-0 (nhặt, nạp, thắp, Bóng Mực, tỏa sáng, thắng/thua, điểm), headless theo Test Contract v1.0, tính tất định, exit 2 khi file hỏng. Bằng chứng: `docs/proof/README.md`.
- **Chưa kiểm / chưa có:** chưa chơi hết một ván thắng bằng tay trên giao diện; chưa có video; chưa đo hiệu năng; `dash` và sự kiện rơi không có.
- **Hỏng phase trước:** không áp dụng (phase đầu).
- **Cần chỉnh:** nếu Phase 2 đổi luật, sửa test kèm lý do trong `docs/notes/`.
- Token Phase 1: ước tính 150–200k (xem `ai-log.md`).

## Phase 2–4
Chưa thực hiện: ticket chưa được phát hành trên lab board tại thời điểm viết (không có yêu cầu để làm theo). Không có tag `phase-2`, `phase-3`, `phase-4` và không có Release `v1.0.0`.

## Retro tạm thời
- Hiệu quả: một `Sim` dùng chung cho headless và bản chơi; viết test trước khi tin code; scenario chạy thật bắt được lỗi scenario của chính mình.
- Khó: môi trường không có Node nên chọn Python; lệnh shell dài dễ lỗi.
- Nếu làm lại: chơi thử bằng tay sớm hơn, thêm snapshot kiểm tra giao diện tự động.
