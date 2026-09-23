#!/usr/bin/env python3
"""bet_threshold_calibration.py — one owner for calibrating MARK bet thresholds.

The live bet CRYPTO-MOM-20260922 uses a +/-2.0% band over a 2-trading-day
horizon (mark-l7-v1). This module answers the only question that makes that bet
falsifiable: is a 2% 2-day move OUTSIDE the noise band of the instrument, and
how often will the band fire at all? A threshold wider than the instrument's
horizon dispersion makes the bet permanently NO_EDGE; one far narrower makes it
noise. Both are failures the thesis must know about before it is scored.

Two price sources are read, both already on disk (no fetched quote, so every
number is reproducible offline and carries its own file provenance):

  PRIMARY   the sourced MARKET_RESEARCH*.json snapshot family (dated quotes,
            contiguous 2026-08-28..2026-09-05 daily coverage)
  SECONDARY the thesis ledger's per-symbol check history, which this module
            gates on input plausibility — and which FAILS that gate. That
            failure is a reported finding, not a crash, so the corrupt series
            can never silently become the basis of a scored outcome.

Usage:
    python3 bet_threshold_calibration.py             # regenerate the JSON
    python3 bet_threshold_calibration.py --selftest  # validations only, no write

Deliberately NOT a new versioned sim family: the vol-sim family already holds
91 files and MARK kill rule K2 (artifact-churn freeze) is TRIPPED, so this
ships as one owned module plus its generated JSON, matching the accepted
mark_winrate.py / MARK_L7_KILL_RULES.json shape.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import math
import random
import re
import statistics
import sys
from datetime import date, datetime, timezone
from pathlib import Path

DIR = Path(__file__).resolve().parent
LEDGER = Path.home() / ".freebuff/market-research/theses.jsonl"
OUT = DIR / "BET_THRESHOLD_CALIBRATION.json"
SCHEMA = "bet-threshold-calibration.v1"
SYMBOLS = ("BTC", "ETH", "SOL")
THRESHOLD_PCT = 2.0      # mark-l7-v1 band, both tails
HORIZON_DAYS = 2         # mark-l7-v1 horizon
MC_DRAWS = 200_000
SEED = 20260923
IMPLAUSIBLE_MOVE = 0.35  # |single-step log return| above this is a bad write
CROSS_SOURCE_TOL = 0.05  # same-date disagreement above this is a K4 defect


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_ledger_series(path: Path = LEDGER) -> dict:
    """Last ledger check per UTC day, per symbol (irregular; gated later)."""
    series = {s: {} for s in SYMBOLS}
    raw = {s: 0 for s in SYMBOLS}
    if not path.exists():
        return {s: {"days": [], "prices": [], "raw_checks": 0} for s in SYMBOLS}
    with path.open() as fh:
        for line in fh:
            if not line.strip():
                continue
            row = json.loads(line)
            sym = row.get("symbol")
            if sym not in series:
                continue
            for chk in row.get("checks") or []:
                ts, price = chk.get("date"), chk.get("price")
                if not ts or not isinstance(price, (int, float)):
                    continue
                raw[sym] += 1
                series[sym][str(ts)[:10]] = float(price)
    out = {}
    for sym, by_day in series.items():
        days = sorted(by_day)
        out[sym] = {"days": days, "prices": [by_day[d] for d in days],
                    "raw_checks": raw[sym]}
    return out


def load_snapshot_series(directory: Path = DIR) -> dict:
    """Last sourced quote per UTC day, per symbol, from the snapshot family."""
    series = {s: {} for s in SYMBOLS}
    files = {s: {} for s in SYMBOLS}
    for fname in sorted(glob.glob(str(directory / "MARKET_RESEARCH*.json"))):
        try:
            doc = json.loads(Path(fname).read_text())
        except (OSError, ValueError):
            continue
        day = str(doc.get("generated_at") or "")[:10]
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day):
            continue
        found = {}

        def walk(node):
            if isinstance(node, dict):
                for k, v in node.items():
                    if isinstance(v, dict) and k.upper() in SYMBOLS:
                        for pk in ("price_usd", "price", "last_close_usd"):
                            if isinstance(v.get(pk), (int, float)):
                                found.setdefault(k.upper(), float(v[pk]))
                                break
                    walk(v)
            elif isinstance(node, list):
                for v in node:
                    walk(v)

        walk(doc)
        for sym, px in found.items():
            series[sym][day] = px
            files[sym][day] = Path(fname).name
    out = {}
    for sym, by_day in series.items():
        days = sorted(by_day)
        out[sym] = {"days": days, "prices": [by_day[d] for d in days],
                    "sources": [files[sym][d] for d in days],
                    "raw_checks": len(days)}
    return out


def log_returns(prices: list) -> list:
    return [math.log(prices[i] / prices[i - 1]) for i in range(1, len(prices))]


def day_gaps(days: list) -> list:
    return [(date.fromisoformat(days[i]) - date.fromisoformat(days[i - 1])).days
            for i in range(1, len(days))]


def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def robust_sigma(rets: list) -> float:
    """MAD-based scale (1.4826*MAD): outlier-resistant companion to stdev."""
    if len(rets) < 2:
        return 0.0
    med = statistics.median(rets)
    return 1.4826 * statistics.median([abs(r - med) for r in rets])


def analytic_band(thr: float, sigma_h: float) -> dict:
    if sigma_h <= 0:
        return {"k": None, "p_outside": 0.0, "p_inside": 1.0,
                "expected_abs_move_pct": 0.0}
    k = thr / sigma_h
    p_out = 2.0 * (1.0 - norm_cdf(k))
    return {"k": k, "p_outside": p_out, "p_inside": 1.0 - p_out,
            "expected_abs_move_pct": 100 * sigma_h * math.sqrt(2.0 / math.pi)}


def mc_band(thr: float, sigma_h: float, draws: int, seed: int) -> float:
    rng, hits = random.Random(seed), 0
    for _ in range(draws):
        if abs(rng.gauss(0.0, sigma_h)) > thr:
            hits += 1
    return hits / draws


def bootstrap_band(daily: list, horizon: int, thr: float, draws: int, seed: int) -> float:
    rng, n, hits = random.Random(seed), len(daily), 0
    for _ in range(draws):
        if abs(sum(daily[rng.randrange(n)] for _ in range(horizon))) > thr:
            hits += 1
    return hits / draws


def overlapping_band(daily: list, horizon: int, thr: float) -> tuple:
    """Empirical frequency over every consecutive window, with its sample size.

    Returned with n because with only a handful of returns this leg is a
    7-sample frequency whose standard error is ~0.19 - it can disagree with a
    model leg by chance, so callers must scale tolerance by that error rather
    than demand agreement on a binary call.
    """
    w = [sum(daily[i:i + horizon]) for i in range(len(daily) - horizon + 1)]
    if not w:
        return 0.0, 0
    return sum(1 for r in w if abs(r) > thr) / len(w), len(w)


def implausible(rets: list, days: list) -> list:
    """Single-step moves too large for a <=1-day gap are bad writes."""
    out = []
    for i, r in enumerate(rets):
        gap = (date.fromisoformat(days[i + 1]) - date.fromisoformat(days[i])).days
        limit = IMPLAUSIBLE_MOVE * max(gap, 1)
        if abs(r) > limit:
            out.append({"date": days[i + 1], "gap_days": gap,
                        "log_return": round(r, 4),
                        "move_pct": round(100 * (math.exp(r) - 1), 2),
                        "limit_pct": round(100 * (math.exp(limit) - 1), 2)})
    return out


def calibrate(source: str, series: dict, thr: float, scope: str) -> tuple:
    per_symbol, checks, bad = {}, [], []
    for sym in SYMBOLS:
        days, prices = series[sym]["days"], series[sym]["prices"]
        rets = log_returns(prices)
        if len(rets) < 5:
            checks.append({"id": f"V5-{sym}", "scope": scope,
                           "check": ">=5 returns for a sigma",
                           "observed": len(rets), "pass": False})
            continue
        bad += [{**b, "symbol": sym, "source": source}
                for b in implausible(rets, days)]
        sigma_d = statistics.stdev(rets)
        sigma_d_rob = robust_sigma(rets)
        sigma_h = sigma_d * math.sqrt(HORIZON_DAYS)
        an = analytic_band(thr, sigma_h)
        p_mc = mc_band(thr, sigma_h, MC_DRAWS, SEED)
        p_bs = bootstrap_band(rets, HORIZON_DAYS, thr, MC_DRAWS, SEED + 1)
        p_ov, n_ov = overlapping_band(rets, HORIZON_DAYS, thr)
        se_ov = (math.sqrt(an["p_outside"] * (1 - an["p_outside"]) / n_ov)
                 if n_ov else 1.0)
        an_rob = analytic_band(thr, sigma_d_rob * math.sqrt(HORIZON_DAYS))
        gaps = day_gaps(days)
        per_symbol[sym] = {
            "points": len(prices), "span": f"{days[0]}..{days[-1]}",
            "returns": len(rets),
            "max_gap_days": max(gaps) if gaps else None,
            "sigma_daily_pct": 100 * sigma_d,
            "sigma_daily_robust_pct": 100 * sigma_d_rob,
            "sigma_horizon_pct": 100 * sigma_h,
            "band_k_sigmas": an["k"],
            "band_k_sigmas_robust": an_rob["k"],
            "p_outside_analytic": an["p_outside"],
            "p_outside_mc": p_mc,
            "p_outside_bootstrap_iid": p_bs,
            "p_outside_overlapping": p_ov,
            "overlapping_windows": n_ov,
            "overlapping_se": se_ov,
            "expected_abs_move_pct": an["expected_abs_move_pct"],
            "expected_no_edge_pct": 100 * an["p_inside"],
            "sources": series[sym].get("sources", []),
        }
        checks += [
            {"id": f"V1-{sym}", "scope": scope,
             "check": "seeded MC matches closed form",
             "observed": round(abs(p_mc - an["p_outside"]), 6), "tolerance": 0.005,
             "pass": abs(p_mc - an["p_outside"]) < 0.005},
            {"id": f"V2-{sym}", "scope": scope,
             "check": "model legs (closed form, i.i.d. bootstrap) agree on the call",
             "observed": [an["p_outside"] > 0.5, p_bs > 0.5],
             "pass": (an["p_outside"] > 0.5) == (p_bs > 0.5)},
            {"id": f"V8-{sym}", "scope": scope,
             "check": "small-sample frequency within 2 SE + 0.05 of the model",
             "observed": {"gap": round(abs(an["p_outside"] - p_ov), 6),
                          "tolerance": round(2 * se_ov + 0.05, 6), "n_windows": n_ov},
             "pass": abs(an["p_outside"] - p_ov) <= 2 * se_ov + 0.05},
            {"id": f"V3-{sym}", "scope": scope,
             "check": "outside/inside partition sums to 1",
             "observed": round(an["p_outside"] + an["p_inside"], 12),
             "pass": abs(an["p_outside"] + an["p_inside"] - 1.0) < 1e-12},
            {"id": f"V5-{sym}", "scope": scope,
             "check": "series is contiguous (max gap <= 1 day)",
             "observed": max(gaps) if gaps else None,
             "pass": bool(gaps) and max(gaps) <= 1},
            {"id": f"V7-{sym}", "scope": scope,
             "check": "no implausible single-step move",
             "observed": len([b for b in bad if b["symbol"] == sym]),
             "pass": not any(b["symbol"] == sym for b in bad)},
        ]
    return per_symbol, checks, bad


def cross_source(primary: dict, secondary: dict) -> dict:
    """Same-date disagreement between the two stores (K4 defect detector).

    Returns the shared dates too: with only a couple of overlapping dates this
    is pointed evidence, not exhaustive coverage, and the caller must say so.
    """
    diffs, shared = [], 0
    for sym in SYMBOLS:
        p = dict(zip(primary[sym]["days"], primary[sym]["prices"]))
        s = dict(zip(secondary[sym]["days"], secondary[sym]["prices"]))
        for d in sorted(set(p) & set(s)):
            shared += 1
            if p[d] and abs(s[d] / p[d] - 1) > CROSS_SOURCE_TOL:
                diffs.append({"symbol": sym, "date": d,
                              "snapshot_price": p[d], "ledger_price": s[d],
                              "diff_pct": round(100 * (s[d] / p[d] - 1), 2)})
    return {"shared_date_count": shared, "disagreements": diffs}


def global_checks() -> list:
    checks = []
    a = mc_band(0.02, 0.03, 50_000, 7)
    b = mc_band(0.02, 0.03, 50_000, 7)
    c = mc_band(0.02, 0.03, 50_000, 8)
    checks.append({"id": "V4", "scope": "global",
                   "check": "same seed reproduces exactly",
                   "observed": [a == b, round(abs(a - c), 6)],
                   "pass": a == b and abs(a - c) < 0.005})
    z = analytic_band(0.02, 0.0)
    checks.append({"id": "NC1", "scope": "global",
                   "check": "zero-vol input -> p_outside 0, no crash",
                   "observed": {"p_outside": z["p_outside"], "k": z["k"]},
                   "pass": z["p_outside"] == 0.0 and z["k"] is None})
    rng, true_s = random.Random(SEED), 0.025
    synth = [rng.gauss(0.0, true_s) for _ in range(200_000)]
    checks.append({"id": "NC2", "scope": "global",
                   "check": "sigma recovered from known-sigma draws",
                   "observed": round(100 * statistics.stdev(synth), 4),
                   "expected_pct": 100 * true_s,
                   "pass": abs(statistics.stdev(synth) - true_s) < 0.001})
    # NC3: the plausibility gate must actually fire on a planted bad write.
    planted = implausible([math.log(2.0)], ["2026-01-01", "2026-01-02"])
    checks.append({"id": "NC3", "scope": "global",
                   "check": "plausibility gate catches a +100% day",
                   "observed": len(planted), "pass": len(planted) == 1})
    return checks


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="MARK bet threshold calibration")
    ap.add_argument("--selftest", action="store_true",
                    help="run validations only; do not write the JSON")
    ns = ap.parse_args(argv)
    thr = THRESHOLD_PCT / 100.0

    snap = load_snapshot_series()
    ledg = load_ledger_series()
    est, checks, bad = calibrate("snapshot_family", snap, thr, "primary")
    ledg_est, ledg_checks, ledg_bad = calibrate("thesis_ledger", ledg, thr, "secondary")
    checks += ledg_checks + global_checks()
    xs = cross_source(snap, ledg)

    p_out = est.get("BTC", {}).get("p_outside_analytic")
    k_btc = est.get("BTC", {}).get("band_k_sigmas")
    sigma_d = (est.get("BTC", {}).get("sigma_daily_pct") or 0) / 100.0
    if k_btc is None or p_out is None:
        verdict = "INSUFFICIENT_PRIMARY_DATA"
    elif k_btc < 0.75:
        verdict = "BAND_INSIDE_NOISE"
    elif p_out < 0.25:
        verdict = "BAND_TOO_WIDE_RARELY_DECISIVE"
    else:
        verdict = "BAND_TESTABLE"
    # A band is 50/50 decisive when it sits at 0.6745 sigma of the horizon
    # dispersion: solve 0.6745 * sigma_d * sqrt(h) = thr for the horizon, and
    # 0.6745 * sigma_d * sqrt(HORIZON_DAYS) for the band at this horizon.
    band_for_50 = (0.6745 * sigma_d * math.sqrt(HORIZON_DAYS)
                   if sigma_d else None)
    horizon_for_50 = (round((thr / (0.6745 * sigma_d)) ** 2, 1)
                      if sigma_d else None)
    # V9: the two calibration outputs must be inverse solutions of the same
    # equation - this check exists because an earlier revision inverted the
    # horizon formula and published 1.7 days where the answer is ~8.
    if sigma_d and horizon_for_50:
        implied = 0.6745 * sigma_d * math.sqrt(horizon_for_50)
        checks.append({"id": "V9", "scope": "global",
                       "check": "band/horizon calibration invert each other",
                       "observed": {"implied_threshold_pct": round(100 * implied, 4),
                                    "threshold_pct": THRESHOLD_PCT},
                       "pass": abs(implied - thr) <= 0.001})

    # Secondary-source failures are FINDINGS (the corrupt ledger is the point);
    # only a primary or global failure blocks the write, because then the
    # calibration itself rests on untrustworthy input.
    blocking = [c for c in checks if not c["pass"] and c.get("scope") != "secondary"]
    failed = [c for c in checks if not c["pass"]]
    primary_ok = not blocking

    doc = {
        "schema_version": SCHEMA, "owner": "MARK",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "purpose": ("Calibrate the mark-l7-v1 +/-2.0% / 2-day band of "
                    "CRYPTO-MOM-20260922 against realized volatility so the bet "
                    "is either testable or provably not, and stop scoring bets "
                    "against a corrupt price series."),
        "k2_rationale": ("K2 (artifact-churn freeze) is tripped, so this ships as "
                         "one owned module + its generated JSON rather than "
                         "vol-sim version 92. It produces evidence."),
        "inputs": {
            "primary": {"kind": "MARKET_RESEARCH*.json snapshot family (sourced quotes)",
                        "dir": str(DIR),
                        "files_scanned": len(glob.glob(str(DIR / "MARKET_RESEARCH*.json"))),
                        "daily_points": {s: len(snap[s]["days"]) for s in SYMBOLS},
                        "spans": {s: (f"{snap[s]['days'][0]}..{snap[s]['days'][-1]}"
                                      if snap[s]["days"] else None) for s in SYMBOLS}},
            "secondary": {"kind": "thesis ledger check history",
                          "path": str(LEDGER),
                          "sha256": _sha256(LEDGER) if LEDGER.exists() else None,
                          "daily_points": {s: len(ledg[s]["days"]) for s in SYMBOLS},
                          "spans": {s: (f"{ledg[s]['days'][0]}..{ledg[s]['days'][-1]}"
                                        if ledg[s]["days"] else None) for s in SYMBOLS}},
            "threshold_pct": THRESHOLD_PCT, "horizon_days": HORIZON_DAYS,
            "mc_draws": MC_DRAWS, "seed": SEED,
        },
        "assumptions": [
            "last sourced quote per UTC day approximates that day's close",
            "log returns; zero drift over a 2-day horizon (drift is not an edge claim)",
            "analytic leg assumes normal increments; the empirical legs use observed returns",
            "bootstrap leg resamples daily returns i.i.d. (no vol clustering)",
            "overlapping leg uses every consecutive 2-day window",
            "the band is judged on BTC, the mark-l7-v1 primary instrument",
            "sigma is a point estimate from the window shown; no confidence interval is claimed",
        ],
        "estimates_primary": est,
        "estimates_secondary_ledger": ledg_est,
        "decision": {
            "verdict": verdict,
            "band_k_sigmas_btc": k_btc,
            "p_outside_2d_btc": p_out,
            "expected_no_edge_pct_btc": (100 * (1 - p_out) if p_out is not None else None),
            "calibrated_band_pct_for_50pct_decisive": (round(100 * band_for_50, 3)
                                                       if band_for_50 else None),
            "calibrated_horizon_days_for_2pct_band": horizon_for_50,
            "binding_rule": ("mark-l7-v1 stays UNCHANGED for CRYPTO-MOM-20260922: "
                             "re-banding after entry would be a goalpost move. This "
                             "calibration is pre-registered and applies to new bets."),
            "for_future_bets": ("state the calibrated k and the expected NO_EDGE "
                                "frequency up front; a 2.0% band on a 2-day horizon "
                                "is decided by noise too rarely to test a 2-day "
                                "momentum claim - use the calibrated band or horizon "
                                "above, or lengthen the horizon"),
        },
        "data_quality_findings": {
            "ledger_implausible_prints": ledg_bad,
            "cross_source": xs,
            "consequence": ("the ledger's check history is not a usable price series: "
                            "it holds impossible single-day moves and disagrees with "
                            "the sourced snapshots on overlapping dates. It must not "
                            "be used to score an outcome (K6)."),
            "action": ("record sourced quotes through the delta check's baseline store "
                       "(crypto_baselines.json, one owner) instead of relying on the "
                       "ledger's raw checks; re-verify the flagged prints before reuse"),
        },
        "validation": checks,
        "validation_summary": {"total": len(checks), "failed": len(failed),
                               "blocking_failed": len(blocking),
                               "secondary_only_failures": len(failed) - len(blocking),
                               "primary_source_ok": primary_ok},
        "limitations": [
            "Primary window is 9 contiguous daily points (2026-08-28..2026-09-05): 8 returns. That is below the n>=10 MARK requires before publishing a rate (K3), so sigma here is directional evidence, not a forecast.",
            "The primary window is a calmer regime than the 2026-09-10..09-22 run in the ledger (BTC ~63.5k -> ~86k); if that move was real, true recent vol is higher and the band is even more decisive than stated.",
            "Fat tails and vol clustering are not modelled; both normal and i.i.d. legs understate true tail frequency, so p_outside is a lower bound.",
            "Both sources are internally generated artifacts, not exchange data; a bad write in the snapshot family would propagate here undetected beyond the V7 gate.",
            "No fresh quote was taken, so the horizon-end score for CRYPTO-MOM-20260922 still needs a sourced quote at 2026-09-24.",
        ],
        "disclaimer": "Research/ops artifact for internal scorekeeping. Not financial advice.",
    }

    for c in checks:
        print(("PASS " if c["pass"] else "FAIL ") + c["id"] + " " + c["check"]
              + " -> " + json.dumps(c["observed"]))
    for s in SYMBOLS:
        v = est.get(s)
        if v:
            print(f"{s}: sigma_d={v['sigma_daily_pct']:.3f}% "
                  f"(robust {v['sigma_daily_robust_pct']:.3f}%) "
                  f"sigma_2d={v['sigma_horizon_pct']:.3f}% k={v['band_k_sigmas']:.3f} "
                  f"p_outside={v['p_outside_analytic']:.3f} "
                  f"no_edge={v['expected_no_edge_pct']:.1f}%")
    print(f"VERDICT {verdict} | validations {len(checks) - len(failed)}/{len(checks)} pass")
    print(f"data-quality: {len(ledg_bad)} implausible ledger prints, "
          f"{len(xs['disagreements'])} cross-source disagreements over "
          f"{xs['shared_date_count']} shared dates")

    if blocking:
        print(f"REFUSING TO WRITE: {len(blocking)} blocking (primary/global) "
              f"validation failure(s)", file=sys.stderr)
        return 1
    if len(failed) != len(blocking):
        print(f"NOTE: {len(failed) - len(blocking)} secondary-source failure(s) "
              f"recorded as data-quality findings, not blockers")
    if ns.selftest:
        print("selftest only; no file written")
        return 0
    tmp = OUT.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n")
    tmp.replace(OUT)
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
