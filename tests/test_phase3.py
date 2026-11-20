"""Ticket-03 'Đèn cạn dầu' (Contract v1.2): fuel, drain, dawn win rule, capacity, new score table."""
import json
import math
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from game.sim import Sim  # noqa: E402
from tests.test_game import mk, run, collect, names, C  # noqa: E402

T, S = C["tuning"], C["score"]
L1 = (0, 25)          # night 1 lantern L1 position (x, z)


def lit(*ids, fuel=None):
    out = []
    for i in ids:
        e = {"id": f"L{i}", "lit": True}
        if fuel is not None:
            e["fuel"] = fuel
        out.append(e)
    return out


class Fuel(unittest.TestCase):
    def test_decay_exact_and_out(self):
        s = mk(lanterns=lit(1))
        self.assertEqual(s.snapshot()["lanterns"][0]["fuel"], 100.0)
        run(s, 60)
        self.assertEqual(s.snapshot()["lanterns"][0]["fuel"], 99.0)       # 1.0 per second
        run(s, 5939)
        self.assertEqual(s.lanterns[0]["fu"], 1)
        self.assertTrue(s.lanterns[0]["lit"])
        ev = collect(s, 1)
        self.assertEqual([e["name"] for e in ev], ["lantern_out"])
        self.assertEqual(ev[0]["tick"], 6000)                              # integer 1/60 units: no float drift
        l = s.snapshot()["lanterns"][0]
        self.assertEqual((l["lit"], l["fuel"], l["deposited"], l["ever_lit"]), (False, 0, 0, True))

    def test_scenario_fuel_default_and_explicit(self):
        s = mk(lanterns=[{"id": "L1", "lit": True}, {"id": "L2", "lit": True, "fuel": 42.5}])
        self.assertEqual([l["fuel"] for l in s.snapshot()["lanterns"][:2]], [100.0, 42.5])
        self.assertTrue(s.lanterns[0]["ever"])

    def test_refuel_formula(self):
        s = mk(player={"pos": [0, 0, 25], "carried": 10}, lanterns=lit(1, fuel=50))
        ev = collect(s, 1, interact=True)
        # decay happens in step 2 before interact: fuel 49.983 -> ceil(50.017/10) = 6 motes
        self.assertEqual(ev[0], {"type": "event", "tick": 1, "name": "refuel",
                                 "data": {"lantern_id": "L1", "amount": 6, "fuel": 100.0}})
        self.assertEqual((s.carried, s.score), (4, 30))
        s = mk(player={"pos": [0, 0, 25], "carried": 2}, lanterns=lit(1, fuel=20))
        collect(s, 1, interact=True)
        self.assertEqual(s.carried, 0)
        self.assertEqual(s.snapshot()["lanterns"][0]["fuel"], round(20 - 1 / 60 + 20, 1))
        s = mk(player={"pos": [0, 0, 25], "carried": 5}, lanterns=lit(1, fuel=95.5))
        collect(s, 1, interact=True)
        self.assertEqual((s.carried, s.snapshot()["lanterns"][0]["fuel"]), (4, 100.0))   # min(100, ...)

    def test_full_lantern_not_selected(self):
        s = mk(player={"pos": [0, 0, 25], "carried": 5}, lanterns=lit(1))
        s.lanterns[0]["fu"] = s.fmax_u
        # lantern at full fuel is skipped, even though it is the nearest; no event, no score
        s.fu_hold = True
        s.step({})                       # decay makes it 99.98..., so re-fill to test the pure rule
        s.lanterns[0]["fu"] = s.fmax_u
        s.prev["interact"] = False
        s.decay_u = 0
        ev = collect(s, 1, interact=True)
        self.assertEqual((ev, s.carried, s.score), ([], 5, 0))
        # a farther unlit lantern within range is chosen instead
        s = mk(player={"pos": [10, 0, 10], "carried": 5},
               lanterns=[{"id": "L1", "lit": True, "pos": [10, 0, 10.5]}, {"id": "L2", "pos": [10, 0, 11.5]}])
        s.decay_u = 0
        s.lanterns[0]["fu"] = s.fmax_u
        collect(s, 1, interact=True)
        self.assertEqual(s.lanterns[1]["deposited"], 5)

    def test_nearest_receiver_tie_by_id(self):
        s = mk(player={"pos": [10, 0, 10], "carried": 3},
               lanterns=[{"id": "L2", "lit": True, "fuel": 10, "pos": [10, 0, 11]},
                         {"id": "L1", "lit": True, "fuel": 10, "pos": [10, 0, 9]}])
        s.decay_u = 0
        s.step({"interact": True})
        self.assertEqual(s.events[0]["data"]["lantern_id"], "L1")

    def test_relight_cost_and_score(self):
        s = mk(player={"pos": [0, 0, 25], "carried": 5}, lanterns=[{"id": "L1", "ever_lit": True}])
        ev = collect(s, 1, interact=True)
        self.assertEqual([e["name"] for e in ev], ["deposit", "lantern_lit"])
        self.assertEqual(ev[1]["data"], {"lantern_id": "L1", "relight": True})
        self.assertEqual(s.score, 5 * 5 + 40)
        l = s.snapshot()["lanterns"][0]
        self.assertEqual((l["lit"], l["fuel"], l["relit_count"]), (True, 100.0, 1))
        s = mk(player={"pos": [0, 0, 25], "carried": 5})                 # never lit: still needs 10
        collect(s, 1, interact=True)
        self.assertFalse(s.lanterns[0]["lit"])
        s.carried = 5
        s.step({"interact": False})
        ev = collect(s, 1, interact=True)
        self.assertEqual(ev[-1]["data"], {"lantern_id": "L1", "relight": False})
        self.assertEqual(s.score, 10 * 5 + 100)

    def test_out_then_relight_cycle(self):
        s = mk(player={"pos": [0, 0, 25], "carried": 10}, lanterns=[{"id": "L1", "lit": True, "fuel": 1 / 60}])
        ev = collect(s, 1)
        self.assertIn("lantern_out", [e["name"] for e in ev])
        collect(s, 1, interact=True)
        self.assertTrue(s.lanterns[0]["lit"])                            # 5 motes were enough
        self.assertEqual(s.carried, 5)

    def test_safe_zone_threshold(self):
        s = mk(lanterns=lit(1, fuel=30 + 1 / 60))
        s.step({})
        self.assertTrue(s._zone(s.lanterns[0]))                          # exactly 30.0 keeps the zone
        s.step({})
        self.assertFalse(s._zone(s.lanterns[0]))                         # 29.98 loses it

    def test_weak_lantern_lets_shades_in_strong_blocks(self):
        for fuel, reached in ((60, False), (20, True)):
            s = mk(player={"pos": [0, 0, 28], "flames": 99}, lanterns=lit(1, fuel=fuel),
                   shades=[{"pos": [0, 0, 16.5], "state": "chase"}])
            run(s, 200)
            self.assertEqual(s.flames < 99, reached, fuel)


class Drain(unittest.TestCase):
    def test_wander_picks_weak_lantern_and_drains(self):
        s = mk(player={"pos": [0, 0, -30], "flames": 99},
               lanterns=[{"id": "L1", "lit": True, "fuel": 25}, {"id": "L2", "lit": True, "fuel": 28}],
               shades=[{"pos": [0, 0, 38]}])
        for _ in range(200):
            s.step({})
            if s.shades[0]["state"] == "drain":
                break
        sh = s.shades[0]
        self.assertEqual((sh["state"], sh["target"]), ("drain", "L1"))
        self.assertLessEqual(math.hypot(sh["x"] - 0, sh["z"] - 25), 2.0 + 1e-9)
        f0 = s.lanterns[0]["fu"]
        run(s, 60)
        self.assertEqual(f0 - s.lanterns[0]["fu"], 6 * 60)                # 1 decay + 5 drain per second
        self.assertEqual(sh["state"], "drain")

    def test_drain_stacks_and_event_every_60(self):
        s = mk(player={"pos": [0, 0, -30]}, lanterns=lit(1, fuel=25),
               shades=[{"pos": [0, 0, 24], "state": "drain", "target_lantern_id": "L1"},
                       {"pos": [0.5, 0, 24], "state": "drain", "target_lantern_id": "L1"}])
        f0 = s.lanterns[0]["fu"]
        ev = collect(s, 60)
        self.assertEqual(f0 - s.lanterns[0]["fu"], 60 * 11)
        fd = [e for e in ev if e["name"] == "fuel_drain"]
        self.assertEqual([(e["tick"], e["data"]["shade_id"]) for e in fd], [(60, "S1"), (60, "S2")])
        self.assertEqual(fd[0]["data"]["fuel"], round(s.lanterns[0]["fu"] / 60, 1))

    def test_target_unlit_when_no_weak(self):
        s = mk(player={"pos": [0, 0, -30]}, lanterns=lit(1, 2, 3, 4), shades=[{"pos": [0, 0, 5]}])
        s.step({})
        self.assertEqual(s.shades[0]["target"], "L5")

    def test_tie_goes_to_smaller_id(self):
        s = mk(player={"pos": [0, 0, -30]}, lanterns=[{"id": "L2", "lit": True, "fuel": 10},
                                                       {"id": "L5", "lit": True, "fuel": 10}],
               shades=[{"pos": [0, 0, 7.7]}])
        s.step({})
        self.assertEqual(s.shades[0]["target"], "L2")

    def test_drain_to_chase_when_player_near(self):
        s = mk(player={"pos": [0, 0, 19]}, lanterns=lit(1, fuel=20),
               shades=[{"pos": [0, 0, 24], "state": "drain", "target_lantern_id": "L1"}])
        s.step({})
        self.assertEqual(s.shades[0]["state"], "chase")

    def test_drain_to_wander_cases(self):
        far = {"player": {"pos": [0, 0, -30]}}
        # lantern out
        s = mk(**far, lanterns=[{"id": "L1", "lit": True, "fuel": 1 / 60}],
               shades=[{"pos": [0, 0, 24], "state": "drain", "target_lantern_id": "L1"}])
        s.step({})
        self.assertEqual((s.lanterns[0]["lit"], s.shades[0]["state"]), (False, "wander"))
        # farther than 2 m
        s = mk(**far, lanterns=lit(1, fuel=20), shades=[{"pos": [0, 0, 22.5], "state": "drain", "target_lantern_id": "L1"}])
        s.step({})
        self.assertNotEqual(s.shades[0]["state"], "drain")
        # refuelled to >= 30
        s = mk(player={"pos": [0, 0, 26.5], "carried": 10}, lanterns=lit(1, fuel=25),
               shades=[{"pos": [0, 0, 24], "state": "drain", "target_lantern_id": "L1"}])
        collect(s, 1, interact=True)
        self.assertGreaterEqual(s.lanterns[0]["fu"], 30 * 60)
        self.assertEqual(s.shades[0]["state"], "wander")

    def test_refuel_expels_harmlessly(self):
        s = mk(player={"pos": [0, 0, 26.5], "carried": 10}, lanterns=lit(1, fuel=25),
               shades=[{"pos": [0, 0, 25.5], "state": "chase"}])
        ev = collect(s, 1, interact=True)
        self.assertIn("refuel", [e["name"] for e in ev])
        self.assertEqual(s.shades[0]["expel"] > 0, True)
        ev = collect(s, 30)
        self.assertNotIn("player_hit", [e["name"] for e in ev])
        self.assertAlmostEqual(math.hypot(s.shades[0]["x"], s.shades[0]["z"] - 25), 6.0, places=6)

    def test_pulse_on_draining_scores_15(self):
        s = mk(player={"pos": [0, 0, 28], "carried": 3}, lanterns=lit(1, fuel=20),
               shades=[{"pos": [0, 0, 24], "state": "drain", "target_lantern_id": "L1"},
                       {"pos": [3, 0, 29]}])
        s.step({"pulse": True})
        self.assertEqual(s.score, 15 + 5)                                 # total 15 for the drainer, 5 for the other
        self.assertEqual([x["state"] for x in s.shades], ["stunned", "stunned"])


class Win(unittest.TestCase):
    def test_thresholds(self):
        for night, total, need in ((1, 5, 3), (2, 6, 4), (3, 7, 5)):
            for n_lit, won in ((need - 1, False), (need, True)):
                s = mk(night, player={"pos": [0, 0, 0] if night < 3 else [0, 0, -30]},
                       lanterns=lit(*range(1, n_lit + 1)), time_left_s=1)
                run(s, 60)
                self.assertEqual(s.result, "won" if won else "lost", (night, n_lit))
                self.assertEqual(s.events[-1]["data"]["reason"], "dawn_survived" if won else "dawn")

    def test_dawn_score(self):
        s = mk(lanterns=lit(1, 2, 3), time_left_s=1)
        run(s, 60)
        self.assertEqual(s.score, 3 * (50 + 99) + 3 * 50)                  # +50 + floor(fuel) per lit lantern, +50 per flame
        s = mk(lanterns=lit(1, 2, 3), time_left_s=1, player={"flames": 2})
        run(s, 60)
        self.assertEqual(s.score, 3 * (50 + 99) + 2 * 50)

    def test_no_time_bonus_when_all_lit(self):
        s = mk(lanterns=lit(1, 2, 3, 4, 5), time_left_s=2)
        run(s, 120)
        self.assertEqual(s.score, 5 * (50 + 98) + 150)

    def test_no_flames_on_dawn_tick(self):
        s = mk(player={"flames": 1}, lanterns=lit(1, 2, 3), shades=[{"pos": [0.5, 0, 0]}], time_left_s=1 / 60)
        s.step({})
        self.assertEqual(s.events[-1]["data"], {"result": "lost", "reason": "no_flames"})

    def test_lantern_out_on_dawn_tick_counts_as_unlit(self):
        lan = [{"id": "L1", "lit": True, "fuel": 1 / 60}] + lit(2, 3)
        s = mk(lanterns=lan, time_left_s=1 / 60)
        s.step({})
        self.assertEqual((s.result, s.events[-1]["data"]["reason"]), ("lost", "dawn"))
        self.assertIn("lantern_out", names(s))

    def test_durations(self):
        for night, secs in ((1, 240), (2, 270), (3, 300)):
            self.assertEqual(mk(night).time0, secs)


class Capacity(unittest.TestCase):
    def test_growth_and_cap(self):
        self.assertEqual(mk().snapshot()["player"]["capacity"], 10)
        for k, cap in ((1, 12), (5, 20), (9, 20)):
            self.assertEqual(mk(player={"successful_lights": k}).snapshot()["player"]["capacity"], cap)

    def test_lights_and_relights_count_prelit_do_not(self):
        s = mk(lanterns=lit(2))
        self.assertEqual(s.capacity(), 10)
        s = mk(player={"pos": [0, 0, 25], "carried": 10})
        collect(s, 1, interact=True)
        self.assertEqual(s.capacity(), 12)
        s = mk(player={"pos": [0, 0, 25], "carried": 5}, lanterns=[{"id": "L1", "ever_lit": True}])
        collect(s, 1, interact=True)
        self.assertEqual(s.capacity(), 12)                               # a relight counts too

    def test_pickup_uses_capacity(self):
        s = mk(player={"successful_lights": 1}, motes=[[0, 0, 0.05 * i] for i in range(15)])
        s.step({})
        self.assertEqual(s.carried, 12)

    def test_refuel_does_not_count(self):
        s = mk(player={"pos": [0, 0, 25], "carried": 5}, lanterns=lit(1, fuel=20))
        collect(s, 1, interact=True)
        self.assertEqual(s.capacity(), 10)


class Score(unittest.TestCase):
    def test_table(self):
        self.assertEqual((S["per_mote"], S["per_lantern"], S["per_relight"], S["per_stun"], S["per_stun_drain"]),
                         (5, 100, 40, 5, 15))
        self.assertEqual((S["per_lit_dawn"], S["per_flame_left"], S["per_second_left"]), (50, 50, 0))


class Headless(unittest.TestCase):
    def cli(self, *args):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "o.jsonl")
            p = subprocess.run([sys.executable, "-m", "game.headless", *args, "--out", out],
                               cwd=ROOT, capture_output=True, text=True)
            rows = []
            if os.path.exists(out):
                with open(out, encoding="utf-8") as f:
                    rows = [json.loads(l) for l in f]
            return p, rows

    def test_snapshot_fields(self):
        p, rows = self.cli("--seed", "1", "--night", "1", "--ticks", "10")
        self.assertEqual(p.returncode, 0)
        a = rows[0]
        for k in ("fuel", "ever_lit", "relit_count", "deposited", "lit"):
            self.assertIn(k, a["lanterns"][0])
        self.assertEqual(a["player"]["capacity"], 10)

    def test_event_names_in_headless(self):
        with tempfile.TemporaryDirectory() as d:
            sc, inp = os.path.join(d, "s.json"), os.path.join(d, "i.json")
            with open(sc, "w") as f:
                json.dump({"random_motes": False, "random_shades": False, "motes": [], "shades": [],
                           "player": {"pos": [0, 0, 25], "carried": 10},
                           "lanterns": [{"id": "L1", "lit": True, "fuel": 30}, {"id": "L3", "lit": True, "fuel": 1}]}, f)
            with open(inp, "w") as f:
                json.dump({"frames": [{"tick": 0, "interact": True}]}, f)
            p, rows = self.cli("--seed", "1", "--night", "1", "--ticks", "200", "--scenario", sc, "--inputs", inp)
            self.assertEqual(p.returncode, 0)
            ev = [r["name"] for r in rows if r["type"] == "event"]
            self.assertIn("refuel", ev)
            self.assertIn("lantern_out", ev)
            self.assertNotIn("all_lit", json.dumps(rows))

    def test_bad_fuel_fields_exit_2(self):
        with tempfile.TemporaryDirectory() as d:
            bad = os.path.join(d, "b.json")
            for content in ('{"lanterns":[{"id":"L1","lit":true,"fuel":"x"}]}',
                            '{"lanterns":[{"id":"L1","ever_lit":1}]}',
                            '{"player":{"successful_lights":"a"}}'):
                with open(bad, "w") as f:
                    f.write(content)
                p, _ = self.cli("--seed", "1", "--night", "1", "--ticks", "5", "--scenario", bad)
                self.assertEqual(p.returncode, 2, content)


if __name__ == "__main__":
    unittest.main()
