import json
import math
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from game.sim import Sim, load_contract  # noqa: E402

C = load_contract()
T, S = C["tuning"], C["score"]
EMPTY = {"random_motes": False, "random_shades": False, "motes": [], "shades": []}
SCN = os.path.join(ROOT, "tests", "scenarios")


def sim(**kw):
    sc = dict(EMPTY)
    sc.update(kw)
    return Sim(1, sc)


def run_steps(s, n, **inp):
    for _ in range(n):
        s.step(inp)


class Contract(unittest.TestCase):
    def test_fields(self):
        for k in ("contract_version", "team", "build_cmd", "run_cmd", "headless_cmd", "tuning", "score"):
            self.assertIn(k, C)
        for k in ("player_speed carry_capacity lantern_cost lantern_count_night1 pickup_radius interact_radius "
                  "pulse_cost pulse_radius night1_duration_s flames invuln_s hit_drop_ratio pulse_stun_s "
                  "pulse_push_m pulse_cooldown_s safe_radius shade_speed shade_hit_radius fall_enabled").split():
            self.assertIn(k, T)
        for k in "per_mote per_lantern per_stun per_second_left per_flame_left".split():
            self.assertIn(k, S)
        self.assertEqual(T["lantern_count_night1"], 5)


class Movement(unittest.TestCase):
    def test_speed_and_start(self):
        s = sim()
        self.assertEqual(s.snapshot()["player"]["pos"], [0, 0, 0])
        run_steps(s, 60, move=(0, 1))
        self.assertAlmostEqual(s.pz, T["player_speed"], places=6)

    def test_diagonal_normalized(self):
        s = sim()
        run_steps(s, 60, move=(1, 1))
        self.assertAlmostEqual(math.hypot(s.px, s.pz), T["player_speed"], places=6)

    def test_yaw_conversion(self):
        s = sim()
        run_steps(s, 60, move=(0, 1), cam_yaw_deg=90)  # x' = z*sin(90) = +1
        self.assertAlmostEqual(s.px, T["player_speed"], places=5)
        self.assertAlmostEqual(s.pz, 0, places=5)

    def test_jump_returns_to_ground(self):
        s = sim()
        s.step({"jump": True})
        self.assertGreater(s.py, 0)
        run_steps(s, 120, jump=False)
        self.assertEqual(s.py, 0)


class Lanterns(unittest.TestCase):
    def test_pickup_capacity_and_score(self):
        s = sim(motes=[[0, 0.5], [0, 0.6], [0, 0.7], [0, 0.8], [0, 0.9], [0, 1.0]])
        s.step({})
        self.assertEqual(s.carried, T["carry_capacity"])
        self.assertEqual(len(s.motes), 1)
        self.assertEqual(s.score, S["per_mote"] * T["carry_capacity"])

    def test_pickup_radius_boundary(self):
        s = sim(motes=[[0, T["pickup_radius"]], [0, T["pickup_radius"] + 0.01]])
        s.step({})
        self.assertEqual(s.carried, 1)

    def test_deposit_requires_range_and_edge(self):
        s = sim(player={"pos": [0, 0, 16 + T["interact_radius"] + 0.1], "carried": 5})
        s.step({"interact": True})
        s.step({"interact": False})
        self.assertEqual(s.carried, 5)  # out of range
        s.pz = 16 + T["interact_radius"]
        s.step({"interact": True})
        self.assertEqual(s.carried, 0)
        self.assertEqual(s.lanterns[0]["deposited"], 5)

    def test_light_all_and_win_score(self):
        lan = [{"id": f"L{i}", "lit": True} for i in range(2, 6)]
        s = sim(player={"pos": [0, 0, 16], "carried": 5}, lanterns=lan, time_left_s=50)
        s.step({"interact": True})
        s.step({"interact": False})
        self.assertEqual(s.state, "playing")
        self.assertEqual(s.lanterns[0]["deposited"], 5)
        s.carried = 5
        s.step({"interact": True})
        self.assertEqual(s.state, "won")
        self.assertTrue(s.lanterns[0]["lit"])
        self.assertEqual([e["name"] for e in s.events], ["deposit", "lantern_lit", "game_over"])
        self.assertEqual(s.events[-1]["data"], {"result": "won", "reason": "all_lit"})
        left = int(s.time_left())
        self.assertEqual(s.score, S["per_lantern"] + left * S["per_second_left"] + T["flames"] * S["per_flame_left"])

    def test_scenario_lit_gives_no_score(self):
        s = sim(lanterns=[{"id": "L1", "lit": True}])
        self.assertEqual(s.score, 0)
        self.assertEqual(s.events, [])


class Shades(unittest.TestCase):
    def test_hit_and_drop_and_invuln(self):
        s = sim(player={"pos": [0, 0, 0], "carried": 5}, shades=[{"pos": [0.5, 0, 0]}])
        s.step({})
        self.assertEqual(s.events[0]["name"], "player_hit")
        self.assertEqual(s.events[0]["data"], {"by": "shade", "flames": 2, "dropped": 2})
        self.assertEqual(s.carried, 3)
        self.assertEqual(len(s.motes), 2)
        n = round(T["invuln_s"] * 60)
        hits = 0
        for _ in range(n - 1):
            s.step({})
            hits += sum(e["name"] == "player_hit" for e in s.events)
        self.assertEqual(hits, 0)
        s.step({})
        self.assertEqual(s.flames, 1)  # next hit exactly invuln_s later

    def test_lose_no_flames(self):
        s = sim(player={"pos": [0, 0, 0], "flames": 1}, shades=[{"pos": [0.5, 0, 0]}])
        s.step({})
        self.assertEqual(s.state, "lost")
        self.assertEqual(s.events[-1]["data"], {"result": "lost", "reason": "no_flames"})

    def test_lose_dawn(self):
        s = sim(time_left_s=1)
        run_steps(s, 60)
        self.assertEqual(s.state, "lost")
        self.assertEqual(s.events[-1]["data"]["reason"], "dawn")
        self.assertEqual(s.time_left(), 0)

    def test_pulse(self):
        s = sim(player={"pos": [0, 0, 0], "carried": 3},
                shades=[{"pos": [3, 0, 0], "id": "A"}, {"pos": [9, 0, 0], "id": "B"}])
        s.step({"pulse": True})
        self.assertEqual(s.events[0]["name"], "pulse")
        self.assertEqual(s.events[0]["data"], {"stunned_ids": ["A"]})
        self.assertEqual(s.carried, 3 - T["pulse_cost"])
        self.assertEqual(s.score, S["per_stun"])
        a = next(x for x in s.shades if x["id"] == "A")
        self.assertEqual(a["state"], "stunned")
        self.assertAlmostEqual(a["x"], 3 + T["pulse_push_m"], places=6)
        # cooldown blocks an immediate second pulse
        s.step({"pulse": False})
        s.step({"pulse": True})
        self.assertEqual(s.events, [])
        self.assertEqual(s.carried, 3 - T["pulse_cost"])
        # the stun wears off after pulse_stun_s
        run_steps(s, round(T["pulse_stun_s"] * 60), pulse=False)
        self.assertNotEqual(next(x for x in s.shades if x["id"] == "A")["state"], "stunned")

    def test_pulse_needs_light(self):
        s = sim(shades=[{"pos": [3, 0, 0]}])
        s.step({"pulse": True})
        self.assertEqual(s.events, [])

    def test_safe_zone(self):
        s = sim(player={"pos": [0, 0, 25]}, lanterns=[{"id": "L1", "lit": True}],
                shades=[{"pos": [0, 0, 10]}])
        run_steps(s, 300)
        l = s.lanterns[0]
        for sh in s.shades:
            self.assertGreaterEqual(math.hypot(sh["x"] - l["x"], sh["z"] - l["z"]), T["safe_radius"] - 1e-6)


class Headless(unittest.TestCase):
    def run_cli(self, *args):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "o.jsonl")
            p = subprocess.run([sys.executable, "-m", "game.headless", *args, "--out", out],
                               cwd=ROOT, capture_output=True, text=True)
            data = ""
            if os.path.exists(out):
                with open(out, encoding="utf-8") as f:
                    data = f.read()
            return p, data

    def test_format_and_cadence(self):
        p, data = self.run_cli("--seed", "5", "--night", "1", "--ticks", "95")
        self.assertEqual(p.returncode, 0)
        rows = [json.loads(l) for l in data.splitlines()]
        self.assertEqual([r["tick"] for r in rows if r["type"] == "snapshot"], list(range(0, 91, 10)))
        self.assertEqual(rows[-1]["type"], "end")
        self.assertEqual(rows[-1]["ticks"], 95)
        self.assertEqual(rows[-1]["state"], "playing")

    def test_deterministic(self):
        a = self.run_cli("--seed", "7", "--night", "1", "--ticks", "1500")[1]
        b = self.run_cli("--seed", "7", "--night", "1", "--ticks", "1500")[1]
        c = self.run_cli("--seed", "8", "--night", "1", "--ticks", "1500")[1]
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)

    def test_stops_at_game_over(self):
        p, data = self.run_cli("--seed", "1", "--night", "1", "--scenario",
                               os.path.join(SCN, "lose_dawn.json"), "--ticks", "500")
        last = json.loads(data.splitlines()[-1])
        self.assertEqual((last["state"], last["ticks"]), ("lost", 30))

    def test_bad_files_exit_2(self):
        with tempfile.TemporaryDirectory() as d:
            bad = os.path.join(d, "bad.json")
            for content in ("{not json", '{"frames":[{"tick":5},{"tick":5}]}', '{"frames":3}'):
                with open(bad, "w") as f:
                    f.write(content)
                p, _ = self.run_cli("--seed", "1", "--night", "1", "--ticks", "5", "--inputs", bad)
                self.assertEqual(p.returncode, 2, content)
                self.assertTrue(p.stderr.strip())
            with open(bad, "w") as f:
                f.write('{"lanterns":[{"id":"L9"}]}')
            p, _ = self.run_cli("--seed", "1", "--night", "1", "--ticks", "5", "--scenario", bad)
            self.assertEqual(p.returncode, 2)
            p, _ = self.run_cli("--seed", "1", "--night", "1", "--ticks", "5", "--scenario", "nope.json")
            self.assertEqual(p.returncode, 2)

    def test_full_scenario_win(self):
        p, data = self.run_cli("--seed", "1", "--night", "1",
                               "--scenario", os.path.join(SCN, "win_two_trips.json"),
                               "--inputs", os.path.join(SCN, "win_two_trips.inputs.json"), "--ticks", "600")
        rows = [json.loads(l) for l in data.splitlines()]
        names = [r["name"] for r in rows if r["type"] == "event"]
        self.assertEqual(names.count("deposit"), 2)
        self.assertIn("lantern_lit", names)
        self.assertEqual(rows[-1]["state"], "won")


if __name__ == "__main__":
    unittest.main()
