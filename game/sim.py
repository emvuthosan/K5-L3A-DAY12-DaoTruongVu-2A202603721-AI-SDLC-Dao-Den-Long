"""Deterministic simulation core for Đảo Đèn Lồng, Test Contract v1.1 (no rendering, no I/O).

60 ticks/s. Units: meters, seconds. Y is up. Angles: x = r*cos(a), z = r*sin(a).
Tick order follows TICKET-02 (see step()).
"""
import json
import math
import os
import random

TICKS = 60
DT = 1.0 / TICKS
JUMP_V = 7.0
GRAVITY = 20.0
CHARM_SPEED = 7.2
CHARM_TICKS = 600
CHARM_RESPAWN = 2700
FALL_Y = -10.0
STEP_UP = 0.3
INVULN_TICKS = 90
DROP_TTL = 480
STUN_TICKS = 120
PUSH_TICKS = 15
PUSH_M = 4.0
RECOIL_TICKS = 60
RECOIL_M = 2.0
SHADE_DETECT = 12.0
SHADE_LOSE = 18.0
SAFE_R = 6.0
EXPEL_TICKS = 30
MOTE_CAP = 30
MOTE_EVERY = 240
DRIFTER_SPEED = 7.0
DRIFTER_IDLE = 2.0
DRIFTER_EVERY = 1200
DRIFTER_MAX = 2
GOLDEN_EVERY = 1500   # extras only (never in headless)
GOLDEN_VALUE = 3
SHADE_STATES = ("spawning", "wander", "chase", "recoil", "stunned")
DRIFTER_STATES = ("idle", "chase", "flee")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class ScenarioError(ValueError):
    """Bad scenario or inputs file (headless exits with code 2)."""


def load_contract(path=None):
    with open(path or os.path.join(ROOT, "game.contract.json"), encoding="utf-8") as f:
        return json.load(f)


def r3(v):
    v = round(v, 3)
    return 0.0 if v == 0 else v


def _ring(cx, cz, r, deg0, step, n):
    return [(cx + r * math.cos(math.radians(deg0 + i * step)),
             cz + r * math.sin(math.radians(deg0 + i * step))) for i in range(n)]


def height_at(night, x, z):
    """Ground height at (x, z); None means void (falls)."""
    if night == 1:
        return 0.0 if x * x + z * z <= 1600.0 else None
    if night == 2:
        if x * x + z * z <= 784.0 or (x - 70) ** 2 + z * z <= 784.0:
            return 0.0
        if 26 <= x <= 44 and -2 <= z <= 2:
            return 0.0
        return None
    r2 = x * x + z * z
    if r2 > 2025.0:
        return None
    h = 0.0
    if r2 <= 64.0:
        h = 6.0
    elif z > 0 and 144.0 <= r2 <= 576.0:
        h = 3.0
    for a in (30.0, 150.0):
        ux, uz = math.cos(math.radians(a)), math.sin(math.radians(a))
        s = x * ux + z * uz
        p = -x * uz + z * ux
        if 24.0 <= s <= 30.0 and abs(p) <= 1.5:
            h = max(h, 3.0 * (30.0 - s) / 6.0)
    return h


def night_cfg(n):
    if n == 1:
        return dict(
            start=(0.0, 0.0, 0.0), dur="night1_duration_s",
            lanterns=[(0, 0, 25), (23.8, 0, 7.7), (14.7, 0, -20.2), (-14.7, 0, -20.2), (-23.8, 0, 7.7)],
            motes=_ring(0, 0, 12, 0, 45, 8) + _ring(0, 0, 33, 0, 22.5, 16),
            shades=_ring(0, 0, 37, 15, 30, 12), shade_interval=480, shade_max=6, shade_speed=4.0,
            charms=[], pads=[], drifters=False, wind=False)
    if n == 2:
        return dict(
            start=(0.0, 0.0, 0.0), dur="night2_duration_s",
            lanterns=[(0, 0, 20), (17, 0, -10), (-17, 0, -10), (70, 0, 20), (87, 0, -10), (53, 0, -10)],
            motes=[p for cx in (0, 70) for p in _ring(cx, 0, 10, 0, 90, 4) + _ring(cx, 0, 22, 0, 45, 8)],
            shades=[p for cx in (0, 70) for p in _ring(cx, 0, 26, 22.5, 45, 8)],
            shade_interval=420, shade_max=8, shade_speed=4.0,
            charms=[(35, 0, 0)],
            pads=[dict(pos=(20, 0, 18), vy=14.0, h=24.0, target=(70.0, 0.0)),
                  dict(pos=(50, 0, -18), vy=14.0, h=24.0, target=(0.0, 0.0))],
            drifters=True, wind=False)
    return dict(
        start=(0.0, 0.0, -30.0), dur="night3_duration_s",
        lanterns=[(0, 6, 6), (18, 3, 10), (-18, 3, 10), (35, 0, -10), (-35, 0, -10), (20, 0, -35), (-20, 0, -35)],
        motes=_ring(0, 0, 34, 0, 20, 18) + _ring(0, 0, 18, 20, 20, 8) + _ring(0, 0, 5, 45, 90, 4),
        shades=_ring(0, 0, 43, 0, 22.5, 16), shade_interval=360, shade_max=10, shade_speed=4.5,
        charms=[(30, 0, 25), (-30, 0, 25)],
        pads=[dict(pos=(0, 3, 13), vy=12.0, h=8.0, dir=(0.0, -1.0))],
        drifters=True, wind=True)


def _pos(v, what):
    if (not isinstance(v, (list, tuple)) or len(v) not in (2, 3)
            or any(isinstance(c, bool) or not isinstance(c, (int, float)) for c in v)):
        raise ScenarioError(f"{what}: pos must be [x,y,z] (or [x,z]) numbers")
    if len(v) == 2:
        return float(v[0]), None, float(v[1])
    return float(v[0]), float(v[1]), float(v[2])


def _num(v, what):
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise ScenarioError(f"{what} must be a number")
    return v


def _int(v, what):
    return int(_num(v, what))


class Sim:
    def __init__(self, seed=0, scenario=None, contract=None, extras=False, night=1):
        if night not in (1, 2, 3):
            raise ScenarioError("night must be 1, 2 or 3")
        c = contract or load_contract()
        self.t = c["tuning"]
        self.sc = c["score"]
        self.night = night
        self.cfg = cfg = night_cfg(night)
        self.seed = seed
        self.extras = extras
        # separate RNG streams so optional features never perturb each other
        self.r_mote = random.Random(seed * 7919 + 1)
        self.r_shade = random.Random(seed * 7919 + 2)
        self.r_drift = random.Random(seed * 7919 + 3)
        self.r_wind = random.Random(seed * 7919 + 4)
        self.r_drop = random.Random(seed * 7919 + 5)
        self.r_x = random.Random(seed * 7919 + 6)
        sc = scenario if scenario is not None else {}
        if not isinstance(sc, dict):
            raise ScenarioError("scenario must be a JSON object")

        self.tick = 0
        self.sim_tick = 0
        self.paused = False
        self.result = None           # None | "won" | "lost"
        self.score = 0
        self.events = []
        self.recent = []
        self._seq = 0
        self.prev = {"jump": False, "interact": False, "pulse": False, "dash": False, "pause": False}
        self.time0 = float(self.t[cfg["dur"]])
        if "time_left_s" in sc:
            self.time0 = float(_num(sc["time_left_s"], "time_left_s"))

        # ---- player
        p = sc.get("player", {})
        if not isinstance(p, dict):
            raise ScenarioError("player must be an object")
        sx, sy, sz = cfg["start"]
        self.start = (sx, sy, sz)
        if "pos" in p:
            x, y, z = _pos(p["pos"], "player")
            if y is None:
                y = height_at(night, x, z) or 0.0
            self.px, self.py, self.pz = x, y, z
        else:
            self.px, self.py, self.pz = sx, sy, sz
        self.vx = self.vz = self.vy = 0.0
        self.fx, self.fz = 0.0, 1.0
        self.carried = _int(p.get("carried", 0), "player.carried")
        self.flames = _int(p.get("flames", self.t["flames"]), "player.flames")
        self.invuln = _int(p.get("invuln_ticks", 0), "invuln_ticks")
        self.dash_cd = _int(p.get("dash_cd_ticks", 0), "dash_cd_ticks")
        self.pulse_cd = _int(p.get("pulse_cd_ticks", 0), "pulse_cd_ticks")
        self.charm = _int(p.get("charm_ticks", 0), "charm_ticks")
        self.dash_left = 0
        self.dash_vx = self.dash_vz = 0.0
        self.launched = False
        self.lvx = self.lvz = 0.0
        h0 = height_at(night, self.px, self.pz)
        self.grounded = h0 is not None and abs(self.py - h0) < 1e-9
        self.respawn_wait = 0

        # ---- lanterns
        self.lanterns = [{"id": f"L{i + 1}", "x": float(x), "y": float(y), "z": float(z),
                          "lit": False, "deposited": 0, "fresh": False}
                         for i, (x, y, z) in enumerate(cfg["lanterns"])]
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
                x, y, z = _pos(e["pos"], "lantern")
                tgt["x"], tgt["z"] = x, z
                tgt["y"] = y if y is not None else 0.0
            if "lit" in e:
                if not isinstance(e["lit"], bool):
                    raise ScenarioError("lantern.lit must be boolean")
                tgt["lit"] = e["lit"]
                tgt["deposited"] = self.t["lantern_cost"] if e["lit"] else 0

        # ---- motes
        self.motes, self.shades, self.drifters, self.charms = [], [], [], []
        self._mn = self._sn = self._dn = 0
        has = lambda k: k in sc
        self.random_motes = bool(sc.get("random_motes", not has("motes")))
        self.random_shades = bool(sc.get("random_shades", not has("shades")))
        self.random_drifters = bool(sc.get("random_drifters", cfg["drifters"] and not has("drifters")))
        self.wind_enabled = bool(sc.get("wind_enabled", cfg["wind"]))
        if has("motes"):
            if not isinstance(sc["motes"], list):
                raise ScenarioError("motes must be a list")
            for m in sc["motes"]:
                if isinstance(m, dict):
                    pos = m.get("pos")
                    ttl = m.get("ttl_ticks")
                    kind = m.get("kind", "random")
                else:
                    pos, ttl, kind = m, None, "random"
                x, y, z = _pos(pos, "mote")
                self._add_mote(x, z, y, kind=kind, ttl=ttl)
        if self.random_motes:
            idx = list(range(len(cfg["motes"])))
            self.r_mote.shuffle(idx)
            for i in sorted(idx[:20]):
                x, z = cfg["motes"][i]
                self._add_mote(x, z, None, sp=i)

        # ---- shades
        if has("shades"):
            if not isinstance(sc["shades"], list):
                raise ScenarioError("shades must be a list")
            for s in sc["shades"]:
                if not isinstance(s, dict) or "pos" not in s:
                    raise ScenarioError("shade entry needs pos")
                x, _, z = _pos(s["pos"], "shade")
                st = s.get("state", "wander")
                if st not in SHADE_STATES:
                    raise ScenarioError(f"bad shade state {st!r}")
                tl = _int(s.get("state_ticks_left", STUN_TICKS if st == "stunned" else
                                RECOIL_TICKS if st == "recoil" else 1 if st == "spawning" else 0),
                          "state_ticks_left")
                self._add_shade(x, z, s.get("id"), st, tl)

        # ---- drifters
        if has("drifters"):
            if not isinstance(sc["drifters"], list):
                raise ScenarioError("drifters must be a list")
            for d in sc["drifters"]:
                if not isinstance(d, dict) or "pos" not in d:
                    raise ScenarioError("drifter entry needs pos")
                x, _, z = _pos(d["pos"], "drifter")
                st = d.get("state", "idle")
                if st not in DRIFTER_STATES:
                    raise ScenarioError(f"bad drifter state {st!r}")
                self._add_drifter(x, z, d.get("id"), st, _int(d.get("stolen", 0), "stolen"),
                                  _int(d.get("state_ticks_left", 240 if st == "flee" else 0), "state_ticks_left"))

        # ---- charms
        if has("charms"):
            if not isinstance(sc["charms"], list):
                raise ScenarioError("charms must be a list")
            for i, e in enumerate(sc["charms"]):
                if not isinstance(e, dict) or "pos" not in e:
                    raise ScenarioError("charm entry needs pos")
                x, y, z = _pos(e["pos"], "charm")
                self.charms.append({"id": str(e.get("id", f"C{i + 1}")), "x": x, "z": z,
                                    "y": y if y is not None else (height_at(night, x, z) or 0.0),
                                    "avail": bool(e.get("available", True)),
                                    "rt": _int(e.get("respawn_ticks", 0), "respawn_ticks")})
        else:
            for i, (x, y, z) in enumerate(cfg["charms"]):
                self.charms.append({"id": f"C{i + 1}", "x": float(x), "z": float(z), "y": float(y),
                                    "avail": True, "rt": 0})
        self.wind_dir = 0.0
        self.wind_active = False

    # ------------------------------------------------------------ helpers
    def hgt(self, x, z):
        return height_at(self.night, x, z)

    def _add_mote(self, x, z, y=None, kind="random", ttl=None, sp=None, v=1, prefix="M"):
        if y is None:
            y = self.hgt(x, z) or 0.0
        self._mn += 1
        self.motes.append({"id": f"{prefix}{self._mn}", "x": x, "y": y, "z": z, "kind": kind,
                           "ttl": ttl, "sp": sp, "v": v})

    def _add_shade(self, x, z, sid=None, state="spawning", tl=1):
        self._sn += 1
        self.shades.append({"id": str(sid) if sid is not None else f"S{self._sn}", "n": self._sn,
                            "x": x, "z": z, "state": state, "tl": tl, "push": 0, "pdx": 1.0, "pdz": 0.0,
                            "expel": 0, "wt": 0, "wdx": 1.0, "wdz": 0.0, "rdx": 0.0, "rdz": 0.0})
        return self.shades[-1]["id"]

    def _add_drifter(self, x, z, did=None, state="idle", stolen=0, tl=0):
        self._dn += 1
        self.drifters.append({"id": str(did) if did is not None else f"D{self._dn}", "n": self._dn,
                              "x": x, "z": z, "state": state, "stolen": stolen, "tl": tl, "wt": 0,
                              "wdx": 1.0, "wdz": 0.0})
        return self.drifters[-1]["id"]

    def _emit(self, name, data):
        ev = {"type": "event", "tick": self.tick, "name": name, "data": data}
        self.events.append(ev)
        self._seq += 1
        self.recent.append((self._seq, ev))
        del self.recent[:-80]

    @property
    def over(self):
        return self.result is not None

    @property
    def state(self):
        return self.result or ("paused" if self.paused else "playing")

    def time_left(self):
        return max(0.0, self.time0 - self.sim_tick / TICKS)

    def _gy(self, x, z):
        h = self.hgt(x, z)
        return 0.0 if h is None else h

    def _drop_motes(self, n, x, z, ttl=DROP_TTL, ring=True):
        for _ in range(n):
            if ring:
                a = self.r_drop.random() * 2 * math.pi
                r = 1.5 + self.r_drop.random()
                mx, mz = x + r * math.cos(a), z + r * math.sin(a)
                if self.hgt(mx, mz) is None:
                    mx, mz = x, z
            else:
                mx, mz = x, z
            h = self.hgt(mx, mz)
            self._add_mote(mx, mz, h if h is not None else self.py, kind="dropped", ttl=ttl)

    # ---------------------------------------------------------- one step
    def step(self, inp=None):
        """Advance one tick with the input state `inp` (dict of held values)."""
        self.events = []
        if self.over:
            return
        inp = inp or {}
        t, sc, cfg = self.t, self.sc, self.cfg
        self.tick += 1

        # 1. input; pause first
        mv = inp.get("move", (0.0, 0.0))
        e = {}
        for k in self.prev:
            cur = bool(inp.get(k))
            e[k] = cur and not self.prev[k]
            self.prev[k] = cur
        if e["pause"]:
            if not self.paused:
                self.paused = True
                self._emit("paused", {})
                return
            self.paused = False
            self._emit("resumed", {})
        if self.paused:
            return
        self.sim_tick += 1
        st = self.sim_tick

        # 2. counters
        if self.dash_cd > 0: self.dash_cd -= 1
        if self.pulse_cd > 0: self.pulse_cd -= 1
        if self.invuln > 0: self.invuln -= 1
        if self.charm > 0: self.charm -= 1
        if self.respawn_wait > 0:
            self.respawn_wait -= 1
            if self.respawn_wait == 0:
                self.px, self.py, self.pz = self.start
                self.vx = self.vy = self.vz = 0.0
                self.grounded, self.launched, self.dash_left = True, False, 0
                self.invuln = INVULN_TICKS
        if self.motes:
            keep = []
            for m in self.motes:
                if m["ttl"] is not None:
                    m["ttl"] -= 1
                    if m["ttl"] <= 0:
                        continue
                keep.append(m)
            self.motes = keep
        for c in self.charms:
            if not c["avail"]:
                c["rt"] -= 1
                if c["rt"] <= 0:
                    c["avail"] = True
        for s in self.shades:
            if s["state"] in ("spawning", "recoil", "stunned"):
                s["tl"] -= 1
                if s["tl"] <= 0:
                    s["state"] = "wander"
        keep = []
        for d in self.drifters:
            if d["state"] == "flee":
                d["tl"] -= 1
                if d["tl"] <= 0:
                    continue
            keep.append(d)
        self.drifters = keep
        if self.wind_enabled and self.night == 3:
            ph = st % 1800
            if ph == 1680:
                self.wind_dir = round(self.r_wind.random() * 360.0, 3)
            self.wind_active = st >= 1800 and ph < 300
        else:
            self.wind_active = False

        frozen = self.respawn_wait > 0
        px0 = self.px

        # 3. move Mây
        if not frozen:
            self._move_player(mv, inp, e)
            if self.py < FALL_Y and self.t.get("fall_enabled", True):
                lost = self.carried
                self.carried = 0
                self.flames -= 1
                self.respawn_wait = 60
                self._emit("player_hit", {"by": "fall", "flames": self.flames, "dropped": 0, "lost": lost})
                frozen = True

        # 4. pickups
        if not frozen:
            for m in list(self.motes):
                if self.carried >= t["carry_capacity"]:
                    break
                if (math.hypot(self.px - m["x"], self.pz - m["z"]) <= t["pickup_radius"]
                        and abs(self.py - m["y"]) <= 1.5):
                    self.motes.remove(m)
                    self.carried = min(t["carry_capacity"], self.carried + m["v"])
                    self._emit("mote_picked", {"carried": self.carried})
            for c in self.charms:
                if (c["avail"] and math.hypot(self.px - c["x"], self.pz - c["z"]) <= t["pickup_radius"]
                        and abs(self.py - c["y"]) <= 1.5):
                    c["avail"] = False
                    c["rt"] = CHARM_RESPAWN
                    self.charm = CHARM_TICKS
                    self._emit("charm_picked", {"charm_id": c["id"], "charm_ticks": CHARM_TICKS})

        # 5. interact
        if not frozen and e["interact"] and self.carried > 0:
            best = None
            for l in self.lanterns:
                if l["lit"]:
                    continue
                d = math.hypot(self.px - l["x"], self.pz - l["z"])
                if d <= t["interact_radius"] and (best is None or d < best[0]):
                    best = (d, l)
            if best:
                l = best[1]
                amt = min(self.carried, t["lantern_cost"] - l["deposited"])
                self.carried -= amt
                l["deposited"] += amt
                self.score += sc["per_mote"] * amt
                self._emit("deposit", {"lantern_id": l["id"], "amount": amt, "deposited": l["deposited"]})
                if l["deposited"] >= t["lantern_cost"]:
                    l["lit"] = True
                    self.score += sc["per_lantern"]
                    self._emit("lantern_lit", {"lantern_id": l["id"]})

        # 6. safe zones: shades inside a lit zone get expelled (<=30 ticks, harmless)
        for l in self.lanterns:
            if not l["lit"]:
                continue
            for s in self.shades:
                if s["expel"] == 0 and math.hypot(s["x"] - l["x"], s["z"] - l["z"]) < SAFE_R - 1e-9:
                    s["expel"] = EXPEL_TICKS

        # 7. pulse
        if not frozen and e["pulse"] and self.carried >= t["pulse_cost"] and self.pulse_cd == 0:
            self.carried -= t["pulse_cost"]
            self.pulse_cd = round(t["pulse_cooldown_s"] * TICKS)
            cx, cy, cz = self.px, self.py + 0.8, self.pz
            hit = []
            for s in sorted(self.shades, key=lambda s: s["n"]):
                sy = self._gy(s["x"], s["z"]) + 0.5
                if math.sqrt((s["x"] - cx) ** 2 + (sy - cy) ** 2 + (s["z"] - cz) ** 2) <= t["pulse_radius"]:
                    hit.append(s["id"])
                    s["state"] = "stunned"
                    s["tl"] = STUN_TICKS
                    dx, dz = s["x"] - cx, s["z"] - cz
                    d = math.hypot(dx, dz)
                    s["pdx"], s["pdz"] = (1.0, 0.0) if d < 1e-9 else (dx / d, dz / d)
                    s["push"] = PUSH_TICKS
                    self.score += sc["per_stun"]
            for d in self.drifters:
                dy = self._gy(d["x"], d["z"]) + 1.5
                if math.sqrt((d["x"] - cx) ** 2 + (dy - cy) ** 2 + (d["z"] - cz) ** 2) > t["pulse_radius"]:
                    continue
                if d["state"] == "chase":
                    d["state"], d["tl"] = "flee", 240
                elif d["state"] == "flee" and d["stolen"] > 0:
                    amt = d["stolen"]
                    d["stolen"] = 0
                    d["tl"] = min(d["tl"], 120)
                    self._drop_motes(amt, d["x"], d["z"], ring=False)
                    self._emit("drifter_drop", {"drifter_id": d["id"], "amount": amt})
            self._emit("pulse", {"stunned_ids": hit})

        # 8. move shades and drifters
        self._move_shades()
        self._move_drifters()

        # 9. contacts: drifters steal first, then shades hit (by id)
        if not frozen:
            for d in sorted(self.drifters, key=lambda d: d["n"]):
                if d["state"] in ("idle", "chase") and self.carried > 0 \
                        and math.hypot(self.px - d["x"], self.pz - d["z"]) <= 1.2:
                    amt = min(3, self.carried)
                    self.carried -= amt
                    d["stolen"] = amt
                    d["state"], d["tl"] = "flee", 240
                    self._emit("drifter_steal", {"drifter_id": d["id"], "amount": amt, "carried": self.carried})
            if self.invuln == 0:
                for s in sorted(self.shades, key=lambda s: s["n"]):
                    if s["state"] in ("spawning", "recoil", "stunned") or s["expel"] > 0:
                        continue
                    if (math.hypot(self.px - s["x"], self.pz - s["z"]) <= t["shade_hit_radius"]
                            and abs(self.py - self._gy(s["x"], s["z"])) <= 1.5):
                        self.flames -= 1
                        dropped = int(self.carried * t["hit_drop_ratio"])
                        self.carried -= dropped
                        self._drop_motes(dropped, self.px, self.pz)
                        self.invuln = INVULN_TICKS
                        dx, dz = s["x"] - self.px, s["z"] - self.pz
                        d = math.hypot(dx, dz)
                        s["rdx"], s["rdz"] = (1.0, 0.0) if d < 1e-9 else (dx / d, dz / d)
                        s["state"], s["tl"] = "recoil", RECOIL_TICKS
                        self._recoil_step(s)
                        self._emit("player_hit", {"by": "shade", "flames": self.flames, "dropped": dropped})
                        break

        # 10. scheduled spawns (new entities interact from next tick)
        if self.random_motes and st % MOTE_EVERY == 0 and len(self.motes) < MOTE_CAP:
            used = {m["sp"] for m in self.motes if m["sp"] is not None}
            free = [i for i in range(len(cfg["motes"])) if i not in used]
            if free:
                i = self.r_mote.choice(free)
                self._add_mote(cfg["motes"][i][0], cfg["motes"][i][1], None, sp=i)
        if self.extras and st % GOLDEN_EVERY == 0:
            a = self.r_x.random() * 2 * math.pi
            r = 4 + 12 * self.r_x.random()
            gx, gz = self.start[0] + r * math.cos(a), self.start[2] + r * math.sin(a)
            if self.hgt(gx, gz) is not None:
                self._add_mote(gx, gz, None, v=GOLDEN_VALUE, prefix="G")
        if self.random_shades and st >= 300 and (st - 300) % cfg["shade_interval"] == 0:
            for _ in range(2 if st == 300 else 1):
                if len(self.shades) >= cfg["shade_max"]:
                    break
                ok = []
                for (x, z) in cfg["shades"]:
                    if math.hypot(x - self.px, z - self.pz) < 15.0:
                        continue
                    if any(l["lit"] and math.hypot(x - l["x"], z - l["z"]) < SAFE_R for l in self.lanterns):
                        continue
                    ok.append((x, z))
                if not ok:
                    break
                x, z = self.r_shade.choice(ok)
                sid = self._add_shade(x, z)
                self._emit("shade_spawned", {"id": sid})
        if self.random_drifters and cfg["drifters"] and st % DRIFTER_EVERY == 0 and len(self.drifters) < DRIFTER_MAX:
            x, z = self.r_drift.choice(cfg["shades"])
            self._add_drifter(x, z)

        # 11. win / lose
        if self.flames <= 0:
            self._finish("lost", "no_flames")
        elif all(l["lit"] for l in self.lanterns):
            self.score += sc["per_second_left"] * int(self.time_left())
            self.score += sc["per_flame_left"] * self.flames
            self._finish("won", "all_lit")
        elif self.time0 - st / TICKS <= 1e-9:
            self._finish("lost", "dawn")

    # ---------------------------------------------------------- player
    def _blocked(self, x, z, y):
        if self.night == 3 and x * x + z * z < 4.0 and y < 14.0:
            return True
        h = self.hgt(x, z)
        return h is not None and h > y + STEP_UP

    def _slide(self, nx, nz):
        if not self._blocked(nx, nz, self.py):
            return nx, nz
        if not self._blocked(nx, self.pz, self.py):
            return nx, self.pz
        if not self._blocked(self.px, nz, self.py):
            return self.px, nz
        return self.px, self.pz

    def _move_player(self, mv, inp, e):
        t = self.t
        mx, mz = float(mv[0]), float(mv[1])
        ln = math.hypot(mx, mz)
        if ln > 1.0:
            mx, mz = mx / ln, mz / ln
        th = math.radians(inp.get("cam_yaw_deg", 0.0))
        wx = mx * math.cos(th) + mz * math.sin(th)
        wz = -mx * math.sin(th) + mz * math.cos(th)
        moving = math.hypot(wx, wz) > 1e-9
        if moving:
            n = math.hypot(wx, wz)
            self.fx, self.fz = wx / n, wz / n
        speed = CHARM_SPEED if self.charm > 0 else t["player_speed"]

        if e["jump"] and self.grounded:
            self.vy = JUMP_V
            self.grounded = False
        if e["dash"] and self.dash_left == 0 and (self.charm > 0 or self.dash_cd == 0):
            dx, dz = (wx, wz) if moving else (self.fx, self.fz)
            n = math.hypot(dx, dz)
            self.dash_vx, self.dash_vz = dx / n * t["dash_speed"], dz / n * t["dash_speed"]
            self.dash_left = round(t["dash_duration_s"] * TICKS)
            if self.charm <= 0:
                self.dash_cd = round(t["dash_cooldown_s"] * TICKS)
            self._emit("dash", {})
        # launch pads
        if self.grounded and not self.launched:
            for p in self.cfg["pads"]:
                px, py, pz = p["pos"]
                if math.hypot(self.px - px, self.pz - pz) <= 1.0 and abs(self.py - py) <= 0.5:
                    if "target" in p:
                        dx, dz = p["target"][0] - self.px, p["target"][1] - self.pz
                    else:
                        dx, dz = p["dir"]
                    n = math.hypot(dx, dz) or 1.0
                    self.lvx, self.lvz = dx / n * p["h"], dz / n * p["h"]
                    self.vy = p["vy"]
                    self.launched, self.grounded = True, False
                    break
        # horizontal velocity
        if self.dash_left > 0:
            self.vx, self.vz = self.dash_vx, self.dash_vz
            self.dash_left -= 1
            dashing = True
        else:
            dashing = False
            if self.launched:
                self.vx, self.vz = self.lvx, self.lvz
            else:
                self.vx, self.vz = wx * speed, wz * speed
        nx, nz = self.px + self.vx * DT, self.pz + self.vz * DT
        if self.wind_active:
            a = math.radians(self.wind_dir)
            nx += 2.0 * DT * math.cos(a)
            nz += 2.0 * DT * math.sin(a)
        self.px, self.pz = self._slide(nx, nz)
        # vertical
        h = self.hgt(self.px, self.pz)
        if self.grounded and h is not None and self.py - h <= STEP_UP:
            self.py, self.vy = h, 0.0
            return
        if dashing:
            self.vy = 0.0
            self.grounded = False
            return
        self.grounded = False
        self.vy -= GRAVITY * DT
        self.py += self.vy * DT
        if h is not None and self.py <= h and self.vy <= 0:
            self.py, self.vy = h, 0.0
            self.grounded, self.launched = True, False

    # ---------------------------------------------------------- shades
    def _try_move(self, s, nx, nz, slide=True):
        ox, oz = s["x"], s["z"]
        h0 = self._gy(ox, oz)
        cands = ((nx, nz), (nx, oz), (ox, nz)) if slide else ((nx, nz),)
        for tx, tz in cands:
            h = self.hgt(tx, tz)
            if h is None or h > h0 + 0.5:
                continue
            if self.night == 3 and tx * tx + tz * tz < 4.0:
                continue
            s["x"], s["z"] = tx, tz
            return True
        return False

    def _recoil_step(self, s):
        k = RECOIL_M / RECOIL_TICKS
        self._try_move(s, s["x"] + s["rdx"] * k, s["z"] + s["rdz"] * k, slide=False)

    def _move_shades(self):
        speed = self.cfg["shade_speed"]
        for s in self.shades:
            if s["state"] == "spawning":
                continue
            moved_by_push = False
            if s["expel"] > 0:
                s["expel"] -= 1
                best = None
                for l in self.lanterns:
                    if l["lit"]:
                        d = math.hypot(s["x"] - l["x"], s["z"] - l["z"])
                        if d < SAFE_R and (best is None or d < best[0]):
                            best = (d, l)
                if best:
                    d, l = best
                    ux, uz = ((s["x"] - l["x"]) / d, (s["z"] - l["z"]) / d) if d > 1e-9 else (1.0, 0.0)
                    left = s["expel"] + 1
                    step = (SAFE_R - d) / left
                    s["x"] += ux * step
                    s["z"] += uz * step
                continue
            if s["push"] > 0:
                s["push"] -= 1
                k = PUSH_M / PUSH_TICKS
                self._try_move(s, s["x"] + s["pdx"] * k, s["z"] + s["pdz"] * k, slide=False)
                moved_by_push = True
            if s["state"] == "stunned":
                continue
            if s["state"] == "recoil":
                if not moved_by_push and s["tl"] > 0:
                    if s["rdx"] == 0.0 and s["rdz"] == 0.0:
                        dx, dz = s["x"] - self.px, s["z"] - self.pz
                        d = math.hypot(dx, dz) or 1.0
                        s["rdx"], s["rdz"] = dx / d, dz / d
                    self._recoil_step(s)
                continue
            d = math.hypot(self.px - s["x"], self.pz - s["z"])
            if s["state"] == "wander" and d <= SHADE_DETECT:
                s["state"] = "chase"
            elif s["state"] == "chase" and d > SHADE_LOSE:
                s["state"] = "wander"
            if s["state"] == "chase":
                if d > 1e-9:
                    k = min(d, speed * DT)
                    self._try_move(s, s["x"] + (self.px - s["x"]) / d * k, s["z"] + (self.pz - s["z"]) / d * k)
            else:
                if s["wt"] <= 0:
                    a = self.r_shade.random() * 2 * math.pi
                    s["wdx"], s["wdz"] = math.cos(a), math.sin(a)
                    s["wt"] = 120
                s["wt"] -= 1
                k = speed * 0.5 * DT
                if not self._try_move(s, s["x"] + s["wdx"] * k, s["z"] + s["wdz"] * k):
                    s["wt"] = 0
            # safe zones block entry (project back to the 6 m edge)
            for l in self.lanterns:
                if l["lit"]:
                    dl = math.hypot(s["x"] - l["x"], s["z"] - l["z"])
                    if dl < SAFE_R:
                        ux, uz = ((s["x"] - l["x"]) / dl, (s["z"] - l["z"]) / dl) if dl > 1e-9 else (1.0, 0.0)
                        s["x"], s["z"] = l["x"] + ux * SAFE_R, l["z"] + uz * SAFE_R

    def _move_drifters(self):
        for d in self.drifters:
            if d["state"] in ("idle", "chase"):
                dist = math.hypot(self.px - d["x"], self.pz - d["z"])
                if self.carried >= 5 and dist <= 15.0:
                    d["state"] = "chase"
                else:
                    d["state"] = "idle"
            if d["state"] == "chase":
                dist = math.hypot(self.px - d["x"], self.pz - d["z"])
                if dist > 1e-9:
                    k = min(dist, DRIFTER_SPEED * DT)
                    d["x"] += (self.px - d["x"]) / dist * k
                    d["z"] += (self.pz - d["z"]) / dist * k
            elif d["state"] == "flee":
                dx, dz = d["x"] - self.px, d["z"] - self.pz
                n = math.hypot(dx, dz) or 1.0
                d["x"] += dx / n * DRIFTER_SPEED * DT
                d["z"] += dz / n * DRIFTER_SPEED * DT
            else:
                if d["wt"] <= 0:
                    a = self.r_drift.random() * 2 * math.pi
                    d["wdx"], d["wdz"] = math.cos(a), math.sin(a)
                    d["wt"] = 120
                d["wt"] -= 1
                d["x"] += d["wdx"] * DRIFTER_IDLE * DT
                d["z"] += d["wdz"] * DRIFTER_IDLE * DT

    def _finish(self, result, reason):
        self.result = result
        self.paused = False
        self._emit("game_over", {"result": result, "reason": reason})

    # ---------------------------------------------------------- output
    def snapshot(self):
        return {
            "type": "snapshot", "tick": self.tick, "sim_tick": self.sim_tick, "night": self.night,
            "state": self.state, "time_left_s": r3(self.time_left()), "score": self.score,
            "wind": {"active": self.wind_active, "dir_deg": r3(self.wind_dir)},
            "player": {"pos": [r3(self.px), r3(self.py), r3(self.pz)],
                       "vel": [r3(self.vx), r3(self.vy), r3(self.vz)], "grounded": self.grounded,
                       "invuln": self.invuln, "flames": self.flames, "carried": self.carried,
                       "dash_cd_s": r3(self.dash_cd / TICKS), "pulse_cd_s": r3(self.pulse_cd / TICKS),
                       "charm_s": r3(self.charm / TICKS), "facing": [r3(self.fx), r3(self.fz)]},
            "lanterns": [{"id": l["id"], "pos": [r3(l["x"]), r3(l["y"]), r3(l["z"])],
                          "lit": l["lit"], "deposited": l["deposited"]} for l in self.lanterns],
            "shades": [{"id": s["id"], "pos": [r3(s["x"]), r3(self._gy(s["x"], s["z"]) + 0.5), r3(s["z"])],
                        "state": s["state"], "state_ticks_left": s["tl"]} for s in self.shades],
            "motes_active": len(self.motes),
            "motes": [{"id": m["id"], "pos": [r3(m["x"]), r3(m["y"]), r3(m["z"])], "kind": m["kind"],
                       "ttl_s": None if m["ttl"] is None else r3(m["ttl"] / TICKS)} for m in self.motes],
            "drifters": [{"id": d["id"], "pos": [r3(d["x"]), r3(self._gy(d["x"], d["z"]) + 1.5), r3(d["z"])],
                          "state": d["state"], "stolen": d["stolen"]} for d in self.drifters],
            "charms": [{"id": c["id"], "pos": [r3(c["x"]), r3(c["y"]), r3(c["z"])], "available": c["avail"],
                        "respawn_s": r3(0 if c["avail"] else c["rt"] / TICKS)} for c in self.charms],
        }

    def end_record(self):
        return {"type": "end", "ticks": self.tick, "state": self.result or "playing", "score": self.score}
