"""Headless runner implementing Test Contract v1.0.

  python3 -m game.headless --seed 1 --night 1|2|3 [--scenario f.json] [--inputs f.json]
                           --ticks N --out out.jsonl [--snapshot-every 10]
"""
import argparse
import json
import sys

from .sim import ScenarioError, Sim, _num


def _load_json(path, what):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError) as e:
        raise ScenarioError(f"cannot read {what} file {path!r}: {e}")


def parse_inputs(doc):
    """Return {tick: frame} after validating the inputs file."""
    if not isinstance(doc, dict) or not isinstance(doc.get("frames"), list):
        raise ScenarioError("inputs file needs a 'frames' array")
    frames, last = {}, -1
    for fr in doc["frames"]:
        if not isinstance(fr, dict) or isinstance(fr.get("tick"), bool) \
                or not isinstance(fr.get("tick"), int) or fr["tick"] < 0:
            raise ScenarioError("each frame needs an integer 'tick' >= 0")
        if fr["tick"] <= last:
            raise ScenarioError("frame ticks must strictly increase")
        last = fr["tick"]
        if "move" in fr:
            m = fr["move"]
            if not isinstance(m, list) or len(m) != 2:
                raise ScenarioError("move must be [x, z]")
            _num(m[0], "move.x"); _num(m[1], "move.z")
        if "cam_yaw_deg" in fr:
            _num(fr["cam_yaw_deg"], "cam_yaw_deg")
        for b in ("jump", "interact", "pulse", "dash"):
            if b in fr and not isinstance(fr[b], bool):
                raise ScenarioError(f"{b} must be boolean")
        frames[fr["tick"]] = fr
    return frames


def run(seed, scenario, frames, ticks, out, every, contract=None, night=1):
    sim = Sim(seed, scenario, contract, night=night)
    cur = {"move": (0.0, 0.0), "cam_yaw_deg": 0.0, "jump": False, "interact": False, "pulse": False,
           "dash": False, "pause": False}

    def w(obj):
        out.write(json.dumps(obj, separators=(",", ":")) + "\n")

    w(sim.snapshot())
    w({"type": "event", "tick": 0, "name": "night_start", "data": {"night": night}})
    for k in range(ticks):
        if sim.over:
            break
        fr = frames.get(k)
        if fr:
            if "move" in fr:
                x, z = fr["move"]
                cur["move"] = (max(-1.0, min(1.0, float(x))), max(-1.0, min(1.0, float(z))))
            for key in ("cam_yaw_deg", "jump", "interact", "pulse", "dash", "pause"):
                if key in fr:
                    cur[key] = fr[key]
        sim.step(cur)
        for ev in sim.events:
            w(ev)
        if sim.tick % every == 0:
            w(sim.snapshot())
    w(sim.end_record())
    return sim


def main(argv=None):
    ap = argparse.ArgumentParser(prog="game.headless")
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--night", type=int, required=True)
    ap.add_argument("--scenario")
    ap.add_argument("--inputs")
    ap.add_argument("--ticks", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--snapshot-every", type=int, default=10)
    a = ap.parse_args(argv)  # argparse exits with code 2 on bad args
    try:
        if a.night not in (1, 2, 3):
            raise ScenarioError("--night must be 1, 2 or 3")
        if a.ticks < 0 or a.snapshot_every < 1:
            raise ScenarioError("--ticks must be >= 0 and --snapshot-every >= 1")
        scenario = _load_json(a.scenario, "scenario") if a.scenario else None
        frames = parse_inputs(_load_json(a.inputs, "inputs")) if a.inputs else {}
        with open(a.out, "w", encoding="utf-8", newline="\n") as out:
            run(a.seed, scenario, frames, a.ticks, out, a.snapshot_every, night=a.night)
    except ScenarioError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
