"""Local server: runs the same Sim as headless mode at 60 Hz and serves the 3D web client.

  python3 -m game.server [--port 8000] [--seed N] [--host 127.0.0.1]   then open http://localhost:8000
  python3 -m game.server --export-leaderboard out.json                  write the leaderboard and exit

Game flow (menu -> night intro -> play -> result -> next night -> dawn) lives here;
all rules live in game/sim.py.
"""
import argparse
import json
import mimetypes
import os
import random
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import leaderboard
from .sim import DT, Sim, bench_scenario, load_contract

WEB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")
NIGHTS = 3


class Game:
    def __init__(self, seed=None, first_night=1, bench_seed=None):
        self.first_night = first_night
        self.lock = threading.Lock()
        self.contract = load_contract()
        self.fixed_seed = seed
        self.inp = {"move": (0.0, 0.0), "cam_yaw_deg": 0.0, "jump": False, "interact": False,
                    "pulse": False, "dash": False, "pause": False}
        self.pause_ticks = 0
        self.phase = "menu"      # menu | intro | playing | result | dawn
        self.night = 1
        self.total = 0           # sum of the scores of the nights won
        self.nights_won = 0
        self.lb_saved = True
        self.sim = None
        self.banked = False
        self.bench_seed = bench_seed
        if bench_seed is not None:            # benchmark scene (Ticket-04): night 1, no gameplay
            self.sim = Sim(bench_seed, bench_scenario(bench_seed), self.contract, night=1, bench=True)
            self.phase = "playing"

    def _new_sim(self):
        seed = self.fixed_seed if self.fixed_seed is not None else random.randrange(1 << 30)
        self.sim = Sim(seed, None, self.contract, extras=True, night=self.night)
        self.sim._emit("night_start", {"night": self.night})
        self.banked = False
        self.pause_ticks = 0
        self.phase = "playing"

    def command(self, cmd):
        with self.lock:
            if self.bench_seed is not None:
                return
            if cmd == "new_game":
                self.night, self.total, self.nights_won, self.sim, self.phase = self.first_night, 0, 0, None, "intro"
            elif cmd == "begin" and self.phase == "intro":
                self._new_sim()
            elif cmd == "retry" and self.phase in ("result", "playing"):
                self._new_sim()
            elif cmd == "next" and self.phase == "result" and self.sim and self.sim.result == "won":
                if self.night < NIGHTS:
                    self.night += 1
                    self.sim, self.phase = None, "intro"
                else:
                    self.phase, self.lb_saved = "dawn", False
            elif cmd == "pause" and self.phase == "playing":
                self.pause_ticks = 2
            elif cmd == "menu":
                self.phase, self.sim = "menu", None

    def loop(self):
        nxt = time.perf_counter()
        while True:
            nxt += DT
            with self.lock:
                if self.phase == "playing" and self.sim:
                    self.inp["pause"] = self.pause_ticks == 2
                    if self.pause_ticks:
                        self.pause_ticks -= 1
                    self.sim.step(self.inp)
                    if self.sim.over:
                        self.phase = "result"
                        if self.sim.result == "won" and not self.banked:
                            self.total += self.sim.score
                            self.nights_won += 1
                            self.banked = True
                        elif self.sim.result == "lost":
                            self.lb_saved = False
            delay = nxt - time.perf_counter()
            if delay > 0:
                time.sleep(delay)
            elif delay < -0.25:
                nxt = time.perf_counter()

    def submit_score(self, name):
        with self.lock:
            lost = self.phase == "result" and self.sim is not None and self.sim.result == "lost"
            if not (lost or self.phase == "dawn") or self.lb_saved or self.bench_seed is not None:
                raise ValueError("nothing to save right now")
            seed = self.sim.seed if self.sim else 0
            entry = leaderboard.add(name, self.total, self.nights_won, seed)
            self.lb_saved = True
            return entry

    def state(self):
        with self.lock:
            s = self.sim
            lost = self.phase == "result" and s is not None and s.result == "lost"
            d = {"phase": self.phase, "night": self.night, "total": self.total, "nights_won": self.nights_won,
                 "can_save": bool((lost or self.phase == "dawn") and not self.lb_saved),
                 "bench": self.bench_seed is not None}
            if s is not None:
                snap = s.snapshot()
                snap.pop("type")
                d.update(snap)
                d["result"] = s.result
                d["capacity"] = s.capacity()
                d["relight_cost"] = s.t["relight_cost"]
                d["reason"] = s.reason
                d["lantern_cost"] = s.t["lantern_cost"]
                d["pulse_ready"] = s.pulse_cd == 0 and s.carried >= s.t["pulse_cost"]
                d["wind_warn"] = (s.night == 3 and s.wind_enabled and not s.wind_active
                                  and s.sim_tick % 1800 >= 1680)
                d["events"] = [{"seq": q, **e} for q, e in s.recent]
                d["seed"] = s.seed
            return d


class QuietServer(ThreadingHTTPServer):
    daemon_threads = True

    def handle_error(self, request, client_address):      # browsers closing sockets is normal
        pass


def make_handler(game, hooks=None):
    hooks = hooks or {}

    class H(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *a):
            pass

        def _send(self, code, body, ctype="application/json"):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            path = self.path.split("?")[0]
            if path == "/state":
                return self._send(200, json.dumps(game.state()).encode())
            if path == "/leaderboard":
                return self._send(200, json.dumps({"entries": leaderboard.load()}, ensure_ascii=False).encode("utf-8"))
            name = "index.html" if path == "/" else path.lstrip("/")
            full = os.path.normpath(os.path.join(WEB, name))
            if not full.startswith(WEB) or not os.path.isfile(full):
                return self._send(404, b"not found", "text/plain")
            ctype = "text/javascript" if full.endswith(".js") else (mimetypes.guess_type(full)[0] or "text/plain")
            with open(full, "rb") as f:
                self._send(200, f.read(), ctype)

        def do_POST(self):
            n = int(self.headers.get("Content-Length", 0))
            try:
                body = json.loads(self.rfile.read(n) or b"{}")
            except ValueError:
                return self._send(400, b"{}")
            if self.path == "/input":
                m = body.get("move", [0, 0])
                game.inp.update({"move": (float(m[0]), float(m[1])), "cam_yaw_deg": float(body.get("yaw", 0)),
                                 "jump": bool(body.get("jump")), "interact": bool(body.get("interact")),
                                 "pulse": bool(body.get("pulse")), "dash": bool(body.get("dash"))})
            elif self.path == "/cmd":
                game.command(str(body.get("cmd", "")))
            elif self.path == "/leaderboard":
                try:
                    entry = game.submit_score(body.get("name"))
                except ValueError as e:
                    return self._send(400, json.dumps({"error": str(e)}, ensure_ascii=False).encode("utf-8"))
                return self._send(200, json.dumps({"entry": entry, "entries": leaderboard.load()},
                                                  ensure_ascii=False).encode("utf-8"))
            elif self.path in hooks:
                hooks[self.path](body)
            else:
                return self._send(404, b"{}")
            self._send(200, b"{}")

    return H


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--seed", type=int)
    ap.add_argument("--night", type=int, default=1, choices=(1, 2, 3), help="first night (for testing)")
    ap.add_argument("--export-leaderboard", metavar="OUT.json", help="write the leaderboard as JSON and exit")
    a = ap.parse_args()
    if a.export_leaderboard:
        leaderboard.export(a.export_leaderboard)
        return 0
    game = Game(a.seed, a.night)
    threading.Thread(target=game.loop, daemon=True).start()
    srv = QuietServer((a.host, a.port), make_handler(game))
    print(f"Dao Den Long: open http://localhost:{a.port}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
