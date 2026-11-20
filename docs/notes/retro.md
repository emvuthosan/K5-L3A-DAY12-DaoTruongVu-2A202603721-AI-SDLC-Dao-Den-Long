# Retro và đánh giá 4 phase — Đảo Đèn Lồng

Con số token/chi phí bên dưới là **ước tính** của tôi (phiên làm việc không cung cấp bộ đếm token), không phải số đo.

## Đánh giá từng phase

| Phase | Đạt | Chưa kiểm / chưa đạt | Hỏng phase trước? | Token ước tính |
|---|---|---|---|---|
| 1 — Đêm 1 (Contract v1.0) | Luật lõi, headless, tất định, exit 2; 21 test | Chưa chơi trọn ván trên giao diện | — | 150–200k |
| 2 — Ba hòn đảo (v1.1) | Số liệu chuẩn, 3 bản đồ, lướt/rơi/Gió Lạc/Bùa Gió/bục nhảy/gió/tạm dừng; 46 test, 14 scenario; một Đêm headless 1.4 s | Âm thanh chưa nghe, màu chưa đo pixel | Luật Phase 1 bị ticket thay: viết lại test kèm lý do | 250–350k |
| 3 — Đèn cạn dầu (v1.2) | Dầu số nguyên, thắp lại, Bóng Mực hút dầu, thắng ở bình minh, sức chứa, điểm mới, mù màu; 77 test, 20 scenario | Hiệu ứng nhấp nháy/xẹp/⚠ chưa quan sát | Chỉ các luật bị thay; sửa/thay test có ghi trong CHANGELOG, không skip | 150–250k |
| 4 — Bình minh (v1.3) | Benchmark, soak, bảng xếp hạng, đổi phím, phụ đề, giảm chuyển động, chữ ≥ 18 px, đóng gói; 89 test | Video demo chưa quay; chưa kiểm trên máy chấm/macOS/Linux | Không | 300–400k |

Tổng ước tính **0.85–1.2 triệu token** cho cả dự án, chủ yếu là sinh mã và đọc lại tài liệu.

## Điều gì hiệu quả
- **Một nơi duy nhất chứa luật** (`game/sim.py`, không I/O). Headless, server, soak và benchmark dùng chung; client chỉ vẽ. Nhờ vậy mỗi ticket đổi luật chỉ chạm một chỗ và bản chơi không thể lệch với headless.
- **Viết kiểm chứng cùng lúc với luật** (test + scenario headless chạy thật) bắt được cả lỗi của AI lẫn lỗi hiểu ticket. `run_proof.py` biến bằng chứng thành thứ chạy lại được và khớp tag.
- **Ghi giả định thay vì đoán ngầm** (`assumptions.md`, 45 mục): chỗ ticket bỏ ngỏ có nơi ghi, và phase sau dễ biết chỗ nào cần đổi.
- **Dầu bằng số nguyên 1/60** (ADR-0003): ngưỡng "đúng 30" và "tắt đúng tick 6000" chính xác, không cần dung sai.

## Điều gì không hiệu quả
- Lệnh shell dài nhiều dấu nháy lỗi cú pháp lặp lại ở mỗi phase; cách chữa (ghi script ra file rồi chạy) lẽ ra phải vào AGENTS.md sớm hơn.
- Kiểm giao diện chỉ làm được từng phần (không có người chơi thật, không nghe được âm thanh, không quay được video).
- Benchmark trên bản web phụ thuộc trình duyệt và không tắt vsync được từ trang; xem giả định #37–39.

## Những lần AI sai và cách phát hiện
1. **Test do AI viết sai** (Phase 2–3: bóng ngoài tầm 12 m, khoảng cách 3D của Tỏa Sáng, đèn bị chính lệnh châm dầu làm đầy): test đỏ → đối chiếu từng chỗ với ticket → sửa test hoặc luật, không nới assert.
2. **Lỗi thật trong sim:** Gió Lạc sinh ở Đêm 1 (Phase 2), Bóng Mực `drain` vẫn hút dầu lúc đang bị đẩy ra (Phase 3). Bắt được nhờ test theo từng câu của ticket và rà ticket-so-với-mã trước khi chạy.
3. **Đo sai hiệu năng:** lần đầu benchmark báo ≈1800 FPS vì `requestAnimationFrame` trả về trước khi GPU vẽ xong; thêm `readPixels` mỗi khung để chờ GPU (còn ≈430 FPS). Phát hiện nhờ nghi ngờ con số quá đẹp.
4. **Ghi "đạt" quá tay:** nhiều lần phải hạ xuống "đạt một phần / chưa quan sát" khi tự rà bảng bằng chứng (ví dụ ⚠ trên HUD, âm thanh, video).

## Harness nào giúp nhiều nhất
- **`AGENTS.md`** ngắn (quy ước tick, RNG riêng từng tính năng, dầu số nguyên, `_zone`) giúp các lần sửa sau không phá ngầm các luật cũ.
- **Skill `verify`** gói đúng chuỗi "unit test → scenario → tất định → đo thời gian".
- **Hook Stop chạy test** ngăn kết thúc khi test đỏ. **CI** chạy lại test và `run_proof.py` mỗi lần push.

## Token và cách tiết kiệm
Đọc tài liệu một lần; một `Sim` dùng chung thay vì viết hai lần (Python + JS); vá có `assert` thay vì viết lại khi phase đổi luật nhỏ; test gom theo file; không dùng subagent; không để agent chạy vòng lặp dài. Đốt thêm token không làm bài tốt hơn; phần đắt nhất là viết lại `sim.py` ở Phase 2 (ticket đổi gần mọi số liệu).

## Nếu làm lại
- Đưa vào AGENTS.md ngay từ Phase 1: "ghi script ra file thay vì heredoc dài" và "mọi bằng chứng giao diện cần ảnh + số đo".
- Chọn engine có benchmark gốc (hoặc đóng gói sẵn một trình duyệt cố định) để số đo không phụ thuộc trình duyệt của máy chấm.
- Làm khung kiểm thử giao diện tự động sớm (chụp ảnh khung hình để so), thay vì kiểm tay từng phần.
- Quay video demo song song với từng phase thay vì để dồn cuối.
