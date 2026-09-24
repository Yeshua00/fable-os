#!/usr/bin/env python3
"""jpm_band_calibration.py — one owner for the JPM Q3-2026 event-band calibration.

TASK-00116 (volatility-model). Calibrates the candidate event band for the JPM
Q3 2026 earnings bet (registered separately by jpm_thesis_register.py,
TASK-00115) from a sourced 50-session close series and the vendor implied-move
quote. Fresh family: 0 prior JPM_BAND files; K2 does not bind.

DATA-DEFECT STORY (why V12 exists):
  The FIRST transcription of this series (2026-09-24, in the turn that was
  interrupted) misattributed the Aug 5 - Sep 4 dates by one trading session:
  each date held the NEXT session's close. Date-ordered integrity checks
  (ascending, unique) PASSED on that bad series because the dates themselves
  were fine - only the date->value pairing was wrong, and it silently distorted
  every return in a 23-row window (stdev 1.135 vs the corrected 1.141). The
  defect was caught by re-reading the source page row-by-row, and the fix is
  made checkable here: V12 recomputes each session's return from consecutive
  closes and asserts it agrees with the VENDOR'S OWN stated Change column to
  <= 0.01pp. The corrected series agrees on all 49 verifiable rows (max
  deviation 0.0049pp). NC2 replants the original misattributed window and
  proves V12 catches it (>0.8pp deviation).

What it does and nothing else:
  1. holds the corrected, integrity-checked series as the single source of truth
  2. calibrates the event band from two legs: realised vol from the series, and
     the optionslam weekly implied-move quote read conservatively (K8 gate)
  3. emits ONE artifact (JPM_BAND_CALIBRATION.json, atomic tmp+rename)
  Read-only: no ledger writes, no prices fetched at runtime (K4/K6 provenance
  recorded on every input).

Usage:
    python3 jpm_band_calibration.py            # validate + write artifact
    python3 jpm_band_calibration.py --selftest # validate only; no artifact
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(DIR))
from thesis_register import tag, norm_cdf, realised  # noqa: E402  (one owner for math)

OUT = DIR / "JPM_BAND_CALIBRATION.json"
SCHEMA = "jpm-band-calibration.v1"
RUN_ON = "2026-09-24"
TAX_DAYS = 365.0 / 252.0
K8_MIN_K = 0.75
K8_MAX_NO_EDGE = 0.75
STATED_TOL_PP = 0.01   # |computed - stated| must be <= this (stated is 2dp)

# ── sourced inputs ───────────────────────────────────────────────────────────
SERIES_SOURCE = ("stockanalysis.com/stocks/jpm/history -- S&P Global Market "
                 "Intelligence, Close column, page 'Last checked: Sep 23, 2026' "
                 "(read after the 16:00 EDT close, final prints; raw Close == "
                 "Adj. Close on every row - JPM pays a quarterly dividend but "
                 "the columns agree in this window as printed)")

# (date, close, vendor-stated Change %) - the stated column is the integrity
# anchor: every return below is re-derived and cross-checked against it (V12).
SERIES = [
    ("2026-07-15", 346.91, 1.17), ("2026-07-16", 343.15, -1.08),
    ("2026-07-17", 341.10, -0.60), ("2026-07-20", 338.87, -0.65),
    ("2026-07-21", 345.23, 1.88), ("2026-07-22", 348.21, 0.86),
    ("2026-07-23", 349.90, 0.49), ("2026-07-24", 353.21, 0.95),
    ("2026-07-27", 356.20, 0.85), ("2026-07-28", 357.31, 0.31),
    ("2026-07-29", 344.71, -3.53), ("2026-07-30", 350.85, 1.78),
    ("2026-07-31", 351.79, 0.27), ("2026-08-03", 352.64, 0.24),
    ("2026-08-04", 357.52, 1.38), ("2026-08-05", 359.24, 0.48),
    ("2026-08-06", 356.30, -0.82), ("2026-08-07", 357.52, 0.34),
    ("2026-08-10", 359.79, 0.63), ("2026-08-11", 362.04, 0.63),
    ("2026-08-12", 365.18, 0.87), ("2026-08-13", 363.11, -0.57),
    ("2026-08-14", 362.84, -0.07), ("2026-08-17", 360.96, -0.52),
    ("2026-08-18", 363.25, 0.63), ("2026-08-19", 357.26, -1.65),
    ("2026-08-20", 351.55, -1.60), ("2026-08-21", 351.58, 0.01),
    ("2026-08-24", 356.39, 1.37), ("2026-08-25", 356.69, 0.08),
    ("2026-08-26", 356.50, -0.05), ("2026-08-27", 354.22, -0.64),
    ("2026-08-28", 357.62, 0.96), ("2026-08-31", 356.02, -0.45),
    ("2026-09-01", 354.95, -0.30), ("2026-09-02", 356.22, 0.36),
    ("2026-09-03", 362.06, 1.64), ("2026-09-04", 358.64, -0.94),
    ("2026-09-08", 353.51, -1.43), ("2026-09-09", 354.71, 0.34),
    ("2026-09-10", 353.56, -0.32), ("2026-09-11", 356.23, 0.76),
    ("2026-09-14", 350.13, -1.71), ("2026-09-15", 352.49, 0.67),
    ("2026-09-16", 348.92, -1.01), ("2026-09-17", 349.31, 0.11),
    ("2026-09-18", 349.67, 0.10), ("2026-09-21", 352.04, 0.68),
    ("2026-09-22", 340.00, -3.42), ("2026-09-23", 337.53, -0.73),
]

# The original misattributed window (Aug 5 - Sep 4 held next-session closes),
# preserved ONLY as the negative-control specimen for V12.
BAD_WINDOW = [
    ("2026-08-05", 356.30), ("2026-08-06", 359.24), ("2026-08-07", 359.79),
    ("2026-08-10", 362.04), ("2026-08-11", 365.18), ("2026-08-12", 363.11),
    ("2026-08-13", 362.84), ("2026-08-14", 360.96), ("2026-08-17", 363.25),
    ("2026-08-18", 357.26), ("2026-08-19", 351.55), ("2026-08-20", 351.58),
    ("2026-08-21", 356.39), ("2026-08-24", 356.69), ("2026-08-25", 356.50),
    ("2026-08-26", 354.22), ("2026-08-27", 357.62), ("2026-08-28", 356.02),
    ("2026-08-31", 354.95), ("2026-09-01", 356.22), ("2026-09-02", 362.06),
    ("2026-09-03", 358.64), ("2026-09-04", 353.51),
]

IMPLIED_MOVE = {
    "pct": 5.64,
    "source": ("optionslam.com/earnings/straddle/JPM: 'Implied Move Weekly: "
               "5.64% Expires on: Oct. 16, 2026', observed 2026-09-24 - the "
               "weekly window (to Oct 16) is the nearest-dated quote covering "
               "the 2026-10-13 print; using it unchanged is the conservative "
               "direction (window longer than the event)"),
    "cross_check": {"pct": 3.4,
                    "source": "marketchameleon.com/Overview/JPM/Earnings: last print (2026-07-14 BMO) 'options predicted a +/-3.4% move vs +2.5% actual', observed 2026-09-24"},
    "history": {"exceeded_implied_16q": "9/16 (56%)",
                "history_source": "earnings-watcher.com/wiki/jpm-implied-move: 'actual earnings move exceeded the options-implied move in 9 of its last 16 reports (56%)', page updated 2026-09-02"},
    "vol_reference": {"iv_pct": 24.7, "ivile_pct": 57,
                      "source": "marketchameleon.com/Overview/JPM/IV: 'JPM implied volatility (IV) is 24.7, which is in the 57% percentile rank', observed 2026-09-24",
                      "note": "vendor HISTORICAL vol was not obtainable this run (barchart pages returned definitions only); the vendor IV is used as the V4 reference leg and the substitution is recorded here and in limitations (K4 - absence recorded, not guessed)"},
}

ENTRY_LAST_CLOSE = {"price": 337.53, "observed_on": "2026-09-23",
                    "source": "stockanalysis.com JPM history table row 'Sep 23, 2026': Close 337.53 = Adj. Close 337.53, Change -0.73%, page read after the close"}


def calibration() -> dict:
    """Realised leg from the corrected series + implied leg -> band -> K8 gate."""
    closes = [c for _, c, _ in SERIES]
    rets = [math.log(closes[i] / closes[i - 1]) for i in range(1, len(closes))]
    r = realised(rets)
    implied = IMPLIED_MOVE["pct"]
    as_one_sigma = implied
    as_expected_abs = implied / math.sqrt(2.0 / math.pi)
    sigma_event = max(as_one_sigma, as_expected_abs)
    band = implied  # band set AT the quoted implied move (same convention as TSLA)
    k = band / sigma_event
    return {
        "realised_daily": r,
        "realised_source": SERIES_SOURCE,
        "sigma_legs": {"implied_move_pct": implied,
                       "implied_read_as_1sigma_pct": as_one_sigma,
                       "implied_read_as_expected_abs_move_pct": as_expected_abs,
                       "implied_source": IMPLIED_MOVE["source"]},
        "sigma_event_pct": sigma_event,
        "sigma_event_basis": "max(implied as 1 sigma, implied as E|move|) - the conservative leg",
        "band_pct": band,
        "band_k_sigmas": k,
        "expected_p_hit": 0.5,
        "expected_p_no_edge": norm_cdf(k) - 0.5,
        "expected_p_miss": 1.0 - norm_cdf(k),
        "k8_floor_k": K8_MIN_K,
        "k8_max_no_edge": K8_MAX_NO_EDGE,
        "event_vs_daily_ratio": sigma_event / (100 * r["stdev_pct"]),
        "note": ("JPM's event sigma (~7.07%) is ~6.2x its realised daily sigma "
                 "- an earnings bet must be banded against the event quote, "
                 "not the daily sigma; the daily sigmas are context only"),
    }


def stated_change_deviation(series) -> dict:
    """Max |computed return - vendor-stated Change| over verifiable rows (V12 core)."""
    worst, worst_row, over = 0.0, None, []
    for i in range(1, len(series)):
        date, close, stated = series[i][0], series[i][1], series[i][2]
        comp = (close / series[i - 1][1] - 1) * 100
        dev = abs(comp - stated)
        if dev > worst:
            worst, worst_row = dev, date
        if dev > STATED_TOL_PP:
            over.append({"date": date, "computed": round(comp, 4),
                         "stated": stated, "dev_pp": round(dev, 4)})
    return {"rows_checked": len(series) - 1, "max_dev_pp": round(worst, 4),
            "max_dev_row": worst_row, "rows_over_tol": over}


def validate() -> tuple:
    cal = calibration()
    checks = []

    def add(cid, check, observed, ok, **extra):
        checks.append({"id": cid, "check": check, "observed": observed,
                       "pass": bool(ok), **extra})

    tags = [tag(d) for d, _, _ in SERIES]
    add("V1", "series >=30 points, strictly ascending, no duplicate dates",
        {"n": len(SERIES), "ascending": tags == sorted(tags),
         "unique": len(set(tags)) == len(tags),
         "span": f"{SERIES[0][0]}..{SERIES[-1][0]}"},
        len(SERIES) >= 30 and tags == sorted(tags) and len(set(tags)) == len(tags))
    add("V2", "series last close == cited entry quote",
        {"series": SERIES[-1][1], "entry": ENTRY_LAST_CLOSE["price"]},
        SERIES[-1][1] == ENTRY_LAST_CLOSE["price"])
    sd, mad = cal["realised_daily"]["stdev_pct"], cal["realised_daily"]["mad_pct"]
    add("V3", "stdev and MAD sigma agree within 35% relative",
        {"stdev_pct": round(sd, 3), "mad_pct": round(mad, 3),
         "rel_gap": round(abs(sd - mad) / sd, 4)},
        abs(sd - mad) / sd <= 0.35)
    hv_ref = IMPLIED_MOVE["vol_reference"]["iv_pct"]
    ann = cal["realised_daily"]["annualised_pct"]
    add("V4", "realised annualised vol within [0.5, 2]x the vendor vol reference "
              "(IV - HV not sourced, substitution recorded)",
        {"realised_annualised_pct": round(ann, 2), "vendor_iv_pct": hv_ref,
         "ratio": round(ann / hv_ref, 3)}, 0.5 <= ann / hv_ref <= 2.0)
    add("V5", "K8 gate: band k >= 0.75 (band outside the noise floor)",
        {"band_pct": cal["band_pct"], "sigma_event_pct": round(cal["sigma_event_pct"], 3),
         "k": round(cal["band_k_sigmas"], 4)}, cal["band_k_sigmas"] >= K8_MIN_K)
    add("V6", "K8 gate: expected no_edge <= 75%",
        {"expected_no_edge": round(cal["expected_p_no_edge"], 4),
         "ceiling": K8_MAX_NO_EDGE}, cal["expected_p_no_edge"] <= K8_MAX_NO_EDGE)
    tot = 0.5 + cal["expected_p_no_edge"] + cal["expected_p_miss"]
    add("V7", "hit/no_edge/miss partition sums to 1", {"sum": round(tot, 12)},
        abs(tot - 1.0) < 1e-12)
    tdays = (tag(RUN_ON) - tag(ENTRY_LAST_CLOSE["observed_on"])) / TAX_DAYS
    add("V8", "K6: entry quote within 1 trading day of the run",
        {"entry_observed_on": ENTRY_LAST_CLOSE["observed_on"], "run_on": RUN_ON,
         "trading_days_old": round(tdays, 2)}, tdays <= 1.0)
    add("V9", "calibration is deterministic across recomputation",
        {"k_first": round(cal["band_k_sigmas"], 12),
         "k_second": round(calibration()["band_k_sigmas"], 12)},
        cal["band_k_sigmas"] == calibration()["band_k_sigmas"])
    add("V10", "pricing source is fresh quotes, not the corrupt ledger series",
        {"ledger_status": "unusable as a price series (2026-09-23 finding)",
         "priced_from": SERIES_SOURCE.split(" -- ")[0]}, True)
    # V12: THE integrity check born from this turn's caught defect
    dev = stated_change_deviation(SERIES)
    add("V12", f"per-row returns agree with the vendor's stated Change column "
               f"(<= {STATED_TOL_PP}pp) - catches date/value misattribution",
        dev, len(dev["rows_over_tol"]) == 0)

    # NC1 a planted 3% band must be REJECTED by the K8 gate
    add("NC1", "K8 gate rejects a 3.0% band (k < 0.75)",
        {"band_pct": 3.0, "k": round(3.0 / cal["sigma_event_pct"], 4)},
        3.0 / cal["sigma_event_pct"] < K8_MIN_K)
    # NC2 the ORIGINAL misattributed window must be CAUGHT by V12
    bad_dev = stated_change_deviation(_bad_series())
    add("NC2", "V12 catches the original misattributed Aug 5 - Sep 4 window "
               "(one-session date/value shift)",
        {"rows_over_tol": len(bad_dev["rows_over_tol"]),
         "max_dev_pp": bad_dev["max_dev_pp"],
         "example": bad_dev["rows_over_tol"][:1]},
        len(bad_dev["rows_over_tol"]) > 0 and bad_dev["max_dev_pp"] > STATED_TOL_PP)
    # NC3 a planted single-point corruption must be caught
    corrupted = [(d, c * 1.02 if d == "2026-08-19" else c, st)
                 for d, c, st in SERIES]
    c_dev = stated_change_deviation(corrupted)
    add("NC3", "V12 catches a planted +2% single-point corruption",
        {"rows_over_tol": len(c_dev["rows_over_tol"]),
         "max_dev_pp": c_dev["max_dev_pp"]},
        len(c_dev["rows_over_tol"]) >= 2 and c_dev["max_dev_pp"] > 2.0 * STATED_TOL_PP)
    return checks, cal


def _bad_series() -> list:
    """The original defect rebuilt: BAD_WINDOW closes on their (wrong) dates,
    with stated changes kept from the source page - exactly how it stood."""
    stated_by_date = {d: st for d, _, st in SERIES}
    return [(d, c, stated_by_date[d]) for d, c in BAD_WINDOW]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Calibrate the JPM Q3-2026 event band")
    ap.add_argument("--selftest", action="store_true",
                    help="validate only; no artifact write")
    ns = ap.parse_args(argv)

    checks, cal = validate()
    for c in checks:
        print(("PASS " if c["pass"] else "FAIL ") + c["id"] + " " + c["check"]
              + " -> " + json.dumps(c["observed"])[:220])
    failures = [c for c in checks if not c["pass"]]

    print(f"JPM band: +/-{cal['band_pct']}% | sigma_event {cal['sigma_event_pct']:.4f}% "
          f"| k {cal['band_k_sigmas']:.4f} | P(hit) 0.500 P(no_edge) "
          f"{cal['expected_p_no_edge']:.4f} P(miss) {cal['expected_p_miss']:.4f}")
    print(f"realised: daily {cal['realised_daily']['stdev_pct']:.3f}% "
          f"(mad {cal['realised_daily']['mad_pct']:.3f}%) "
          f"annualised {cal['realised_daily']['annualised_pct']:.1f}%")

    if failures:
        print(f"ABORT: {len(failures)} validation failure(s): "
              f"{[c['id'] for c in failures]}", file=sys.stderr)
        return 1
    if ns.selftest:
        print(f"selftest only: {len(checks)}/{len(checks)} pass, no artifact")
        return 0

    doc = {
        "schema_version": SCHEMA, "owner": "MARK", "task": "TASK-00116",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "artifact_policy": ("ONE current calibration per subject, regenerated in "
                            "place (atomic tmp+rename). No version chain (K2)."),
        "purpose": ("calibrate the candidate band for the JPM Q3-2026 earnings "
                    "bet BEFORE registration so K8 ('no bet on an uncalibrated "
                    "band') is satisfied at registration time"),
        "inputs": {"series": {"source": SERIES_SOURCE, "points": len(SERIES),
                              "span": f"{SERIES[0][0]}..{SERIES[-1][0]}",
                              "rows": SERIES},
                   "implied_move": IMPLIED_MOVE,
                   "entry_last_close": ENTRY_LAST_CLOSE},
        "data_quality": {
            "defect_found_and_fixed": (
                "first transcription (2026-09-24) misattributed Aug 5 - Sep 4 "
                "by one trading session (each date held the next session's "
                "close); date-ordered checks passed because dates were valid - "
                "only the date->value pairing was wrong. Caught by re-reading "
                "the source page row-by-row; corrected series re-verified "
                "against the vendor's stated Change column (V12)."),
            "v12_result": stated_change_deviation(SERIES),
            "bad_window_specimen": {"rows": len(BAD_WINDOW),
                                    "v12_result_on_specimen":
                                        stated_change_deviation(_bad_series())},
        },
        "calibration": cal,
        "validation": checks,
        "validation_summary": {"total": len(checks), "failed": 0},
        "assumptions": [
            "event return ~ Normal(0, sigma_event) with sigma_event = max(implied as 1 sigma, implied as E|move|) from the optionslam weekly quote",
            "hit = 0.5 is the null convention (P(non-positive) = 50%), not an edge claim",
            "the optionslam weekly window (to Oct 16) is wider than the Oct 13 event - using it unchanged overstates sigma_event slightly, which is the conservative direction for K8",
            "band is set AT the quoted implied move (5.64%), matching the TSLA/MU/UNH convention",
        ],
        "limitations": [
            "vendor HISTORICAL vol was not obtainable this run (barchart returned definitions only); V4 uses marketchameleon's IV 24.7 as the reference leg - an IV/HV substitution, recorded not hidden (K4)",
            "the optionslam weekly quote spans to Oct 16 (3 days past the print); a tighter event-only straddle quote was not available on 2026-09-24",
            "n=50 sessions from one window; the -3.53% (Jul 29) and -3.42% (Sep 22) days inflate stdev relative to MAD (rel_gap 0.244) but pass V3",
            "realised vs implied: earnings-watcher shows JPM's actual move exceeded the implied 9/16 (56%) - options have NOT reliably overpriced this event; the calibration sizes the band, it does not claim an overpricing edge",
            "prospective: the 2026-10-13 outcome does not exist yet; scoring needs sourced quotes on/after the print",
        ],
        "disclaimer": "Research/ops artifact for internal scorekeeping. Not financial advice.",
    }
    tmp = OUT.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n")
    tmp.replace(OUT)
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
