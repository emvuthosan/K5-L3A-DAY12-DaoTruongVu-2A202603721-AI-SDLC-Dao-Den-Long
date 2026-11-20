"""Deterministic simulation core for Đảo Đèn Lồng (no rendering, no I/O).

Fixed 60 ticks/s. Units are meters, Y is up, ground is Y=0.
All horizontal distances are measured on the XZ plane.
"""
import json
import math
import os
import random

TICKS_PER_S = 60
DT = 1.0 / TICKS_PER_S
ISLAND_R = 30.0          # round island radius (player and shades are kept inside)
LANTERN_RING_R = 16.0    # lanterns sit on this ring, 72 degrees apart
GRAVITY = 20.0
JUMP_SPEED = 8.0
INITIAL_MOTES = 60
INITIAL_SHADES = 3
SHADE_SPAWN_EVERY_S = 20
SHADE_MAX = 6
GOLDEN_EVERY_S = 25      # extras only (never in headless)
GOLDEN_VALUE = 3

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class ScenarioError(ValueError):
    """Bad scenario or inputs file (headless exits with code 2)."""


def load_contract(path=None):
    with open(path or os.path.join(ROOT, "game.contract.json"), encoding="utf-8") as f:
        return json.load(f)


def r3(v):
    v = round(v, 3)
    return 0.0 if v == 0 else v  # avoid -0.0


def _pos(v, what, default_y=0.0):
    if (not isinstance(v, (list, tuple)) or len(v) not in (2, 3)
            or any(isinstance(c, bool) or not isinstance(c, (int, float)) for c in v)):
        raise ScenarioError(f"{what}: pos must be [x,y,z] (or [x,z]) numbers")
    if len(v) == 2:
        return float(v[0]), default_y, float(v[1])
    return float(v[0]), float(v[1]), float(v[2])


def _num(v, what):
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise ScenarioError(f"{what} must be a number")
    return v


def lantern_positions(n=5):
    out = []
    for i in range(n):
        a = math.radians(i * 72.0)
        out.append((LANTERN_RING_R * math.sin(a), LANTERN_RING_R * math.cos(a)))
    return out


class Sim:
    def __init__(self, seed=0, scenario=None, contract=None, extras=False):
        c = contract or load_contract()
        self.t = c["tuning"]
        self.sc = c["score"]
        self.rng = random.Random(seed)
        self.xrng = random.Random(seed + 1_000_003)  # extras use their own stream
        self.extras = extras
        self.seed = seed
        sc = scenario or {}
        if not isinstance(sc, dict):
            raise ScenarioError("scenario must be a JSON object")

        self.tick = 0
        self.state = "playing"
        self.score = 0
        self.events = []        # events produced by the last step
        self.recent = []        # rolling log for UI: (seq, event)
        self._seq = 0
        self.prev = {"jump": False, "interact": False, "pulse": False}

        self.time0 = float(self.t["night1_duration_s"])
        if "time_left_s" in sc:
            self.time0 = float(_num(sc["time_left_s"], "time_left_s"))

        # player
        p = sc.get("player", {})
        if not isinstance(p, dict):
            raise ScenarioError("player must be an object")
        self.px, self.py, self.pz = _pos(p["pos"], "player") if "pos" in p else (0.0, 0.0, 0.0)
        self.vy = 0.0
        self.carried = int(_num(p.get("carried", 0), "player.carried"))
        self.flames = int(_num(p.get("flames", self.t["flames"]), "player.flames"))
        self.invuln = 0
        self.pulse_cd = 0

        # lanterns
        self.lanterns = []
        for i, (x, z) in enumerate(lantern_positions(self.t["lantern_count_night1"])):
            self.lanterns.append({"id": f"L{i + 1}", "x": x, "y": 0.0, "z": z,
                                  "lit": False, "deposited": 0})
        lan = sc.get("lanterns", [])
        if not isinstance(lan, list):
            raise ScenarioError("lanterns must be a list")
        for e in lan:
            if not isinstance(e, dict) or "id" not in e:
                raise ScenarioError("lantern entry needs an id")
            tgt = next((l for l in self.lanterns if l["id"] == e["id"]), None)
            if tgt is None:
                raise ScenarioError(f"unknown lantern id {e['id']!r}")
            if "pos" in e:
                tgt["x"], tgt["y"], tgt["z"] = _pos(e["pos"], "lantern")
            if "lit" in e:
                if not isinstance(e["lit"], bool):
                    raise ScenarioError("lantern.lit must be boolean")
                tgt["lit"] = e["lit"]
                tgt["deposited"] = self.t["lantern_cost"] if e["lit"] else 0

        # motes / shades
        self.motes, self.shades = [], []
        self._mote_n = 0
        self._shade_n = 0
        has_motes = "motes" in sc
        has_shades = "shades" in sc
        self.random_motes = bool(sc.get("random_motes", not has_motes))
        self.random_shades = bool(sc.get("random_shades", not has_shades))
        if has_motes:
            if not isinstance(sc["motes"], list):
                raise ScenarioError("motes must be a list")
            for m in sc["motes"]:
                x, _, z = _pos(m, "mote")
                self._add_mote(x, z)
        elif self.random_motes:
            self._random_motes()
        if self.random_motes and has_motes:
            self._random_motes()
        if has_shades:
            if not isinstance(sc["shades"], list):
                raise ScenarioError("shades must be a list")
            for s in sc["shades"]:
                if not isinstance(s, dict) or "pos" not in s:
                    raise ScenarioError("shade entry needs pos")
                x, _, z = _pos(s["pos"], "shade")
                self._add_shade(x, z, s.get("id"))
        elif self.random_shades:
            for _ in range(INITIAL_SHADES):
                a = self.rng.random() * 2 * math.pi
                self._add_shade(24 * math.sin(a), 24 * math.cos(a))
        if self.random_shades and has_shades:
            for _ in range(INITIAL_SHADES):
                a = self.rng.random() * 2 * math.pi
                self._add_shade(24 * math.sin(a), 24 * math.cos(a))

    # -- helpers ---------------------------------------------------------
    def _add_mote(self, x, z, value=1, prefix="M"):
        self._mote_n += 1
        self.motes.append({"id": f"{prefix}{self._mote_n}", "x": x, "z": z, "v": value})

    def _random_motes(self):
        n = 0
        while n < INITIAL_MOTES:
            a = self.rng.random() * 2 * math.pi
            r = 3 + 24 * math.sqrt(self.rng.random())
            self._add_mote(r * math.sin(a), r * math.cos(a))
            n += 1

    def _add_shade(self, x, z, sid=None):
        self._shade_n += 1
        if sid is None:
            sid = f"S{self._shade_n}"
        self.shades.append({"id": str(sid), "x": x, "z": z, "state": "chase", "stun": 0})
        return self.shades[-1]["id"]

    def _emit(self, name, data):
        ev = {"type": "event", "tick": self.tick, "name": name, "data": data}
        self.events.append(ev)
        self._seq += 1
        self.recent.append((self._seq, ev))
        del self.recent[:-60]

    def time_left(self):
        return max(0.0, self.time0 - self.tick / TICKS_PER_S)

    def _dist(self, ax, az, bx, bz):
        return math.hypot(ax - bx, az - bz)

    def _clamp_island(self, x, z):
        d = math.hypot(x, z)
        if d > ISLAND_R:
            return x * ISLAND_R / d, z * ISLAND_R / d
        return x, z

    # -- one step --------------------------------------------------------
    def step(self, inp=None):
        """Advance one tick using the input state `inp` (dict) for this tick."""
        self.events = []
        if self.state != "playing":
            return
        inp = inp or {}
        t = self.t
        self.tick += 1

        mx, mz = inp.get("move", (0.0, 0.0))
        ln = math.hypot(mx, mz)
        if ln > 1.0:
            mx, mz = mx / ln, mz / ln
        th = math.radians(inp.get("cam_yaw_deg", 0.0))
        wx = mx * math.cos(th) + mz * math.sin(th)
        wz = -mx * math.sin(th) + mz * math.cos(th)
        jump, interact, pulse = bool(inp.get("jump")), bool(inp.get("interact")), bool(inp.get("pulse"))
        j_edge = jump and not self.prev["jump"]
        i_edge = interact and not self.prev["interact"]
        p_edge = pulse and not self.prev["pulse"]
        self.prev = {"jump": jump, "interact": interact, "pulse": pulse}

        if self.invuln > 0:
            self.invuln -= 1
        if self.pulse_cd > 0:
            self.pulse_cd -= 1

        # 1. movement + jump (fall_enabled is false: the island rim is a soft wall)
        self.px += wx * t["player_speed"] * DT
        self.pz += wz * t["player_speed"] * DT
        self.px, self.pz = self._clamp_island(self.px, self.pz)
        if j_edge and self.py <= 0.0:
            self.vy = JUMP_SPEED
        if self.py > 0.0 or self.vy > 0.0:
            self.vy -= GRAVITY * DT
            self.py += self.vy * DT
            if self.py <= 0.0:
                self.py, self.vy = 0.0, 0.0

        # 2. pick up motes
        for m in list(self.motes):
            if self.carried >= t["carry_capacity"]:
                break
            if self._dist(self.px, self.pz, m["x"], m["z"]) <= t["pickup_radius"]:
                self.motes.remove(m)
                self.carried = min(t["carry_capacity"], self.carried + m["v"])
                self.score += self.sc["per_mote"] * m["v"]
                self._emit("mote_picked", {"carried": self.carried})

        # 3. interact: deposit into the nearest unlit lantern in range
        if i_edge and self.carried > 0:
            best = None
            for l in self.lanterns:
                if l["lit"]:
                    continue
                d = self._dist(self.px, self.pz, l["x"], l["z"])
                if d <= t["interact_radius"] and (best is None or d < best[0]):
                    best = (d, l)
            if best:
                l = best[1]
                amt = min(self.carried, t["lantern_cost"] - l["deposited"])
                self.carried -= amt
                l["deposited"] += amt
                self._emit("deposit", {"lantern_id": l["id"], "amount": amt,
                                       "deposited": l["deposited"]})
                if l["deposited"] >= t["lantern_cost"]:
                    l["lit"] = True
                    self.score += self.sc["per_lantern"]
                    self._emit("lantern_lit", {"lantern_id": l["id"]})

        # 4. pulse
        if p_edge and self.carried >= t["pulse_cost"] and self.pulse_cd == 0:
            self.carried -= t["pulse_cost"]
            self.pulse_cd = round(t["pulse_cooldown_s"] * TICKS_PER_S)
            hit = []
            for s in sorted(self.shades, key=lambda s: s["id"]):
                d = self._dist(self.px, self.pz, s["x"], s["z"])
                if d <= t["pulse_radius"]:
                    hit.append(s["id"])
                    s["state"] = "stunned"
                    s["stun"] = round(t["pulse_stun_s"] * TICKS_PER_S)
                    if d < 1e-9:
                        ux, uz = 1.0, 0.0
                    else:
                        ux, uz = (s["x"] - self.px) / d, (s["z"] - self.pz) / d
                    s["x"], s["z"] = self._clamp_island(s["x"] + ux * t["pulse_push_m"],
                                                        s["z"] + uz * t["pulse_push_m"])
                    self.score += self.sc["per_stun"]
            self._emit("pulse", {"stunned_ids": hit})

        # 5. shades: chase, respect lit-lantern safe zones
        for s in self.shades:
            if s["state"] == "stunned":
                s["stun"] -= 1
                if s["stun"] <= 0:
                    s["state"] = "chase"
                continue
            d = self._dist(self.px, self.pz, s["x"], s["z"])
            if d > 1e-9:
                step = min(d, t["shade_speed"] * DT)
                s["x"] += (self.px - s["x"]) / d * step
                s["z"] += (self.pz - s["z"]) / d * step
            s["state"] = "chase"
            for l in self.lanterns:
                if not l["lit"]:
                    continue
                dl = self._dist(s["x"], s["z"], l["x"], l["z"])
                if dl < t["safe_radius"]:
                    if dl < 1e-9:
                        ux, uz = 1.0, 0.0
                    else:
                        ux, uz = (s["x"] - l["x"]) / dl, (s["z"] - l["z"]) / dl
                    s["x"] = l["x"] + ux * t["safe_radius"]
                    s["z"] = l["z"] + uz * t["safe_radius"]
                    s["state"] = "repelled"

        # 6. timed shade spawns
        if (self.random_shades and self.tick % (SHADE_SPAWN_EVERY_S * TICKS_PER_S) == 0
                and len(self.shades) < SHADE_MAX):
            a = self.rng.random() * 2 * math.pi
            sid = self._add_shade((ISLAND_R - 2) * math.sin(a), (ISLAND_R - 2) * math.cos(a))
            self._emit("shade_spawned", {"id": sid})

        # extras (UI only): golden fireflies
        if self.extras and self.tick % (GOLDEN_EVERY_S * TICKS_PER_S) == 0:
            a = self.xrng.random() * 2 * math.pi
            r = 4 + 20 * self.xrng.random()
            self._add_mote(r * math.sin(a), r * math.cos(a), GOLDEN_VALUE, "G")

        # 7. shade contact
        if self.invuln == 0:
            for s in sorted(self.shades, key=lambda s: s["id"]):
                if s["state"] == "stunned":
                    continue
                if self._dist(self.px, self.pz, s["x"], s["z"]) <= t["shade_hit_radius"]:
                    self.flames -= 1
                    dropped = int(self.carried * t["hit_drop_ratio"])
                    self.carried -= dropped
                    for k in range(dropped):
                        a = 2 * math.pi * k / max(1, dropped)
                        x, z = self._clamp_island(self.px + 2.0 * math.sin(a),
                                                  self.pz + 2.0 * math.cos(a))
                        self._add_mote(x, z)
                    self.invuln = round(t["invuln_s"] * TICKS_PER_S)
                    self._emit("player_hit", {"by": "shade", "flames": self.flames,
                                              "dropped": dropped})
                    break

        # 8. end conditions
        if self.flames <= 0:
            self._finish("lost", "no_flames")
        elif all(l["lit"] for l in self.lanterns):
            self.score += self.sc["per_second_left"] * int(self.time_left())
            self.score += self.sc["per_flame_left"] * self.flames
            self._finish("won", "all_lit")
        elif self.time0 - self.tick / TICKS_PER_S <= 0:
            self._finish("lost", "dawn")

    def _finish(self, result, reason):
        self.state = result
        self._emit("game_over", {"result": result, "reason": reason})

    # -- output ----------------------------------------------------------
    def snapshot(self):
        return {
            "type": "snapshot", "tick": self.tick, "sim_tick": self.tick,
            "state": self.state, "time_left_s": r3(self.time_left()), "score": self.score,
            "player": {"pos": [r3(self.px), r3(self.py), r3(self.pz)],
                       "flames": self.flames, "carried": self.carried},
            "lanterns": [{"id": l["id"], "pos": [r3(l["x"]), r3(l["y"]), r3(l["z"])],
                          "lit": l["lit"], "deposited": l["deposited"]} for l in self.lanterns],
            "shades": [{"id": s["id"], "pos": [r3(s["x"]), 0.5, r3(s["z"])],
                        "state": s["state"]} for s in self.shades],
            "motes_active": len(self.motes),
            "motes": [{"id": m["id"], "pos": [r3(m["x"]), 0.0, r3(m["z"])]} for m in self.motes],
        }

    def end_record(self):
        return {"type": "end", "ticks": self.tick, "state": self.state, "score": self.score}
