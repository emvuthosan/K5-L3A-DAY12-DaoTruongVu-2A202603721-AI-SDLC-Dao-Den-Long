# Kịch bản video demo (chưa quay)

Yêu cầu: `.mp4` dưới 5 phút, đính kèm GitHub Release `v1.0.0` (hoặc commit vào `docs/demo/demo.mp4` nếu < 100 MB), link ở đầu README.

**Trạng thái trung thực:** video này **chưa được quay** — phiên làm bài không có công cụ ghi màn hình/mã hóa video (không có ffmpeg). Cần người nộp tự quay theo kịch bản dưới đây (Windows: Win+Alt+R hoặc Xbox Game Bar; macOS: Cmd+Shift+5), nén bằng:

```
ffmpeg -i input.mov -t 290 -c:v libx264 -crf 28 -preset veryfast -c:a aac -b:a 96k demo.mp4
```

| Thời gian | Cảnh | Lệnh / thao tác |
|---|---|---|
| 0:00–0:20 | Giới thiệu, repo, tag `phase-1`…`phase-4` | `git tag --list`, `git log --oneline` |
| 0:20–1:30 | Chơi thật Đêm 1: nhặt đom đóm, thắp, châm dầu, Tỏa Sáng, Bóng Mực hút dầu | `python3 -m game.server` |
| 1:30–2:00 | Menu: Cài đặt (đổi phím, chữ lớn, mù màu), Bảng xếp hạng | |
| 2:00–3:00 | Bằng chứng: chạy test và scenario | `python3 -m unittest discover -s tests -q`, `python3 tests/run_proof.py` |
| 3:00–3:40 | Headless một Đêm | `python3 -m game.headless --seed 1 --night 3 --ticks 18000 --out out.jsonl` |
| 3:40–4:20 | Benchmark và soak | `python3 -m game.bench --seed 42 --duration 30 --out bench.json`, `python3 -m game.soak --seed 7 --nights 10 --out soak.json` |
| 4:20–4:50 | Lướt qua harness (`AGENTS.md`, skill `verify`, hook Stop) và CHANGELOG | |
