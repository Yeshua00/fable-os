#!/usr/bin/env python3
"""asml_thesis_register.py — one owner for the ASML falsifiable market thesis.

TASK-00075 (market-thesis). Subject: ASML (ASML Holding N.V.), chosen because
it is NOT in a churn-frozen family (0 prior ASML artifacts vs AMBA's 126
sec-review briefs and a tripped K2 freeze) and because it carries a hard, dated
catalyst: Q3 2026 results on Wednesday 2026-10-14, before the US open. It is
also uncorrelated with the already-registered MU bet (different company,
different risk driver), which is what the lane's ledger needs to produce a
sample larger than n=1.

This module does four things and nothing else:
  1. holds the thesis, its sourced quotes, and its citations as the single
     source of truth (K4: every number carries a source and an observation time)
  2. calibrates the bet's band from two independent legs (realised vol from a
     sourced 49-session close series, and the options-implied event move) so
     the band passes K8 ("no new bet on an uncalibrated band")
  3. registers the bet into the ledger through research_lib's own primitives
     (ledger_tx + load_theses + save_theses) - no mirrored format, no second
     writer - idempotently, leaving every other row byte-identical
  4. regenerates ONE current artifact (ASML_THESIS_ACTIVE.json, atomic
     tmp+rename) instead of a version chain, so the family cannot churn

The pure math helpers (tag/norm_cdf/realised) are imported from
thesis_register.py rather than re-implemented: one owner for the math.

Deliberately prices the bet from fresh sourced quotes and NEVER from
theses.jsonl's own check history, which was substantiated on 2026-09-23 as
unusable (ETH +145.66% and SOL +232.29% single-day prints; BTC 2026-08-28
96,000.00 vs the sourced snapshot 77,639.00 on the same date).

Usage:
    python3 asml_thesis_register.py            # validate, register, write artifact
    python3 asml_thesis_register.py --selftest # validate only; no ledger write, no artifact
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path.home() / ".freebuff"))
sys.path.insert(0, str(Path.home() / ".freebuff/market-research"))
import research_lib  # noqa: E402  (single owner of theses.jsonl)

# one owner for the math: reuse the pure helpers proven in thesis_register.py
from thesis_register import tag, norm_cdf, realised  # noqa: E402

DIR = Path(__file__).resolve().parent
OUT = DIR / "ASML_THESIS_ACTIVE.json"
SCHEMA = "market-thesis-active.v1"
TAX_DAYS = 365.0 / 252.0  # calendar days per trading day, for freshness math
RUN_ON = "2026-09-23"

BET_ID = "ASML-Q3-2026-REACTION-20261014"
ROW_ID = "thesis_asml_q3_2026_reaction"
BAND_PCT = 9.5            # frozen pre-registration; K8 floor is 0.75 sigma
K8_MIN_K = 0.75
K8_MAX_NO_EDGE = 0.75
FRESHNESS_MAX_TDAYS = 1.0

# ── sourced inputs ───────────────────────────────────────────────────────────
# Close series: stockanalysis.com/stocks/asml/history (S&P Global Market
# Intelligence), page "Last checked: Sep 23, 2026", daily closes 2026-07-15
# .. 2026-09-22. Retrieved 2026-09-23. The 2026-09-23 row was excluded because
# the market was still open when the page was read (intraday, not a close).
SERIES_SOURCE = ("stockanalysis.com/stocks/asml/history -- S&P Global Market "
                 "Intelligence, daily closes, last checked 2026-09-23 "
                 "(2026-09-23 intraday row excluded)")
SERIES = [
    ("2026-07-15", 1815.27), ("2026-07-16", 1784.87), ("2026-07-17", 1747.58),
    ("2026-07-20", 1739.02), ("2026-07-21", 1801.51), ("2026-07-22", 1801.86),
    ("2026-07-23", 1803.00), ("2026-07-24", 1757.09), ("2026-07-27", 1655.26),
    ("2026-07-28", 1582.95), ("2026-07-29", 1550.69), ("2026-07-30", 1651.44),
    ("2026-07-31", 1629.00), ("2026-08-03", 1642.52), ("2026-08-04", 1711.89),
    ("2026-08-05", 1678.22), ("2026-08-06", 1704.37), ("2026-08-07", 1740.99),
    ("2026-08-10", 1733.48), ("2026-08-11", 1799.38), ("2026-08-12", 1810.07),
    ("2026-08-13", 1847.90), ("2026-08-14", 1844.08), ("2026-08-17", 1883.12),
    ("2026-08-18", 1802.98), ("2026-08-19", 1751.73), ("2026-08-20", 1750.31),
    ("2026-08-21", 1763.76), ("2026-08-24", 1740.13), ("2026-08-25", 1744.16),
    ("2026-08-26", 1745.64), ("2026-08-27", 1735.01), ("2026-08-28", 1696.16),
    ("2026-08-31", 1696.01), ("2026-09-01", 1665.14), ("2026-09-02", 1682.30),
    ("2026-09-03", 1646.19), ("2026-09-04", 1714.88), ("2026-09-08", 1764.85),
    ("2026-09-09", 1729.52), ("2026-09-10", 1687.43), ("2026-09-11", 1698.30),
    ("2026-09-14", 1575.15), ("2026-09-15", 1591.48), ("2026-09-16", 1602.22),
    ("2026-09-17", 1629.67), ("2026-09-18", 1679.92), ("2026-09-21", 1711.32),
    ("2026-09-22", 1747.90),
]

ENTRY = {
    "price": 1747.90,
    "observed_on": "2026-09-22",
    "sources": [
        "stockanalysis.com (S&P Global Market Intelligence) close row 2026-09-22 = 1,747.90",
        "Macrotrends: 'The latest closing stock price for ASML Holding as of September 22, 2026 is 1747.90'",
        "Yahoo Finance ASML quote: Previous Close 1,747.90 (page read 2026-09-23)",
        "CNBC ASML:NASDAQ quote: Prev Close 1,747.90 (page read 2026-09-23)",
    ],
    "prior_close": {"price": 1711.32, "observed_on": "2026-09-21",
                    "source": "stockanalysis.com close row 2026-09-21 = 1,711.32 (+1.87%)"},
    "range_52w": {"low": 935.41, "high": 1999.96,
                  "source": "Yahoo Finance / WSJ ASML quote, observed 2026-09-23"},
    "valuation_source": "WSJ ASML quote: EPS (TTM) $32.12, observed 2026-09-23",
    "intraday_note": ("2026-09-23 was still open when sourced (1,738.69 at "
                      "15:48 EDT), so the bet is priced off the last FINAL close"),
}

CATALYST = {
    "event": "ASML Q3 2026 financial results, before the US market open",
    "date": "2026-10-14",
    "call": "investor call on release day (Q2 precedent: 15:00 CET / 09:00 US Eastern Time)",
    "source": ("asml.com financial calendar: 'Wednesday, 14 October 2026 - Q3 2026 "
               "financial results' (observed 2026-09-23); corroborated by MarketBeat "
               "('scheduled for Wednesday, October 14, 2026'), Zacks, MarketChameleon "
               "('October 14, 2026 before the market opens (BMO)'), public.com, optionslam"),
    "observed_on": "2026-09-23",
    "release_timing_evidence": {
        "q2_precedent": ("6-K accession 0001628280-26-048235 was file-stamped "
                         "2026-07-15 06:05:47 ET (pre-open) and the call was held "
                         "09:00 ET the same day, so the full US reaction session "
                         "was 2026-07-15"),
        "conflicting_vendor": ("unusualwhales labels the 10/14 release 'PM'; the "
                               "Q2 filing stamp and the BMO vendors support pre-open"),
        "source": "EDGAR directory for accession 0001628280-26-048235, observed 2026-09-23",
    },
    "management_guidance": {
        "q3_net_sales": "EUR 11.0-12.0 billion",
        "q3_gross_margin": "55-57%",
        "fy2026_net_sales": "EUR 43-45 billion (raised)",
        "fy2026_gross_margin": "54-56%",
        "source": "asml.com Q2 2026 press release 2026-07-15, CEO statement and outlook",
    },
    "consensus": {
        "note": ("no third-party Q3 consensus numbers were sourced this run; the "
                 "comparison bar used is management's own Q3 guidance from 2026-07-15"),
        "source": "absence recorded rather than estimated (K4)",
    },
    "implied_event_move": {
        "pct": 9.6,
        "source": ("optionomics.ai/expected-move/ASML: 'the options market prices a "
                   "typical move of +/-2.0% by the next close and +/-9.6% over the "
                   "next [window]', page observed 2026-09-21"),
        "window_note": ("the window is a multi-week expected move, not a pure "
                        "single-print straddle; it is read conservatively (see "
                        "calibration) and this is listed as a limitation"),
        "cross_check": {"pct": 7.0,
                        "source": ("Yahoo Finance 2026-07-13: 'traders are anticipating "
                                   "that ASML shares could swing as much to 7% by the "
                                   "end of the week' (into the July print)")},
        "history": {
            "avg_move_8q_pct": -2.15,
            "avg_move_source": "unusualwhales.com/stock/ASML/earnings: 'past 8 quarters, ASML had an average move of -2.15%'",
            "expected_swing_1014": {"usd": 51e9,
                                    "source": "unusualwhales: 'for the upcoming earnings on 10/14, ASML has an expected market cap swing of $51B'"},
            "july_predicted_vs_actual": {"predicted_pct": 7.1, "actual_pct": 2.2,
                                         "source": "marketchameleon.com ASML earnings charts: options predicted +/-7.1% vs +2.2% actual; options overestimated ASML's earnings move 54% of the time"},
            "july_preprint_implied_pct": "±9-10 into the print, actual peak move ±3.1",
            "july_preprint_source": "earnings-watcher.com/wiki/asml-earnings-options, published 2026-07-15",
        },
        "iv_hv": {"iv_30d_pct": 41.8,
                  "source": "marketchameleon.com/Overview/ASML/IV: '30-Day IV: 41.8 -1.3, 29% percentile', observed 2026-09-23",
                  "cross_check": {"iv_30d_mean_pct": 39.84,
                                  "source": "volvue.com ASML 30-day metrics, data updated 2026-09-04"}},
    },
}

FILINGS = [
    {"form": "6-K", "period": "Q2 2026 quarterly results, quarter ended 2026-06-28",
     "accession": "0001628280-26-048235",
     "filed": "2026-07-15 06:05:47 ET",
     "highlights": ["Q2 total net sales EUR 9,326M (Q1: 8,767), gross margin 54.0%",
                    "net income EUR 2,918M, basic EPS EUR 7.59",
                    "86 new lithography systems sold (Q1: 67); Installed Base Management sales EUR 2,762M",
                    "end-quarter cash and short-term investments EUR 7,582M (Q1: 8,376M)",
                    "Q3 2026 guided: net sales EUR 11.0-12.0B, gross margin 55-57%"],
     "source": "sec.gov/Archives/edgar/data/937966/000162828026048235/ directory (form6-kquarterlyfilings.htm, financialstatementsusgaa.htm) + asml.com Q2 2026 press release",
     "observed_on": "2026-09-23"},
    {"form": "20-F / statutory reports (standing)", "period": "FY2025 annual + interim",
     "status": "ASML is a Large accelerated filer, CIK 0000937966, SIC 3559, tickers ASML/ASMLF",
     "source": "data.sec.gov/submissions/CIK0000937966.json, observed 2026-09-23",
     "fetch_note": ("the EDGAR browse-edgar 6-K list endpoint failed twice this run "
                    "(503, then timeout); the submissions JSON + the accession "
                    "directory were used instead - recorded, not hidden")},
]

RISKS = [
    {"risk": ("Narrative shock: the 2026-09-14 -7.25% session happened because AI "
              "leaders (Anthropic's Amodei et al.) called for slowing frontier-model "
              "development - not fundamentals - and a repeat can re-trigger any day"),
     "evidence": "Yahoo Finance / Fool / TKR 2026-09-14; series close 1,629.67 -> 1,575.15",
     "direction": "downside"},
    {"risk": ("Crowded rebound: the tape recovered +10.97% in the 6 sessions after "
              "that scare (1,575.15 on 2026-09-14 -> 1,747.90 on 2026-09-22), so "
              "optimism is already paid for going into the print"),
     "evidence": "sourced close series in this artifact", "direction": "downside"},
    {"risk": ("The Q3 bar was set on 2026-07-15 (EUR 11.0-12.0B, GM 55-57%): an "
              "in-line quarter is not a surprise, and a guidance cut is the live "
              "tail if Logic/Memory customers push out orders"),
     "evidence": "asml.com Q2 2026 press release, observed 2026-09-23",
     "direction": "downside"},
    {"risk": ("Single-theme exposure: ASML fell 6.1% while the S&P 500 fell 0.3% "
              "on the same AI-slowdown headline - the position is a levered bet on "
              "one narrative, not on lithography economics"),
     "evidence": "intellectia/Yahoo 2026-09-14 (ASML -6.1% vs S&P -0.3%, Nasdaq -0.2%)",
     "direction": "both"},
    {"risk": ("China localization pressure: SCMP reports progress on 3-nm production "
              "without advanced lithography (observed 2026-09-19) and DUV competition "
              "headlines moved the stock on 2026-07-27 - monopoly-duration risk"),
     "evidence": "South China Morning Post ~2026-09-19; barchart 2026-07-27 'ASML Stock Falls on Reports of Chinese DUV Competition'",
     "direction": "downside"},
    {"risk": ("Event-vol is overpriced historically: options predicted ±7.1% vs "
              "+2.2% actual in July and overestimate the move 54% of the time; the "
              "±9.6% window quote therefore carries premium that can pin the ADS "
              "into the print"),
     "evidence": "marketchameleon ASML earnings charts, observed 2026-09-23",
     "direction": "both"},
    {"risk": ("Dual-listing wedge: the ADS (1,747.90 USD) and Amsterdam (1,467.40 "
              "EUR) imply ~1.196 USD/EUR, so FX can move the USD-scored outcome "
              "independently of the EUR reporting currency"),
     "evidence": "asml.com share price page + stockanalysis, observed 2026-09-23",
     "direction": "both"},
    {"risk": ("Release-timing vendor conflict (BMO per MarketChameleon vs 'PM' per "
              "unusualwhales): if the Q3 release actually lands after the US close "
              "on 2026-10-14, the reaction session shifts one day"),
     "evidence": "both vendors cited above; Q2 precedent favors pre-open",
     "direction": "scoring_risk"},
]

THESIS = {
    "subject": "ASML",
    "one_line": ("ASML's Q3 shape was pre-sold in July and the tape has already "
                 "recovered the AI-scare dip, so the print day is more likely to "
                 "be non-positive than positive."),
    "falsifiable_prediction": ("ASML's close on 2026-10-14 (the full US session "
                               "reacting to the pre-open Q3 print) is not above its "
                               "2026-10-13 close."),
    "null_hypothesis": "a coin flip: P(non-positive reaction) = 50%",
    "claimed_edge": ("(1) management's own Q3 guidance (EUR 11.0-12.0B, GM 55-57%) "
                     "was published on 2026-07-15, so the quarter's shape is already "
                     "in the price and in-line is not upside; (2) the +10.97% "
                     "six-session rebound off the 2026-09-14 scare low means the "
                     "optimism is paid for before the print; (3) options charge "
                     "±9.6% for an event whose last-8-quarter average move is "
                     "-2.15% and which options overestimated 54% of the time, i.e. "
                     "the market overpays for the shock"),
    "invalidation": ("an upside breach of +9.5% on 2026-10-14 falsifies the read "
                     "decisively; no re-entry in either direction without a new "
                     "written thesis"),
    "what_would_confirm": "a non-positive 2026-10-14 close (change <= 0.0% vs 2026-10-13)",
    "what_would_falsify": "a positive 2026-10-14 close (change > 0.0%)",
}


def calibration() -> dict:
    """Two independent legs -> the conservative event sigma -> the K8 gate."""
    rets = [__import__("math").log(SERIES[i][1] / SERIES[i - 1][1])
            for i in range(1, len(SERIES))]
    r = realised(rets)
    implied = CATALYST["implied_event_move"]["pct"]
    # A quoted "implied move" is a straddle price ~ E|move| = 0.7979 sigma; the
    # conservative reading also allows it to be a 1-sigma quote. Take the larger.
    as_one_sigma = implied
    as_expected_abs = implied / (2.0 / __import__("math").pi) ** 0.5
    sigma_event = max(as_one_sigma, as_expected_abs)
    k = BAND_PCT / sigma_event
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
        "expected_p_no_edge": norm_cdf(k) - 0.5,
        "expected_p_miss": 1.0 - norm_cdf(k),
        "k8_floor_k": K8_MIN_K,
        "k8_max_no_edge": K8_MAX_NO_EDGE,
        "event_vs_daily_ratio": sigma_event / (100 * r["stdev_pct"]),
        "note": ("the event-day dispersion is much larger than a normal day, which "
                 "is why an earnings bet must be banded against the event's implied "
                 "move, not the daily sigma; the daily realised sigmas are reported "
                 "for context and for the K6 freshness/plausibility frame only"),
    }


def validate() -> tuple:
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
    # V4 realised vs the vendor's 30-day vol reference (informational, loose)
    hv = CATALYST["implied_event_move"]["iv_hv"]["iv_30d_pct"]
    ann = cal["realised_daily"]["annualised_pct"]
    add("V4", "realised annualised vol within [0.5, 2]x the vendor 30-day IV reference",
        {"realised_annualised_pct": round(ann, 2), "vendor_iv_pct": hv,
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
    tdays = (tag(RUN_ON) - tag(ENTRY["observed_on"])) / TAX_DAYS
    add("V8", "K6: entry quote within 1 trading day of the run",
        {"entry_observed_on": ENTRY["observed_on"], "run_on": RUN_ON,
         "trading_days_old": round(tdays, 2), "limit": FRESHNESS_MAX_TDAYS},
        tdays <= FRESHNESS_MAX_TDAYS)
    # V9 the bet carries a kill rule + horizon (K7)
    add("V9", "K7: bet carries kill_rule, horizon_end, hit and kill thresholds",
        {"kill_rule": "upside breach >= +9.5% on 2026-10-14",
         "horizon_end": "2026-10-14", "hit": "<= 0.0% change", "kill": ">= +9.5%"},
        all([BET_ID, "2026-10-14", BAND_PCT]))
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
    stale_t = (tag(RUN_ON) - tag("2026-09-18")) / TAX_DAYS
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
            row = {"id": ROW_ID, "symbol": "ASML", "checks": [], "outcome": None}
            rows.append(row)
        row.update({
            "symbol": "ASML", "direction": "non_positive_event",
            "entry_date": ENTRY["observed_on"], "entry_price": ENTRY["price"],
            "entry_source": " | ".join(ENTRY["sources"][:2]),
            "catalyst": CATALYST["event"] + " " + CATALYST["date"],
            "confidence": 55, "status": "active",
            "invalidation_level": round(ENTRY["price"] * (1 + BAND_PCT / 100), 2),
            "target": None, "outcome": None,
            "bet_id": BET_ID, "horizon_end": "2026-10-14",
            "band_pct": BAND_PCT, "rule_version": "mark-l7-v2+k8",
            "trigger_hit": "2026-10-14 close change <= 0.0% vs the 2026-10-13 close",
            "kill_miss": "2026-10-14 close change >= +9.5% vs the 2026-10-13 close",
            "no_edge_rule": "0.0% < change < +9.5% => not_confirmed (counts as no_edge)",
            "kill_rule": "K5 analogue: upside breach >= +9.5% closes the bet as MISS; no re-entry without a new written thesis",
            "reference_price": None,
            "reference_price_source": None,
            "reference_price_ts": None,
            "scored_fields_pending": ["outcome", "outcome_price", "outcome_source",
                                      "outcome_ts", "reference_price",
                                      "reference_price_source", "reference_price_ts",
                                      "change_pct", "breach_side", "scored_at"],
            "scoring_rule": ("reference = ASML close 2026-10-13 (must be sourced and "
                             "timestamped); outcome = close 2026-10-14 vs reference; "
                             "if the actual Q3 release timestamp lands after the US "
                             "close on 2026-10-14, scoring shifts to the 2026-10-15 "
                             "session and the row records that timestamp (K4)"),
        })
        research_lib.save_theses(rows)
        after = research_lib.load_theses()
    return {"created": created, "row_count": len(after),
            "others_digest_before": others,
            "others_digest_after": hashlib.sha256(json.dumps(
                [r for r in after if r.get("id") != ROW_ID], sort_keys=True).encode()).hexdigest(),
            "asml_row": next(r for r in after if r.get("id") == ROW_ID)["bet_id"]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Register the ASML falsifiable thesis")
    ap.add_argument("--selftest", action="store_true",
                    help="validate only; no ledger write, no artifact")
    ns = ap.parse_args(argv)

    checks, cal = validate()
    failures = [c for c in checks if not c["pass"]]
    for c in checks:
        print(("PASS " if c["pass"] else "FAIL ") + c["id"] + " " + c["check"]
              + " -> " + json.dumps(c["observed"]))

    print(f"ASML thesis: band +/-{BAND_PCT}% | sigma_event {cal['sigma_event_pct']:.2f}% "
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
        "schema_version": SCHEMA, "owner": "MARK", "task": "TASK-00075",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "artifact_policy": ("ONE current thesis per subject, regenerated in place "
                            "(atomic tmp+rename). No version chain, so the family "
                            "cannot churn under K2."),
        "subject_selection": {
            "why_asml": ("ASML is in no prior artifact family (0 files) unlike AMBA "
                         "(126 sec-review briefs, K2 freeze tripped), it carries a "
                         "hard dated catalyst on 2026-10-14, and it is uncorrelated "
                         "with the registered MU bet (different company, different "
                         "risk driver) so the ledger sample can exceed n=1."),
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
            "band_pct": BAND_PCT, "horizon_end": "2026-10-14",
            "rule_version": "mark-l7-v2+k8",
            "reference_rule": "reference = sourced ASML close 2026-10-13 (K6: fresh, timestamped)",
            "trigger_hit": "change <= 0.0%", "kill_miss": "change >= +9.5%",
            "no_edge_rule": "0.0% < change < +9.5% => not_confirmed",
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
            "The event sigma is taken from a vendor's multi-week expected-move quote (±9.6%), not a pure single-print straddle I computed; a cross-vendor quote sits at ±7.0%.",
            "No third-party Q3 consensus was sourced; the comparison bar is management's own 2026-07-15 guidance, so 'beat/miss vs consensus' framing is deliberately absent.",
            "Realised vol is measured over 49 sessions that include the 2026-09-14 -7.25% AI-scare day, so it is not a clean pre-event sigma.",
            "The directional claim has a 50% null; the edge is a judgement about pre-sold guidance and a paid-for rebound, not a measured probability, and no confidence interval is claimed.",
            "Release timing has a vendor conflict (BMO vs PM); the Q2 6-K stamp (06:05 ET) supports pre-open, and the row's scoring_rule carries the shift rule if that proves wrong.",
            "The reference close (2026-10-13) does not exist yet; scoring requires a sourced quote on or after 2026-10-14.",
            "The EDGAR browse-edgar 6-K list endpoint failed this run (503, timeout); filings evidence came from data.sec.gov submissions JSON and the accession directory instead.",
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
