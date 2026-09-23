#!/usr/bin/env python3
"""MARK win-rate calculator — the reproducible source for every win-rate claim.

Why this exists (L7 fix, 2026-09-23): MARK dispatch prompts carried win-rate
claims ("market-research run win 92%, 6x", "sec-review 61%, 7x",
"volatility-model 79%, 15x") that match no live store. This script recomputes
the real numbers from the two stores that actually record outcomes, so any
future claim is checkable by Yeshua with one command.

Stores (both read-only):
  ~/.freebuff/cos/state/reinforcement.jsonl  raw per-outcome rows (agent, theme,
                                             signal +1/-1, verdict, note, ts)
  ~/.freebuff/cos/state/lessons-mark.json    system-weighted summary per theme

Definition of a win used here: raw ratio of signal=+1 rows to all scored rows
for a theme. It is deliberately blunt — it counts what the grader scored, not
what the agent hoped. The system's own `win` field is a weighted, smoothed
value and is printed alongside so the two can never be confused again.

Usage: python3 mark_winrate.py [--agent mark] [--window 20]
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys

HOME = os.path.expanduser("~")
REINFORCEMENT = os.path.join(HOME, ".freebuff", "cos", "state", "reinforcement.jsonl")
LESSONS = {
    "mark": os.path.join(HOME, ".freebuff", "cos", "state", "lessons-mark.json"),
    "onus": os.path.join(HOME, ".freebuff", "cos", "state", "lessons-onus.json"),
    "cosa": os.path.join(HOME, ".freebuff", "cos", "state", "lessons-cosa.json"),
}


def load_rows(path: str) -> list[dict]:
    """Parse reinforcement.jsonl into rows. Raises ValueError on a malformed line."""
    rows = []
    with open(path, encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{lineno}: {exc}") from exc
    return rows


def themed_counts(rows: list[dict]) -> dict[str, dict[str, int]]:
    """Group scored rows by theme → {pos, neg, n}."""
    by: dict[str, dict[str, int]] = collections.defaultdict(
        lambda: {"pos": 0, "neg": 0, "n": 0}
    )
    for row in rows:
        theme = row.get("theme") or "unthemed"
        bucket = by[theme]
        bucket["n"] += 1
        if row.get("signal") == 1:
            bucket["pos"] += 1
        else:
            bucket["neg"] += 1
    return dict(by)


def raw_win(counts: dict[str, int]) -> float:
    """Positive share of scored rows; 0.0 when nothing was scored."""
    return counts["pos"] / counts["n"] if counts["n"] else 0.0


def load_lessons(path: str) -> dict:
    """Load the system summary, or return {} when it does not exist yet."""
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def report(agent: str, window: int) -> int:
    """Print the reconciliation table. Returns a shell exit code."""
    if not os.path.exists(REINFORCEMENT):
        print(f"reinforcement store missing: {REINFORCEMENT}", file=sys.stderr)
        return 2
    rows = [r for r in load_rows(REINFORCEMENT) if r.get("agent") == agent]
    if not rows:
        print(f"no scored rows for agent={agent}", file=sys.stderr)
        return 2

    lessons = load_lessons(LESSONS.get(agent, ""))
    # lesson rows key the agent as a list under "agents"; tolerate a scalar "agent" too.
    weighted = {
        item["theme"]: item
        for item in lessons.get("lessons", [])
        if agent in item.get("agents", []) or item.get("agent") == agent
    }

    print(f"agent={agent}  scored_rows={len(rows)}  window={window}")
    print(f"source: {REINFORCEMENT}")
    if lessons:
        print(f"source: {LESSONS[agent]}  updated={lessons.get('updated')}  "
              f"n_outcomes={lessons.get('n_outcomes')}")
    print()
    print(f"{'theme':<46} {'n':>4} {'pos':>4} {'neg':>4} {'raw_win':>8} {'sys_win':>8}")
    print("-" * 82)
    counts = themed_counts(rows)
    for theme, c in sorted(counts.items(), key=lambda kv: (-kv[1]["n"], kv[0])):
        sys_win = weighted.get(theme, {}).get("win")
        sys_txt = f"{sys_win:.3f}" if isinstance(sys_win, float) else "n/a"
        print(f"{theme[:45]:<46} {c['n']:>4} {c['pos']:>4} {c['neg']:>4} "
              f"{raw_win(c):>8.3f} {sys_txt:>8}")

    recent = rows[-window:]
    recent_pos = sum(1 for r in recent if r.get("signal") == 1)
    print()
    print(f"ALL-TIME   raw_win={raw_win({'pos': sum(1 for r in rows if r.get('signal') == 1), 'neg': 0, 'n': len(rows)}):.3f} "
          f"({sum(1 for r in rows if r.get('signal') == 1)}/{len(rows)})")
    print(f"LAST {len(recent):<4}  raw_win={recent_pos / len(recent):.3f} ({recent_pos}/{len(recent)})")
    print()
    print("REMINDER: a claim without (store path, n, generated_at) is not a claim.")
    print("KILL RULE K1: theme raw_win < 0.45 over the trailing window for 3 consecutive")
    print("scoring revisions => FREEZE that lane and report to CH1P.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--agent", default="mark")
    parser.add_argument("--window", type=int, default=20)
    args = parser.parse_args()
    return report(args.agent, args.window)


if __name__ == "__main__":
    raise SystemExit(main())
