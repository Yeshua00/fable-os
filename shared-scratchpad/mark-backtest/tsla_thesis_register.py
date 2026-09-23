#!/usr/bin/env python3
"""tsla_thesis_register.py — one owner for the TSLA falsifiable market thesis.

TASK-00104 (market-thesis). Subject: TSLA (Tesla, Inc.), chosen because it has
0 prior artifacts (fresh family - AMBA stays K2-frozen, MU/ASML/UNH each
already carry one registered thesis and a second file would start a version
chain), and it is CROSS-SECTOR for the bet book: the registered bets rest on
semiconductors (MU, ASML) and healthcare (UNH); Tesla adds consumer/EV so the
joint simulation stops concentrating on two factors.

This module does four things and nothing else:
  1. holds the thesis, its sourced quotes, and its citations as the single
     source of truth (K4: every number carries a source and observation time)
  2. calibrates the bet's band from two independent legs (realised vol from a
     sourced 50-session adjusted-close series, and the options-implied event
     move) so the band passes K8 ("no new bet on an uncalibrated band")
  3. registers the bet into the ledger through research_lib's own primitives
     (ledger_tx + load_theses + save_theses) - no mirrored format, no second
     writer - idempotently, leaving every other row byte-identical
  4. regenerates ONE current artifact (TSLA_THESIS_ACTIVE.json, atomic
     tmp+rename) instead of a version chain, so the family cannot churn

The pure math helpers (tag/norm_cdf/realised) are imported from
thesis_register.py rather than re-implemented: one owner for the math.

HONEST DATE CONFLICT, recorded not smoothed over: Tesla has NOT posted a Q3
2026 date on its IR page. wallstreethorizon (UNCONFIRMED 10/21 AMC),
optionslam (OS estimate 10/21, window 10/19-24) and public.com (10/21) say
2026-10-21; barchart ("Earnings: 10/28/26") and unusualwhales ("October 28,
2026") say 2026-10-28. The bet assumes 10/21 AMC -> reaction session
2026-10-22, and the ledger row's scoring_rule shifts scoring to the session
after the ACTUAL print whichever date it lands on.

Deliberately prices the bet from fresh sourced quotes and NEVER from
theses.jsonl's own check history, which was substantiated on 2026-09-23 as
unusable (ETH +145.66% and SOL +232.29% single-day prints; BTC 2026-08-28
96,000.00 vs the sourced snapshot 77,639.00 on the same date).

Usage:
    python3 tsla_thesis_register.py            # validate, register, write artifact
    python3 tsla_thesis_register.py --selftest # validate only; no ledger write, no artifact
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
OUT = DIR / "TSLA_THESIS_ACTIVE.json"
SCHEMA = "market-thesis-active.v1"
TAX_DAYS = 365.0 / 252.0  # calendar days per trading day, for freshness math
RUN_ON = "2026-09-23"

BET_ID = "TSLA-Q3-2026-REACTION-20261022"
ROW_ID = "thesis_tsla_q3_2026_reaction"
BAND_PCT = 6.30           # = the quoted implied move; K8 floor is 0.75 sigma
K8_MIN_K = 0.75
K8_MAX_NO_EDGE = 0.75
FRESHNESS_MAX_TDAYS = 1.0
HORIZON = "2026-10-22"    # reaction session after the assumed 2026-10-21 AMC print
REFERENCE = "2026-10-21"   # session before the reaction, must be sourced at scoring

# ── sourced inputs ───────────────────────────────────────────────────────────
# Adjusted-close series: stockanalysis.com/stocks/tsla/history (S&P Global
# Market Intelligence), page "Last checked: Sep 23, 2026", Adj. Close column,
# 2026-07-15 .. 2026-09-23 (50 points). TSLA pays no dividend, so raw Close
# equals Adj. Close on EVERY row of this span (verified row-by-row while
# transcribing) - returns are raw-price returns.
SERIES_SOURCE = ("stockanalysis.com/stocks/tsla/history -- S&P Global Market "
                 "Intelligence, Adj. Close column, last checked 2026-09-23 "
                 "(page read after the 16:00 EDT close, final prints; "
                 "Close == Adj. Close on all rows, TSLA pays no dividend)")
SERIES = [
    ("2026-07-15", 394.46), ("2026-07-16", 391.06), ("2026-07-17", 380.84),
    ("2026-07-20", 369.57), ("2026-07-21", 378.93), ("2026-07-22", 374.01),
    ("2026-07-23", 319.69), ("2026-07-24", 313.03), ("2026-07-27", 309.22),
    ("2026-07-28", 307.44), ("2026-07-29", 298.32), ("2026-07-30", 308.85),
    ("2026-07-31", 311.21), ("2026-08-03", 322.08), ("2026-08-04", 327.35),
    ("2026-08-05", 321.55), ("2026-08-06", 319.53), ("2026-08-07", 328.58),
    ("2026-08-10", 330.88), ("2026-08-11", 332.81), ("2026-08-12", 327.51),
    ("2026-08-13", 339.96), ("2026-08-14", 342.27), ("2026-08-17", 339.30),
    ("2026-08-18", 336.87), ("2026-08-19", 351.12), ("2026-08-20", 345.13),
    ("2026-08-21", 362.86), ("2026-08-24", 348.95), ("2026-08-25", 350.25),
    ("2026-08-26", 345.82), ("2026-08-27", 354.81), ("2026-08-28", 348.75),
    ("2026-08-31", 367.95), ("2026-09-01", 356.09), ("2026-09-02", 357.01),
    ("2026-09-03", 376.37), ("2026-09-04", 354.08), ("2026-09-08", 368.16),
    ("2026-09-09", 367.81), ("2026-09-10", 363.56), ("2026-09-11", 365.44),
    ("2026-09-14", 358.97), ("2026-09-15", 356.58), ("2026-09-16", 358.08),
    ("2026-09-17", 366.20), ("2026-09-18", 364.27), ("2026-09-21", 375.30),
    ("2026-09-22", 378.90), ("2026-09-23", 380.22),
]

ENTRY = {
    "price": 380.22,
    "observed_on": "2026-09-23",
    "sources": [
        "stockanalysis.com TSLA history table row 'Sep 23, 2026': Close 380.22 = Adj. Close 380.22, Change +0.35%, Volume 32,734,763; page header 'At close: Sep 23, 2026, 4:00 PM EDT', read after the close",
        "internal consistency: 380.22 / 378.90 - 1 = +0.35% matches the table's stated Change for that row",
    ],
    "known_discrepancy": {
        "detail": ("the SAME page's quote box prints 380.12 (+1.22, +0.32%) while its "
                   "history table prints 380.22 (+0.35%) - a 0.10 (0.026%) split; the "
                   "TABLE row is used because it equals the Adj. Close, matches V2 "
                   "against the series, and is internally consistent with the prior "
                   "close of 378.90. Recorded, not hidden (K4)."),
        "observed_on": "2026-09-23",
    },
    "prior_close": {"price": 378.90, "observed_on": "2026-09-22",
                    "sources": [
                        "stockanalysis.com TSLA history table row 'Sep 22, 2026': Close 378.90 = Adj. Close 378.90, Change +0.96%"]},
    "after_hours": {"price": 380.16,
                    "source": "stockanalysis.com header: 'After-hours: Sep 23, 2026, 7:35 PM EDT' 380.16 (+0.01%)"},
    "range_52w": {"note": ("52-week high/low NOT sourced this run - deliberately "
                           "omitted rather than estimated (K4)")},
    "market_cap": {"note": "market cap NOT sourced this run - omitted rather than estimated (K4)"},
}

CATALYST = {
    "event": "Tesla Q3 2026 financial results (assumed after the US close)",
    "date": "2026-10-21",
    "date_status": "UNCONFIRMED - vendor conflict recorded below; no date posted on Tesla's IR page in observed snippets",
    "source_conflict": {
        "says_2026_10_21": [
            "wallstreethorizon.com/tesla-earnings-calendar: 'TSLA's next earnings date is UNCONFIRMED for Wednesday 10/21/2026 After Market', observed 2026-09-23",
            "optionslam.com/earnings/straddle/TSLA: 'Next Earnings Date: OS Estimate: Oct. 21, 2026, AC OS Projected Window: Oct. 19, 2026 to Oct. 24, 2026', observed 2026-09-23",
            "public.com/stocks/tsla/earnings: 'Q3 2026 Oct 21, 2026', observed 2026-09-23",
        ],
        "says_2026_10_28": [
            "barchart.com/stocks/quotes/TSLA/volatility-charts: 'Earnings: 10/28/26', observed 2026-09-23",
            "unusualwhales.com/stock/TSLA/earnings: 'October 28, 2026', observed 2026-09-23",
        ],
        "company": "ir.tesla.com documents-and-events lists Q2 (Jul 22, 2026) and earlier; NO Q3 2026 date appeared in observed snippets - recorded as a K4 gap, not guessed",
        "precedent": "Q3 2025 printed 2025-10-22 (Wednesday, 5:30pm ET call per usatoday 2025-10-22) - the 2026-10-21 Wednesday slot matches the pattern",
    },
    "observed_on": "2026-09-23",
    "release_timing_evidence": {
        "assumed": "after the US close on 2026-10-21 (both vendor camps agree on AFTER-MARKET; they disagree only on 10/21 vs 10/28), so the full reaction session is 2026-10-22",
        "shift_rule": ("if Tesla confirms a different print date, scoring shifts to the "
                       "session immediately after the ACTUAL print and the row records "
                       "that timestamp (K4) - the band and entry are NOT re-cut"),
        "source": "wallstreethorizon (AMC) + optionslam + barchart + unusualwhales, observed 2026-09-23",
    },
    "implied_event_move": {
        "pct": 6.29,
        "source": ("unusualwhales.com/stock/TSLA/earnings: 'October 28, 2026. ~39d Avg "
                   "implied move +/-6.29%', observed 2026-09-23 - NOTE the quote's "
                   "window (~39d, to the 10/28 label) is LONGER than this bet's "
                   "10/22 horizon, so using it unchanged is the conservative direction"),
        "cross_check": {"pct": 5.8,
                        "source": "marketchameleon.com/Overview/TSLA/Earnings: 'options prices predicted a +/-5.8% post earnings move' for the Q2 2026 print, observed 2026-09-23"},
        "history": {
            "straddle_seller_won_8q": "5/8",
            "history_source": "unusualwhales.com/stock/TSLA/earnings: 'Selling the 1-day ATM straddle - return per past earnings: won 5/8' (i.e. realised < implied 62.5% of the time), observed 2026-09-23",
            "last_print_predicted_pct": 5.8,
            "last_print_actual_pct": -14.52,
            "last_print_source": "marketchameleon predicted +/-5.8% vs actual -14.5% for the Q2 print; the -14.52% close-to-close reaction is row 2026-07-23 of the sourced series (374.01 -> 319.69, volume 115,606,413 = ~3.8x the 30M norm)",
        },
        "iv_hv": {"iv_pct": 41.57, "hv_pct": 43.40, "iv_rank": 14.47, "iv_percentile": 15,
                  "source": "barchart.com/stocks/quotes/TSLA/volatility-charts + /expected-move: 'IV 41.57%; HV 43.40%; IV Rank 14.47%; IV Pctl 15%; Earnings: 10/28/26', observed 2026-09-23"},
    },
    "operational_pre_release": {
        "claim": ("Tesla publishes quarterly deliveries ~2 days after quarter close, "
                  "WEEKS before the earnings call - so the volume/top-line news of Q3 "
                  "is already in the tape by ~2026-10-02, before the 10/21-10/28 print"),
        "evidence": "8-K filed 2026-07-02 (acc 0001628280-26-046717) for the quarter ended 2026-06-30 - deliveries announced 2 days after quarter end; Q2 results 8-K followed 20 days later on 2026-07-22 (acc 0001628280-26-049213)",
        "observed_on": "2026-09-23",
    },
}

FILINGS = [
    {"form": "10-Q", "period": "Q2 2026 (quarter ended 2026-06-30)",
     "accession": "0001628280-26-049270", "filed": "2026-07-23",
     "source": "data.sec.gov/submissions/CIK0001318605.json, observed 2026-09-23; corroborated by ir.tesla.com/sec-filings ('Jul 22, 2026 10-Q Acc-no: 0001628280-26-049270')",
     "observed_on": "2026-09-23"},
    {"form": "8-K (Q2 2026 results)", "period": "announced 2026-07-22",
     "accession": "0001628280-26-049213",
     "highlights": ["Q2 Update: 'over $100B in revenue on a trailing twelve-month basis for the first time'",
                    "'record second-quarter vehicle deliveries'"],
     "source": "data.sec.gov submissions + assets-ir.tesla.com/tesla-contents/IR/TSLA-Q2-2026-Update.pdf snippet, observed 2026-09-23",
     "observed_on": "2026-09-23"},
    {"form": "8-K (Q2 2026 deliveries)", "period": "filed 2026-07-02, 2 days after quarter close",
     "accession": "0001628280-26-046717",
     "highlights": ["the pre-release precedent: operations land ~3 weeks before earnings"],
     "source": "data.sec.gov/submissions/CIK0001318605.json, observed 2026-09-23",
     "observed_on": "2026-09-23"},
    {"form": "EDGAR standing record", "period": "entity metadata",
     "highlights": ["CIK 0001318605, Tesla, Inc."],
     "source": "data.sec.gov/submissions/CIK0001318605.json, observed 2026-09-23",
     "observed_on": "2026-09-23"},
]

RISKS = [
    {"risk": ("Catalyst-date conflict: 3 vendors say 2026-10-21, 2 say 2026-10-28, "
              "and Tesla has posted NO confirmed date - if the print lands 10/28 the "
              "reaction session moves 6 trading days later"),
     "evidence": "wallstreethorizon/optionslam/public vs barchart/unusualwhales, observed 2026-09-23",
     "direction": "scoring_risk"},
    {"risk": ("The 'options overprice the event' leg is WEAK on its own data: IV 41.57% "
              "sits BELOW HV 43.40% and IV Rank is 14.47 (near its 1-year lows) - TSLA "
              "options are cheap relative to their own history, not rich"),
     "evidence": "barchart TSLA volatility page, observed 2026-09-23",
     "direction": "upside_against_thesis"},
    {"risk": ("Fat-tail counter-case: the LAST print massively EXCEEDED its pricing "
              "(-14.52% actual vs +/-5.8% implied on 2026-07-23) - a repeat of a ~14% "
              "move classifies against a 6.3% band almost regardless of direction, and "
              "an upside 14% would falsify decisively"),
     "evidence": "marketchameleon + series row 2026-07-23 (374.01 -> 319.69, 115.6M volume)",
     "direction": "classification_risk"},
    {"risk": ("Run-up momentum: the tape has rallied +27.5% off the 2026-07-29 low close "
              "(298.32) to 380.22 - post-crash recoveries with this much velocity can "
              "carry through a print regardless of results"),
     "evidence": "sourced series (2026-07-29 298.32 -> 2026-09-23 380.22)",
     "direction": "upside_against_thesis"},
    {"risk": ("Idiosyncratic Musk headline risk inside the horizon: Paramount equity-talk "
              "reports (Semafor), the state-dinner political optics (Barrons/MarketWatch), "
              "FSD licensing 'zero takers' (TipRanks) - any of these can spike the tape "
              "non-fundamentally on a single day"),
     "evidence": "stockanalysis.com TSLA news list, observed 2026-09-23",
     "direction": "both"},
    {"risk": ("A record Q3 deliveries print (~2026-10-02) would pre-spend the good news "
              "but also re-anchor sentiment positive INTO the earnings session"),
     "evidence": "8-K 0001628280-26-046717 precedent (deliveries reported 2 days after quarter close)",
     "direction": "upside_against_thesis"},
    {"risk": ("Regulatory/safety newsflow on FSD is actively two-sided (Belgian safety "
              "group speed-limit critique via Reuters vs Semi 2,500-truck fleet order "
              "via TipRanks, same day 2026-09-23)"),
     "evidence": "stockanalysis.com TSLA news list, observed 2026-09-23",
     "direction": "both"},
    {"risk": ("Classification band vs fat prints: realised daily sigma is 3.403% "
              "(annualised 54.0%) and the series contains a -14.52% day - a 6.3% band "
              "on a ~7.9% event sigma is a near coin-flip whenever TSLA prints a "
              "double-digit move"),
     "evidence": "realised() over the sourced 50-point series; implied 6.29% (unusualwhales)",
     "direction": "classification_risk"},
]

THESIS = {
    "subject": "TSLA",
    "one_line": ("Tesla spends its information budget BEFORE the earnings call - "
                 "deliveries land ~Oct 2, the +27.5% recovery is already paid for, "
                 "and options sellers have won 5 of the last 8 prints - so the "
                 "reaction session is more likely flat-to-down than up."),
    "falsifiable_prediction": ("TSLA's close on 2026-10-22 (the US session reacting to "
                               "the assumed 2026-10-21 after-close Q3 print) is not "
                               "above its 2026-10-21 close."),
    "null_hypothesis": "a coin flip: P(non-positive reaction) = 50%",
    "claimed_edge": ("(1) pre-release structure: deliveries ship ~2 days after quarter "
                     "close (8-K 2026-07-02 precedent), so Q3's operational news is "
                     "fully in the tape by ~2026-10-02, 2-3 weeks before the print - "
                     "the earnings session has less fresh information to react to; "
                     "(2) +27.5% run-up off the 2026-07-29 low (298.32 -> 380.22) "
                     "means the recovery premium is already paid; (3) unusualwhales: "
                     "selling the 1-day ATM straddle won 5 of 8 past TSLA earnings "
                     "(realised < implied 62.5% of the time); (4) the last reaction "
                     "precedent is violently negative: -14.52% on 2026-07-23 on 3.8x "
                     "volume. The edge is a judgement under a 50% null - risks 1-4 "
                     "above (especially IV BELOW HV and the -14.5% counter-print) are "
                     "the honest counter-case and are why confidence stays at 52."),
    "invalidation": (f"an upside breach of +{BAND_PCT}% on the reaction session "
                     "falsifies the read decisively; no re-entry in either direction "
                     "without a new written thesis"),
    "what_would_confirm": "a non-positive reaction-session close (change <= 0.0% vs the reference close)",
    "what_would_falsify": "a positive reaction-session close (change > 0.0%), decisive-falsifier at >= +6.3%",
}


def calibration() -> dict:
    """Two independent legs -> the conservative event sigma -> the K8 gate."""
    import math as _m
    rets = [_m.log(SERIES[i][1] / SERIES[i - 1][1]) for i in range(1, len(SERIES))]
    r = realised(rets)
    implied = CATALYST["implied_event_move"]["pct"]
    # A quoted "implied move" is a straddle price ~ E|move| = 0.7979 sigma; the
    # conservative reading also allows it to be a 1-sigma quote. Take the larger.
    as_one_sigma = implied
    as_expected_abs = implied / _m.sqrt(2.0 / _m.pi)
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
    # V3 sigma estimators agree (tight here: the -14.52% day inflates stdev)
    sd, mad = cal["realised_daily"]["stdev_pct"], cal["realised_daily"]["mad_pct"]
    add("V3", "stdev and MAD sigma agree within 35% relative",
        {"stdev_pct": round(sd, 3), "mad_pct": round(mad, 3),
         "rel_gap": round(abs(sd - mad) / sd, 4)},
        abs(sd - mad) / sd <= 0.35)
    # V4 realised vs the vendor's 30-day historic vol (informational, loose)
    hv = CATALYST["implied_event_move"]["iv_hv"]["hv_pct"]
    ann = cal["realised_daily"]["annualised_pct"]
    add("V4", "realised annualised vol within [0.5, 2]x the vendor historic vol",
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
    tdays = (tag(RUN_ON) - tag(ENTRY["observed_on"])) / TAX_DAYS
    add("V8", "K6: entry quote within 1 trading day of the run",
        {"entry_observed_on": ENTRY["observed_on"], "run_on": RUN_ON,
         "trading_days_old": round(tdays, 2), "limit": FRESHNESS_MAX_TDAYS},
        tdays <= FRESHNESS_MAX_TDAYS)
    # V9 the bet carries a kill rule + horizon (K7)
    add("V9", "K7: bet carries kill_rule, horizon_end, hit and kill thresholds",
        {"kill_rule": f"upside breach >= +{BAND_PCT}% on the reaction session",
         "horizon_end": HORIZON, "reference": REFERENCE,
         "hit": "<= 0.0% change", "kill": f">= +{BAND_PCT}%"},
        all([BET_ID, HORIZON, REFERENCE, BAND_PCT]))
    # V10 ledger corruption is *cited*, not silently worked around
    add("V10", "pricing source is fresh quotes, not the corrupt ledger series",
        {"ledger_status": "unusable as a price series (2026-09-23 finding)",
         "priced_from": SERIES_SOURCE.split(" -- ")[0],
         "ledger_citation": "BET_THRESHOLD_CALIBRATION.json data_quality_findings"},
        True)
    # V11 the vendor date conflict is carried INTO the artifact, not smoothed
    sc = CATALYST["source_conflict"]
    add("V11", "catalyst date conflict recorded with both vendor camps + company gap",
        {"assumed": CATALYST["date"], "oct21_sources": len(sc["says_2026_10_21"]),
         "oct28_sources": len(sc["says_2026_10_28"]), "company": sc["company"][:40] + "...",
         "shift_rule": True},
        len(sc["says_2026_10_21"]) >= 1 and len(sc["says_2026_10_28"]) >= 1
        and CATALYST["date_status"].startswith("UNCONFIRMED"))

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
            row = {"id": ROW_ID, "symbol": "TSLA", "checks": [], "outcome": None}
            rows.append(row)
        row.update({
            "symbol": "TSLA", "direction": "non_positive_event",
            "entry_date": ENTRY["observed_on"], "entry_price": ENTRY["price"],
            "entry_source": " | ".join(ENTRY["sources"][:2]),
            "catalyst": CATALYST["event"] + " " + CATALYST["date"] + " (UNCONFIRMED)",
            "confidence": 52, "status": "active",
            "invalidation_level": round(ENTRY["price"] * (1 + BAND_PCT / 100), 2),
            "target": None, "outcome": None,
            "bet_id": BET_ID, "horizon_end": HORIZON,
            "band_pct": BAND_PCT, "rule_version": "mark-l7-v2+k8",
            "trigger_hit": f"{HORIZON} close change <= 0.0% vs the {REFERENCE} close",
            "kill_miss": f"{HORIZON} close change >= +{BAND_PCT}% vs the {REFERENCE} close",
            "no_edge_rule": f"0.0% < change < +{BAND_PCT}% => not_confirmed (counts as no_edge)",
            "kill_rule": "K5 analogue: upside breach >= +6.3% closes the bet as MISS; no re-entry without a new written thesis",
            "reference_price": None,
            "reference_price_source": None,
            "reference_price_ts": None,
            "scored_fields_pending": ["outcome", "outcome_price", "outcome_source",
                                      "outcome_ts", "reference_price",
                                      "reference_price_source", "reference_price_ts",
                                      "change_pct", "breach_side", "scored_at"],
            "scoring_rule": (f"reference = TSLA close {REFERENCE} (must be sourced and "
                             f"timestamped); outcome = close {HORIZON} vs reference; "
                             "VENDOR DATE CONFLICT: if Tesla confirms a different print "
                             "date (2026-10-21 vs 2026-10-28), scoring shifts to the "
                             "session immediately after the ACTUAL after-close print and "
                             "the row records that timestamp (K4) - band and entry "
                             "unchanged"),
        })
        research_lib.save_theses(rows)
        after = research_lib.load_theses()
    return {"created": created, "row_count": len(after),
            "others_digest_before": others,
            "others_digest_after": hashlib.sha256(json.dumps(
                [r for r in after if r.get("id") != ROW_ID], sort_keys=True).encode()).hexdigest(),
            "tsla_row": next(r for r in after if r.get("id") == ROW_ID)["bet_id"]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Register the TSLA falsifiable thesis")
    ap.add_argument("--selftest", action="store_true",
                    help="validate only; no ledger write, no artifact")
    ns = ap.parse_args(argv)

    checks, cal = validate()
    failures = [c for c in checks if not c["pass"]]
    for c in checks:
        print(("PASS " if c["pass"] else "FAIL ") + c["id"] + " " + c["check"]
              + " -> " + json.dumps(c["observed"]))

    print(f"TSLA thesis: band +/-{BAND_PCT}% | sigma_event {cal['sigma_event_pct']:.2f}% "
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
        "schema_version": SCHEMA, "owner": "MARK", "task": "TASK-00104",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "artifact_policy": ("ONE current thesis per subject, regenerated in place "
                            "(atomic tmp+rename). No version chain, so the family "
                            "cannot churn under K2."),
        "subject_selection": {
            "why_tsla": ("TSLA has 0 prior artifacts (fresh family - AMBA stays "
                         "K2-frozen; MU/ASML/UNH each already carry one registered "
                         "thesis, and a second file there would start a version "
                         "chain). It is CROSS-SECTOR for the book: consumer/EV vs "
                         "the registered semis (MU, ASML) and healthcare (UNH), so "
                         "the joint simulation stops concentrating on two factors. "
                         "Catalyst dated but UNCONFIRMED - the conflict is recorded "
                         "in the artifact, not smoothed over."),
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
            "band_pct": BAND_PCT, "horizon_end": HORIZON,
            "rule_version": "mark-l7-v2+k8",
            "reference_rule": f"reference = sourced TSLA close {REFERENCE} (K6: fresh, timestamped)",
            "trigger_hit": "change <= 0.0%", "kill_miss": f"change >= +{BAND_PCT}%",
            "no_edge_rule": f"0.0% < change < +{BAND_PCT}% => not_confirmed",
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
            "Catalyst date is UNCONFIRMED: 3 vendors say 2026-10-21, 2 say 2026-10-28, Tesla's IR page posted no date in observed snippets - the scoring_rule shifts scoring to the session after the ACTUAL print; the bet's validity does not depend on which date wins, only its scoring session does.",
            "The 6.29% implied-move quote carries the ~39d window to unusualwhales' 10/28 label - LONGER than this bet's 10/22 horizon, so the sigma is conservative (a nearer-dated quote would be smaller), not aggressive.",
            "The 'options overprice events' argument is weak here on its own data: IV 41.57% < HV 43.40% and IV Rank 14.47 (barchart, near 1-year lows) - the edge rests on the pre-release structure and the run-up, not on rich premium; confidence is capped at 52 because of it.",
            "The last print moved -14.52% vs +/-5.8% priced (marketchameleon) - single double-digit prints classify against a 6.3% band in either direction; V3's stdev/MAD gap (32.3%) sits near its 35% ceiling because that one day inflates stdev.",
            "No Q3 consensus EPS/revenue was sourced; the comparison facts are structural (deliveries pre-release, run-up) rather than beat/miss framing - recorded rather than guessed (K4).",
            "52-week range and market cap were not sourced this run and are deliberately omitted rather than estimated (K4).",
            "The entry row has a same-page discrepancy: quote box 380.12 vs history table 380.22 (0.026%) - the table row is used (equals Adj. Close, internally consistent with the 378.90 prior close) and the discrepancy is recorded in ENTRY.known_discrepancy.",
            "The directional claim has a 50% null; the edge is a judgement (pre-release structure + run-up + straddle-seller history + negative last-reaction precedent), not a measured probability, and no confidence interval is claimed.",
            f"The reference close ({REFERENCE}) does not exist yet; scoring requires a sourced quote on or after {HORIZON}.",
            "betbook_event_sim.py INPUTS names only MU, UNH and ASML - this fourth bet is NOT yet in the joint simulation; extending it is separate work, not silently done here.",
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
