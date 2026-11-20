# Đảo Đèn Lồng

> Video demo: _(chưa có — sẽ đặt link Release `v1.0.0` ở đây sau Phase 4)_
> Đề bài lab gốc: [LAB-README.md](LAB-README.md) · Ghi chép: [docs/notes](docs/notes) · Bằng chứng: [docs/proof](docs/proof/README.md)

Game 3D góc nhìn thứ ba. Bạn là **Mây**, người giữ đèn nhỏ tuổi: gom đom đóm, thắp lại các **Đèn Lồng Lớn** trên ba hòn đảo và né **Bóng Mực** trong sương đen. Hiện đã xong **Phase 3** (Đèn cạn dầu, Test Contract v1.2).

## Cài đặt và chạy (2 lệnh)

Cần Python 3.9+ (không cần cài thêm thư viện) và trình duyệt có WebGL. Chạy được trên macOS, Linux, Windows.

```
git clone <repo> && cd <repo>
python3 -m game.server        # rồi mở http://localhost:8000
```

## Điều khiển

| Phím | Việc |
|---|---|
| W A S D | Di chuyển (theo hướng camera) |
| Space | Nhảy |
| Shift | Lướt (14 m/s trong 0.2 s, hồi 1.5 s) |
| E | Nạp ánh sáng vào đèn lồng gần nhất (trong 2 m) |
| F | Tỏa Sáng: choáng và đẩy lùi Bóng Mực trong 5 m (tốn 3 đom đóm, hồi 3 s) |
| Kéo chuột / ← → | Xoay camera (độ nhạy chỉnh trong Cài đặt) |
| Esc / P | Tạm dừng (Tiếp tục, Chơi lại Đêm, Cài đặt, Về menu) |

## Luật

- Ba Đêm: **Đảo Bến** (5 đèn, 240 s), **Đảo Cau** (hai đảo nối cầu tre, bục nhảy, Bùa Gió, Gió Lạc; 6 đèn, 270 s), **Đảo Chuông** (3 tầng, dốc, tháp, gió mạnh; 7 đèn, 300 s). Thắng Đêm 3 là màn Bình Minh; thua thì chơi lại Đêm đó.
- **Mục tiêu: giữ đảo sáng tới bình minh.** Thắng khi Mây còn sống lúc hết giờ và số đèn đang sáng ≥ 60% (3/5, 4/6, 5/7). Thắp đủ đèn không kết thúc Đêm.
- **Đèn có dầu:** thắp lần đầu cần 10 đom đóm, dầu 100 và hao 1/s; bấm E ở đèn đang sáng để châm dầu (10 dầu mỗi đom đóm). Hết dầu đèn tắt, thắp lại chỉ cần 5 đom đóm. Đèn dầu < 30 mất vùng an toàn và nhấp nháy; **Bóng Mực** đi lang thang sẽ tới hút dầu (5/s) đèn yếu.
- Sức chứa đom đóm = 10 + 2 × số lần thắp thành công (tối đa 20).
- Nhặt đom đóm (≤ 1 m). Bóng Mực chạm vào: −1 Ngọn Lửa (có 3), rơi một nửa đom đóm đang mang, bất tử 1.5 s. Rơi khỏi đảo: −1 Ngọn Lửa, mất hết đom đóm, hồi sinh sau 1 s. Đèn sáng có dầu ≥ 30 có vùng an toàn bán kính 6 m.
- **Gió Lạc** cướp tối đa 3 đom đóm của người mang ≥ 5; Tỏa Sáng đuổi nó và lấy lại đồ. **Bùa Gió** (10 s): chạy 7.2 m/s, lướt không hồi chiêu.
- Điểm: +5 mỗi đom đóm nạp/châm, +100 thắp lần đầu, +40 thắp lại, +5 mỗi Bóng Mực trúng Tỏa Sáng (+15 nếu nó đang hút dầu); bình minh (khi thắng): +50 + dầu cho mỗi đèn sáng và +50 mỗi Ngọn Lửa còn lại. Tổng điểm là tổng các Đêm đã thắng.

Số liệu chuẩn: [game.contract.json](game.contract.json). Spec: [phase 2](docs/notes/spec-phase2.md), [phase 3](docs/notes/spec-phase3.md). Quyết định thiết kế: [ADR-0003](docs/notes/ADR-0003-fuel-and-dawn-rule.md). Thay đổi phá vỡ: [CHANGELOG.md](CHANGELOG.md). Giả định: [docs/notes/assumptions.md](docs/notes/assumptions.md).

## Test và chế độ headless

```
python3 -m unittest discover -s tests -q      # 77 test
python3 tests/run_proof.py                    # 20 scenario, tính tất định, đo 1 Đêm; ghi docs/proof/phase3
python3 -m game.headless --seed 1 --night 1 --ticks 600 --out out.jsonl \
    [--scenario f.json] [--inputs f.json] [--snapshot-every 10]
```

Headless theo Test Contract v1.2 (60 tick/s, `--night 1|2|3`, JSONL snapshot / event / end, tạm dừng bằng `pause`, file hỏng -> exit 2). Một Đêm đầy đủ (tối đa 18 000 tick) chạy xong trong vài giây. Logic nằm hoàn toàn trong `game/sim.py`; server web và headless dùng chung nó.

## Sáng tạo của tôi

**Đom đóm vàng** (chỉ trong bản chơi): mỗi 25 s một đom đóm vàng lớn xuất hiện, nhặt được 3 ánh sáng một lần. Bật bằng `Sim(extras=True)` và RNG riêng, nên headless và đầu ra Test Contract không đổi. Bằng chứng: `run_proof.py` chạy headless (extras tắt) vẫn tất định, và test dùng `Sim` mặc định (extras tắt).

## Harness AI

[AGENTS.md](AGENTS.md), skill [.claude/skills/verify](.claude/skills/verify/SKILL.md), hook `Stop` chạy test ([.claude/settings.json](.claude/settings.json)), CI [.github/workflows/test.yml](.github/workflows/test.yml).
