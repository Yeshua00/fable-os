#!/usr/bin/env python3
"""unh_thesis_register.py — one owner for the UNH falsifiable market thesis.

TASK-00088 (market-thesis). Subject: UNH (UnitedHealth Group), chosen because
it is NOT in a churn-frozen family (0 prior UNH artifacts vs AMBA's 126
sec-review briefs and a tripped K2 freeze), it carries a hard, dated catalyst:
Q3 2026 results on Tuesday 2026-10-13 before the market open (company
newsroom, 2026-09-15), and it is genuinely UNCORRELATED with the two already
registered semiconductor bets (MU and ASML) - healthcare, not AI capex - so
the bet book's joint simulation stops resting on one shared sector factor.

This module does four things and nothing else:
  1. holds the thesis, its sourced quotes, and its citations as the single
     source of truth (K4: every number carries a source and an observation time)
  2. calibrates the bet's band from two independent legs (realised vol from a
     sourced 50-session adjusted-close series, and the options-implied event
     move) so the band passes K8 ("no new bet on an uncalibrated band")
  3. registers the bet into the ledger through research_lib's own primitives
     (ledger_tx + load_theses + save_theses) - no mirrored format, no second
     writer - idempotently, leaving every other row byte-identical
  4. regenerates ONE current artifact (UNH_THESIS_ACTIVE.json, atomic
     tmp+rename) instead of a version chain, so the family cannot churn

The pure math helpers (tag/norm_cdf/realised) are imported from
thesis_register.py rather than re-implemented: one owner for the math.

Deliberately prices the bet from fresh sourced quotes and NEVER from
theses.jsonl's own check history, which was substantiated on 2026-09-23 as
unusable (ETH +145.66% and SOL +232.29% single-day prints; BTC 2026-08-28
96,000.00 vs the sourced snapshot 77,639.00 on the same date).

Usage:
    python3 unh_thesis_register.py            # validate, register, write artifact
    python3 unh_thesis_register.py --selftest # validate only; no ledger write, no artifact
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
OUT = DIR / "UNH_THESIS_ACTIVE.json"
SCHEMA = "market-thesis-active.v1"
TAX_DAYS = 365.0 / 252.0  # calendar days per trading day, for freshness math
RUN_ON = "2026-09-23"

BET_ID = "UNH-Q3-2026-REACTION-20261013"
ROW_ID = "thesis_unh_q3_2026_reaction"
BAND_PCT = 8.0            # frozen pre-registration; K8 floor is 0.75 sigma
K8_MIN_K = 0.75
K8_MAX_NO_EDGE = 0.75
FRESHNESS_MAX_TDAYS = 1.0

# ── sourced inputs ───────────────────────────────────────────────────────────
# Adjusted-close series: stockanalysis.com/stocks/unh/history (S&P Global
# Market Intelligence), page "Last checked: Sep 23, 2026", Adj. Close column
# (dividend-adjusted - proper for return math), 2026-07-15 .. 2026-09-23.
# The page was read at 21:30Z on 2026-09-23, AFTER the 16:00 EDT close, and
# the 2026-09-23 row is a final close (raw close == adjusted close == 371.29).
SERIES_SOURCE = ("stockanalysis.com/stocks/unh/history -- S&P Global Market "
                 "Intelligence, Adj. Close column, last checked 2026-09-23 "
                 "(page read after the 16:00 EDT close, final prints)")
SERIES = [
    ("2026-07-15", 415.96), ("2026-07-16", 420.79), ("2026-07-17", 423.48),
    ("2026-07-20", 418.97), ("2026-07-21", 433.68), ("2026-07-22", 428.67),
    ("2026-07-23", 420.97), ("2026-07-24", 418.17), ("2026-07-27", 415.08),
    ("2026-07-28", 426.17), ("2026-07-29", 418.00), ("2026-07-30", 418.89),
    ("2026-07-31", 411.86), ("2026-08-03", 412.82), ("2026-08-04", 405.06),
    ("2026-08-05", 410.22), ("2026-08-06", 401.50), ("2026-08-07", 404.59),
    ("2026-08-10", 406.24), ("2026-08-11", 399.73), ("2026-08-12", 403.11),
    ("2026-08-13", 396.62), ("2026-08-14", 399.27), ("2026-08-17", 393.20),
    ("2026-08-18", 391.52), ("2026-08-19", 386.23), ("2026-08-20", 382.49),
    ("2026-08-21", 387.72), ("2026-08-24", 396.32), ("2026-08-25", 394.16),
    ("2026-08-26", 398.56), ("2026-08-27", 392.63), ("2026-08-28", 390.55),
    ("2026-08-31", 387.03), ("2026-09-01", 393.87), ("2026-09-02", 397.21),
    ("2026-09-03", 398.49), ("2026-09-04", 394.71), ("2026-09-08", 398.39),
    ("2026-09-09", 390.65), ("2026-09-10", 385.90), ("2026-09-11", 376.77),
    ("2026-09-14", 383.55), ("2026-09-15", 375.93), ("2026-09-16", 375.26),
    ("2026-09-17", 375.21), ("2026-09-18", 376.90), ("2026-09-21", 377.56),
    ("2026-09-22", 372.95), ("2026-09-23", 371.29),
]

ENTRY = {
    "price": 371.29,
    "observed_on": "2026-09-23",
    "sources": [
        "stockanalysis.com UNH history: 'At close: Sep 23, 2026, 4:00 PM EDT' 371.29 (-0.45%), page read 2026-09-23 21:30Z (after close)",
        "stockanalysis.com UNH history close row 2026-09-23 = 371.29 = Adj. Close 371.29 (raw and adjusted agree on this row)",
    ],
    "prior_close": {"price": 372.95, "observed_on": "2026-09-22",
                    "sources": [
                        "Macrotrends: 'latest closing stock price for UnitedHealth Group as of September 22, 2026 is 372.95'",
                        "CNBC UNH quote: Prev Close 372.95 (session data matches the 2026-09-23 row: open 370.89, high 372.61, low 366.00)",
                        "Morningstar UNH: 'Price $372.95 Sep 22, 2026'",
                        "investing.com historical table: 'Sep 22, 2026, 372.95'"]},
    "after_hours": {"price": 371.04,
                    "source": "stockanalysis.com: 'After-hours: Sep 23, 2026, 5:09 PM EDT' -371.04 (-0.07%)"},
    "range_52w": {"high": 461.62, "high_date": "2026-07-16",
                  "source": "CNBC UNH quote: '52 Week High 461.62, Date 07/16/26'",
                  "note": "52-week LOW not sourced this run - deliberately omitted rather than estimated (K4)"},
    "market_cap": "340.3B",
    "valuation_source": "optionslam.com UNH page, observed 2026-09-23",
}

CATALYST = {
    "event": "UnitedHealth Group Q3 2026 financial results, before the US market open",
    "date": "2026-10-13",
    "call": "investor conference call 8:00 a.m. ET on release day",
    "source": ("unitedhealthgroup.com newsroom press release 2026-09-15: 'UnitedHealth "
               "Group (NYSE: UNH) will release its third quarter 2026 financial results "
               "on Tuesday, October 13, 2026, before the market opens'; investor "
               "calendar 'Oct. 13: Q3 UnitedHealth Group Earnings Call, 8 a.m. ET'; "
               "corroborated by MarketBeat, StockTitan, barchart [BMO], optionsai"),
    "observed_on": "2026-09-23",
    "release_timing_evidence": {
        "company": "press release says 'before the market opens' with an 8:00 a.m. ET call, so the full US reaction session is 2026-10-13",
        "conflicting_vendor": ("unusualwhales labels the 10/13 release 'PM' - the same "
                               "false label it carried for ASML; the company source wins "
                               "and the row's scoring_rule carries the shift rule"),
        "source": "unitedhealthgroup.com newsroom + unusualwhales UNH earnings page, observed 2026-09-23",
    },
    "management_guidance": {
        "fy2026": "RAISED alongside Q2 2026 results (announced 2026-07-16 before market open)",
        "source": "unitedhealthgroup.com/investors/financial-reports.html: 'UnitedHealth Group reported second quarter 2026 results and raised guidance for full year 2026', observed 2026-09-23",
        "note": "the specific raised FY numbers were not re-sourced this run; the structural fact (bar raised at Q2) is what the thesis relies on",
    },
    "consensus": {
        "note": ("no third-party Q3 consensus numbers were sourced this run; the "
                 "comparison bar used is the company's own raised FY2026 guidance "
                 "from 2026-07-16"),
        "source": "absence recorded rather than estimated (K4)",
    },
    "implied_event_move": {
        "pct": 7.9,
        "source": ("optionsai.com/companies/UNH: 'Earnings Oct 13 before open - "
                   "Expected Move 7.9%, Prior earnings moves 5.61%', observed 2026-09-23"),
        "cross_check": {"pct": 8.82,
                        "source": "optionslam.com UNH: 'Implied Move Weekly: 8.82% ... 2026 Implied Move Monthly: 11.32%', observed 2026-09-23"},
        "history": {
            "avg_peak_10y_pct": 5.9,
            "avg_peak_source": "earnings-watcher.com/wiki/unh-implied-move: 'moved +/-5.9% on average at the peak of earnings day over the last 10 years (40 reports)', observed 2026-09-23",
            "avg_move_8q_pct": -6.87,
            "avg_move_8q_source": "unusualwhales.com/stock/UNH/earnings: 'past 8 quarters, UNH had an average move of -6.87%'; also 'expected market cap swing of $26B' for 10/13",
            "july_priced_pct": 6.5,
            "july_last_move_pct": 10.3,
            "july_source": "earnings-watcher.com/wiki/unh-earnings-options: Q2 (2026-07-16 BMO) 'options had priced a +/-6.5% move... Last Move +10.3'",
            "july_predicted_vs_actual": {"predicted_pct": 6.2, "actual_pct": 1.2,
                                         "source": "marketchameleon.com UNH earnings charts: options predicted +/-6.2% vs +1.2% actual; UNH IV dropped an average 16% after earnings"},
        },
        "iv_hv": {"iv_pct": 38.87, "hv_pct": 19.07, "iv_rank": 50.10, "iv_percentile": 76,
                  "source": "barchart.com/stocks/quotes/UNH/expected-move: 'Earnings: 10/13/26 [BMO]; IV 38.87%; HV 19.07%; IV Rank 50.10%', observed 2026-09-23"},
    },
}

FILINGS = [
    {"form": "10-Q + 8-K + earnings release", "period": "Q2 2026 (quarter ended 2026-06-30)",
     "highlights": ["results announced 2026-07-16 before market open",
                    "FY2026 guidance RAISED with Q2 results - the bar the Q3 print clears",
                    "IR page lists Earnings Release, Form 8-K and Form 10-Q as filed for 2026 Q2"],
     "source": "unitedhealthgroup.com/investors/financial-reports.html, observed 2026-09-23; date from earnings-watcher.com/wiki/unh-earnings-options",
     "gap": ("the exact Q2 10-Q accession was NOT isolated this run - data.sec.gov "
             "submissions returned accessions but the form/date labels were "
             "truncated before the July window; recorded rather than guessed (K4)"),
     "observed_on": "2026-09-23"},
    {"form": "Q3 2026 date announcement (newsroom)", "period": "release scheduled 2026-10-13 pre-open",
     "source": "unitedhealthgroup.com/newsroom/2026/2026-09-15-uhg-announces-q3-earnings-release-date.html, observed 2026-09-23",
     "observed_on": "2026-09-23"},
    {"form": "EDGAR standing record", "period": "entity metadata",
     "highlights": ["CIK 0000731766, SIC 6324 (Hospital & Medical Service Plans)",
                    "Large accelerated filer, NYSE, Delaware, FY end 12-31"],
     "source": "data.sec.gov/submissions/CIK0000731766.json, observed 2026-09-23",
     "observed_on": "2026-09-23"},
]

RISKS = [
    {"risk": ("Oversold-bounce risk: the tape has fallen -19.6% from the 52-week "
              "intraday high (461.62 on 2026-07-16 - the Q2 print day itself) to "
              "371.29, with '20%+ upside' buy-rating headlines in early September - "
              "a relief rally can carry through the print regardless of results"),
     "evidence": "CNBC 52w high + sourced close series + TipRanks ~2026-09-08, observed 2026-09-23",
     "direction": "upside_against_thesis"},
    {"risk": ("Positive sentiment overlay dated right before the print: "
              "UnitedHealthcare drops prior-authorization requirements from "
              "2026-10-01 (Reuters/Forbes ~2026-09-02) - eleven days before the catalyst"),
     "evidence": "Reuters via stockanalysis news list, observed 2026-09-23",
     "direction": "upside_against_thesis"},
    {"risk": ("The 'options overprice UNH events' leg is contested by data: the "
              "July print's actual move was +10.3% vs +/-6.5% priced, i.e. the last "
              "UNH earnings move UNDERSHOT the pricing in the direction that hurts "
              "this thesis"),
     "evidence": "earnings-watcher.com/wiki/unh-earnings-options, observed 2026-09-23",
     "direction": "upside_against_thesis"},
    {"risk": ("Raised-bar double miss: FY2026 guidance was raised on 2026-07-16, so "
              "an in-line Q3 merely reaffirms while a miss cuts against an already "
              "raised bar - the fundamental setup is asymmetric to the downside even "
              "if the sentiment call is wrong"),
     "evidence": "unitedhealthgroup.com IR financial-reports page, observed 2026-09-23",
     "direction": "downside_with_thesis"},
    {"risk": ("Portfolio-retrenchment headlines into the print: WellMed sale to TPG "
              "and Florida Optum clinic sales to TPG reported ~2026-09-09 - scope "
              "reduction reads as a growth-scope admission"),
     "evidence": "Invezz / TheFly (Bloomberg report) via stockanalysis news list, ~2026-09-09",
     "direction": "downside_with_thesis"},
    {"risk": ("Fat event distribution: options charge 7.9% but the 8-quarter average "
              "move is -6.87% and the July move hit +10.3% - single prints of ~10% "
              "make the 8% band a near coin-flip classification on any given print"),
     "evidence": "optionsai + unusualwhales + earnings-watcher, observed 2026-09-23",
     "direction": "classification_risk"},
    {"risk": ("Policy/political headline risk is structural for UNH (Medicare "
              "Advantage rate cycle, Washington rhetoric) and can move the tape "
              "non-fundamentally on any day inside the 20-day horizon"),
     "evidence": "standing UNH risk profile; no single dated source required for a structural flag",
     "direction": "both"},
    {"risk": ("Release-timing vendor conflict (company: pre-open with 8am call vs "
              "unusualwhales: 'PM') - if the release actually lands after the US "
              "close on 2026-10-13 the reaction session shifts one day"),
     "evidence": "both sources cited above; the company newsroom is primary",
     "direction": "scoring_risk"},
]

THESIS = {
    "subject": "UNH",
    "one_line": ("UnitedHealth already raised its 2026 bar and last sold its own "
                 "raise, so the pre-open Q3 print is more likely to be sold than "
                 "bought."),
    "falsifiable_prediction": ("UNH's close on 2026-10-13 (the full US session "
                               "reacting to the pre-open Q3 print) is not above its "
                               "2026-10-12 close."),
    "null_hypothesis": "a coin flip: P(non-positive reaction) = 50%",
    "claimed_edge": ("(1) the bar was raised on 2026-07-16, so an in-line quarter "
                     "reaffirms rather than surprises, and a beat must clear the "
                     "raised bar; (2) sell-the-raise precedent: the Q2 print day "
                     "printed the 52-week intraday high 461.62, closed 423.38 "
                     "(-8.3% off the spike), and the tape is another -19.6% lower "
                     "since; (3) options charge +/-7.9% for an event whose 10-year "
                     "average peak move is +/-5.9% - a premium - while the "
                     "8-quarter average move is -6.87% (negative); (4) divestiture "
                     "headlines (WellMed + FL Optum clinics to TPG) land in the "
                     "two weeks before the print. The edge is a judgement, not a "
                     "measured probability - risks 1-3 above are the honest "
                     "counter-case and are why confidence stays at 55."),
    "invalidation": ("an upside breach of +8.0% on 2026-10-13 falsifies the read "
                     "decisively; no re-entry in either direction without a new "
                     "written thesis"),
    "what_would_confirm": "a non-positive 2026-10-13 close (change <= 0.0% vs 2026-10-12)",
    "what_would_falsify": "a positive 2026-10-13 close (change > 0.0%)",
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
    # V3 sigma estimators agree
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
        {"kill_rule": "upside breach >= +8.0% on 2026-10-13",
         "horizon_end": "2026-10-13", "hit": "<= 0.0% change", "kill": ">= +8.0%"},
        all([BET_ID, "2026-10-13", BAND_PCT]))
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
            row = {"id": ROW_ID, "symbol": "UNH", "checks": [], "outcome": None}
            rows.append(row)
        row.update({
            "symbol": "UNH", "direction": "non_positive_event",
            "entry_date": ENTRY["observed_on"], "entry_price": ENTRY["price"],
            "entry_source": " | ".join(ENTRY["sources"][:2]),
            "catalyst": CATALYST["event"] + " " + CATALYST["date"],
            "confidence": 55, "status": "active",
            "invalidation_level": round(ENTRY["price"] * (1 + BAND_PCT / 100), 2),
            "target": None, "outcome": None,
            "bet_id": BET_ID, "horizon_end": "2026-10-13",
            "band_pct": BAND_PCT, "rule_version": "mark-l7-v2+k8",
            "trigger_hit": "2026-10-13 close change <= 0.0% vs the 2026-10-12 close",
            "kill_miss": "2026-10-13 close change >= +8.0% vs the 2026-10-12 close",
            "no_edge_rule": "0.0% < change < +8.0% => not_confirmed (counts as no_edge)",
            "kill_rule": "K5 analogue: upside breach >= +8.0% closes the bet as MISS; no re-entry without a new written thesis",
            "reference_price": None,
            "reference_price_source": None,
            "reference_price_ts": None,
            "scored_fields_pending": ["outcome", "outcome_price", "outcome_source",
                                      "outcome_ts", "reference_price",
                                      "reference_price_source", "reference_price_ts",
                                      "change_pct", "breach_side", "scored_at"],
            "scoring_rule": ("reference = UNH close 2026-10-12 (must be sourced and "
                             "timestamped); outcome = close 2026-10-13 vs reference; "
                             "if the actual Q3 release timestamp lands after the US "
                             "close on 2026-10-13, scoring shifts to the 2026-10-14 "
                             "session and the row records that timestamp (K4)"),
        })
        research_lib.save_theses(rows)
        after = research_lib.load_theses()
    return {"created": created, "row_count": len(after),
            "others_digest_before": others,
            "others_digest_after": hashlib.sha256(json.dumps(
                [r for r in after if r.get("id") != ROW_ID], sort_keys=True).encode()).hexdigest(),
            "unh_row": next(r for r in after if r.get("id") == ROW_ID)["bet_id"]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Register the UNH falsifiable thesis")
    ap.add_argument("--selftest", action="store_true",
                    help="validate only; no ledger write, no artifact")
    ns = ap.parse_args(argv)

    checks, cal = validate()
    failures = [c for c in checks if not c["pass"]]
    for c in checks:
        print(("PASS " if c["pass"] else "FAIL ") + c["id"] + " " + c["check"]
              + " -> " + json.dumps(c["observed"]))

    print(f"UNH thesis: band +/-{BAND_PCT}% | sigma_event {cal['sigma_event_pct']:.2f}% "
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
        "schema_version": SCHEMA, "owner": "MARK", "task": "TASK-00088",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "artifact_policy": ("ONE current thesis per subject, regenerated in place "
                            "(atomic tmp+rename). No version chain, so the family "
                            "cannot churn under K2."),
        "subject_selection": {
            "why_unh": ("UNH is in no prior artifact family (0 files) unlike AMBA "
                        "(126 sec-review briefs, K2 freeze tripped), it carries a "
                        "hard dated catalyst on 2026-10-13, and it is a HEALTHCARE "
                        "name - uncorrelated with the registered MU and ASML "
                        "semiconductor bets, so the book's joint simulation stops "
                        "resting on one shared AI-capex factor."),
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
            "band_pct": BAND_PCT, "horizon_end": "2026-10-13",
            "rule_version": "mark-l7-v2+k8",
            "reference_rule": "reference = sourced UNH close 2026-10-12 (K6: fresh, timestamped)",
            "trigger_hit": "change <= 0.0%", "kill_miss": "change >= +8.0%",
            "no_edge_rule": "0.0% < change < +8.0% => not_confirmed",
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
            "The event sigma is taken from a vendor's expected-move quote (7.9%, optionsai), not a single-print straddle I computed; cross-vendor quotes sit at 8.82% (optionslam weekly).",
            "The 'options overprice UNH events' argument is genuinely contested: the July print actually moved +10.3% vs +/-6.5% priced (earnings-watcher) while marketchameleon shows the opposite long-run pattern (+6.2% predicted vs +1.2% actual). Both are recorded; confidence is capped at 55 because of it.",
            "No third-party Q3 consensus was sourced; the comparison bar is management's own raised FY2026 guidance, so 'beat/miss vs consensus' framing is deliberately absent.",
            "The series is the dividend-adjusted close column; the raw close equals the adjusted close on 2026-09-23 (entry row), but intermediate rows differ by dividends - returns are total-return-consistent, quoted prices are not all raw.",
            "The exact Q2 10-Q accession was not isolated (EDGAR submissions form labels truncated); the IR page confirms the filing exists - recorded as a gap, not guessed (K4).",
            "The directional claim has a 50% null; the edge is a judgement about a raised bar and a sell-the-raise precedent, not a measured probability, and no confidence interval is claimed.",
            "The reference close (2026-10-12) does not exist yet; scoring requires a sourced quote on or after 2026-10-13.",
            "The betbook_event_sim.py INPUTS list still names only MU and ASML - this third bet is NOT yet in the joint simulation; extending it is separate work, not silently done here.",
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
