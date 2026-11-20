"""Soak test (Ticket-04): many nights in ONE process with seeded random input.

  python3 -m game.soak --seed 7 --nights 10 --out soak.json

Night i (i = 1..N) uses night ((i - 1) % 3) + 1 and seed = seed + i. Input: every 30 ticks a new random
move direction; every tick 5% jump, 3% dash, 2% pulse, 10% interact.
"""
import argparse
import ctypes
import gc
import json
import math
import os
import random
import subprocess
import sys
import time

from .sim import Sim


def rss_mb():
    """Resident set size of this process in MB (current, not peak)."""
    try:
        if sys.platform.startswith("linux"):
            with open("/proc/self/status") as f:
                for line in f:
                    if line.startswith("VmRSS:"):
                        return int(line.split()[1]) / 1024.0
        if sys.platform == "win32":
            class PMC(ctypes.Structure):
                _fields_ = [("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong),
                            ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                            ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]
            pmc = PMC()
            pmc.cb = ctypes.sizeof(PMC)
            h = ctypes.windll.kernel32.GetCurrentProcess()
            ctypes.windll.psapi.GetProcessMemoryInfo.argtypes = [ctypes.c_void_p, ctypes.POINTER(PMC), ctypes.c_ulong]
            if ctypes.windll.psapi.GetProcessMemoryInfo(ctypes.c_void_p(h), ctypes.byref(pmc), pmc.cb):
                return pmc.WorkingSetSize / (1024.0 * 1024.0)
        out = subprocess.run(["ps", "-o", "rss=", "-p", str(os.getpid())], capture_output=True, text=True)
        return int(out.stdout.strip()) / 1024.0
    except Exception:
        return None


def random_inputs(rng):
    """Returns a function tick -> input dict."""
    state = {"move": (0.0, 0.0)}

    def inp(tick):
        if tick % 30 == 0:
            a = rng.random() * 2 * math.pi
            state["move"] = (math.cos(a), math.sin(a)) if rng.random() < 0.9 else (0.0, 0.0)
        return {"move": state["move"], "cam_yaw_deg": 0.0,
                "jump": rng.random() < 0.05, "dash": rng.random() < 0.03,
                "pulse": rng.random() < 0.02, "interact": rng.random() < 0.10}
    return inp


def run_night(i, seed):
    night = (i - 1) % 3 + 1
    s = Sim(seed + i, None, night=night)
    rng = random.Random((seed + i) * 31 + 5)
    inp = random_inputs(rng)
    return s, inp


def main(argv=None):
    ap = argparse.ArgumentParser(prog="game.soak")
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--nights", type=int, required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    if a.nights < 1:
        print("error: --nights must be >= 1", file=sys.stderr)
        return 2
    t0 = time.time()
    results, crashes = [], 0
    mem_start = None
    for i in range(1, a.nights + 1):
        try:
            sim, inp = run_night(i, a.seed)
            if mem_start is None:
                gc.collect()
                mem_start = rss_mb()                       # after the first night is loaded
            k = 0
            while not sim.over:
                sim.step(inp(k))
                k += 1
            results.append(sim.result)
        except Exception as e:                              # a crash is counted, the soak keeps going
            crashes += 1
            results.append("crash")
            print(f"night {i} crashed: {e!r}", file=sys.stderr)
        finally:
            sim = inp = None
    gc.collect()
    mem_end = rss_mb()                                      # after the last night has been reset/released
    out = {"nights": a.nights, "crashes": crashes, "results": results,
           "mem_start_mb": None if mem_start is None else round(mem_start, 1),
           "mem_end_mb": None if mem_end is None else round(mem_end, 1),
           "duration_s": round(time.time() - t0, 1)}
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(out, f)
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
