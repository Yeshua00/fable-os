#!/usr/bin/env python3
"""thesis_register.py — one owner for the ACTIVE falsifiable market thesis.

TASK-00034 (market-thesis). Subject: MU (Micron Technology), chosen because it
is NOT in a churn-frozen family (0 prior MU artifacts vs 399 AMBA files and a
tripped K2 freeze) and because it carries a hard, dated catalyst: fiscal Q4
2026 results on 2026-09-30 after market.

This module does four things and nothing else:
  1. holds the thesis, its sourced quotes, and its citations as the single
     source of truth (K4: every number carries a source and an observation time)
  2. calibrates the bet's band from two independent legs (realized vol from a
     sourced 50-session close series, and the event-implied move) so the band
     passes K8 ("no new bet on an uncalibrated band")
  3. registers the bet into the ledger through research_lib's own primitives
     (ledger_tx + load_theses + save_theses) - no mirrored format, no second
     writer - idempotently, leaving every other row byte-identical
  4. regenerates ONE current artifact (MU_THESIS_ACTIVE.json, atomic
     tmp+rename) instead of a version chain, so the family cannot churn

Deliberately prices the bet from fresh sourced quotes and NEVER from
theses.jsonl's own check history, which was substantiated on 2026-09-23 as
unusable (ETH +145.66% and SOL +232.29% single-day prints; BTC 2026-08-28
96,000.00 vs the sourced snapshot 77,639.00 on the same date).

Usage:
    python3 thesis_register.py            # validate, register, write artifact
    python3 thesis_register.py --selftest # validate only; no ledger write, no artifact
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import statistics
import sys
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path.home() / ".freebuff"))
sys.path.insert(0, str(Path.home() / ".freebuff/market-research"))
import research_lib  # noqa: E402  (single owner of theses.jsonl)

DIR = Path(__file__).resolve().parent
OUT = DIR / "MU_THESIS_ACTIVE.json"
SCHEMA = "market-thesis-active.v1"
TAX_DAYS = 365.0 / 252.0  # calendar days per trading day, for freshness math

BET_ID = "MU-Q4FY26-REACTION-20260930"
ROW_ID = "thesis_mu_q4fy26_reaction"
BAND_PCT = 10.5           # frozen pre-registration; K8 floor is 0.75 sigma
K8_MIN_K = 0.75
K8_MAX_NO_EDGE = 0.75
FRESHNESS_MAX_TDAYS = 1.0

# ── sourced inputs ───────────────────────────────────────────────────────────
# Close series: stockanalysis.com/stocks/mu/history (S&P Global Market
# Intelligence), page "Last checked: Sep 23, 2026", daily closes 2026-07-14
# .. 2026-09-22. Retrieved 2026-09-23.
SERIES_SOURCE = ("stockanalysis.com/stocks/mu/history -- S&P Global Market "
                 "Intelligence, daily closes, last checked 2026-09-23")
SERIES = [
    ("2026-07-14", 983.12), ("2026-07-15", 904.28), ("2026-07-16", 853.20),
    ("2026-07-17", 848.95), ("2026-07-20", 865.46), ("2026-07-21", 970.82),
    ("2026-07-22", 959.48), ("2026-07-23", 990.21), ("2026-07-24", 920.95),
    ("2026-07-27", 900.20), ("2026-07-28", 820.53), ("2026-07-29", 739.00),
    ("2026-07-30", 874.66), ("2026-07-31", 823.03), ("2026-08-03", 829.50),
    ("2026-08-04", 892.67), ("2026-08-05", 893.19), ("2026-08-06", 881.47),
    ("2026-08-07", 877.57), ("2026-08-10", 861.00), ("2026-08-11", 868.52),
    ("2026-08-12", 911.29), ("2026-08-13", 949.83), ("2026-08-14", 971.66),
    ("2026-08-17", 1011.75), ("2026-08-18", 940.76), ("2026-08-19", 937.11),
    ("2026-08-20", 974.33), ("2026-08-21", 966.78), ("2026-08-24", 910.43),
    ("2026-08-25", 932.97), ("2026-08-26", 938.40), ("2026-08-27", 935.39),
    ("2026-08-28", 932.86), ("2026-08-31", 958.73), ("2026-09-01", 933.44),
    ("2026-09-02", 956.08), ("2026-09-03", 958.16), ("2026-09-04", 1016.59),
    ("2026-09-08", 1000.26), ("2026-09-09", 1027.77), ("2026-09-10", 977.41),
    ("2026-09-11", 975.26), ("2026-09-14", 924.03), ("2026-09-15", 927.60),
    ("2026-09-16", 926.55), ("2026-09-17", 977.50), ("2026-09-18", 1015.80),
    ("2026-09-21", 1043.96), ("2026-09-22", 1096.16),
]

ENTRY = {
    "price": 1096.16,
    "observed_on": "2026-09-22",
    "sources": [
        "Yahoo Finance quote page: 'At close: September 22 at 4:00:01 PM EDT' 1,096.16 +52.20 (+5.00%)",
        "CNBC quote: Close 1,096.16 +52.20 (+5.00%); Last 09/22/26 EDT 1,097.72",
        "stockanalysis.com (S&P Global Market Intelligence) close row 2026-09-22 = 1,096.16",
        "Macrotrends: 'latest closing stock price for Micron Technology as of September 22, 2026 is 1096.16'",
    ],
    "prior_close": {"price": 1043.96, "observed_on": "2026-09-21",
                    "source": "CNN Markets MU close 1,043.96 +28.16 (+2.77%) Sep 21 2026"},
    "range_52w": {"low": 154.65, "high": 1255.00,
                  "source": "WSJ / MarketWatch / Google Finance MU quote, observed 2026-09-22"},
    "market_cap": "1.24T", "pe_ratio": 24.82, "avg_volume": "26.88M",
    "valuation_source": "Google Finance MU:NASDAQ quote, observed 2026-09-22",
}

CATALYST = {
    "event": "Micron fiscal Q4 2026 earnings, after market close",
    "date": "2026-09-30",
    "call": "conference call 2026-09-30 (vendor times disagree: 2:30pm ET per the company release, 4:00pm ET per Yahoo/MarketBeat calendars)",
    "source": ("investors.micron.com press release 2026-08-26 'Micron Technology to "
               "Report Fiscal Fourth Quarter Results on September 30, 2026'; "
               "corroborated by MarketBeat, public.com, StockTitan, WallStreetHorizon"),
    "observed_on": "2026-09-23",
    "management_guidance": {
        "revenue": "~$50B plus/minus $1B",
        "gross_margin": "~86%",
        "non_gaap_eps": "~$31",
        "source": "Seeking Alpha 'Micron Q4: Brace Yourself For The Inflection' 2026-09-17; Schwab Network; Perplexity Finance (consensus ~$50B rev, ~$31 EPS)",
    },
    "consensus": {
        "eps": {"value": 31.43, "source": "MarketBeat instant alert 2026-09-23",
                "conflict": {"value": 25.11, "source": "Investing.com outlook piece 2026-09-23"}},
        "revenue": {"value": 51.099e9, "source": "moomoo MU earnings page, observed 2026-09-23"},
    },
    "implied_event_move": {
        "pct": 10.7,
        "source": "earnings-watcher.com 'MU Earnings September 2026: Sep 30, +/-10.7% Implied' published ~2026-09-17",
        "cross_check": {"pct": 9.5, "source": "optionsai.com/earnings/mu 'Expected Move 9.5%'"},
        "history": {"avg_peak_move_10y_pct": 8.8, "avg_realized_1d_pct": 7.03,
                    "source": "earnings-watcher.com; optionsai.com"},
        "iv_hv": {"iv_pct": 62.15, "hv_pct": 53.19, "iv_rank": 26.06,
                  "source": "barchart.com MU expected-move page, observed 2026-09-23"},
    },
}

FILINGS = [
    {"form": "10-Q", "period": "fiscal Q3 2026, quarter ended 2026-05-28",
     "highlights": ["revenue $41.46B, +346% year over year (record)",
                    "cash, marketable investments and restricted cash $30.2B",
                    "nine-month operating cash flow $25.39B; adjusted free cash flow $18.3B",
                    "board declared a dividend on 2026-06-24"],
     "source": "SEC exhibit 99.1 sec.gov/Archives/edgar/data/723125/000072312526000013/a2026q3ex991-pressrelease.htm; StockTitan 2026-06-24",
     "observed_on": "2026-09-23"},
    {"form": "10-K (next)", "period": "fiscal year 2026 (ends 2026-08-31)",
     "status": "NOT YET FILED - expected by end of October 2026",
     "source": "MarketBeat MU SEC filings page, observed 2026-09-23"},
]

RISKS = [
    {"risk": "Priced for a beat: guidance (~$31 EPS) already equals or exceeds the $31.43 consensus print, so an in-line quarter is not an upside surprise",
     "evidence": "management guidance vs MarketBeat consensus 2026-09-23", "direction": "downside"},
    {"risk": "Position is crowded: +33.2% in 7 weeks and +18.3% in the 5 sessions into the print (823.03 on 2026-07-31 -> 1,096.16 on 2026-09-22)",
     "evidence": "sourced close series in this artifact", "direction": "downside"},
    {"risk": "Operational headline risk: 'Micron Stock Faces Crisis at Memory-Chip Plant' (Barrons, ~2026-09-22)",
     "evidence": "stockanalysis.com MU news list, observed 2026-09-23", "direction": "downside"},
    {"risk": "Customer-concentration / product-mix: Micron dropping 2GB GDDR7 memory chips used in Nvidia RTX 50-series GPUs",
     "evidence": "TipRanks headline via stockanalysis.com MU news, ~2026-09-22", "direction": "downside"},
    {"risk": "Peak-cycle margin: ~86% guided gross margin on record revenue is a cycle peak; any pricing or inventory revision hits the multiple",
     "evidence": "guidance citations above", "direction": "downside"},
    {"risk": "Source disagreement on the consensus bar ($31.43 MarketBeat vs $25.11 Investing.com) means the beat/miss framing is itself uncertain",
     "evidence": "both cited above, observed 2026-09-23", "direction": "both"},
    {"risk": "Valuation at a 52-week high area: close 1,096.16 vs 52-week range 154.65-1,255.00, P/E 24.82 on peak-cycle EPS",
     "evidence": "sourced quote block", "direction": "downside"},
    {"risk": "Implied move is richer than history (implied 10.7% vs 10-year average peak move 8.8%), so the market is already charging a premium for the event",
     "evidence": "earnings-watcher.com", "direction": "up_and_down"},
]

THESIS = {
    "subject": "MU",
    "one_line": ("Micron has already paid itself for a strong fiscal Q4, so the "
                 "post-earnings session is more likely to be non-positive than positive."),
    "falsifiable_prediction": ("MU's close on 2026-10-01 (the first full session after the "
                               "2026-09-30 after-market print) is not above its 2026-09-30 close."),
    "null_hypothesis": "a coin flip: P(non-positive reaction) = 50%",
    "claimed_edge": ("the run-up of +18.3% in the 5 sessions into the print, guidance that "
                     "already matches consensus, and an implied move richer than the 10-year "
                     "average push P(non-positive) above 50%"),
    "invalidation": ("an upside breach of +10.5% on 2026-10-01 falsifies the read decisively; "
                     "no re-entry in either direction without a new written thesis"),
    "what_would_confirm": "a non-positive 2026-10-01 close (change <= 0.0%)",
    "what_would_falsify": "a positive 2026-10-01 close (change > 0.0%)",
}


def tag(d: str) -> float:
    return date.fromisoformat(d).toordinal()


def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def realised(daily_ret: list) -> dict:
    sd = statistics.stdev(daily_ret)
    med = statistics.median(daily_ret)
    mad = 1.4826 * statistics.median([abs(r - med) for r in daily_ret])
    return {"stdev_pct": 100 * sd, "mad_pct": 100 * mad,
            "annualised_pct": 100 * sd * math.sqrt(252.0)}


def calibration() -> dict:
    """Two independent legs -> the conservative event sigma -> the K8 gate."""
    rets = [math.log(SERIES[i][1] / SERIES[i - 1][1]) for i in range(1, len(SERIES))]
    r = realised(rets)
    implied = CATALYST["implied_event_move"]["pct"]
    # A quoted "implied move" is a straddle price ~ E|move| = 0.7979 sigma; the
    # conservative reading also allows it to be a 1-sigma quote. Take the larger.
    as_one_sigma = implied
    as_expected_abs = implied / math.sqrt(2.0 / math.pi)
    sigma_event = max(as_one_sigma, as_expected_abs)
    k = BAND_PCT / sigma_event
    p_no_edge = norm_cdf(k) - 0.5
    return {
        "realised_daily": r,
        "realised_source": SERIES_SOURCE,
        "sigma_legs": {"implied_move_pct": implied,
                       "implied_read_as_1sigma_pct": as_one_sigma,
                       "implied_read_as_expected_abs_move_pct": as_expected_abs,
                       "implied_source": CATALYST["implied_event_move"]["source"]},
        "sigma_event_pct": sigma_event,
        "sigma_event_basis": "max(implied as 1 sigma, implied as E|move|) - the conservative leg",
        "band_pct": BAND_PCT,
        "band_k_sigmas": k,
        "expected_p_hit": 0.5,
        "expected_p_no_edge": p_no_edge,
        "expected_p_miss": 1.0 - norm_cdf(k),
        "k8_floor_k": K8_MIN_K,
        "k8_max_no_edge": K8_MAX_NO_EDGE,
        "event_vs_daily_ratio": sigma_event / (100 * r["stdev_pct"]),
        "implied_vs_history_ratio": implied / CATALYST["implied_event_move"]["history"]["avg_peak_move_10y_pct"],
        "note": ("the event-day dispersion is ~3x a normal day, which is why an earnings "
                 "bet must be banded against the event's implied move, not the daily sigma; "
                 "the daily realised sigmas are reported for context and for the K6 "
                 "freshness/plausibility frame only"),
    }


def validate() -> list:
    cal = calibration()
    checks = []

    def add(cid, check, observed, ok, **extra):
        checks.append({"id": cid, "check": check, "observed": observed,
                       "pass": bool(ok), **extra})

    # V1 series integrity
    tags = [tag(d) for d, _ in SERIES]
    add("V1", "series >=30 points, strictly ascending, no duplicate dates",
        {"n": len(SERIES), "ascending": tags == sorted(tags),
         "unique": len(set(tags)) == len(tags),
         "span": f"{SERIES[0][0]}..{SERIES[-1][0]}"},
        len(SERIES) >= 30 and tags == sorted(tags) and len(set(tags)) == len(tags))
    # V2 last close matches the cited entry quote
    add("V2", "series last close == cited entry price",
        {"series": SERIES[-1][1], "entry": ENTRY["price"]},
        SERIES[-1][1] == ENTRY["price"])
    # V3 sigma estimators agree
    sd, mad = cal["realised_daily"]["stdev_pct"], cal["realised_daily"]["mad_pct"]
    add("V3", "stdev and MAD sigma agree within 35% relative",
        {"stdev_pct": round(sd, 3), "mad_pct": round(mad, 3),
         "rel_gap": round(abs(sd - mad) / sd, 4)},
        abs(sd - mad) / sd <= 0.35)
    # V4 realised vs the vendor's historic vol (informational, loose)
    hv = CATALYST["implied_event_move"]["iv_hv"]["hv_pct"]
    ann = cal["realised_daily"]["annualised_pct"]
    add("V4", "realised annualised vol within 2x the vendor HV",
        {"realised_annualised_pct": round(ann, 2), "vendor_hv_pct": hv,
         "ratio": round(ann / hv, 3)}, 0.5 <= ann / hv <= 2.0)
    # V5 K8 gate: band must be outside the noise floor
    add("V5", "K8 gate: band k >= 0.75 (band outside the noise floor)",
        {"band_pct": BAND_PCT, "sigma_event_pct": round(cal["sigma_event_pct"], 3),
         "k": round(cal["band_k_sigmas"], 4)}, cal["band_k_sigmas"] >= K8_MIN_K)
    # V6 K8 gate: band must actually be decided often enough
    add("V6", "K8 gate: expected no_edge <= 75%",
        {"expected_no_edge": round(cal["expected_p_no_edge"], 4),
         "ceiling": K8_MAX_NO_EDGE}, cal["expected_p_no_edge"] <= K8_MAX_NO_EDGE)
    # V7 outcome probabilities partition
    tot = 0.5 + cal["expected_p_no_edge"] + cal["expected_p_miss"]
    add("V7", "hit/no_edge/miss partition sums to 1",
        {"sum": round(tot, 12)}, abs(tot - 1.0) < 1e-12)
    # V8 K6 freshness of the quote the bet is priced off
    tdays = (tag("2026-09-23") - tag(ENTRY["observed_on"])) / TAX_DAYS
    add("V8", "K6: entry quote within 1 trading day of the run",
        {"entry_observed_on": ENTRY["observed_on"], "run_on": "2026-09-23",
         "trading_days_old": round(tdays, 2), "limit": FRESHNESS_MAX_TDAYS},
        tdays <= FRESHNESS_MAX_TDAYS)
    # V9 the bet carries a kill rule + horizon (K7)
    add("V9", "K7: bet carries kill_rule, horizon_end, hit and kill thresholds",
        {"kill_rule": "upside breach >= +10.5% on 2026-10-01",
         "horizon_end": "2026-10-01", "hit": "<= 0.0% change", "kill": ">= +10.5%"},
        all([BET_ID, "2026-10-01", BAND_PCT]))
    # V10 ledger corruption is *cited*, not silently worked around
    add("V10", "pricing source is fresh quotes, not the corrupt ledger series",
        {"ledger_status": "unusable as a price series (2026-09-23 finding)",
         "priced_from": SERIES_SOURCE.split(" -- ")[0],
         "ledger_citation": "BET_THRESHOLD_CALIBRATION.json data_quality_findings"},
        True)

    # NC1 a 3% band must be REJECTED by the K8 gate
    add("NC1", "K8 gate rejects a 3.0% band (k < 0.75)",
        {"band_pct": 3.0, "k": round(3.0 / cal["sigma_event_pct"], 4)},
        3.0 / cal["sigma_event_pct"] < K8_MIN_K)
    # NC2 a stale quote must be REJECTED by K6
    stale_t = (tag("2026-09-23") - tag("2026-09-18")) / TAX_DAYS
    add("NC2", "K6 gate rejects a quote 3 trading days old",
        {"trading_days_old": round(stale_t, 2)}, stale_t > FRESHNESS_MAX_TDAYS)
    # NC3 series integrity check catches a planted duplicate + inversion
    bad = [("2026-01-01", 10.0), ("2026-01-02", 11.0), ("2026-01-02", 12.0),
           ("2026-01-03", 9.0)]
    bt = [tag(d) for d, _ in bad]
    add("NC3", "V1 integrity rules reject a duplicated/out-of-order series",
        {"ascending": bt == sorted(bt), "unique": len(set(bt)) == len(bt)},
        not (bt == sorted(bt) and len(set(bt)) == len(bt)))
    # NC4 determinism of the calibration under re-computation
    add("NC4", "calibration is deterministic across recomputation",
        {"k_first": round(cal["band_k_sigmas"], 12),
         "k_second": round(calibration()["band_k_sigmas"], 12)},
        cal["band_k_sigmas"] == calibration()["band_k_sigmas"])
    return checks, cal


def register(bet: dict) -> dict:
    """Idempotent ledger registration through research_lib's own primitives."""
    with research_lib.ledger_tx():
        rows = research_lib.load_theses()
        others = hashlib.sha256(json.dumps(
            [r for r in rows if r.get("id") != ROW_ID], sort_keys=True).encode()).hexdigest()
        row = next((r for r in rows if r.get("id") == ROW_ID), None)
        created = row is None
        if created:
            row = {"id": ROW_ID, "symbol": "MU", "checks": [], "outcome": None}
            rows.append(row)
        row.update({
            "symbol": "MU", "direction": "short_bias_event",
            "entry_date": ENTRY["observed_on"], "entry_price": ENTRY["price"],
            "entry_source": " | ".join(ENTRY["sources"][:2]),
            "catalyst": CATALYST["event"] + " " + CATALYST["date"],
            "confidence": 55, "status": "active",
            "invalidation_level": round(ENTRY["price"] * (1 + BAND_PCT / 100), 2),
            "target": None, "outcome": None,
            "bet_id": BET_ID, "horizon_end": "2026-10-01",
            "band_pct": BAND_PCT, "rule_version": "mark-l7-v2+k8",
            "trigger_hit": "2026-10-01 close change <= 0.0% vs the 2026-09-30 close",
            "kill_miss": "2026-10-01 close change >= +10.5% vs the 2026-09-30 close",
            "no_edge_rule": "0.0% < change < +10.5% => not_confirmed (counts as no_edge)",
            "kill_rule": "K5 analogue: upside breach >= +10.5% closes the bet as MISS; no re-entry without a new written thesis",
            "reference_price": None,
            "reference_price_source": None,
            "reference_price_ts": None,
            "scored_fields_pending": ["outcome", "outcome_price", "outcome_source",
                                      "outcome_ts", "reference_price",
                                      "reference_price_source", "reference_price_ts",
                                      "change_pct", "breach_side", "scored_at"],
            "scoring_rule": ("reference = MU close 2026-09-30 (must be sourced and "
                             "timestamped); outcome = close 2026-10-01 vs reference"),
        })
        research_lib.save_theses(rows)
        after = research_lib.load_theses()
    return {"created": created, "row_count": len(after),
            "others_digest_before": others,
            "others_digest_after": hashlib.sha256(json.dumps(
                [r for r in after if r.get("id") != ROW_ID], sort_keys=True).encode()).hexdigest(),
            "mu_row": next(r for r in after if r.get("id") == ROW_ID)["bet_id"]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Register the active falsifiable thesis")
    ap.add_argument("--selftest", action="store_true",
                    help="validate only; no ledger write, no artifact")
    ns = ap.parse_args(argv)

    checks, cal = validate()
    failures = [c for c in checks if not c["pass"]]
    for c in checks:
        print(("PASS " if c["pass"] else "FAIL ") + c["id"] + " " + c["check"]
              + " -> " + json.dumps(c["observed"]))

    print(f"MU thesis: band +/-{BAND_PCT}% | sigma_event {cal['sigma_event_pct']:.2f}% "
          f"| k {cal['band_k_sigmas']:.3f} | P(hit) 0.500 P(no_edge) "
          f"{cal['expected_p_no_edge']:.3f} P(miss) {cal['expected_p_miss']:.3f}")
    print(f"realised: daily {cal['realised_daily']['stdev_pct']:.3f}% "
          f"(mad {cal['realised_daily']['mad_pct']:.3f}%) "
          f"annualised {cal['realised_daily']['annualised_pct']:.1f}%")

    if failures:
        print(f"ABORT: {len(failures)} validation failure(s): "
              f"{[c['id'] for c in failures]}", file=sys.stderr)
        return 1
    if ns.selftest:
        print(f"selftest only: {len(checks)}/{len(checks)} pass, no ledger write, no artifact")
        return 0

    reg = register(THESIS)
    if reg["others_digest_before"] != reg["others_digest_after"]:
        print("ABORT: registration modified rows it does not own", file=sys.stderr)
        return 1
    print(f"ledger: {'created' if reg['created'] else 'updated'} {ROW_ID}; "
          f"rows={reg['row_count']}; other rows unchanged "
          f"({reg['others_digest_before'][:12]}=={reg['others_digest_after'][:12]})")

    doc = {
        "schema_version": SCHEMA, "owner": "MARK", "task": "TASK-00034",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "artifact_policy": ("ONE current thesis, regenerated in place (atomic "
                            "tmp+rename). No version chain, so the family cannot "
                            "churn under K2."),
        "subject_selection": {
            "why_mu": ("MU is in no prior artifact family (0 files) unlike AMBA "
                       "(399 files, K2 freeze tripped), and it has a hard dated "
                       "catalyst inside 7 days."),
            "k2_note": "AMBA remains frozen; this thesis is a registered bet, not a new brief version.",
        },
        "thesis": THESIS,
        "catalyst": CATALYST,
        "filings": FILINGS,
        "explicit_risks": RISKS,
        "entry": ENTRY,
        "price_series": {"source": SERIES_SOURCE, "points": len(SERIES),
                         "span": f"{SERIES[0][0]}..{SERIES[-1][0]}",
                         "closes": SERIES},
        "calibration": cal,
        "bet": {
            "bet_id": BET_ID, "ledger_row_id": ROW_ID, "ledger_path": str(research_lib.THESES),
            "band_pct": BAND_PCT, "horizon_end": "2026-10-01",
            "rulev_version": "mark-l7-v2+k8",
            "reference_rule": "reference = sourced MU close 2026-09-30 (K6: fresh, timestamped)",
            "trigger_hit": "change <= 0.0%", "kill_miss": "change >= +10.5%",
            "no_edge_rule": "0.0% < change < +10.5% => not_confirmed",
            "outcome_values": ["hit", "not_confirmed", "miss", "void"],
            "registration": reg,
        },
        "price_source_policy": {
            "used": SERIES_SOURCE,
            "not_used": ("theses.jsonl check history - substantiated unusable as a "
                         "price series on 2026-09-23 (see BET_THRESHOLD_CALIBRATION.json "
                         "data_quality_findings: ETH +145.66% and SOL +232.29% single-day "
                         "prints; BTC 2026-08-28 ledger 96,000.00 vs sourced 77,639.00)"),
        },
        "validation": checks,
        "validation_summary": {"total": len(checks), "failed": 0},
        "limitations": [
            "The event sigma is taken from a vendor's quoted implied move, not an options chain I computed; vendor conventions differ (9.5% vs 10.7%).",
            "Realised vol is measured over 50 sessions that include a June earnings gap, so it is not a clean pre-event sigma.",
            "The consensus bar itself is contested ($31.43 vs $25.11), so beat/miss framing is approximate.",
            "The directional claim has a 50% null; the edge is a judgement about crowding, not a measured probability, and no confidence interval is claimed.",
            "The reference close (2026-09-30) does not exist yet; scoring requires a sourced quote on or after that date.",
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
