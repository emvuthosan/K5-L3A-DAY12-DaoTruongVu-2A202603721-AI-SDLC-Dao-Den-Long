"""Regenerates docs/proof/phase3/*.jsonl by running the headless CLI, then checks them.

Usage: python3 tests/run_proof.py     (exit code 0 only if every check passes)
"""
import hashlib
import json
import math
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "proof", "phase3")
SCN = os.path.join(ROOT, "tests", "scenarios")
os.makedirs(OUT, exist_ok=True)


def headless(name, night, ticks, seed=1, scenario=None):
    out = os.path.join(OUT, name + ".jsonl")
    cmd = [sys.executable, "-m", "game.headless", "--seed", str(seed), "--night", str(night),
           "--ticks", str(ticks), "--out", out]
    if scenario:
        cmd += ["--scenario", os.path.join(SCN, scenario + ".json"),
                "--inputs", os.path.join(SCN, scenario + ".inputs.json")]
    t0 = time.time()
    subprocess.run(cmd, cwd=ROOT, check=True)
    with open(out, encoding="utf-8") as f:
        rows = [json.loads(l) for l in f]
    with open(out, "rb") as f:
        digest = hashlib.sha256(f.read()).hexdigest()[:12]
    return rows, digest, time.time() - t0


def evs(rows, name):
    return [r for r in rows if r["type"] == "event" and r["name"] == name]


def snaps(rows):
    return [r for r in rows if r["type"] == "snapshot"]


def at(rows, tick):
    return next(r for r in snaps(rows) if r["tick"] == tick)


results = []


def check(label, ok, detail=""):
    results.append((label, bool(ok), detail))


def scenario(name, night, ticks, fn):
    rows, digest, _ = headless(name, night, ticks, scenario=name)
    ok, detail = fn(rows)
    check(f"scenario {name} (night {night})", ok, f"{detail} [{digest}]")


def win(rows):
    e = rows[-1]
    return e["state"] == "won" and len(evs(rows, "deposit")) == 2, json.dumps(e)


def lose(rows):
    e = rows[-1]
    return e["state"] == "lost" and e["ticks"] == 30, json.dumps(e)


def dash(rows):
    e = evs(rows, "dash")
    z = at(rows, 20)["player"]["pos"][2]
    return len(e) == 1 and e[0]["tick"] == 1 and 3.5 < z < 4.5, f"dash@{e[0]['tick']} z@20={z}"


def pause(rows):
    last = snaps(rows)[-1]
    ok = len(evs(rows, "paused")) == 1 and len(evs(rows, "resumed")) == 1 and last["sim_tick"] == last["tick"] - 30
    return ok, f"tick={last['tick']} sim_tick={last['sim_tick']}"


def fall(rows):
    e = evs(rows, "player_hit")[0]
    last = snaps(rows)[-1]["player"]
    ok = e["data"]["by"] == "fall" and e["data"]["lost"] == 4 and e["data"]["flames"] == 2         and (last["pos"] == [0, 0, 0] or last["invuln"] > 0)
    return ok, f"{e['data']} last={last['pos']}"


def ramp(rows):
    y = snaps(rows)[-1]["player"]["pos"][1]
    return y == 3.0, f"y={y}"


def pad2(rows):
    p = snaps(rows)[-1]["player"]
    x, z = p["pos"][0], p["pos"][2]
    return p["grounded"] and (x - 70) ** 2 + z * z <= 784, f"landed ({x},{z})"


def pad3(rows):
    p = snaps(rows)[-1]["player"]
    return p["pos"][1] == 6.0 and p["grounded"], f"landed {p['pos']}"


def wind(rows):
    before, on, off = at(rows, 1790), at(rows, 1810), at(rows, 2100)
    a, b = before["player"]["pos"], off["player"]["pos"]
    d = math.hypot(b[0] - a[0], b[2] - a[2])
    ok = not before["wind"]["active"] and on["wind"]["active"] and not off["wind"]["active"] and abs(d - 10) < 0.2
    return ok, f"displacement {d:.3f} m (expected 10) dir={on['wind']['dir_deg']}"


def charm(rows):
    e = evs(rows, "charm_picked")
    return len(e) == 1 and e[0]["data"] == {"charm_id": "C1", "charm_ticks": 600}, str(e[0]["data"])


def steal(rows):
    e = evs(rows, "drifter_steal")
    return len(e) == 1 and e[0]["data"]["amount"] == 3, str(e[0]["data"])


def drop(rows):
    e = evs(rows, "drifter_drop")
    return len(e) == 1 and e[0]["data"]["amount"] == 3, str(e[0]["data"])


def pulse(rows):
    e = evs(rows, "pulse")[0]
    return e["data"]["stunned_ids"] == ["A"] and rows[-1]["score"] == 5, str(e["data"])


def out_relight(rows):
    names_ = [(e["tick"], e["name"], e["data"]) for e in rows if e["type"] == "event"]
    out = [x for x in names_ if x[1] == "lantern_out"]
    lit = [x for x in names_ if x[1] == "lantern_lit"]
    ok = (len(out) == 1 and out[0][0] == 180 and len(lit) == 1 and lit[0][2]["relight"] is True
          and rows[-1]["score"] == 5 * 5 + 40)
    return ok, f"out@{out[0][0] if out else None} relight={lit[0][2] if lit else None} score={rows[-1]['score']}"


def refuel(rows):
    e = evs(rows, "refuel")
    ok = len(e) == 1 and e[0]["data"]["amount"] == 6 and e[0]["data"]["fuel"] == 100.0
    return ok, str(e[0]["data"]) if e else "no refuel"


def drain(rows):
    d = evs(rows, "fuel_drain")
    out = evs(rows, "lantern_out")
    states = {s["state"] for r in snaps(rows) for s in r["shades"]}
    return bool(d) and len(out) == 1 and "drain" in states, f"drain events={len(d)} out@{out[0]['tick'] if out else None}"


def dawn_win(rows):
    e = rows[-1]
    g = evs(rows, "game_over")[0]["data"]
    return e["state"] == "won" and g["reason"] == "dawn_survived" and e["ticks"] == 120, f"{g} score={e['score']}"


def dawn_lose(rows):
    g = evs(rows, "game_over")[0]["data"]
    return rows[-1]["state"] == "lost" and g["reason"] == "dawn", str(g)


def capacity(rows):
    a, b = at(rows, 0)["player"]["capacity"], snaps(rows)[-1]["player"]["capacity"]
    return (a, b) == (10, 12), f"capacity {a} -> {b} after one light"


def zone(rows):
    zs = [s["pos"][2] for r in snaps(rows) for s in r["shades"]]
    return max(zs) <= 19.001 and zs[-1] > 18.9, f"max shade z={max(zs)}, final {zs[-1]} (zone edge 19)"


for name, night, ticks, fn in [
        ("win_two_trips", 1, 600, win), ("lose_dawn", 1, 500, lose), ("dash", 1, 60, dash),
        ("pause", 1, 80, pause), ("fall", 1, 200, fall), ("tiers_ramp", 3, 140, ramp),
        ("pad_night2", 2, 150, pad2), ("pad_night3", 3, 150, pad3), ("wind", 3, 2200, wind),
        ("fuel_out_relight", 1, 400, out_relight), ("refuel", 1, 20, refuel), ("drain", 1, 1500, drain),
        ("dawn_win", 1, 400, dawn_win), ("dawn_lose", 1, 400, dawn_lose), ("capacity", 1, 20, capacity),
        ("charm", 2, 100, charm), ("drifter_steal", 2, 200, steal),
        ("drifter_pulse_drop", 2, 10, drop), ("pulse_shade", 1, 140, pulse), ("safe_zone", 1, 300, zone)]:
    scenario(name, night, ticks, fn)

for night in (1, 2, 3):
    a = headless(f"determinism_night{night}_run1", night, 3000, seed=42)
    b = headless(f"determinism_night{night}_run2", night, 3000, seed=42)
    check(f"determinism night {night} (seed 42 twice)", a[1] == b[1], f"{a[1]} vs {b[1]}")

# longest night (night 3 = 300 s = 18000 ticks) must finish in <= 30 s
sc_path = os.path.join(OUT, "_long_scenario.json")
with open(sc_path, "w") as f:
    json.dump({"player": {"flames": 100000, "carried": 9}}, f)
t0 = time.time()
subprocess.run([sys.executable, "-m", "game.headless", "--seed", "3", "--night", "3", "--ticks", "21600",
                "--scenario", sc_path, "--out", os.path.join(OUT, "_long.jsonl")], cwd=ROOT, check=True)
dt = time.time() - t0
os.remove(sc_path)
os.remove(os.path.join(OUT, "_long.jsonl"))
check("full night 3 (18000 ticks) headless <= 30 s", dt <= 30, f"{dt:.2f} s")

for label, ok, detail in results:
    print("PASS" if ok else "FAIL", label, "-", detail)
sys.exit(0 if all(ok for _, ok, _ in results) else 1)
