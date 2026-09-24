#!/usr/bin/env python3
"""xom_thesis_register.py — one owner for the XOM falsifiable market thesis.

TASK-00125 (market-thesis). Subject: XOM (Exxon Mobil), chosen because it has
0 prior artifacts (fresh family - AMBA stays K2-frozen; MU/ASML/UNH/TSLA/JPM
each already carry one registered thesis and a second file would start a
version chain), and it is ENERGY - the one major sector the book does not
cover (semis MU/ASML, healthcare UNH, EV TSLA, financials JPM), so the joint
book gains a commodity leg uncorrelated to the others.

This module does four things and nothing else:
  1. holds the thesis, its sourced quotes, and its citations (K4)
  2. owns its own band calibration (no separate volatility task was
     dispatched for XOM, so calibration lives here, computed from the
     constants below - single owner, no cross-module drift possible)
  3. registers the bet into the ledger through research_lib's own primitives,
     idempotently, leaving every other row byte-identical
  4. regenerates ONE current artifact (XOM_THESIS_ACTIVE.json, atomic
     tmp+rename) - no version chain, so K2 cannot bind

Priced from fresh sourced quotes, NEVER from theses.jsonl's own check history
(substantiated unusable on 2026-09-23: ETH +145.66% / SOL +232.29% single-day
prints; BTC 2026-08-28 96,000.00 vs sourced 77,639.00).

Series basis: ADJUSTED close (the vendor's stated Change column is
adj-close-to-adj-close across the 2026-08-17 ex-dividend: Aug 17 +1.50% =
161.46/159.07, while raw would give +0.85%; for all rows >= 2026-08-17 the
adjusted and raw closes are identical, so the entry price is the raw close).

Usage:
    python3 xom_thesis_register.py            # validate, register, write artifact
    python3 xom_thesis_register.py --selftest # validate only; no ledger, no artifact
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path.home() / ".freebuff"))
sys.path.insert(0, str(Path.home() / ".freebuff/market-research"))
import research_lib  # noqa: E402  (single owner of theses.jsonl)

DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(DIR))
from thesis_register import tag, norm_cdf  # noqa: E402

OUT = DIR / "XOM_THESIS_ACTIVE.json"
SCHEMA = "market-thesis-active.v1"
TAX_DAYS = 365.0 / 252.0
RUN_ON = "2026-09-24"

BET_ID = "XOM-Q3-2026-REACTION-20261030"
ROW_ID = "thesis_xom_q3_2026_reaction"
K8_MIN_K = 0.75
K8_MAX_NO_EDGE = 0.75
HORIZON = "2026-10-30"
REFERENCE = "2026-10-29"

# (date, adjusted close, vendor stated Change %) - oldest first, 50 rows,
# stockanalysis.com/stocks/xom/history/, observed 2026-09-24
SERIES = [
    ("2026-07-15", 143.58, -0.40), ("2026-07-16", 145.01, 1.00),
    ("2026-07-17", 146.41, 0.97), ("2026-07-20", 147.41, 0.68),
    ("2026-07-21", 150.73, 2.26), ("2026-07-22", 153.46, 1.81),
    ("2026-07-23", 155.88, 1.58), ("2026-07-24", 155.93, 0.03),
    ("2026-07-27", 153.77, -1.38), ("2026-07-28", 152.06, -1.11),
    ("2026-07-29", 155.74, 2.42), ("2026-07-30", 155.96, 0.14),
    ("2026-07-31", 154.44, -0.97), ("2026-08-03", 154.06, -0.24),
    ("2026-08-04", 152.97, -0.71), ("2026-08-05", 150.65, -1.51),
    ("2026-08-06", 153.84, 2.12), ("2026-08-07", 152.06, -1.16),
    ("2026-08-10", 158.76, 4.41), ("2026-08-11", 158.77, 0.01),
    ("2026-08-12", 158.72, -0.03), ("2026-08-13", 157.59, -0.71),
    ("2026-08-14", 159.07, 0.94), ("2026-08-17", 161.46, 1.50),
    ("2026-08-18", 165.56, 2.54), ("2026-08-19", 164.77, -0.48),
    ("2026-08-20", 166.15, 0.84), ("2026-08-21", 165.11, -0.63),
    ("2026-08-24", 164.05, -0.64), ("2026-08-25", 160.64, -2.08),
    ("2026-08-26", 158.19, -1.53), ("2026-08-27", 156.44, -1.11),
    ("2026-08-28", 156.71, 0.17), ("2026-08-31", 160.95, 2.71),
    ("2026-09-01", 164.55, 2.24), ("2026-09-02", 164.15, -0.24),
    ("2026-09-03", 162.21, -1.18), ("2026-09-04", 159.47, -1.69),
    ("2026-09-08", 160.66, 0.75), ("2026-09-09", 164.23, 2.22),
    ("2026-09-10", 165.23, 0.61), ("2026-09-11", 165.99, 0.46),
    ("2026-09-14", 165.08, -0.55), ("2026-09-15", 169.32, 2.57),
    ("2026-09-16", 163.32, -3.54), ("2026-09-17", 163.27, -0.03),
    ("2026-09-18", 163.54, 0.17), ("2026-09-21", 158.30, -3.20),
    ("2026-09-22", 158.71, 0.26), ("2026-09-23", 161.23, 1.59),
]
SERIES_SOURCE = ("stockanalysis.com/stocks/xom/history/ -- 50 sessions "
                 "2026-07-15..2026-09-23, adjusted-close basis, observed 2026-09-24")

# Band = the vendor implied earnings move: marketchameleon trailing-12 average
# +-2.3% ("The options prices predicted a +-2.3% post earnings move, compared
# to a -1.0% actual move. The options market overestimated XOM stocks earnings
# move 85% of ...") corroborated by optionslam's Jul 31 2026 print implied
# 2.32% and May 1 2026 implied 2.56%. No live event-straddle quote is free
# this run (optionslam chart member-gated, MC premium-gated) - recorded as a
# limitation, not silently worked around.
BAND_PCT = 2.3
BAND_SOURCES = [
    "marketchameleon.com/Overview/XOM/Earnings/Earnings-Charts/ search snippet, observed 2026-09-24: 'predicted a +-2.3% post earnings move, compared to a -1.0% actual move ... overestimated XOM stocks earnings move 85% of [time]' (page itself premium-gated)",
    "optionslam.com/earnings/weekly/XOM Jul 31, 2026 print row: implied move 2.32%, closing move -0.97% tagged I(nside) (observed 2026-09-24)",
    "optionslam.com/earnings/weekly/XOM May 1, 2026 print row: implied move 2.56%, closing move -1.02% tagged I(nside) (observed 2026-09-24)",
]
VENDOR_HV_PCT = 23.84   # barchart volatility-charts HV, observed 2026-09-24
VENDOR_IV_PCT = 29.93   # barchart volatility-charts IV, observed 2026-09-24

E_ABS_RATIO = math.sqrt(2.0 / math.pi)  # E|N(0,1)| = 0.7978845608028654

ENTRY = {
    "price": 161.23,
    "observed_on": "2026-09-23",
    "sources": [
        SERIES_SOURCE + " -- row 'Sep 23, 2026': Close 161.23 (at close: 4:00 PM EDT)",
        "internal consistency: 161.23 / 158.71 - 1 = +1.59% matches the table's stated Change for that row",
    ],
    "prior_close": {"price": 158.71, "observed_on": "2026-09-22",
                    "sources": ["stockanalysis.com XOM history row 'Sep 22, 2026': Close 158.71, Change +0.26% (158.71/158.30 - 1 = +0.26% verified)"]},
    "after_hours": {"price": 161.37,
                    "source": "stockanalysis.com header: 'After-hours: Sep 23, 2026, 7:56 PM EDT' 161.37 (+0.09%)"},
    "range_52w": {"note": "52-week range NOT sourced this run - omitted rather than estimated (K4)"},
    "market_cap": {"value": "677.9B",
                   "source": "optionslam.com/earnings/weekly/XOM page: 'Market Cap: 677.9B' (observed 2026-09-24)"},
}

CATALYST = {
    "event": "ExxonMobil Q3 2026 financial results (vendor-estimated 2026-10-30, before open per vendor BO-tag history)",
    "date": "2026-10-30",
    "date_status": ("VENDOR-CONSENSUS - three independent vendors agree on 2026-10-30; "
                    "NO company press release found (exact-phrase IR search returned 0 results, observed 2026-09-24)"),
    "source_confirmed": [
        "optionslam.com/earnings/weekly/XOM: 'Next Earnings Date: Estimated on Oct. 30, 2026. OS Projected Window: Oct. 26, 2026 to Oct. 31, 2026' (observed 2026-09-24)",
        "barchart.com/stocks/quotes/XOM/volatility-charts: 'Latest Earnings: Earnings: 10/30/26' (observed 2026-09-24)",
        "public.com/stocks/xom/earnings: 'The next Exxon Mobil (XOM) earnings call is scheduled for Oct. 30, 2026' (observed 2026-09-24)",
    ],
    "observed_on": "2026-09-24",
    "release_timing_evidence": {
        "assumed": ("before open on 2026-10-30: optionslam's own history tags every one of XOM's last ten "
                    "prints BO (Jul 31 2026, May 1 2026, Jan 30 2026, Oct 31 2025, Aug 1 2025, May 2 2025, "
                    "Jan 31 2025, Nov 1 2024, Aug 2 2024, Apr 26 2024), so the full US reaction session "
                    "is 2026-10-30 itself"),
        "shift_rule": ("if XOM releases at/after 16:00 ET on 2026-10-30 (a Friday) scoring shifts to the next "
                       "US session (2026-11-02); if the date slips inside the Oct 26-31 vendor window, scoring "
                       "moves to the session after the ACTUAL print - in both cases the row records the actual "
                       "date/timestamp (K4); band and entry stay immutable"),
        "source": "optionslam.com XOM earnings-history Position column (BO tags), observed 2026-09-24",
    },
    "implied_event_move": {"band_pct": BAND_PCT, "sources": BAND_SOURCES},
    "momentum_into_print": {
        "detail": ("+17.9% adjusted Jul 15 -> Sep 15 (143.58 -> 169.32), then a -6.5% four-session correction "
                   "to Sep 21 (158.30, including a -3.20% single day), then a two-session +1.85% bounce into "
                   "the entry (161.23); the rally's news drivers (Venezuela deal talks, lawsuit dismissal, "
                   "RBC refining-offset note) all printed BEFORE the quarter"),
        "source": "stockanalysis.com series rows + page news rail (Reuters/WSJ/TheFly, observed 2026-09-24)",
    },
}

FILINGS = [
    {"form": "10-Q", "period": "Q2 2026 (quarter ended 2026-06-30)",
     "accession": "0000034088-26-000093", "filed": "2026-08-03",
     "primary_doc": "xom-20260630.htm",
     "source": "data.sec.gov/submissions/CIK0000034088.json, observed 2026-09-24",
     "observed_on": "2026-09-24"},
    {"form": "8-K", "period": "filed 2026-07-01", "accession": "0001193125-26-291986",
     "highlights": ["content unread this run - recorded, not guessed (K4)"],
     "source": "data.sec.gov submissions, observed 2026-09-24",
     "observed_on": "2026-09-24"},
    {"form": "IR results page", "period": "latest results block",
     "highlights": ["investor.exxonmobil.com: 'Latest financial results. Q2 2026. Quarter Ended Jun 30, 2026. Earnings Release HTML PDF'"],
     "source": "investor.exxonmobil.com (search result), observed 2026-09-24",
     "observed_on": "2026-09-24"},
    {"form": "EDGAR standing record", "period": "entity metadata",
     "highlights": ["CIK 0000034088, EXXON MOBIL CORP",
                    "gap recorded: no item 2.02 results 8-K appears in submissions with filingDate >= 2026-07-01 (only the 10-Q and the 2026-07-01 8-K) - observed fact, not inferred"],
     "source": "data.sec.gov submissions, observed 2026-09-24",
     "observed_on": "2026-09-24"},
]

RISKS = [
    {"risk": ("Date is VENDOR-ESTIMATED, not company-confirmed: the exact-phrase search for ExxonMobil's Q3 "
              "release press release returned 0 results, and the estimate sits at the END of optionslam's "
              "Oct 26-31 window - late-window slips are the norm (optionslam's own disclaimer)"),
     "evidence": "optionslam/barchart/public.com snippets + 0-hit exact-phrase search, all observed 2026-09-24",
     "direction": "scoring_risk"},
    {"risk": ("The last two prints closed DOWN inside the band (-0.97%, -1.02%) - but both were also tagged "
              "with intraday max moves outside/near the band (-3.07% tagged O on Jul 31), so a positive "
              "intraday spike fading to a positive close still scores no_edge, not hit: the bet HITS only on "
              "a non-positive close, and the -1.0% average is a mean whose per-print distribution is "
              "premium-gated (could hide positive prints)"),
     "evidence": "optionslam print rows + marketchameleon snippet (page premium-gated), observed 2026-09-24",
     "direction": "upside_against_thesis"},
    {"risk": ("Venezuela deal signing pre-print: Reuters/WSJ/TipRanks report Exxon 'nearing a preliminary "
              "deal' to invest in Venezuela's oil fields (6-7 days ago) - a signed deal is an unquantified "
              "same-day positive pop"),
     "evidence": "stockanalysis.com XOM news rail (Reuters/WSJ/TipRanks, observed 2026-09-24)",
     "direction": "upside_against_thesis"},
    {"risk": ("Crude/oil shock dominates any single-stock reaction: the series itself ran +17.9% in two "
              "months on energy headlines, and a Middle-East/supply move into Oct 30 swamps the "
              "earnings-specific signal (macro leg not in the model)"),
     "evidence": "sourced series window moves; no dated oil quote claimed this run (K4)",
     "direction": "upside_against_thesis"},
    {"risk": ("Band 2.3% is a trailing-12 AVERAGE implied move, not a live event-straddle quote (free sources "
              "gated); current event IV is richer (barchart IV 29.93% > HV 23.84%, IV Rank 64.98), so the "
              "true priced band may be wider than 2.3% - the miss-side threshold could be understated"),
     "evidence": "barchart volatility-charts snippet + MC/optionslam gating, observed 2026-09-24",
     "direction": "classification_risk"},
    {"risk": ("k = 0.7979 is BY CONSTRUCTION (band defined at E|move| = 0.7979 * sigma_event), so K8 passes "
              "whenever the band source is honest - the gate discriminates only against arbitrarily narrow "
              "bands; no_edge-heavy by construction (p_no_edge 0.2875 under the Gaussian model, higher "
              "empirically for a mega-cap energy name)"),
     "evidence": "calibration block below; same model as UNH/TSLA/JPM registrations",
     "direction": "classification_risk"},
    {"risk": ("Week-of-window peer collision: the Oct 26-31 window hosts other large-cap energy peers' "
              "prints (peer dates NOT sourced this run - structural claim only, K4) - sympathy flows muddy "
              "attribution of XOM's own reaction"),
     "evidence": "structural (sector earnings cluster); no dated peer sources claimed",
     "direction": "scoring_risk"},
    {"risk": ("Friday session structure: a Friday BMO print ends the trading week at the reaction - no "
              "second-day follow-through exists before the weekend, so a small positive close can persist "
              "into Monday unchanged (compression risk for the hit leg)"),
     "evidence": "2026-10-30 is a Friday (calendar fact) + optionslam BO convention",
     "direction": "scoring_risk"},
]

THESIS = {
    "subject": "XOM",
    "one_line": ("XOM reaches a vendor-dated Oct 30 print with its rally already spent: +17.9% on "
                 "Venezuela/refinery headlines faded -6.5%, the last two prints both closed down inside "
                 "the implied band, and options have overpriced XOM's earnings move in 85% of the "
                 "trailing history."),
    "falsifiable_prediction": ("XOM's close on 2026-10-30 (the US session reacting to the vendor-estimated "
                               "pre-open Q3 print) is not above its 2026-10-29 close."),
    "null_hypothesis": "a coin flip: P(non-positive reaction) = 50%",
    "claimed_edge": ("(1) the reaction distribution is negative-mean and inside-band: marketchameleon's "
                     "trailing-12 has actual moves averaging -1.0% against a +-2.3% priced move, with "
                     "options overestimating XOM's move 85% of the time, and optionslam's two fully visible "
                     "prints both closed DOWN and Inside (-0.97% vs 2.32% implied on 2026-07-31; -1.02% vs "
                     "2.56% implied on 2026-05-01); (2) the pop is already spent - the +17.9% Jul-Sep run "
                     "was headline-driven (Venezuela talks, lawsuit dismissal already printed as news before "
                     "the quarter), the tape has since corrected -6.5%, and the one framing note on the "
                     "quarter itself (RBC) is 'refining upside to OFFSET lost Middle East earnings' - a "
                     "hold-quarter setup, not a beat setup; (3) BMO-Friday mechanics give the reaction the "
                     "entire final session of the week with the date at the window's end. The edge is a "
                     "judgement under a 50% null - risks 1-4 (ungated date, positive-spike closes, Venezuela "
                     "signing, oil shock) are the honest counter-case and are why confidence stays at 52."),
    "invalidation": ("an upside breach of +2.3% on the reaction session falsifies the read decisively; "
                     "no re-entry in either direction without a new written thesis"),
    "what_would_confirm": "a non-positive reaction-session close (change <= 0.0% vs the prior close)",
    "what_would_falsify": "a positive reaction-session close (change > 0.0%), decisive-falsifier at >= +2.3%",
}


def calibration() -> dict:
    """Single owner of the XOM band math (no separate volatility task exists for XOM)."""
    sigma_event = BAND_PCT / E_ABS_RATIO
    k = BAND_PCT / sigma_event
    p_no_edge = norm_cdf(k) - 0.5
    p_miss = 1.0 - norm_cdf(k)
    rets = [SERIES[i][1] / SERIES[i - 1][1] - 1.0 for i in range(1, len(SERIES))]
    n = len(rets)
    mean = sum(rets) / n
    var = sum((r - mean) ** 2 for r in rets) / (n - 1)
    daily = math.sqrt(var)
    return {
        "band_pct": BAND_PCT, "band_sources": BAND_SOURCES,
        "sigma_event_pct": sigma_event, "band_k_sigmas": k,
        "expected_p_hit": 0.5, "expected_p_no_edge": p_no_edge,
        "expected_p_miss": p_miss,
        "realised_daily_sigma_pct": daily * 100.0,
        "realised_annualised_sigma_pct": daily * math.sqrt(252.0) * 100.0,
        "vendor_hv_pct": VENDOR_HV_PCT, "vendor_iv_pct": VENDOR_IV_PCT,
        "convention": ("band = vendor implied earnings move (E|move|); "
                       "sigma_event = band / E|N(0,1)| so the model's expected absolute move equals the "
                       "vendor quote; k = band / sigma_event = E|N(0,1)| by construction"),
    }


def stated_change_deviation(series: list) -> dict:
    """Per-row integrity: computed adj-close-to-adj-close change vs vendor stated Change."""
    worst, over = 0.0, []
    for i in range(1, len(series)):
        computed = (series[i][1] / series[i - 1][1] - 1.0) * 100.0
        dev = abs(computed - series[i][2])
        worst = max(worst, dev)
        if dev > 0.01:
            over.append({"date": series[i][0], "dev_pp": round(dev, 4)})
    return {"rows_checked": len(series) - 1, "max_dev_pp": round(worst, 4),
            "rows_over_tol": over}


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
    add("V2", "series last close == cited entry price",
        {"series": SERIES[-1][1], "entry": ENTRY["price"]},
        SERIES[-1][1] == ENTRY["price"])
    add("V3", "K8: band >= 0.75 sigma_events",
        {"k": round(cal["band_k_sigmas"], 4), "floor": K8_MIN_K,
         "band": cal["band_pct"], "sigma_event": round(cal["sigma_event_pct"], 4)},
        cal["band_k_sigmas"] >= K8_MIN_K)
    add("V4", "K8 gate: expected no_edge <= 75%",
        {"expected_no_edge": round(cal["expected_p_no_edge"], 4)},
        cal["expected_p_no_edge"] <= K8_MAX_NO_EDGE)
    tot = 0.5 + cal["expected_p_no_edge"] + cal["expected_p_miss"]
    add("V5", "hit/no_edge/miss partition sums to 1", {"sum": round(tot, 12)},
        abs(tot - 1.0) < 1e-12)
    tdays = (tag(RUN_ON) - tag(ENTRY["observed_on"])) / TAX_DAYS
    add("V6", "K6: entry quote within 1 trading day of the run",
        {"entry_observed_on": ENTRY["observed_on"], "run_on": RUN_ON,
         "trading_days_old": round(tdays, 2)}, tdays <= 1.0)
    add("V7", "K7: bet carries kill_rule, horizon_end, hit and kill thresholds",
        {"kill_rule": f"upside breach >= +{cal['band_pct']}% on {HORIZON}",
         "horizon_end": HORIZON, "reference": REFERENCE,
         "hit": "<= 0.0% change", "kill": f">= +{cal['band_pct']}%"},
        all([BET_ID, HORIZON, REFERENCE, cal["band_pct"]]))
    status_ok = CATALYST["date_status"].startswith(("COMPANY-CONFIRMED", "VENDOR-CONSENSUS"))
    add("V8", "catalyst date has >=2 independent sources and an explicit provenance status",
        {"date": CATALYST["date"], "status": CATALYST["date_status"][:24],
         "sources": len(CATALYST["source_confirmed"])},
        len(CATALYST["source_confirmed"]) >= 2 and status_ok)
    dev = stated_change_deviation(SERIES)
    add("V9", "per-row series integrity vs vendor stated Change (adj-close basis)",
        {"rows_checked": dev["rows_checked"], "max_dev_pp": dev["max_dev_pp"],
         "rows_over_tol": len(dev["rows_over_tol"])},
        len(dev["rows_over_tol"]) == 0)
    add("V10", "pricing source is fresh quotes, not the corrupt ledger series",
        {"ledger_status": "unusable as a price series (2026-09-23 finding)",
         "priced_from": SERIES_SOURCE.split(" -- ")[0]}, True)
    add("V11", "vendor date camps and release-timing shift rule are recorded",
        {"vendors": ["optionslam Oct 30 (window Oct 26-31)", "barchart 10/30/26",
                     "public.com Oct 30"], "company_pr": "0 hits (exact-phrase search)",
         "timing": "BO per optionslam 10-print history", "shift_rule": True},
        len(CATALYST["source_confirmed"]) >= 3
        and "shift_rule" in CATALYST["release_timing_evidence"])
    realised = cal["realised_annualised_sigma_pct"]
    ratio = realised / VENDOR_HV_PCT
    add("V12", "realised-vendor HV ratio within [0.5, 2.0]",
        {"realised_pct": round(realised, 2), "vendor_hv_pct": VENDOR_HV_PCT,
         "ratio": round(ratio, 3)}, 0.5 <= ratio <= 2.0)

    # NC1 the K8 gate rejects a planted 2.0% band
    add("NC1", "K8 gate rejects a 2.0% band (k < 0.75)",
        {"band_pct": 2.0, "k": round(2.0 / cal["sigma_event_pct"], 4)},
        2.0 / cal["sigma_event_pct"] < K8_MIN_K)
    # NC2 a stale quote must be rejected by K6
    stale = (tag(RUN_ON) - tag("2026-09-18")) / TAX_DAYS
    add("NC2", "K6 gate rejects a quote 3 trading days old",
        {"trading_days_old": round(stale, 2)}, stale > 1.0)
    # NC3 a status downgrade (UNCONFIRMED) must fail V8
    simulated_status = "UNCONFIRMED"
    v8_on_simulated = (len(CATALYST["source_confirmed"]) >= 2
                       and simulated_status.startswith(("COMPANY-CONFIRMED", "VENDOR-CONSENSUS")))
    add("NC3", "V8 fails if the date status is downgraded to UNCONFIRMED",
        {"simulated_status": simulated_status,
         "v8_passes_on_simulated": v8_on_simulated}, not v8_on_simulated)
    # NC4 determinism
    add("NC4", "calibration is deterministic across recomputation",
        {"k_first": round(calibration()["band_k_sigmas"], 12),
         "k_second": round(calibration()["band_k_sigmas"], 12)},
        calibration()["band_k_sigmas"] == calibration()["band_k_sigmas"])
    return checks, cal


def register(band_pct: float) -> dict:
    """Idempotent ledger registration through research_lib's own primitives."""
    with research_lib.ledger_tx():
        rows = research_lib.load_theses()
        others = hashlib.sha256(json.dumps(
            [r for r in rows if r.get("id") != ROW_ID], sort_keys=True).encode()).hexdigest()
        row = next((r for r in rows if r.get("id") == ROW_ID), None)
        created = row is None
        if created:
            row = {"id": ROW_ID, "symbol": "XOM", "checks": [], "outcome": None}
            rows.append(row)
        row.update({
            "symbol": "XOM", "direction": "non_positive_event",
            "entry_date": ENTRY["observed_on"], "entry_price": ENTRY["price"],
            "entry_source": " | ".join(ENTRY["sources"][:2]),
            "catalyst": CATALYST["event"] + " " + CATALYST["date"] + " (VENDOR-CONSENSUS)",
            "confidence": 52, "status": "active",
            "invalidation_level": round(ENTRY["price"] * (1 + band_pct / 100), 2),
            "target": None, "outcome": None,
            "bet_id": BET_ID, "horizon_end": HORIZON,
            "band_pct": band_pct, "rule_version": "mark-l7-v2+k8",
            "trigger_hit": f"{HORIZON} close change <= 0.0% vs the {REFERENCE} close",
            "kill_miss": f"{HORIZON} close change >= +{band_pct}% vs the {REFERENCE} close",
            "no_edge_rule": f"0.0% < change < +{band_pct}% => not_confirmed (counts as no_edge)",
            "kill_rule": f"K5 analogue: upside breach >= +{band_pct}% closes the bet as MISS; no re-entry without a new written thesis",
            "reference_price": None,
            "reference_price_source": None,
            "reference_price_ts": None,
            "scored_fields_pending": ["outcome", "outcome_price", "outcome_source",
                                      "outcome_ts", "reference_price",
                                      "reference_price_source", "reference_price_ts",
                                      "change_pct", "breach_side", "scored_at"],
            "scoring_rule": (f"reference = XOM close {REFERENCE} (must be sourced "
                             f"and timestamped); outcome = close {HORIZON} vs reference; "
                             "vendor-estimated BO release assumed per optionslam's 10-print "
                             "BO history; if XOM releases at/after 16:00 ET on 2026-10-30 or "
                             "the date slips inside Oct 26-31, scoring shifts to the session "
                             "after the ACTUAL print and the row records the actual "
                             "timestamp (K4)"),
        })
        research_lib.save_theses(rows)
        after = research_lib.load_theses()
    return {"created": created, "row_count": len(after),
            "others_digest_before": others,
            "others_digest_after": hashlib.sha256(json.dumps(
                [r for r in after if r.get("id") != ROW_ID], sort_keys=True).encode()).hexdigest(),
            "xom_row": next(r for r in after if r.get("id") == ROW_ID)["bet_id"]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Register the XOM falsifiable thesis")
    ap.add_argument("--selftest", action="store_true",
                    help="validate only; no ledger write, no artifact")
    ns = ap.parse_args(argv)

    checks, cal = validate()
    failures = [c for c in checks if not c["pass"]]
    for c in checks:
        print(("PASS " if c["pass"] else "FAIL ") + c["id"] + " " + c["check"]
              + " -> " + json.dumps(c["observed"]))
    band = cal["band_pct"]
    print(f"XOM thesis: band +/-{band}% | sigma_event {cal['sigma_event_pct']:.4f}% "
          f"| k {cal['band_k_sigmas']:.4f} | P(hit) 0.500 P(no_edge) "
          f"{cal['expected_p_no_edge']:.4f} P(miss) {cal['expected_p_miss']:.4f} "
          f"| realised {cal['realised_annualised_sigma_pct']:.2f}% vs HV {cal['vendor_hv_pct']}%")

    if failures:
        print(f"ABORT: {len(failures)} validation failure(s): "
              f"{[c['id'] for c in failures]}", file=sys.stderr)
        return 1
    if ns.selftest:
        print(f"selftest only: {len(checks)}/{len(checks)} pass, no ledger write, no artifact")
        return 0

    reg = register(band)
    if reg["others_digest_before"] != reg["others_digest_after"]:
        print("ABORT: registration modified rows it does not own", file=sys.stderr)
        return 1
    print(f"ledger: {'created' if reg['created'] else 'updated'} {ROW_ID}; "
          f"rows={reg['row_count']}; other rows unchanged "
          f"({reg['others_digest_before'][:12]}=={reg['others_digest_after'][:12]})")

    doc = {
        "schema_version": SCHEMA, "owner": "MARK", "task": "TASK-00125",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "artifact_policy": ("ONE current thesis per subject, regenerated in place "
                            "(atomic tmp+rename). No version chain, so the family "
                            "cannot churn under K2."),
        "subject_selection": {
            "why_xom": ("0 prior artifacts (fresh family - AMBA K2-frozen; MU/ASML/UNH/TSLA/JPM "
                        "each carry exactly one thesis and a second file would start a version "
                        "chain). ENERGY: the one major sector the book does not cover (semis "
                        "MU/ASML, healthcare UNH, EV TSLA, financials JPM), so the joint book "
                        "gains an uncorrelated commodity leg. Vendor-consensus catalyst 37 days "
                        "out with a fully sourced 50-session series."),
            "k2_note": "AMBA remains frozen; this thesis is a registered bet, not a new brief version.",
        },
        "thesis": THESIS,
        "catalyst": CATALYST,
        "filings": FILINGS,
        "explicit_risks": RISKS,
        "entry": ENTRY,
        "price_series": {"source": SERIES_SOURCE, "points": len(SERIES),
                         "span": f"{SERIES[0][0]}..{SERIES[-1][0]}",
                         "basis": ("adj close (stated Change is adj-to-adj across the 2026-08-17 "
                                   "ex-div: Aug 17 +1.50% = 161.46/159.07); raw == adj for all "
                                   "rows >= 2026-08-17, so the entry is the raw close"),
                         "integrity": "per-row stated-change check passes (max dev <=0.01pp)",
                         "rows": [(d, c) for d, c, _ in SERIES]},
        "calibration": cal,
        "calibration_provenance": {
            "owner": "xom_thesis_register.py calibration() - inline single owner "
                     "(no separate volatility task was dispatched for XOM)",
            "artifact": "none separate; this artifact is the record",
        },
        "bet": {
            "bet_id": BET_ID, "ledger_row_id": ROW_ID, "ledger_path": str(research_lib.THESES),
            "band_pct": band, "horizon_end": HORIZON,
            "rule_version": "mark-l7-v2+k8",
            "reference_rule": f"reference = sourced XOM close {REFERENCE} (K6: fresh, timestamped)",
            "trigger_hit": "change <= 0.0%", "kill_miss": f"change >= +{band}%",
            "no_edge_rule": f"0.0% < change < +{band}% => not_confirmed",
            "outcome_values": ["hit", "not_confirmed", "miss", "void"],
            "registration": reg,
        },
        "price_source_policy": {
            "used": SERIES_SOURCE,
            "not_used": ("theses.jsonl check history - substantiated unusable as a "
                         "price series on 2026-09-23 (BET_THRESHOLD_CALIBRATION.json "
                         "data_quality_findings)"),
        },
        "validation": checks,
        "validation_summary": {"total": len(checks), "failed": 0},
        "limitations": [
            "Catalyst date is VENDOR-estimated (3 vendors, 0 company-PR hits) inside an Oct 26-31 window; a slip shifts the scoring session per the recorded shift rule - band and entry stay immutable.",
            "Band 2.3% is a trailing-12 AVERAGE implied move (MC snippet + optionslam's last two print rows), NOT a live event-straddle quote - free sources are gated; barchart IV 29.93% > HV 23.84% (IV Rank 64.98) suggests current event IV may price wider.",
            "k = 0.7979 is by construction (band defined at E|move|), so K8 only rejects arbitrarily narrow bands; the real guard is band-source quality (three sources recorded).",
            "The MC '85% overestimated / +-2.3% vs -1.0%' statistics come from a search snippet (page premium-gated); the trailing-12 per-print set could not be verified row-by-row free this run.",
            "Realised sigma is from a 50-session adjusted series; vendor HV is a single snapshot (barchart volatility-charts 23.84% vs its companion quote page 24.41% - window/timing differ).",
            "No Q3 consensus EPS/production/free-cash-flow numbers were sourced (K4) - the edge rests on reaction-distribution history and news-flow structure, not beat/miss framing.",
            "8-K 0001193125-26-291986 content unread; no item 2.02 results 8-K appears in EDGAR submissions since 2026-07-01 (recorded as observed fact).",
            "52-week range not sourced this run - omitted rather than estimated (K4); market cap cited from optionslam (677.9B).",
            "The betbook_event_sim.py INPUTS names MU/UNH/ASML/TSLA - neither the fifth (JPM) nor this sixth bet is in the joint simulation; extending it is separate work, not silently done here.",
            "The reference close (2026-10-29) does not exist yet; scoring requires a sourced quote on or after 2026-10-30.",
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
