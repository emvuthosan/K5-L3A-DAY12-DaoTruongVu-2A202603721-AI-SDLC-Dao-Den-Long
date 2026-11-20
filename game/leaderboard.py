"""Local leaderboard (Ticket-04): top 10, stored on disk, survives restarts.

Entry: {name, score, nights_won, achieved_at (ISO 8601 with timezone), seed}.
Order: score descending; equal score -> the one achieved earlier ranks higher.
Storage: $DDL_DATA_DIR/leaderboard.json (default: <repo>/data/leaderboard.json).
"""
import json
import os
import re
import tempfile
import unicodedata
from datetime import datetime, timezone

from .sim import ROOT

TOP = 10
ASCII_OK = re.compile(r"[A-Za-z0-9_]")


def path():
    return os.path.join(os.environ.get("DDL_DATA_DIR") or os.path.join(ROOT, "data"), "leaderboard.json")


def valid_name(name):
    """3-12 characters of [A-Za-z0-9_]; Latin letters with diacritics (Vietnamese) are accepted too."""
    if not isinstance(name, str):
        return None
    name = unicodedata.normalize("NFC", name)
    if not 3 <= len(name) <= 12:
        return None
    for c in name:
        if ASCII_OK.fullmatch(c):
            continue
        if unicodedata.category(c).startswith("L") and "LATIN" in unicodedata.name(c, ""):
            continue
        return None
    return name


def _key(i_e):
    i, e = i_e
    try:
        t = datetime.fromisoformat(e["achieved_at"]).timestamp()
    except (ValueError, KeyError, TypeError):
        t = float("inf")
    return (-e["score"], t, i)


def _order(entries):
    return [e for _, e in sorted(enumerate(entries), key=_key)][:TOP]


def load():
    try:
        with open(path(), encoding="utf-8") as f:
            data = json.load(f)
        entries = [e for e in data.get("entries", []) if isinstance(e, dict) and "score" in e]
    except (OSError, ValueError, AttributeError):
        return []
    return _order(entries)


def _save(entries):
    p = path()
    os.makedirs(os.path.dirname(p), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(p), suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump({"entries": entries}, f, ensure_ascii=False, indent=2)
    os.replace(tmp, p)


def add(name, score, nights_won, seed, now=None):
    n = valid_name(name)
    if n is None:
        raise ValueError("name must be 3-12 characters: letters, digits or _")
    if not isinstance(score, int) or score < 0 or nights_won not in (0, 1, 2, 3):
        raise ValueError("bad score or nights_won")
    entry = {"name": n, "score": score, "nights_won": nights_won,
             "achieved_at": (now or datetime.now(timezone.utc).astimezone()).isoformat(timespec="seconds"),
             "seed": seed}
    entries = _order(load() + [entry])
    _save(entries)
    return entry


def export(out_path):
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"entries": load()}, f, ensure_ascii=False, indent=2)
