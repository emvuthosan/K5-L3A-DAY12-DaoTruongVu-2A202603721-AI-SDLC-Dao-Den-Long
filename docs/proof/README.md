# Bằng chứng kiểm chứng

Tái tạo: `python3 -m unittest discover -s tests -q` và `python3 tests/run_proof.py` (đầu ra jsonl trong `docs/proof/phase1/` do chương trình sinh, không sửa tay). Máy: Windows 10, Python 3.11.9.

## Phase 1

| Yêu cầu | Cách kiểm chứng | Bằng chứng | Kết quả |
|---|---|---|---|
| contract `game.contract.json` đủ trường | `tests/test_game.py::Contract` | 21/21 test xanh | Đạt |
| Di chuyển, chuẩn hóa chéo, quy đổi `cam_yaw_deg`, nhảy | `Movement` | unit test | Đạt |
| Nhặt đom đóm (bán kính, sức chứa, điểm) | `Lanterns` | unit test | Đạt |
| Nạp ánh sáng, thắp đèn, thắng + điểm | `test_light_all_and_win_score`, scenario `win_two_trips` | `phase1/win_two_trips.jsonl` (end: won, score 439) | Đạt |
| Bóng Mực: chạm, rơi ánh sáng, bất tử, thua hết lửa | `Shades` | unit test | Đạt |
| Tỏa sáng: tốn ánh sáng, cooldown, choáng, đẩy lùi, điểm | `test_pulse*` | unit test | Đạt |
| Vùng an toàn quanh đèn sáng | `test_safe_zone` | unit test | Đạt |
| Thua khi bình minh | `test_lose_dawn`, scenario `lose_dawn` | `phase1/lose_dawn.jsonl` | Đạt |
| Headless: định dạng, nhịp snapshot, dừng khi game over | `Headless` | unit test | Đạt |
| Tính tất định (cùng seed -> cùng đầu ra) | chạy seed 42 hai lần, so SHA-256 | `run_proof.py`: `15848cdbfd1b` = `15848cdbfd1b` | Đạt |
| File đầu vào hỏng -> exit 2 + stderr | `test_bad_files_exit_2` | unit test | Đạt |
| Bản chơi 3D: render, HUD, di chuyển bằng phím | Chạy server, mở trình duyệt, chụp ảnh | [phase1-gameplay.jpg](phase1-gameplay.jpg) (Mây, đom đóm, Bóng Mực, đèn, HUD); phím W làm z tăng 0.1 -> 2.4 | Đạt (một phần, xem dưới) |
| Chơi hết một ván thắng trên giao diện | — | — | **Chưa kiểm** bằng tay: mới xác nhận qua scenario headless |
| Chơi lại sau thắng/thua | Nút/phím R gọi `/restart` | gọi `/restart` thủ công trong phiên thử, ván mới bắt đầu tick 0 | Đạt (không chụp riêng nút) |

Giới hạn trung thực: các con số hiệu năng chưa đo (Phase 1 không yêu cầu); `dash` và sự kiện rơi không có (ghi trong README). Ảnh chụp lấy từ commit làm Phase 1; client chưa được điều chỉnh sau đó.
