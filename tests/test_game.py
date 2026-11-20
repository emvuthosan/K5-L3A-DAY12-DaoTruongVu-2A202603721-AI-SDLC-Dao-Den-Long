import json
import math
import os
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from game.sim import Sim, load_contract, height_at  # noqa: E402

C = load_contract()
T, S = C["tuning"], C["score"]
SCN = os.path.join(ROOT, "tests", "scenarios")


def mk(night=1, **kw):
    sc = {"random_motes": False, "random_shades": False, "random_drifters": False,
          "wind_enabled": False, "motes": [], "shades": [], "drifters": []}
    if night == 1:
        sc["charms"] = []
    sc.update(kw)
    return Sim(1, sc, night=night)


def run(s, n, **inp):
    for _ in range(n):
        s.step(inp)


def names(s):
    return [e["name"] for e in s.events]


def collect(s, n, **inp):
    out = []
    for _ in range(n):
        s.step(inp)
        out += s.events
    return out


class Contract(unittest.TestCase):
    def test_v12_values(self):
        # Phase 3 [THAY THẾ]: v1.2 changes the night durations and the score table (see docs/notes/ADR-0003).
        self.assertEqual(C["contract_version"], "1.3")   # v1.3 (Phase 4) keeps every v1.2 value below
        std = dict(player_speed=6.0, carry_capacity=10, lantern_cost=10, lantern_count_night1=5,
                   pickup_radius=1.0, interact_radius=2.0, pulse_cost=3, pulse_radius=5.0,
                   night1_duration_s=240, night2_duration_s=270, night3_duration_s=300, flames=3,
                   invuln_s=1.5, hit_drop_ratio=0.5, pulse_stun_s=2.0, pulse_push_m=4.0,
                   pulse_cooldown_s=3.0, safe_radius=6.0, shade_speed=4.0, shade_hit_radius=1.0,
                   dash_speed=14.0, dash_duration_s=0.2, dash_cooldown_s=1.5, fuel_max=100, fuel_decay_per_s=1.0,
                   fuel_per_mote=10, relight_cost=5, win_ratio=0.6, drain_per_s=5, low_fuel_threshold=30,
                   capacity_max=20)
        for k, v in std.items():
            self.assertEqual(T[k], v, k)
        self.assertIn("fall_enabled", T)
        for k, v in dict(per_mote=5, per_lantern=100, per_relight=40, per_stun=5, per_stun_drain=15,
                         per_lit_dawn=50, per_flame_left=50, per_second_left=0).items():
            self.assertEqual(S[k], v, k)


class Movement(unittest.TestCase):
    def test_speed_start_diagonal_yaw(self):
        s = mk()
        self.assertEqual(s.snapshot()["player"]["pos"], [0, 0, 0])
        run(s, 60, move=(0, 1))
        self.assertAlmostEqual(s.pz, 6.0, places=6)
        s = mk()
        run(s, 60, move=(1, 1))
        self.assertAlmostEqual(math.hypot(s.px, s.pz), 6.0, places=6)
        s = mk()
        run(s, 60, move=(0, 1), cam_yaw_deg=90)
        self.assertAlmostEqual(s.px, 6.0, places=5)

    def test_jump_only_on_ground(self):
        s = mk()
        s.step({"jump": True})
        self.assertGreater(s.vy, 6.0)
        top = 0
        for i in range(120):
            s.step({"jump": i == 0 or (i % 2 == 0 and i < 30)})  # mashing jump in the air must not re-jump
            top = max(top, s.py)
        self.assertLess(top, 1.3)
        self.assertEqual(s.py, 0.0)
        self.assertTrue(s.grounded)

    def test_dash(self):
        s = mk()
        ev = collect(s, 1, dash=True, move=(0, 1))
        self.assertEqual([e["name"] for e in ev], ["dash"])
        run(s, 11, dash=True, move=(0, 1))
        self.assertAlmostEqual(s.pz, 14.0 * 0.2, places=6)       # 12 ticks at 14 m/s
        run(s, 1, dash=False, move=(0, 1))
        self.assertAlmostEqual(s.pz, 2.8 + 0.1, places=6)         # back to run speed
        # cooldown 1.5 s measured from the start (tick 1): second dash allowed at tick 91, not 90
        s = mk()
        for second, expect in ((90, False), (91, True)):
            s = mk()
            got = []
            for k in range(1, 100):
                s.step({"dash": k in (1, second)})
                if "dash" in names(s):
                    got.append(s.tick)
            self.assertEqual(got, [1, second] if expect else [1])

    def test_dash_air_keeps_height_and_default_direction(self):
        s = mk()
        run(s, 3, jump=True)
        y = s.py
        s.step({"dash": True})
        for _ in range(11):
            s.step({})
        self.assertAlmostEqual(s.py, y, places=9)
        self.assertGreater(s.pz, 2.7)                              # no input -> facing (+Z)

    def test_fall_once_wait_respawn(self):
        s = mk(player={"pos": [39.9, 0, 0], "carried": 4})
        ev = []
        while not any(e["name"] == "player_hit" for e in ev):
            s.step({"move": (1, 0)})
            ev += s.events
        k = s.tick
        self.assertEqual(ev[-1]["data"], {"by": "fall", "flames": 2, "dropped": 0, "lost": 4})
        self.assertEqual(s.carried, 0)
        for _ in range(59):
            s.step({})
        self.assertLess(s.py, -10)
        self.assertEqual(s.flames, 2)
        s.step({})
        self.assertEqual(s.tick, k + 60)
        self.assertEqual(s.snapshot()["player"]["pos"], [0, 0, 0])
        self.assertEqual(s.invuln, 90)
        self.assertEqual(s.snapshot()["player"]["vel"], [0, 0, 0])

    def test_fall_last_flame_loses(self):
        s = mk(player={"pos": [39.9, 0, 0], "flames": 1})
        ev = collect(s, 120, move=(1, 0))
        self.assertEqual(ev[-1]["data"], {"result": "lost", "reason": "no_flames"})
        self.assertTrue(s.over)


class Lanterns(unittest.TestCase):
    def test_pickup_rules(self):
        s = mk(motes=[[0, 0, 1.0], [0, 0, 1.01]])
        s.step({})
        self.assertEqual(s.carried, 1)
        self.assertEqual(s.score, 0)                               # scoring happens on deposit
        s = mk(motes=[[0, 1.5, 0.5], [0, 1.51, -0.5]])
        s.step({})
        self.assertEqual(s.carried, 1)
        s = mk(motes=[[0, 0, 0.1 * i] for i in range(12)])
        s.step({})
        self.assertEqual(s.carried, T["carry_capacity"])

    def test_deposit_score_and_range(self):
        s = mk(player={"pos": [0, 0, 25 + 2.01], "carried": 10})
        s.step({"interact": True})
        s.step({"interact": False})
        self.assertEqual(s.carried, 10)
        s.pz = 27.0
        s.step({"interact": True})
        self.assertEqual(s.carried, 0)
        self.assertTrue(s.lanterns[0]["lit"])
        self.assertEqual(s.score, 10 * 5 + 100)   # Phase 3: +5 per mote, +100 first light

    def test_partial_and_min(self):
        s = mk(player={"pos": [0, 0, 25], "carried": 4})
        s.step({"interact": True})
        self.assertEqual((s.carried, s.lanterns[0]["deposited"], s.score), (0, 4, 20))
        s.carried = 9
        s.step({"interact": False})
        s.step({"interact": True})
        self.assertEqual((s.carried, s.lanterns[0]["deposited"]), (3, 10))

    def test_nearest_then_id(self):
        s = mk(player={"pos": [12, 0, 12], "carried": 5},
               lanterns=[{"id": "L1", "pos": [12, 0, 13]}, {"id": "L2", "pos": [12, 0, 11]}])
        s.step({"interact": True})
        self.assertEqual((s.lanterns[0]["deposited"], s.lanterns[1]["deposited"]), (5, 0))

    def test_no_early_win_and_dawn_win(self):
        # Phase 3 [THAY THẾ] "thắng ngay khi tất cả đèn sáng": lighting every lantern no longer ends the night.
        lan = [{"id": f"L{i}", "lit": True} for i in range(1, 6)]
        s = mk(lanterns=lan, time_left_s=1)
        run(s, 59)
        self.assertFalse(s.over)
        s.step({})
        self.assertEqual(s.events[-1]["data"], {"result": "won", "reason": "dawn_survived"})

    def test_lose_dawn_and_no_flames_priority(self):
        s = mk(time_left_s=1)
        run(s, 60)
        self.assertEqual(s.events[-1]["data"], {"result": "lost", "reason": "dawn"})

    def test_scenario_lit_no_score_no_events(self):
        s = mk(lanterns=[{"id": "L1", "lit": True}])
        self.assertEqual((s.score, s.events), (0, []))


class Pulse(unittest.TestCase):
    def test_pulse_effects(self):
        s = mk(player={"pos": [0, 0, 0], "carried": 5},
               shades=[{"id": "A", "pos": [3, 0, 0]}, {"id": "B", "pos": [0, 0, 5.0]},
                       {"id": "C", "pos": [4.9, 0, 0]}])
        ev = collect(s, 1, pulse=True)
        self.assertEqual(ev[0], {"type": "event", "tick": 1, "name": "pulse", "data": {"stunned_ids": ["A", "C"]}})
        self.assertEqual((s.carried, s.score), (2, 10))
        self.assertEqual(s.snapshot()["player"]["pulse_cd_s"], 3.0)
        a = s.shades[0]
        self.assertEqual((a["state"], a["tl"]), ("stunned", 120))
        run(s, 14, pulse=False)
        self.assertAlmostEqual(a["x"], 7.0, places=6)               # 4 m total in the first 15 ticks
        run(s, 105, pulse=False)
        self.assertEqual(a["state"], "stunned")                      # tick 120
        run(s, 1, pulse=False)
        self.assertNotEqual(a["state"], "stunned")                   # tick 121

    def test_pulse_refresh_counts_stunned(self):
        s = mk(player={"pos": [0, 0, 0], "carried": 3},
               shades=[{"pos": [2, 0, 0], "state": "stunned", "state_ticks_left": 50}])
        s.step({"pulse": True})
        self.assertEqual((s.shades[0]["tl"], s.score), (120, 5))

    def test_pulse_gating(self):
        s = mk(player={"pos": [0, 0, 0], "carried": 2}, shades=[{"pos": [2, 0, 0]}])
        s.step({"pulse": True})
        self.assertEqual((s.events, s.carried, s.pulse_cd), ([], 2, 0))
        s = mk(player={"pos": [0, 0, 0], "carried": 9, "pulse_cd_ticks": 10})
        s.step({"pulse": True})
        self.assertEqual((s.events, s.carried), ([], 9))
        s = mk(player={"pos": [0, 0, 0], "carried": 9})
        s.step({"pulse": True})
        s.step({"pulse": False})
        s.step({"pulse": True})
        self.assertEqual(s.carried, 6)                               # cooldown blocked the second pulse

    def test_push_stops_at_obstacle_and_plus_x(self):
        s = mk(player={"pos": [36, 0, 0], "carried": 3}, shades=[{"pos": [39, 0, 0]}])
        run(s, 1, pulse=True)
        run(s, 20)
        self.assertLessEqual(s.shades[0]["x"], 40.0)
        s = mk(player={"pos": [5, 0, 5], "carried": 3}, shades=[{"pos": [5, 0, 5]}])
        s.step({"pulse": True})
        self.assertGreater(s.shades[0]["x"], 5.2)


class Shades(unittest.TestCase):
    def test_hit_drop_invuln_recoil(self):
        s = mk(player={"pos": [0, 0, 0], "carried": 5}, shades=[{"pos": [0.5, 0, 0], "state": "chase"}])
        ev = collect(s, 1)
        self.assertEqual(ev[0]["data"], {"by": "shade", "flames": 2, "dropped": 2})
        self.assertEqual((s.carried, s.invuln), (3, 90))
        self.assertEqual([m["kind"] for m in s.motes], ["dropped", "dropped"])
        for m in s.motes:
            self.assertTrue(1.5 <= math.hypot(m["x"], m["z"]) <= 2.5)
            self.assertEqual(m["ttl"], 480)
        run(s, 59)
        self.assertEqual(s.shades[0]["state"], "recoil")
        self.assertAlmostEqual(s.shades[0]["x"], 0.5 - 4 / 60 + 2.0, places=6)   # 2 m over 60 ticks
        run(s, 1)
        self.assertNotEqual(s.shades[0]["state"], "recoil")

    def test_invuln_ignores_contact_and_one_hit_per_tick(self):
        s = mk(player={"pos": [0, 0, 0], "invuln_ticks": 3}, shades=[{"pos": [0.5, 0, 0]}])
        run(s, 2)
        self.assertEqual((s.flames, s.shades[0]["state"]), (3, "chase"))
        run(s, 1)
        self.assertEqual(s.flames, 2)
        s = mk(player={"pos": [0, 0, 0]}, shades=[{"pos": [0.5, 0, 0]}, {"pos": [0, 0, 0.5]}])
        s.step({})
        self.assertEqual(s.flames, 2)

    def test_height_difference_no_hit(self):
        s = mk(player={"pos": [0, 1.6, 0]}, shades=[{"pos": [0.5, 0, 0]}])
        s.step({})
        self.assertEqual(s.flames, 3)

    def test_detect_and_lose(self):
        s = mk(player={"pos": [0, 0, 0]}, shades=[{"pos": [11.9, 0, 0]}, {"pos": [20, 0, 0]}])
        s.step({})
        self.assertEqual([x["state"] for x in s.shades], ["chase", "wander"])
        s.shades[0]["x"] = 18.5
        s.step({})
        self.assertEqual(s.shades[0]["state"], "wander")

    def test_speeds(self):
        s = mk(player={"pos": [0, 0, 0]}, shades=[{"pos": [10, 0, 0]}])
        run(s, 60)
        self.assertAlmostEqual(s.shades[0]["x"], 6.0, places=5)      # 4 m/s toward Mây
        s = mk(3, player={"pos": [0, 0, -30]}, shades=[{"pos": [0, 0, -20]}])
        run(s, 60)
        self.assertAlmostEqual(s.shades[0]["z"], -24.5, places=5)    # 4.5 m/s on night 3

    def test_spawn_schedule(self):
        for night, first, gap, cap in ((1, 300, 480, 6), (2, 300, 420, 8), (3, 300, 360, 10)):
            s = mk(night, random_shades=True, shades=[], player={"pos": [0, 0, 0] if night < 3 else [0, 0, -30],
                                                                  "flames": 9999})
            seen = {}
            for _ in range(first + gap * 12 + 1):
                s.step({})
                for e in s.events:
                    if e["name"] == "shade_spawned":
                        seen.setdefault(s.tick, []).append(e["data"]["id"])
                if s.tick == first:
                    self.assertEqual([x["state"] for x in s.shades], ["spawning", "spawning"])
                if s.tick == first + 1:
                    self.assertTrue(all(x["state"] != "spawning" for x in s.shades))
            ticks = sorted(seen)
            self.assertEqual(seen[first], ["S1", "S2"])
            self.assertEqual(ticks[1:4], [first + gap, first + 2 * gap, first + 3 * gap])
            self.assertEqual(len(s.shades), cap)

    def test_spawn_far_from_player(self):
        s = mk(random_shades=True, player={"pos": [37 * math.cos(math.radians(15)), 0,
                                                    37 * math.sin(math.radians(15))], "flames": 99})
        run(s, 300)
        for sh in s.shades:
            self.assertGreaterEqual(math.hypot(sh["x"] - s.px, sh["z"] - s.pz), 15.0)

    def test_safe_zone_blocks(self):
        s = mk(player={"pos": [0, 0, 28]}, lanterns=[{"id": "L1", "lit": True}], shades=[{"pos": [0, 0, 16.5]}])
        run(s, 300)
        self.assertLessEqual(s.shades[0]["z"], 19.0 + 1e-6)
        self.assertGreater(s.shades[0]["z"], 18.9)

    def test_expel_is_harmless_and_bounded(self):
        s = mk(player={"pos": [0, 0, 23.5]}, lanterns=[{"id": "L1", "lit": True}], shades=[{"pos": [0, 0, 23]}])
        ev = collect(s, 30)
        self.assertNotIn("player_hit", [e["name"] for e in ev])
        self.assertAlmostEqual(math.hypot(s.shades[0]["x"], s.shades[0]["z"] - 25), 6.0, places=6)


class World(unittest.TestCase):
    def test_initial_motes_and_schedule(self):
        for night, cap_by_points in ((1, 24), (2, 24), (3, 30)):
            s = Sim(5, {"random_shades": False, "random_drifters": False}, night=night)
            self.assertEqual(len(s.motes), 20)
            self.assertEqual(len({(m["x"], m["z"]) for m in s.motes}), 20)
            s.px, s.pz = 0.0, 0.0
            s.invuln = 10 ** 9
            for _ in range(240):
                s.step({})
            self.assertEqual(len(s.motes), 21 if night != 3 else 21)
            for _ in range(240 * 12):
                s.step({})
            self.assertEqual(len(s.motes), cap_by_points)            # trần 30 / hết điểm thì bỏ lượt

    def test_dropped_ttl(self):
        s = mk(motes=[{"pos": [10, 0, 10], "kind": "dropped", "ttl_ticks": 3}])
        run(s, 2)
        self.assertEqual(len(s.motes), 1)
        run(s, 1)
        self.assertEqual(len(s.motes), 0)

    def test_terrain_night2(self):
        s = mk(2, charms=[], player={"pos": [24, 0, 0]})
        run(s, 120, move=(1, 0))
        self.assertAlmostEqual(s.px, 36.0, places=5)
        self.assertEqual(s.py, 0.0)
        s = mk(2, player={"pos": [35, 0, 1.5]})
        ev = collect(s, 200, move=(0, 1))
        self.assertIn("player_hit", [e["name"] for e in ev])         # no rails: falls off the bridge

    def test_terrain_night3(self):
        s = mk(3, player={"pos": [0, 0, 11]})
        run(s, 60, move=(0, 1))
        self.assertLess(s.pz, 12.0 + 1e-6)
        self.assertEqual(s.py, 0.0)                                  # tier wall is not climbable
        a = math.radians(30)
        s = mk(3, player={"pos": [32 * math.cos(a), 0, 32 * math.sin(a)]})
        run(s, 120, move=(-math.cos(a), -math.sin(a)))
        self.assertAlmostEqual(s.py, 3.0, places=6)                  # ramp leads to tier 1
        s = mk(3, player={"pos": [0, 6, 6]})
        run(s, 120, move=(0, -1))
        self.assertGreaterEqual(s.pz, 2.0 - 1e-6)                    # tower blocks
        s = mk(3, player={"pos": [0, 3, 15]})
        run(s, 200, move=(0, 1))
        self.assertEqual((s.py, s.grounded), (0.0, True))            # walking off a tier drops down
        self.assertEqual(height_at(3, 0, 0), 6.0)

    def test_launch_pads(self):
        s = mk(2, player={"pos": [20, 0, 17]})
        run(s, 150, move=(0, -1))
        self.assertTrue(s.grounded)
        self.assertLessEqual((s.px - 70) ** 2 + s.pz ** 2, 28 ** 2)
        s = mk(2, player={"pos": [20, 0, 17]})
        s.step({"move": (0, 1)})
        self.assertAlmostEqual(s.vy, 14.0 - 20 / 60, places=6)
        s = mk(3, player={"pos": [0, 3, 15]})
        run(s, 150, move=(0, -1))
        self.assertEqual((s.py, s.grounded), (6.0, True))
        self.assertLess(math.hypot(s.px, s.pz), 8.0)

    def test_wind(self):
        s = mk(3, wind_enabled=True, player={"pos": [0, 0, -30]})
        run(s, 1799)
        self.assertFalse(s.snapshot()["wind"]["active"])
        self.assertEqual((s.px, s.pz), (0.0, -30.0))
        run(s, 1)
        self.assertTrue(s.snapshot()["wind"]["active"])
        run(s, 299)
        self.assertAlmostEqual(math.hypot(s.px, s.pz + 30), 10.0, places=4)   # 2 m/s for 5 s
        run(s, 1)
        self.assertFalse(s.snapshot()["wind"]["active"])


class Drifters(unittest.TestCase):
    def test_chase_then_steal_then_vanish(self):
        s = mk(2, player={"pos": [0, 0, 0], "carried": 6}, drifters=[{"pos": [10, 0, 0]}])
        s.step({})
        self.assertEqual(s.drifters[0]["state"], "chase")
        ev = []
        while "drifter_steal" not in [e["name"] for e in ev]:
            s.step({})
            ev += s.events
        self.assertEqual(ev[-1]["data"], {"drifter_id": "D1", "amount": 3, "carried": 3})
        self.assertEqual((s.drifters[0]["state"], s.drifters[0]["stolen"]), ("flee", 3))
        run(s, 239)
        self.assertEqual(len(s.drifters), 1)
        run(s, 1)
        self.assertEqual(len(s.drifters), 0)

    def test_idle_when_poor_and_steal_min(self):
        s = mk(2, player={"pos": [0, 0, 0], "carried": 4}, drifters=[{"pos": [10, 0, 0]}])
        run(s, 5)
        self.assertEqual(s.drifters[0]["state"], "idle")
        s = mk(2, player={"pos": [0, 0, 0], "carried": 2, "invuln_ticks": 99}, drifters=[{"pos": [0.5, 0, 0]}])
        ev = collect(s, 1)
        self.assertEqual(ev[0]["data"], {"drifter_id": "D1", "amount": 2, "carried": 0})

    def test_pulse_effects(self):
        s = mk(2, player={"pos": [0, 0, 0], "carried": 6}, drifters=[{"pos": [4, 0, 0], "state": "chase"}])
        s.step({"pulse": True})
        self.assertEqual((s.drifters[0]["state"], s.drifters[0]["stolen"]), ("flee", 0))
        self.assertEqual(s.flames, 3)
        s = mk(2, player={"pos": [0, 0, 0], "carried": 3},
               drifters=[{"pos": [3, 0, 0], "state": "flee", "stolen": 3, "state_ticks_left": 200}])
        ev = collect(s, 1, pulse=True)
        self.assertEqual([e["name"] for e in ev], ["drifter_drop", "pulse"])
        self.assertEqual(ev[0]["data"], {"drifter_id": "D1", "amount": 3})
        self.assertEqual([m["kind"] for m in s.motes], ["dropped"] * 3)
        self.assertEqual((s.drifters[0]["stolen"], s.drifters[0]["tl"]), (0, 120))

    def test_spawn_schedule(self):
        s = mk(2, random_drifters=True, player={"pos": [0, 0, 0], "flames": 99})
        run(s, 1199)
        self.assertEqual(s.drifters, [])
        run(s, 1)
        self.assertEqual([d["id"] for d in s.drifters], ["D1"])
        run(s, 3600)
        self.assertEqual(len(s.drifters), 2)                         # at most 2
        s = mk(1, random_drifters=True)
        run(s, 1300)
        self.assertEqual(s.drifters, [])


class Charms(unittest.TestCase):
    def test_pick_speed_expiry_respawn(self):
        s = mk(2, player={"pos": [34.5, 0, 0]})
        s.step({"move": (1, 0)})
        self.assertEqual(s.events[0]["data"], {"charm_id": "C1", "charm_ticks": 600})
        self.assertEqual(s.snapshot()["player"]["charm_s"], 10.0)
        self.assertEqual(s.snapshot()["charms"][0]["available"], False)
        x0 = s.px
        run(s, 60, move=(1, 0))
        self.assertAlmostEqual(s.px - x0, 7.2, places=5)
        run(s, 540)
        self.assertEqual(s.charm, 0)
        s = mk(2, player={"pos": [35, 0, 0]})
        ev = collect(s, 2701)
        picks = [e["tick"] for e in ev if e["name"] == "charm_picked"]
        self.assertEqual(picks, [1, 2701])                           # back after 2700 ticks

    def test_charm_dash_no_cooldown(self):
        s = mk(2, player={"pos": [0, 0, 0], "charm_ticks": 600})
        got = []
        for k in range(1, 40):
            s.step({"dash": k % 2 == 1, "move": (0, 1)})
            if "dash" in names(s):
                got.append(s.tick)
        self.assertEqual(got[:2], [1, 13])      # pressing during a dash is ignored; no cooldown afterwards
        self.assertEqual(s.snapshot()["player"]["dash_cd_s"], 0.0)

    def test_night3_charm_positions(self):
        s = mk(3)
        self.assertEqual([(c["x"], c["z"]) for c in s.charms], [(30.0, 25.0), (-30.0, 25.0)])


class Pause(unittest.TestCase):
    def test_pause_freezes(self):
        s = mk(player={"pos": [0, 0, 0], "carried": 5}, time_left_s=100)
        s.step({"move": (0, 1)})
        self.assertEqual(s.sim_tick, 1)
        s.step({"move": (0, 1), "pause": True})
        self.assertEqual(names(s), ["paused"])
        self.assertEqual((s.tick, s.sim_tick, s.snapshot()["state"]), (2, 1, "paused"))
        z = s.pz
        for _ in range(30):
            s.step({"move": (0, 1), "pause": False})
        self.assertEqual((s.pz, s.sim_tick, s.tick), (z, 1, 32))
        s.step({"move": (0, 1), "pause": True})
        self.assertEqual(names(s), ["resumed"])
        self.assertEqual((s.sim_tick, s.snapshot()["state"]), (2, "playing"))
        self.assertGreater(s.pz, z)
        self.assertAlmostEqual(s.time_left(), 100 - 2 / 60)


class Headless(unittest.TestCase):
    def cli(self, *args):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "o.jsonl")
            p = subprocess.run([sys.executable, "-m", "game.headless", *args, "--out", out],
                               cwd=ROOT, capture_output=True, text=True)
            data = ""
            if os.path.exists(out):
                with open(out, encoding="utf-8") as f:
                    data = f.read()
            return p, data

    def test_format(self):
        for night in (1, 2, 3):
            p, data = self.cli("--seed", "5", "--night", str(night), "--ticks", "95")
            self.assertEqual(p.returncode, 0)
            rows = [json.loads(l) for l in data.splitlines()]
            snaps = [r for r in rows if r["type"] == "snapshot"]
            self.assertEqual([r["tick"] for r in snaps], list(range(0, 91, 10)))
            a = snaps[0]
            for k in ("tick sim_tick night state time_left_s score wind player lanterns shades motes_active "
                      "motes drifters charms").split():
                self.assertIn(k, a)
            self.assertEqual(a["night"], night)
            self.assertEqual(set(a["wind"]), {"active", "dir_deg"})
            for k in "pos vel grounded invuln flames carried dash_cd_s pulse_cd_s charm_s".split():
                self.assertIn(k, a["player"])
            for k in ("id", "pos", "kind", "ttl_s"):
                self.assertIn(k, a["motes"][0])
            self.assertEqual(rows[-1], {"type": "end", "ticks": 95, "state": "playing", "score": 0})
            self.assertEqual(rows[1]["name"], "night_start")

    def test_deterministic_all_nights(self):
        for night in ("1", "2", "3"):
            a = self.cli("--seed", "7", "--night", night, "--ticks", "2500")[1]
            b = self.cli("--seed", "7", "--night", night, "--ticks", "2500")[1]
            c = self.cli("--seed", "8", "--night", night, "--ticks", "2500")[1]
            self.assertEqual(a, b)
            self.assertNotEqual(a, c)

    def test_bad_input_exit_2(self):
        with tempfile.TemporaryDirectory() as d:
            bad = os.path.join(d, "bad.json")
            for content in ("{not json", '{"frames":[{"tick":5},{"tick":5}]}', '{"frames":3}',
                            '{"frames":[{"tick":1,"dash":1}]}'):
                with open(bad, "w") as f:
                    f.write(content)
                p, _ = self.cli("--seed", "1", "--night", "1", "--ticks", "5", "--inputs", bad)
                self.assertEqual(p.returncode, 2, content)
                self.assertTrue(p.stderr.strip())
            for content in ('{"lanterns":[{"id":"L9"}]}', '{"shades":[{"pos":[0,0,0],"state":"dead"}]}',
                            '{"drifters":[{"pos":"x"}]}'):
                with open(bad, "w") as f:
                    f.write(content)
                p, _ = self.cli("--seed", "1", "--night", "1", "--ticks", "5", "--scenario", bad)
                self.assertEqual(p.returncode, 2, content)
        self.assertEqual(self.cli("--seed", "1", "--night", "4", "--ticks", "5")[0].returncode, 2)
        self.assertEqual(self.cli("--seed", "1", "--night", "1", "--ticks", "5", "--scenario", "nope.json")[0].returncode, 2)

    def test_full_night_under_30s(self):
        with tempfile.TemporaryDirectory() as d:
            sc = os.path.join(d, "s.json")
            with open(sc, "w") as f:
                json.dump({"player": {"flames": 100000, "carried": 9}}, f)
            t0 = time.time()
            p, data = self.cli("--seed", "3", "--night", "3", "--ticks", "21600", "--scenario", sc)
            self.assertEqual(p.returncode, 0)
            self.assertLess(time.time() - t0, 30)
            self.assertEqual(json.loads(data.splitlines()[-1])["ticks"], 18000)   # night 3 = 300 s at dawn

    def test_phase1_scenario_still_wins(self):
        p, data = self.cli("--seed", "1", "--night", "1",
                           "--scenario", os.path.join(SCN, "win_two_trips.json"),
                           "--inputs", os.path.join(SCN, "win_two_trips.inputs.json"), "--ticks", "600")
        rows = [json.loads(l) for l in data.splitlines()]
        self.assertEqual(rows[-1]["state"], "won")          # now at dawn (Phase 3), after both deposits
        self.assertEqual(sum(r["name"] == "deposit" for r in rows if r["type"] == "event"), 2)
        self.assertEqual(rows[-1]["ticks"], 360)


if __name__ == "__main__":
    unittest.main()
