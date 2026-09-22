#!/usr/bin/env python3
"""crypto_delta.py — one owner for the recurring crypto portfolio delta check.

One command computes every delta against the stored baselines, regenerates
the ONE current report (atomic tmp+rename), appends today's observation to
the existing thesis ledger (research_lib theses.jsonl — reuse, not a new
store), and emits exactly one deduplicated task completion to the poke
outbox.

Replaces the hand-rolled per-turn flow that shipped duplicate completions
(TASK-00033 x2) and copy-pasted baseline tables across dated reports
(20260920/20260922 audit findings).

Usage:
    python3 crypto_delta.py --task TASK-00033 \
        --price 'BTC=85968|Forbes 08:23 ET|2026-09-22' \
        --price 'ETH=2762|MetaMask|2026-09-22' \
        --price 'SOL=117.00|Paybis|2026-09-22' \
        --verdict "Prior BTC targets cleared (+1); ETH avoid call missed (-1)."

Ledger note: research_lib.save_theses is the SINGLE atomic write path
for theses.jsonl (made tmp+rename 2026-09-22, bl-204) and
research_lib.ledger_tx is the shared cross-process guard around every
load..save — this file loads, applies, and delegates under that lock,
with no mirrored format or concurrency knowledge here.
Scope decisions: no holdings store exists (none found anywhere in the
workspace — research-only mode, intentionally not scaffolded) and the
thesis ledger is the pre-existing ~/.freebuff/market-research/theses.jsonl
via research_lib, not a new file.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import date
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path.home() / ".freebuff"))
sys.path.insert(0, str(Path.home() / ".freebuff/market-research"))

import freebuff_lib
import freebuff_registry as fbr
import research_lib

DIR = Path(__file__).resolve().parent
BASELINES_PATH = DIR / "crypto_baselines.json"
REPORT_PATH = DIR / "CRYPTO_PORTFOLIO_DELTA.md"
OUTBOX_PATH = Path.home() / ".freebuff/poke-freebuff/outbox-mark.jsonl"
SCHEMA = "crypto-delta.v1"


@dataclass(frozen=True)
class Quote:
    """One caller-observed price crossing the CLI boundary."""
    symbol: str
    price: float
    source: str
    observed_on: str


@dataclass(frozen=True)
class Baseline:
    """One stored historical price row deltas are computed against.

    prices is treated as read-only after parsing (scratch dict, frozen
    attribute — matches the skill's 'dicts fine for scratch').
    """
    date: str
    prices: dict
    source: str


def parse_quote(spec: str) -> Quote:
    """Parse one --price spec 'SYM=PRICE|SOURCE|DATE' at the CLI boundary.

    The only place untrusted spec text becomes a typed Quote. Raises
    ValueError carrying the offending spec so main() can report it.
    """
    if "=" not in spec:
        raise ValueError(f"price spec must be SYM=PRICE|SOURCE|DATE, got: {spec!r}")
    sym, _, rest = spec.partition("=")
    parts = rest.split("|")
    if len(parts) != 3 or not sym.strip() or not all(p.strip() for p in parts):
        raise ValueError(f"price spec must be SYM=PRICE|SOURCE|DATE, got: {spec!r}")
    price_s, source, observed_on = (p.strip() for p in parts)
    try:
        price = float(price_s)
    except ValueError:
        raise ValueError(f"price is not a number in spec: {spec!r}") from None
    if not math.isfinite(price) or price <= 0:
        raise ValueError(f"price must be a finite positive number in spec: {spec!r}")
    try:
        date.fromisoformat(observed_on)
    except ValueError:
        raise ValueError(
            f"observation date must be a real YYYY-MM-DD date in spec: {spec!r}"
        ) from None
    return Quote(sym.strip().upper(), price, source, observed_on)


def load_baselines(path: Path | None = None) -> list:
    """Parse the owned baseline store once into typed rows, oldest first.

    path=None resolves the module constant at CALL time so callers and
    tests can redirect the store (a def-time default silently ignored
    overrides — caught exercising this seam). Boundary parse for file
    state: malformed shapes raise ValueError, a missing/unreadable store
    raises OSError; main maps both to (False, msg) instead of a traceback.
    """
    if path is None:
        path = BASELINES_PATH
    raw = json.loads(path.read_text())
    rows = []
    for i, b in enumerate(raw.get("baselines", [])):
        date, prices = b.get("date"), b.get("prices")
        if not date or not isinstance(prices, dict) or not prices:
            raise ValueError(f"{path}: baseline #{i} missing date or prices")
        rows.append(Baseline(date,
                             {str(k).upper(): float(v) for k, v in prices.items()},
                             b.get("source", "")))
    if not rows:
        raise ValueError(f"{path}: no baselines stored")
    return sorted(rows, key=lambda b: b.date)


def compute_deltas(quotes: list, baselines: list) -> dict:
    """Pure: {symbol: {baseline_date: pct_change}} for baselines holding the symbol."""
    out = {}
    for q in quotes:
        per = {}
        for b in baselines:
            base = b.prices.get(q.symbol)
            if base:
                per[b.date] = (q.price - base) / base * 100.0
        out[q.symbol] = per
    return out


def apply_checks(rows: list, quotes: list, verdict: str, generated_at: str):
    """Pure ledger mutation: append one dated check per matching ACTIVE thesis.

    Returns (lines, appended_any). Honest line for symbols with no active
    row — never fabricates a ledger entry. Idempotent per (symbol, UTC
    day, price): an identical same-day check is suppressed, matching
    emit_completion's per-day dedupe (a re-run with a genuinely new price
    still appends). main rejects duplicate symbols at the parse boundary,
    so quotes are assumed unique here — trust the boundary, no
    double-guard. Mutates rows in place; caller owns persistence.
    """
    day = generated_at[:10]
    lines, appended = [], False
    for q in quotes:
        match = next((r for r in rows
                      if r.get("symbol") == q.symbol and r.get("status") == "active"), None)
        if match is None:
            lines.append(f"{q.symbol}: no active ledger row — nothing appended")
            continue
        if any(c.get("date", "")[:10] == day and c.get("price") == q.price
               for c in match.get("checks", [])):
            lines.append(f"{q.symbol}: {day} @ {q.price} already recorded — duplicate suppressed")
            continue
        note = (f"delta-check {generated_at}: price {q.price} ({q.source}); "
                f"verdict: {verdict or 'none'}")
        match.setdefault("checks", []).append(
            {"date": generated_at, "price": q.price, "note": note})
        lines.append(f"{q.symbol}: appended check to {match.get('id', '?')}")
        appended = True
    return lines, appended


def render_report(generated_at: str, task: str | None, quotes: list,
                  baseline_dates: list, deltas: dict, verdict: str,
                  ledger_lines: list) -> str:
    """Pure markdown for the one current report.

    Only computed facts appear here — every % traces to a stored baseline;
    no unsourced comparatives (the audit's 'first time since...' failure).
    Judgment prose arrives only via the caller-labeled verdict section.
    """
    latest = baseline_dates[-1]
    hdr = "| Asset | Price | Observed | Source | " + \
          " | ".join(f"vs {d}" for d in baseline_dates) + " |"
    sep = "|-------|------:|----------|--------|" + \
          "------:|" * len(baseline_dates)
    lines_out = []
    for q in quotes:
        cells = []
        for d in baseline_dates:
            v = deltas[q.symbol].get(d)
            cells.append(f"{v:+.1f}%" if v is not None else "-")
        lines_out.append(
            f"| {q.symbol} | ${q.price:,.2f} | {q.observed_on} | {q.source} | "
            + " | ".join(cells) + " |")

    have = {s: deltas[s][latest] for s in deltas if latest in deltas[s]}
    if have:
        lead = max(have, key=have.get)
        lagg = min(have, key=have.get)
        facts = (f"**Facts:** vs {latest} — leader {lead} {have[lead]:+.1f}%, "
                 f"laggard {lagg} {have[lagg]:+.1f}%.")
    else:
        facts = f"**Facts:** no stored baseline for {latest}."
    missing = [s for s in deltas if latest not in deltas[s]]
    if missing:
        facts += f" No stored baseline for: {', '.join(sorted(missing))}."

    ledger_bullets = [f"- {ln}" for ln in ledger_lines] or ["- nothing appended"]

    return "\n".join([
        "# Crypto Portfolio Delta Check (current)",
        f"**Generated:** {generated_at} · **Task:** {task or '—'} · "
        f"**Owner:** crypto_delta.py · **Schema:** {SCHEMA}",
        "",
        "Prices are caller-observed; every % below is computed against the "
        "stored baselines in `crypto_baselines.json`.",
        "",
        "## Prices and deltas",
        "",
        hdr, sep, *lines_out,
        "",
        facts,
        "",
        "## Ledger (research_lib theses.jsonl)",
        "",
        *ledger_bullets,
        "",
        "## Verdict (caller-supplied judgment, not computed)",
        "",
        verdict or "—",
        "",
        "---",
        "*Informational research only — not financial advice.*",
        "",
    ])


def append_ledger_checks(quotes: list, verdict: str, generated_at: str) -> list:
    """IO wrapper: ledger_tx -> load -> apply_checks -> save, all via
    research_lib (single writer, single lock).

    The cross-process guard lives at the source
    (research_lib.ledger_tx), so the old CAS stat/retry loop is gone: a
    concurrent worker upsert waits for the lock instead of racing this
    load->save — both directions of the proven reverse-clobber are
    excluded, and the stat->replace TOCTOU closes with it. Writers that
    bypass ledger_tx are out of scope: every writer of theses.jsonl goes
    through research_lib. Returns the human-readable report lines.
    """
    with research_lib.ledger_tx():
        rows = research_lib.load_theses()
        lines, appended = apply_checks(rows, quotes, verdict, generated_at)
        if appended:
            research_lib.save_theses(rows)
    return lines


def emit_completion(task_id: str | None, summary: str, artifact: Path,
                    generated_at: str, outbox: Path | None = None):
    """Append exactly ONE completion per (task, artifact, UTC date).

    Duplicate key → (False, reason) and zero bytes written — the fix for
    the TASK-00033 double-send. A genuinely new run on a later date is a
    legitimate new completion. outbox=None resolves OUTBOX_PATH at CALL
    time so a rebound module constant actually redirects (a def-time
    default silently ignored it — caught exercising this seam).
    Envelope carries schema_version, correlation_id, ts per bl-40.
    Contract: duplicate → ok=True (the postcondition — exactly one
    completion for (task, artifact, day) — already holds; the detail says
    'suppressed'), so callers never sniff prose to classify the outcome.
    Returns (ok, detail).
    """
    if not task_id:
        return (False, "no task id — completion not emitted")
    if outbox is None:
        outbox = OUTBOX_PATH
    day = generated_at[:10]
    for row in freebuff_lib.read_jsonl(outbox, required=("type", "task_id")):
        if (row.get("type") == "completion"
                and row.get("task_id") == task_id
                and row.get("artifact") == artifact.name
                and str(row.get("ts", ""))[:10] == day):
            return (True, f"duplicate suppressed for {task_id} {day} "
                           f"(existing ts={row.get('ts')})")
    try:
        freebuff_lib.append_jsonl(outbox, {
            "schema_version": "1.0.0",
            "correlation_id": f"delta-{day.replace('-', '')}-{task_id}",
            "type": "completion",
            "task_id": task_id,
            "from": "mark",
            "ts": generated_at,
            "artifact": artifact.name,
            "summary": summary,
        })
    except OSError as e:
        return (False, f"outbox write failed: {e}")
    return (True, f"completion emitted for {task_id}")


def main(argv=None):
    """CLI entry: parse quotes -> deltas -> ledger -> report -> completion.

    Returns (ok, detail) per the daemons' 1-2 level call pattern.
    Boundary catches are ValueError/OSError (typed — bad input or an
    unreadable store), never bare Exception.
    """
    ap = argparse.ArgumentParser(
        prog="crypto_delta",
        description="Recurring crypto portfolio delta check (single current report).")
    ap.add_argument("--price", action="append", required=True,
                    metavar="SYM=PRICE|SOURCE|DATE",
                    help="one observed quote; repeat per symbol")
    ap.add_argument("--task", default=None,
                    help="task id; omit to skip the outbox completion")
    ap.add_argument("--verdict", default="",
                    help="caller judgment, labeled as such in the report")
    ns = ap.parse_args(argv)

    try:
        quotes = [parse_quote(s) for s in ns.price]
        syms = [q.symbol for q in quotes]
        if len(set(syms)) != len(syms):
            dup = next(s for s in syms if syms.count(s) > 1)
            raise ValueError(
                f"duplicate symbol in --price: {dup} "
                "(deltas would be computed from the wrong row)")
        baselines = load_baselines()
    except (ValueError, OSError) as e:
        print(f"delta: {e}")
        return (False, str(e))

    generated_at = fbr.now_iso()
    deltas = compute_deltas(quotes, baselines)
    ledger_lines = append_ledger_checks(quotes, ns.verdict, generated_at)
    report = render_report(generated_at, ns.task, quotes,
                           [b.date for b in baselines], deltas,
                           ns.verdict, ledger_lines)
    fbr.atomic_write_text(str(REPORT_PATH), report)
    print(f"delta: report {REPORT_PATH.name} "
          f"({len(report.splitlines())} lines) for {len(quotes)} quotes")

    facts = " ".join(f"{s} {deltas[s][baselines[-1].date]:+.1f}%"
                     for s in deltas if baselines[-1].date in deltas[s])
    summary = (f"Crypto delta {generated_at[:10]} vs {baselines[-1].date}: {facts}. "
               f"Prices: " + ", ".join(f"{q.symbol} ${q.price:,.2f}" for q in quotes)
               + (f" Verdict: {ns.verdict}" if ns.verdict else ""))
    if ns.task:
        ok, why = emit_completion(ns.task, summary, REPORT_PATH, generated_at)
        print(f"delta: {why}")
        if not ok:
            return (False, why)
    return (True, f"ok — {len(quotes)} quotes, report {REPORT_PATH.name}")


if __name__ == "__main__":
    ok, detail = main()
    sys.exit(0 if ok else 1)
