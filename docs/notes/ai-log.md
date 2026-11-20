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


# Phase 3 (Ticket-03)

Token Phase 3: **ước tính** 150–250k (sửa sim bằng patch có kiểm `assert`, test mới, client). Là ước tính.

Quyết định: dầu lưu số nguyên 1/60 (ADR-0003) vì ticket yêu cầu rõ và vì ngưỡng "đúng 30" cần chính xác. Sửa `sim.py` bằng script vá có assert từng đoạn thay vì viết lại, để diff nhỏ và biết ngay nếu mỏ neo không khớp.

Lỗi của AI / lần sai và cách phát hiện:
1. Trạng thái `drain` còn tiếp tục hút dầu trong lúc bóng đang bị "đẩy ra" sau khi đèn được châm ≥ 30 (đọc lại luồng: vòng hút ở bước 2 đếm theo `state == "drain"`, còn nhánh đẩy ra `continue` trước khi đổi trạng thái). Phát hiện khi tự rà ticket-vs-code trước khi chạy test; sửa ở bước 6 (đổi về `wander` khi bắt đầu đẩy ra) và có test `test_refuel_expels_harmlessly`.
2. Hai test của tôi viết sai kỳ vọng: pulse đặt bóng cách 5.0 m nhưng khoảng cách 3D (tâm +0.8) làm nó ngoài tầm; scenario headless có đèn L1 bị chính lệnh châm dầu làm đầy nên không bao giờ tắt. Test đỏ → đối chiếu với ticket → sửa test, không nới assert. Scenario `refuel` kỳ vọng 5 đom đóm nhưng đúng luật là 6 (hao dầu trước tương tác): sửa kỳ vọng + ghi giả định #29.
3. Lệnh shell nhiều dấu nháy lại lỗi: chuyển sang ghi script vá ra file.
Harness chỉnh: AGENTS.md ghi "đèn: dùng `_zone`, dầu là số nguyên 1/60"; skill `verify` trỏ tới `docs/proof/phase3`.

# Phase 4 (Ticket-04)

Token Phase 4: **ước tính** 300–400k (client viết lại, bench/soak/bảng xếp hạng, test, tài liệu). Là ước tính.

Quyết định: bản chơi là web nên benchmark chạy trình duyệt thật (không headless) và đo `requestAnimationFrame` từ trang; số đo tải từ trang về server Python qua `/bench_report`, server tính các chỉ số đúng định nghĩa của ticket (có test đơn vị cho công thức). Vẽ bằng `InstancedMesh` để 200 Bóng Mực + 100 đom đóm chỉ tốn 6 draw call.

Lỗi của AI / lần sai trong phase này:
1. Benchmark đầu báo ≈1800 FPS (rAF không chờ GPU) → thêm `readPixels` mỗi khung, còn ≈430 FPS; ghi vào giả định #39.
2. Lần chạy benchmark 30 s đầu treo (trình duyệt/cửa sổ) và bị `timeout` bao ngoài không dừng được tiến trình con trên Windows; phải kill tay rồi chạy lại ở nền. Ghi nhận như hạn chế của lệnh `timeout` trên Windows.
3. Sót kiểm cỡ chữ: kiểm bằng JS tìm ra nút/ô nhập mặc định 13.3 px (nằm ngoài `.screen`) → thêm quy tắc `button,input{font-size:1rem}`.
4. Kiểm tay giao diện bị chặn: ván đứng yên không thua nên không tới màn nhập tên; kiểm logic lưu bằng test gọi trực tiếp `Game.submit_score` thay vì chơi qua giao diện (ghi rõ trong proof).
Harness chỉnh: AGENTS.md thêm lệnh bench/soak/export và quy ước "cảnh bench không có thêm thứ gì".
