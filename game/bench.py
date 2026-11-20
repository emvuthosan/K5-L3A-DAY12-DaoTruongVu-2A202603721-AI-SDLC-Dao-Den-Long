"""Benchmark (Ticket-04).

  python3 -m game.bench --seed 42 --duration 30 --out bench.json [--browser PATH] [--headless]

Starts the game server with the benchmark scene (night 1, 200 wandering Bóng Mực, 100 fireflies, L1-L3 lit,
idle player, camera orbiting at radius 30 m / height 15 m, 15 s per turn), opens it in a Chromium-family
browser at 1280x720 with vsync and the frame-rate limit disabled, measures every rendered frame after a 3 s
warm-up for --duration seconds, writes bench.json and exits with code 0.
"""
import argparse
import ctypes
import json
import math
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import threading
import time

T_START = time.time()                      # process start (for load_ms)

from .server import Game, QuietServer, make_handler    # noqa: E402
from .sim import load_contract            # noqa: E402


def find_browser(explicit=None):
    cands = [explicit, os.environ.get("BENCH_BROWSER")]
    if sys.platform == "win32":
        for base in (os.environ.get("PROGRAMFILES"), os.environ.get("PROGRAMFILES(X86)"), os.environ.get("LOCALAPPDATA")):
            if base:
                cands += [os.path.join(base, "Google", "Chrome", "Application", "chrome.exe"),
                          os.path.join(base, "Microsoft", "Edge", "Application", "msedge.exe"),
                          os.path.join(base, "Chromium", "Application", "chrome.exe")]
    elif sys.platform == "darwin":
        cands += ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                  "/Applications/Chromium.app/Contents/MacOS/Chromium",
                  "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"]
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge", "chrome"):
        cands.append(shutil.which(name))
    for c in cands:
        if c and os.path.isfile(c):
            return c
    return None


# ---- RSS of a process tree (the browser) -------------------------------------------------------------
def _win_tree_rss(root):
    class PE(ctypes.Structure):
        _fields_ = [("dwSize", ctypes.c_ulong), ("cntUsage", ctypes.c_ulong), ("th32ProcessID", ctypes.c_ulong),
                    ("th32DefaultHeapID", ctypes.c_size_t), ("th32ModuleID", ctypes.c_ulong),
                    ("cntThreads", ctypes.c_ulong), ("th32ParentProcessID", ctypes.c_ulong),
                    ("pcPriClassBase", ctypes.c_long), ("dwFlags", ctypes.c_ulong), ("szExeFile", ctypes.c_char * 260)]

    class PMC(ctypes.Structure):
        _fields_ = [("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong), ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t), ("a", ctypes.c_size_t), ("b", ctypes.c_size_t),
                    ("c", ctypes.c_size_t), ("d", ctypes.c_size_t), ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t)]
    k32, psapi = ctypes.windll.kernel32, ctypes.windll.psapi
    k32.CreateToolhelp32Snapshot.restype = ctypes.c_void_p
    k32.OpenProcess.restype = ctypes.c_void_p
    k32.Process32First.argtypes = k32.Process32Next.argtypes = [ctypes.c_void_p, ctypes.POINTER(PE)]
    k32.CloseHandle.argtypes = [ctypes.c_void_p]
    psapi.GetProcessMemoryInfo.argtypes = [ctypes.c_void_p, ctypes.POINTER(PMC), ctypes.c_ulong]
    snap = k32.CreateToolhelp32Snapshot(2, 0)
    parents, e = {}, PE()
    e.dwSize = ctypes.sizeof(PE)
    ok = k32.Process32First(snap, ctypes.byref(e))
    while ok:
        parents[e.th32ProcessID] = e.th32ParentProcessID
        ok = k32.Process32Next(snap, ctypes.byref(e))
    k32.CloseHandle(snap)
    tree, changed = {root}, True
    while changed:
        changed = False
        for pid, ppid in parents.items():
            if ppid in tree and pid not in tree:
                tree.add(pid)
                changed = True
    total = 0
    for pid in tree:
        h = k32.OpenProcess(0x1000, False, pid)         # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            continue
        pmc = PMC()
        pmc.cb = ctypes.sizeof(PMC)
        if psapi.GetProcessMemoryInfo(h, ctypes.byref(pmc), pmc.cb):
            total += pmc.WorkingSetSize
        k32.CloseHandle(h)
    return total / (1024.0 * 1024.0)


def _posix_tree_rss(root):
    out = subprocess.run(["ps", "-eo", "pid=,ppid=,rss="], capture_output=True, text=True).stdout
    rows = [tuple(int(x) for x in l.split()) for l in out.splitlines() if len(l.split()) == 3]
    tree, changed = {root}, True
    while changed:
        changed = False
        for pid, ppid, _ in rows:
            if ppid in tree and pid not in tree:
                tree.add(pid)
                changed = True
    return sum(r for pid, _, r in rows if pid in tree) / 1024.0


def tree_rss_mb(root):
    try:
        return _win_tree_rss(root) if sys.platform == "win32" else _posix_tree_rss(root)
    except Exception:
        return None


# ---- metrics (definitions from the ticket) -----------------------------------------------------------
def metrics(dts):
    n = len(dts)
    avg_fps = 1000.0 * n / sum(dts)
    k = max(1, math.ceil(0.01 * n))
    worst = sorted(dts, reverse=True)[:k]
    p1_low = 1000.0 / (sum(worst) / k)
    p95 = sorted(dts)[max(0, math.ceil(0.95 * n) - 1)]
    return n, avg_fps, p1_low, p95


def main(argv=None):
    ap = argparse.ArgumentParser(prog="game.bench")
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--duration", type=float, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--browser", help="path to a Chromium-family browser (default: auto-detect, or $BENCH_BROWSER)")
    ap.add_argument("--headless", action="store_true", help="no window (software rendering: slow, for CI smoke tests)")
    a = ap.parse_args(argv)
    if a.duration <= 0:
        print("error: --duration must be > 0", file=sys.stderr)
        return 2
    exe = find_browser(a.browser)
    if not exe:
        print("error: no Chrome/Chromium/Edge found; install one or pass --browser PATH", file=sys.stderr)
        return 1

    game = Game(bench_seed=a.seed)
    got = {"first": None, "report": None}
    ev = threading.Event()

    def on_first(_):
        got["first"] = time.time()

    def on_report(body):
        got["report"] = body
        ev.set()

    threading.Thread(target=game.loop, daemon=True).start()
    srv = QuietServer(("127.0.0.1", 0), make_handler(game, {"/bench_first_frame": on_first, "/bench_report": on_report}))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    port = srv.server_address[1]
    url = f"http://127.0.0.1:{port}/?bench=1&duration={a.duration:g}"

    prof = tempfile.mkdtemp(prefix="ddl-bench-")
    flags = ["--disable-gpu-vsync", "--disable-frame-rate-limit", "--window-size=1280,800", "--window-position=0,0",
             "--no-first-run", "--no-default-browser-check", "--disable-background-timer-throttling",
             "--disable-renderer-backgrounding", "--disable-backgrounding-occluded-windows",
             "--autoplay-policy=no-user-gesture-required", f"--user-data-dir={prof}"]
    if a.headless:
        flags += ["--headless=new", "--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"]
    proc = subprocess.Popen([exe] + flags + [url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    peak, stop = [0.0], threading.Event()

    def sampler():
        while not stop.is_set():
            if got["first"] is not None:
                m = tree_rss_mb(proc.pid)
                if m:
                    peak[0] = max(peak[0], m)
            stop.wait(1.0)

    threading.Thread(target=sampler, daemon=True).start()
    ok = ev.wait(timeout=a.duration + 120)
    stop.set()
    try:
        proc.terminate()
        proc.wait(timeout=10)
    except Exception:
        proc.kill()
    shutil.rmtree(prof, ignore_errors=True)
    srv.shutdown()
    if not ok or not got["report"] or not got["report"].get("dts"):
        print("error: the browser did not report any frames", file=sys.stderr)
        return 1

    rep = got["report"]
    n, avg_fps, p1_low, p95 = metrics(rep["dts"])
    ua = rep.get("ua", "")
    out = {
        "contract_version": load_contract()["contract_version"],
        "avg_fps": round(avg_fps, 1), "p1_low_fps": round(p1_low, 1), "frame_ms_p95": round(p95, 1),
        "frames": n, "load_ms": int(round((got["first"] - T_START) * 1000)),
        "peak_mem_mb": round(peak[0]) if peak[0] else None,
        "vsync_off": not a.headless,
        "renderer": f"{rep.get('renderer', '?')}; {os.path.basename(exe)}; viewport {rep.get('size')} dpr {rep.get('dpr')}; {ua[ua.find('Chrome'):ua.find('Chrome') + 40] if 'Chrome' in ua else ua}",
        "os": platform.platform(),
    }
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
