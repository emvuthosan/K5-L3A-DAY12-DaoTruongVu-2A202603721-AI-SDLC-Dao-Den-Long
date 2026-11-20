"""Ticket-04 'Bình minh': benchmark scene and metrics, soak, leaderboard, contract v1.3."""
import json
import math
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from game import leaderboard  # noqa: E402
from game.bench import metrics  # noqa: E402
from game.server import Game  # noqa: E402
from game.sim import Sim, bench_scenario, load_contract  # noqa: E402


class Contract13(unittest.TestCase):
    def test_version_and_commands(self):
        c = load_contract()
        self.assertEqual(c["contract_version"], "1.3")
        self.assertIn("bench_cmd", c)
        self.assertIn("soak_cmd", c)
        self.assertEqual(c["tuning"]["fuel_max"], 100)               # v1.2 values are kept


class BenchScene(unittest.TestCase):
    def setUp(self):
        self.sc = bench_scenario(42)

    def test_composition_and_determinism(self):
        s = Sim(42, self.sc, bench=True)
        snap = s.snapshot()
        self.assertEqual((len(snap["shades"]), len(snap["motes"])), (200, 100))
        self.assertTrue(all(x["state"] == "wander" for x in snap["shades"]))
        self.assertEqual([(l["id"], l["lit"], l["fuel"]) for l in snap["lanterns"]],
                         [("L1", True, 100.0), ("L2", True, 100.0), ("L3", True, 100.0),
                          ("L4", False, 0), ("L5", False, 0)])
        self.assertEqual(snap["player"]["pos"], [0, 0, 0])
        self.assertEqual(bench_scenario(42), self.sc)                # same seed, same scene
        self.assertNotEqual(bench_scenario(43), self.sc)
        # spread over the island, not clumped: every shade within the island and several radii used
        rs = sorted(math.hypot(x["pos"][0], x["pos"][2]) for x in snap["shades"])
        self.assertLessEqual(rs[-1], 40)
        self.assertGreater(rs[100], 15)

    def test_gameplay_disabled_but_shades_move(self):
        s = Sim(42, self.sc, bench=True)
        before = [(x["pos"][0], x["pos"][2]) for x in s.snapshot()["shades"]]
        for _ in range(1200):
            s.step({})
        a = s.snapshot()
        self.assertEqual((len(a["shades"]), len(a["motes"])), (200, 100))   # no spawns, no pickups
        self.assertEqual(a["player"]["flames"], 3)                           # no damage
        self.assertEqual([l["fuel"] for l in a["lanterns"][:3]], [100.0] * 3)  # no fuel decay
        self.assertEqual(a["state"], "playing")
        after = [(x["pos"][0], x["pos"][2]) for x in a["shades"]]
        self.assertNotEqual(before, after)                                    # still wandering

    def test_normal_game_unaffected(self):
        s = Sim(1, {"random_motes": False, "random_shades": False, "lanterns": [{"id": "L1", "lit": True}]})
        s.step({})
        self.assertEqual(s.lanterns[0]["fu"], 6000 - 1)                       # fuel still decays outside bench


class BenchMetrics(unittest.TestCase):
    def test_definitions(self):
        dts = [10.0] * 98 + [50.0, 100.0]                                    # N = 100 -> k = 1
        n, avg, low, p95 = metrics(dts)
        self.assertEqual(n, 100)
        self.assertAlmostEqual(avg, 1000 * 100 / 1130)
        self.assertAlmostEqual(low, 1000 / 100.0)                             # slowest single frame
        self.assertEqual(p95, 10.0)                                           # 95th percentile (nearest rank)
        dts = [10.0] * 148 + [30.0, 50.0]                                     # N = 150 -> k = 2
        n, avg, low, p95 = metrics(dts)
        self.assertAlmostEqual(low, 1000 / 40.0)                              # mean of the 2 worst
        n, avg, low, p95 = metrics([20.0] * 50)                               # k = max(1, ceil(0.5)) = 1
        self.assertAlmostEqual(low, 50.0)


class Soak(unittest.TestCase):
    def test_runs_and_is_deterministic(self):
        outs = []
        for _ in range(2):
            with tempfile.TemporaryDirectory() as d:
                o = os.path.join(d, "soak.json")
                p = subprocess.run([sys.executable, "-m", "game.soak", "--seed", "7", "--nights", "4", "--out", o],
                                   cwd=ROOT, capture_output=True, text=True)
                self.assertEqual(p.returncode, 0, p.stderr)
                with open(o) as f:
                    outs.append(json.load(f))
        a, b = outs
        self.assertEqual((a["nights"], a["crashes"]), (4, 0))
        self.assertEqual(len(a["results"]), 4)
        self.assertTrue(all(r in ("won", "lost") for r in a["results"]))
        self.assertEqual(a["results"], b["results"])                          # seeded: same outcomes
        self.assertLessEqual(a["mem_end_mb"], 1.2 * a["mem_start_mb"])
        for k in ("nights", "crashes", "results", "mem_start_mb", "mem_end_mb", "duration_s"):
            self.assertIn(k, a)


class Leaderboard(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["DDL_DATA_DIR"] = self.tmp.name

    def tearDown(self):
        os.environ.pop("DDL_DATA_DIR", None)
        self.tmp.cleanup()

    def test_name_rules(self):
        for ok in ("abc", "Mây_Nhỏ1", "a" * 12, "Đào_Vũ"):
            self.assertIsNotNone(leaderboard.valid_name(ok), ok)
        for bad in ("ab", "a" * 13, "has space", "dấu-gạch", "x!y", "", None, 12345, "日本語名前"):
            self.assertIsNone(leaderboard.valid_name(bad), bad)

    def test_order_top10_and_ties(self):
        t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
        for i in range(12):
            leaderboard.add(f"p{i:02d}", 100 + i * 10, 1, i, now=t0 + timedelta(minutes=i))
        leaderboard.add("tieEarly", 150, 2, 1, now=t0 - timedelta(days=1))   # same score as p05, achieved earlier
        es = leaderboard.load()
        self.assertEqual(len(es), 10)
        self.assertEqual([e["score"] for e in es], sorted([e["score"] for e in es], reverse=True))
        self.assertEqual(es[0]["name"], "p11")
        names = [e["name"] for e in es]
        self.assertLess(names.index("tieEarly"), names.index("p05"))           # earlier wins a tie
        self.assertNotIn("p00", names)                                          # dropped out of the top 10
        for e in es:
            self.assertEqual(set(e), {"name", "score", "nights_won", "achieved_at", "seed"})
            self.assertIsNotNone(datetime.fromisoformat(e["achieved_at"]).tzinfo)

    def test_persists_and_exports(self):
        leaderboard.add("Persist", 500, 3, 9)
        out = os.path.join(self.tmp.name, "out.json")
        env = dict(os.environ, DDL_DATA_DIR=self.tmp.name)
        p = subprocess.run([sys.executable, "-m", "game.server", "--export-leaderboard", out],
                           cwd=ROOT, capture_output=True, text=True, env=env)   # a different process
        self.assertEqual(p.returncode, 0, p.stderr)
        with open(out, encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual([e["name"] for e in data["entries"]], ["Persist"])
        self.assertEqual(data["entries"][0]["nights_won"], 3)

    def test_export_when_empty(self):
        out = os.path.join(self.tmp.name, "e.json")
        leaderboard.export(out)
        with open(out) as f:
            self.assertEqual(json.load(f), {"entries": []})

    def test_bad_inputs(self):
        for args in (("ab", 1, 0, 1), ("okname", -1, 0, 1), ("okname", 1, 4, 1)):
            with self.assertRaises(ValueError):
                leaderboard.add(*args)

    def test_game_submit_rules(self):
        g = Game(seed=5)
        with self.assertRaises(ValueError):
            g.submit_score("Valid_name")                                       # nothing to save in the menu
        g.command("new_game")
        g.command("begin")
        g.sim.result = "lost"                                                  # lost during night 1
        g.phase, g.lb_saved = "result", False
        g.total, g.nights_won = 0, 0
        self.assertTrue(g.state()["can_save"])
        with self.assertRaises(ValueError):
            g.submit_score("x")                                                # invalid name
        e = g.submit_score("Mây_Nhỏ")
        self.assertEqual((e["score"], e["nights_won"], e["seed"]), (0, 0, 5))
        self.assertFalse(g.state()["can_save"])                                # saved once
        g.phase, g.lb_saved, g.total, g.nights_won = "dawn", False, 1234, 3    # won night 3
        g.submit_score("WinnerOne")
        self.assertEqual([x["score"] for x in leaderboard.load()], [1234, 0])


if __name__ == "__main__":
    unittest.main()
