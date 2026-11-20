"""Local server: runs the same Sim as headless mode at 60 Hz and serves the 3D web client.

  python3 -m game.server [--port 8000] [--seed N]   then open http://localhost:8000
"""
import argparse
import json
import mimetypes
import os
import random
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .sim import DT, Sim, load_contract

WEB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")


class Game:
    def __init__(self, seed):
        self.lock = threading.Lock()
        self.contract = load_contract()
        self.inp = {"move": (0.0, 0.0), "cam_yaw_deg": 0.0, "jump": False, "interact": False, "pulse": False}
        self.reset(seed)

    def reset(self, seed=None):
        with self.lock:
            self.seed = seed if seed is not None else random.randrange(1 << 30)
            self.sim = Sim(self.seed, None, self.contract, extras=True)

    def loop(self):
        nxt = time.perf_counter()
        while True:
            nxt += DT
            with self.lock:
                self.sim.step(self.inp)
            delay = nxt - time.perf_counter()
            if delay > 0:
                time.sleep(delay)
            elif delay < -0.25:
                nxt = time.perf_counter()

    def state(self):
        with self.lock:
            s = self.sim
            d = s.snapshot()
            d.pop("type")
            d["invuln"] = s.invuln > 0
            d["pulse_ready"] = s.pulse_cd == 0 and s.carried >= s.t["pulse_cost"]
            d["capacity"] = s.t["carry_capacity"]
            d["lantern_cost"] = s.t["lantern_cost"]
            d["events"] = [{"seq": q, **e} for q, e in s.recent]
            d["seed"] = self.seed
            return d


def make_handler(game):
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
                game.inp = {"move": (float(m[0]), float(m[1])), "cam_yaw_deg": float(body.get("yaw", 0)),
                            "jump": bool(body.get("jump")), "interact": bool(body.get("interact")),
                            "pulse": bool(body.get("pulse"))}
            elif self.path == "/restart":
                game.reset()
            else:
                return self._send(404, b"{}")
            self._send(200, b"{}")

    return H


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--seed", type=int)
    a = ap.parse_args()
    game = Game(a.seed)
    threading.Thread(target=game.loop, daemon=True).start()
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), make_handler(game))
    print(f"Dao Den Long: open http://localhost:{a.port}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
