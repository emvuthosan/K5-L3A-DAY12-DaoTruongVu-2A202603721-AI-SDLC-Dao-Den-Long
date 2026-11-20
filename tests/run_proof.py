"""Regenerates docs/proof/phase1/*.jsonl and checks them. Usage: python3 tests/run_proof.py"""
import hashlib, json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "proof", "phase1")
os.makedirs(OUT, exist_ok=True)
S = os.path.join(ROOT, "tests", "scenarios")


def run(name, *extra):
    out = os.path.join(OUT, name + ".jsonl")
    cmd = [sys.executable, "-m", "game.headless", "--night", "1", *extra, "--out", out]
    subprocess.run(cmd, cwd=ROOT, check=True)
    with open(out, "rb") as f:
        return out, hashlib.sha256(f.read()).hexdigest()[:12]


rows = []
a = run("random_seed42_run1", "--seed", "42", "--ticks", "3000")
b = run("random_seed42_run2", "--seed", "42", "--ticks", "3000")
rows.append(("determinism: same seed twice", a[1] == b[1], f"{a[1]} vs {b[1]}"))
w = run("win_two_trips", "--seed", "1", "--scenario", f"{S}/win_two_trips.json",
        "--inputs", f"{S}/win_two_trips.inputs.json", "--ticks", "600")
end = json.loads(open(w[0]).read().splitlines()[-1])
rows.append(("scenario win_two_trips ends won", end["state"] == "won", json.dumps(end)))
d = run("lose_dawn", "--seed", "1", "--scenario", f"{S}/lose_dawn.json", "--ticks", "500")
end = json.loads(open(d[0]).read().splitlines()[-1])
rows.append(("scenario lose_dawn ends lost at tick 30", end["state"] == "lost" and end["ticks"] == 30, json.dumps(end)))
for r in rows:
    print(("PASS" if r[1] else "FAIL"), r[0], "-", r[2])
sys.exit(0 if all(r[1] for r in rows) else 1)
