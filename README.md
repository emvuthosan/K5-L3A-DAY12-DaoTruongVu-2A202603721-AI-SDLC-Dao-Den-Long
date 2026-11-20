# Đảo Đèn Lồng

> Video demo: _(chưa có — sẽ đặt link Release `v1.0.0` ở đây sau Phase 4)_
> Đề bài lab gốc: [LAB-README.md](LAB-README.md) · Ghi chép: [docs/notes](docs/notes) · Bằng chứng: [docs/proof](docs/proof/README.md)

Game 3D góc nhìn thứ ba. Bạn là **Mây**, người giữ đèn nhỏ tuổi: gom đom đóm, thắp lại **5 Đèn Lồng Lớn** trên đảo và né **Bóng Mực** trong sương đen. Hiện đã xong **Phase 1** (Đêm 1 – Đảo Bến).

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
| E | Đưa ánh sáng vào đèn lồng gần nhất (đứng trong 2.5 m) |
| F | Tỏa sáng: choáng và đẩy lùi Bóng Mực trong 5 m (tốn 1 ánh sáng) |
| Kéo chuột / ← → | Xoay camera |
| R | Chơi lại (cũng có nút khi thắng/thua) |

## Luật và cách tính điểm

- Nhặt đom đóm bằng cách đi lại gần (≤ 1.2 m). Mang tối đa **5** ánh sáng. Mỗi đèn cần **10** ánh sáng (nhiều chuyến). Thắp đủ 5 đèn trước bình minh (**180 s**) là thắng.
- Bóng Mực đuổi theo Mây; chạm vào mất **1 ngọn lửa** (có 3), rơi một nửa ánh sáng đang mang và bất tử 1.5 s. Hết ngọn lửa là thua; hết giờ cũng thua. Bóng Mực không vào được vòng 4 m quanh đèn đã sáng.
- Điểm: +1 mỗi đom đóm, +100 mỗi đèn thắp, +5 mỗi Bóng Mực bị choáng; khi thắng thêm +1 mỗi giây còn lại và +50 mỗi ngọn lửa còn lại.

Mọi số liệu nằm trong [game.contract.json](game.contract.json). Các giả định chỗ PRD chưa nói: [docs/notes/assumptions.md](docs/notes/assumptions.md).

## Test và chế độ headless

```
python3 -m unittest discover -s tests -q      # 21 test
python3 tests/run_proof.py                    # chạy scenario, kiểm tra tính tất định, ghi docs/proof/phase1
python3 -m game.headless --seed 1 --night 1 --ticks 600 --out out.jsonl \
    [--scenario f.json] [--inputs f.json] [--snapshot-every 10]
```

Headless theo Test Contract v1.0 (60 tick/s, không cần cửa sổ, JSONL gồm snapshot / event / end, file đầu vào hỏng -> exit 2). Không có `dash`; `fall_enabled=false` nên không có sự kiện rơi (ghi `false` trong contract). Logic nằm hoàn toàn trong `game/sim.py`; server web và headless dùng chung nó.

## Sáng tạo của tôi

**Đom đóm vàng** (chỉ trong bản chơi): mỗi 25 s một đom đóm vàng lớn xuất hiện, nhặt được 3 ánh sáng một lần. Bật bằng `Sim(extras=True)` và RNG riêng, nên headless và đầu ra Test Contract không đổi. Bằng chứng: bài test `test_deterministic` và `run_proof.py` chạy headless (extras tắt) vẫn ra kết quả giống hệt qua hai lần chạy.

## Harness AI

[AGENTS.md](AGENTS.md), skill [.claude/skills/verify](.claude/skills/verify/SKILL.md), hook `Stop` chạy test ([.claude/settings.json](.claude/settings.json)), CI [.github/workflows/test.yml](.github/workflows/test.yml).
