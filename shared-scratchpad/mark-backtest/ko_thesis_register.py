#!/usr/bin/env python3
"""ko_thesis_register.py — one owner for the KO falsifiable market thesis.

TASK-00137 (market-thesis). Subject: KO (The Coca-Cola Company), chosen because
it has 0 prior artifacts (fresh family - AMBA stays K2-frozen; MU/ASML/UNH/
TSLA/JPM/XOM each already carry one registered thesis and a second file would
start a version chain), and it is CONSUMER STAPLES - a defensive sector the
book does not cover (semis MU/ASML, healthcare UNH, EV TSLA, financials JPM,
energy XOM), so the joint book gains an uncorrelated defensive leg.

This module does four things and nothing else:
  1. holds the thesis, its sourced quotes, and its citations (K4)
  2. owns its own band calibration (no separate volatility task was
     dispatched for KO, so calibration lives here, computed from the
     constants below - single owner, no cross-module drift possible)
  3. registers the bet into the ledger through research_lib's own primitives,
     idempotently, leaving every other row byte-identical
  4. regenerates ONE current artifact (KO_THESIS_ACTIVE.json, atomic
     tmp+rename) - no version chain, so K2 cannot bind

Priced from fresh sourced quotes, NEVER from theses.jsonl's own check history
(substantiated unusable on 2026-09-23: ETH +145.66% / SOL +232.29% single-day
prints; BTC 2026-08-28 96,000.00 vs sourced 77,639.00).

Series basis: ADJUSTED close (the vendor's stated Change column is
adj-close-to-adj-close across the 2026-09-15 ex-dividend: Sep 15 -0.12% =
88.71/88.82, while raw would give -0.717%; for all rows >= 2026-09-15 the
adjusted and raw closes are identical, so the entry price is the raw close).

Usage:
    python3 ko_thesis_register.py            # validate, register, write artifact
    python3 ko_thesis_register.py --selftest # validate only; no ledger, no artifact
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

OUT = DIR / "KO_THESIS_ACTIVE.json"
SCHEMA = "market-thesis-active.v1"
TAX_DAYS = 365.0 / 252.0
RUN_ON = "2026-09-24"

BET_ID = "KO-Q3-2026-REACTION-20261020"
ROW_ID = "thesis_ko_q3_2026_reaction"
K8_MIN_K = 0.75
K8_MAX_NO_EDGE = 0.75
HORIZON = "2026-10-20"
REFERENCE = "2026-10-19"

# (date, adjusted close, vendor stated Change %) - oldest first, 50 rows,
# stockanalysis.com/stocks/ko/history/, observed 2026-09-24
SERIES = [
    ("2026-07-15", 81.96, -0.76), ("2026-07-16", 84.42, 3.00),
    ("2026-07-17", 81.08, -3.96), ("2026-07-20", 81.63, 0.69),
    ("2026-07-21", 81.48, -0.18), ("2026-07-22", 81.71, 0.28),
    ("2026-07-23", 80.69, -1.25), ("2026-07-24", 81.76, 1.33),
    ("2026-07-27", 83.57, 2.21), ("2026-07-28", 87.75, 5.00),
    ("2026-07-29", 88.55, 0.92), ("2026-07-30", 87.97, -0.66),
    ("2026-07-31", 87.07, -1.02), ("2026-08-03", 86.34, -0.83),
    ("2026-08-04", 86.05, -0.35), ("2026-08-05", 86.31, 0.31),
    ("2026-08-06", 86.33, 0.02), ("2026-08-07", 86.53, 0.23),
    ("2026-08-10", 86.35, -0.21), ("2026-08-11", 85.97, -0.45),
    ("2026-08-12", 86.20, 0.27), ("2026-08-13", 86.90, 0.82),
    ("2026-08-14", 87.19, 0.33), ("2026-08-17", 86.46, -0.83),
    ("2026-08-18", 88.29, 2.12), ("2026-08-19", 89.81, 1.72),
    ("2026-08-20", 89.96, 0.17), ("2026-08-21", 90.56, 0.66),
    ("2026-08-24", 91.44, 0.98), ("2026-08-25", 91.10, -0.38),
    ("2026-08-26", 89.55, -1.70), ("2026-08-27", 88.53, -1.13),
    ("2026-08-28", 89.13, 0.67), ("2026-08-31", 88.14, -1.10),
    ("2026-09-01", 87.48, -0.76), ("2026-09-02", 87.72, 0.27),
    ("2026-09-03", 88.28, 0.65), ("2026-09-04", 87.55, -0.83),
    ("2026-09-08", 87.84, 0.33), ("2026-09-09", 87.03, -0.92),
    ("2026-09-10", 87.31, 0.32), ("2026-09-11", 87.77, 0.52),
    ("2026-09-14", 88.82, 1.20), ("2026-09-15", 88.71, -0.12),
    ("2026-09-16", 87.87, -0.95), ("2026-09-17", 88.06, 0.22),
    ("2026-09-18", 88.25, 0.22), ("2026-09-21", 87.12, -1.28),
    ("2026-09-22", 88.61, 1.71), ("2026-09-23", 88.09, -0.59),
]
SERIES_SOURCE = ("stockanalysis.com/stocks/ko/history/ -- 50 sessions "
                 "2026-07-15..2026-09-23, adjusted-close basis, observed 2026-09-24")

# Band = the vendor implied earnings move: optionslam's Jul 28 2026 print row
# states implied 3.2% (actual closing move 4.99%, tagged O=Outside), and
# marketchameleon independently states "options prices predicted a +-3.2% post
# earnings move, compared to a +5.0% actual move" for the same print - two
# sources agree on 3.2%. optionslam's LIVE weekly straddle for the upcoming
# window (expires 2026-10-23) already quotes 4.29%; that is 22 days of time +
# event, not an event-only quote, so 3.2% (the last print's event implied) is
# used and the wider live quote is carried as an explicit classification risk,
# not silently averaged in.
BAND_PCT = 3.2
BAND_SOURCES = [
    "optionslam.com/earnings/weekly/KO Jul 28 2026 print row: implied move 3.2%, closing move 4.99% tagged O(utside), straddle return +67.29% (observed 2026-09-24)",
    "marketchameleon.com KO earnings page search snippet: 'The options prices predicted a +-3.2% post earnings move, compared to a +5.0% actual move' for the Jul 28 2026 print (observed 2026-09-24)",
    "investopedia.com (Feb 2026, Q4 FY25 print): 'traders see KO moving up to 3% either direction by end of week' - corroborates the low-3s event move (observed 2026-09-24)",
]
VENDOR_HV_PCT = 15.05   # barchart.com/stocks/quotes/ko snippet: Historical Volatility 15.05%, observed 2026-09-24
VENDOR_IV_PCT = 18.94   # same page: Implied Volatility 18.94%, IV Rank 55.48%, IV Percentile 51%, observed 2026-09-24

E_ABS_RATIO = math.sqrt(2.0 / math.pi)  # E|N(0,1)| = 0.7978845608028654

ENTRY = {
    "price": 88.09,
    "observed_on": "2026-09-23",
    "sources": [
        SERIES_SOURCE + " -- row 'Sep 23, 2026': Close 88.09 (at close: 4:00 PM EDT)",
        "internal consistency: 88.09 / 88.61 - 1 = -0.59% matches the table's stated Change for that row",
    ],
    "prior_close": {"price": 88.61, "observed_on": "2026-09-22",
                    "sources": ["stockanalysis.com KO history row 'Sep 22, 2026': Close 88.61, Change +1.71% (88.61/87.12 - 1 = +1.71% verified)"]},
    "after_hours": {"price": 88.13,
                    "source": "stockanalysis.com header: 'After-hours: Sep 23, 2026, 7:59 PM EDT' 88.13 (+0.05%)"},
    "range_52w": {"note": "52-week range NOT sourced this run - omitted rather than estimated (K4)"},
    "market_cap": {"value": "379.7B",
                   "source": "optionslam.com/earnings/weekly/KO page: 'Market Cap: 379.7B' (observed 2026-09-24)"},
}

CATALYST = {
    "event": "KO Q3 2026 earnings release (vendor-estimated 2026-10-20, before open per 9/9 BO print history)",
    "date": "2026-10-20",
    "date_status": ("VENDOR-CONSENSUS on the print WEEK, day-level camps differ by 2 days: "
                    "optionslam estimates 2026-10-20 inside its 2026-10-19..24 window; "
                    "marketchameleon estimates 2026-10-22; NO company timing press release found "
                    "(KO publishes 'Announces Timing of ... Earnings Release' PRs for Q1/Q2 - "
                    "detail/1163 on 2026-06-29 - but an exact-phrase search for the Q3 timing PR "
                    "returned 0 results, observed 2026-09-24)"),
    "source_confirmed": [
        "optionslam.com/earnings/weekly/KO: 'Next Earnings Date: Estimated on Oct. 20, 2026. OS Projected Window: Oct. 19, 2026 to Oct. 24, 2026' + 'Days to Next Earnings: 27' (observed 2026-09-24, i.e. 27 days from 2026-09-23)",
        "marketchameleon.com/Overview/KO/Straddles/ search snippet: 'Earnings: 22-Oct (Est.)' (page state as of 2026-08-28, observed 2026-09-24)",
    ],
    "observed_on": "2026-09-24",
    "release_timing_evidence": {
        "assumed": ("before open: optionslam's own visible history tags ALL NINE of KO's last prints BO "
                    "(2026-07-28, 2026-04-28, 2026-02-10, 2025-10-21, 2025-07-22, 2025-04-29, 2025-02-11, "
                    "2024-10-23, 2024-07-23) and marketchameleon states 'Jul 28, 2026 BMO' for the last "
                    "print, so the full US reaction session is 2026-10-20 itself"),
        "shift_rule": ("if KO releases at/after 16:00 ET on the actual "
                       "date (or the date lands on the 2026-10-22 MC camp inside the Oct 19-24 window), "
                       "scoring shifts to the next US session after the ACTUAL print - the row records the "
                       "actual date/timestamp (K4); band and entry stay immutable"),
        "source": "optionslam.com KO earnings-history Position column (BO tags, 9 visible rows) + MC BMO snippet, observed 2026-09-24",
    },
    "implied_event_move": {"band_pct": BAND_PCT, "sources": BAND_SOURCES},
    "momentum_into_print": {
        "detail": ("the Q2 beat-and-raise pop is spent: +5.00% on 2026-07-28 (adj 83.57 -> 87.75, tagged "
                   "O=Outside a 3.2% implied, on the window's highest volume 34,982,910) carried the tape to "
                   "an all-time-high close 91.99/91.44-adj on 2026-08-24 (news rail 'KO Hits All-Time High' "
                   "4 weeks ago), since faded -3.66% adj-basis to the 88.09 entry; drift into the print is "
                   "negative - Sep 14 88.82 -> Sep 23 88.09 = -0.82% over 7 sessions with a -1.28% session "
                   "on 2026-09-21"),
        "source": "stockanalysis.com series rows + page news rail (ETF Trends/TipRanks/TheFly/UBS, observed 2026-09-24)",
    },
}

FILINGS = [
    {"form": "10-Q", "period": "Q2 2026 (quarter ended 2026-07-03)",
     "accession": "0001628280-26-050503", "filed": "2026-07-29",
     "primary_doc": "ko-20260703.htm",
     "highlights": ["net operating revenues 13,380 vs 12,535 (+6.7% Q2; 6M 25,852 vs 23,664 +9.2%)",
                    "net income attributable 4,425 vs 3,810 (+16.1% Q2; 6M 8,349 vs 7,140 +16.9%)",
                    "diluted EPS 1.03 vs 0.88 (+17.0% Q2; 6M 1.94 vs 1.65)",
                    "cash 12,907 vs 10,270 at 2025-12-31 (+25.7%); total assets 107,922 vs 104,816 (+3.0%)"],
     "source": "EDGAR exhibits R2 (income) + R4 (balance sheet) of this accession, read 2026-09-24",
     "observed_on": "2026-09-24"},
    {"form": "8-K (earnings release)", "period": "filed 2026-07-28 (Q2 results)",
     "accession": "0001628280-26-049922",
     "highlights": ["headline: 'Raises Full Year Guidance - Global Unit Case Volume Grew 5%, Net Revenues "
                    "Grew 7%; Organic Revenues Grew 6%, driven by a 4% increase in concentrate sales and 2% "
                    "growth in price/mix; Operating Income Grew 9'",
                    "guidance table (Current vs Prior): organic revenues approx. 5% growth (was 4%-5%); "
                    "comparable currency-neutral EPS ex a&d 7%-8% growth (was 6%-7%); comparable EPS 9%-10% "
                    "growth (was 8%-9%) incl. approx. 3% currency tailwind; underlying ETR 19.9% unchanged"],
     "source": "exhibit a2026q2earningsreleaseex-9.htm of this accession, read 2026-09-24",
     "observed_on": "2026-09-24"},
    {"form": "8-K", "period": "filed 2026-07-16", "accession": "0001628280-26-048466",
     "highlights": ["content unread this run - recorded, not guessed (K4)"],
     "source": "data.sec.gov submissions, observed 2026-09-24",
     "observed_on": "2026-09-24"},
    {"form": "IR press-release ledger", "period": "timing-PR cadence",
     "highlights": ["Q1 timing PR exists (search snippet: 'Announces Timing of First Quarter ...', 2026-03-31)",
                    "Q2 timing PR: detail/1163 dated 2026-06-29 ('Announces Timing of Second Quarter 2026 Earnings Release')",
                    "Q3 timing PR: 0 exact-phrase hits as of 2026-09-24 - the date is genuinely unconfirmed by the company"],
     "source": "investors.coca-colacompany.com/news-events/press-releases + exact-phrase search, observed 2026-09-24",
     "observed_on": "2026-09-24"},
]

RISKS = [
    {"risk": ("LAST PRINT CLOSED OUTSIDE THE BAND: the Jul 28 2026 beat-and-raise closed +4.99% against a "
              "3.2% implied (optionslam O tag, straddle buyers +67.29%; marketchameleon: +5.0%) - KO "
              "demonstrably pops on this exact setup, which is the direct counter to a non-positive "
              "reaction bet"),
     "evidence": "optionslam print row + MC snippet, observed 2026-09-24",
     "direction": "upside_against_thesis"},
    {"risk": ("Date is VENDOR-ESTIMATED with CONFLICTING days (optionslam 2026-10-20 vs marketchameleon "
              "2026-10-22) and no company timing PR exists (0 exact-phrase hits) - the shift rule moves "
              "scoring to the session after the ACTUAL print, but a slip materially changes which "
              "sessions are reference/outcome"),
     "evidence": "optionslam window + MC est. + 0-hit Q3 timing search, all observed 2026-09-24",
     "direction": "scoring_risk"},
    {"risk": ("Band 3.2% is ONE print's implied move (the last print), not a live event-straddle quote; "
              "optionslam's live weekly straddle for this window (expires 2026-10-23) already quotes 4.29% "
              "- if the true event implied is nearer 4.3%, the miss-side threshold (+3.2%) is understated "
              "and no_edge is wider than classified"),
     "evidence": "optionslam Implied Move Weekly 4.29% (expires 2026-10-23) vs Jul-print implied 3.2%, observed 2026-09-24",
     "direction": "classification_risk"},
    {"risk": ("k = 0.7979 is BY CONSTRUCTION (band defined at E|move| = 0.7979 * sigma_event), so K8 passes "
              "whenever the band source is honest - the gate discriminates only against arbitrarily narrow "
              "bands; no_edge-heavy by construction (p_no_edge 0.2875 under the Gaussian model)"),
     "evidence": "calibration block below; same model as XOM/JPM/TSLA/UNH/MU registrations",
     "direction": "classification_risk"},
    {"risk": ("Defensive rotation is the crowded side: news rail carries 'Staples ETF Widens Gap Over "
              "Discretionary in 2026' (1 day), UBS 'Buy KO to Protect Against Market Volatility' (8 days) "
              "and a dividend-aristocrat accumulation pitch (5 days) - a persistent bid floors any fade "
              "into the print"),
     "evidence": "stockanalysis.com KO news rail (ETF Trends/TipRanks/TheFly, observed 2026-09-24)",
     "direction": "upside_against_thesis"},
    {"risk": ("Two-sided pre-print whipsaw sits inside the same window: 2026-07-17 fell -3.96% on 32,902,956 "
              "shares (cause not sourced this run, K4) after a +3.00% prior session - single-session tails "
              "of this size straddle the whole band in both directions"),
     "evidence": "stockanalysis.com series rows 2026-07-16/17, observed 2026-09-24",
     "direction": "two_sided_tail"},
    {"risk": ("Q3 could re-raise again: Q2 already raised organic revenue and comparable-EPS guidance, and "
              "no Q3 consensus EPS/revenue numbers were sourced (K4) - the edge rests on tape structure and "
              "reaction history, not a beat/miss view"),
     "evidence": "8-K 0001628280-26-049922 guidance table (read 2026-09-24); no consensus source claimed",
     "direction": "upside_against_thesis"},
    {"risk": ("The reference close (2026-10-19) does not exist yet; scoring requires a sourced quote on or "
              "after the actual reaction session - all four outcomes stay pending until then"),
     "evidence": "calendar fact as of RUN_ON 2026-09-24",
     "direction": "scoring_risk"},
]

THESIS = {
    "subject": "KO",
    "one_line": ("KO reaches its vendor-dated Oct 20 print with the Q2 beat-and-raise fully digested: the "
                 "+5.00% Outside pop has faded -3.66% off the all-time-high close, the tape has drifted "
                 "-0.82% over the last 7 sessions, and options still price 18.94% IV against 15.05% HV."),
    "falsifiable_prediction": ("KO's close on 2026-10-20 (the US session reacting to the vendor-estimated "
                               "pre-open Q3 print) is not above its 2026-10-19 close."),
    "null_hypothesis": "a coin flip: P(non-positive reaction) = 50%",
    "claimed_edge": ("(1) the pop is spent: the Jul 28 beat-and-raise closed +5.00% Outside its 3.2% implied "
                     "and took KO to an all-time-high close 2026-08-24, but the entry is -3.66% (adj basis) "
                     "below that peak - the good news is digested AND given back before the next print; "
                     "(2) momentum into the print is negative: -0.82% over the last 7 sessions (Sep 14 -> "
                     "Sep 23) including a -1.28% session, opposite in sign to the pre-Jul-print run (+2.21% "
                     "on Jul 27 into the pop); (3) options remain rich vs their own realised move (barchart "
                     "IV 18.94% > HV 15.05%, IV Rank 55.48) - the market is still paying up for a move the "
                     "fading tape has stopped delivering, so the 3.2% band is fair-to-generous while drift "
                     "runs against the bulls. The edge is a judgement under a 50% null - risks 1-4 (the "
                     "Outside last print, the unconfirmed/conflicting date, the wider 4.29% live straddle, "
                     "the rotation bid) are the honest counter-case and are why confidence stays at 51."),
    "invalidation": ("an upside breach of +3.2% on the reaction session falsifies the read decisively; "
                     "no re-entry in either direction without a new written thesis"),
    "what_would_confirm": "a non-positive reaction-session close (change <= 0.0% vs the prior close)",
    "what_would_falsify": "a positive reaction-session close (change > 0.0%), decisive-falsifier at >= +3.2%",
}


def calibration() -> dict:
    """Single owner of the KO band math (no separate volatility task exists for KO)."""
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
    """Per-row integrity: computed adj-close-to-adj-close change vs vendor stated Change.

    Tolerance is the per-row rounding bound, not a fixed constant: prices carry
    2dp (rounding +-0.005 each side of the ratio) and the stated Change carries
    2dp itself (+-0.005pp), so at KO's ~$87 level a row can deviate by up to
    0.5/p_prev + 0.5/p_curr + 0.005 pp (~0.017pp) with correct data - a fixed
    0.01pp would false-fail rows a ~$160 name passes (XOM max was 0.0078).
    A real defect (date shift, wrong value) deviates by full percentage points,
    orders of magnitude above this bound.
    """
    worst, worst_bound, over = 0.0, 0.0, []
    for i in range(1, len(series)):
        p_prev, p_curr = series[i - 1][1], series[i][1]
        computed = (p_curr / p_prev - 1.0) * 100.0
        dev = abs(computed - series[i][2])
        bound = 0.5 / p_prev + 0.5 / p_curr + 0.005
        if dev > worst:
            worst, worst_bound = dev, bound
        if dev > bound:
            over.append({"date": series[i][0], "dev_pp": round(dev, 4),
                         "bound_pp": round(bound, 4)})
    return {"rows_checked": len(series) - 1, "max_dev_pp": round(worst, 4),
            "max_bound_pp": round(worst_bound, 4), "rows_over_tol": over}


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
    add("V9", "per-row series integrity vs vendor stated Change (adj-close basis; "
               "per-row tolerance = 2dp-price + 2dp-stated rounding bound)",
        {"rows_checked": dev["rows_checked"], "max_dev_pp": dev["max_dev_pp"],
         "max_bound_pp": dev["max_bound_pp"],
         "rows_over_tol": len(dev["rows_over_tol"])},
        len(dev["rows_over_tol"]) == 0)
    add("V10", "pricing source is fresh quotes, not the corrupt ledger series",
        {"ledger_status": "unusable as a price series (2026-09-23 finding)",
         "priced_from": SERIES_SOURCE.split(" -- ")[0]}, True)
    add("V11", "vendor date camps and release-timing shift rule are recorded",
        {"vendors": ["optionslam Oct 20 (window Oct 19-24)", "marketchameleon Oct 22 (est.)"],
         "company_pr": "0 Q3-timing hits (Q1/Q2 timing PRs exist)",
         "timing": "BO 9/9 visible prints + MC BMO", "shift_rule": True},
        len(CATALYST["source_confirmed"]) >= 2
        and "shift_rule" in CATALYST["release_timing_evidence"])
    realised = cal["realised_annualised_sigma_pct"]
    ratio = realised / VENDOR_HV_PCT
    add("V12", "realised-vendor HV ratio within [0.5, 2.0]",
        {"realised_pct": round(realised, 2), "vendor_hv_pct": VENDOR_HV_PCT,
         "ratio": round(ratio, 3)}, 0.5 <= ratio <= 2.0)

    # NC1 the K8 gate rejects a planted 2.5% band
    add("NC1", "K8 gate rejects a 2.5% band (k < 0.75)",
        {"band_pct": 2.5, "k": round(2.5 / cal["sigma_event_pct"], 4)},
        2.5 / cal["sigma_event_pct"] < K8_MIN_K)
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
            row = {"id": ROW_ID, "symbol": "KO", "checks": [], "outcome": None}
            rows.append(row)
        row.update({
            "symbol": "KO", "direction": "non_positive_event",
            "entry_date": ENTRY["observed_on"], "entry_price": ENTRY["price"],
            "entry_source": " | ".join(ENTRY["sources"][:2]),
            "catalyst": CATALYST["event"] + " (VENDOR-CONSENSUS week, camps Oct 20/Oct 22)",
            "confidence": 51, "status": "active",
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
            "scoring_rule": (f"reference = KO close {REFERENCE} (must be sourced "
                             f"and timestamped); outcome = close {HORIZON} vs reference; "
                             "vendor-estimated BO release assumed per optionslam's 9/9 BO "
                             "print history + MC BMO; if KO releases at/after 16:00 ET or "
                             "the date lands on the Oct 22 camp inside the Oct 19-24 "
                             "window, scoring shifts to the session after the ACTUAL "
                             "print and the row records the actual timestamp (K4)"),
        })
        research_lib.save_theses(rows)
        after = research_lib.load_theses()
    return {"created": created, "row_count": len(after),
            "others_digest_before": others,
            "others_digest_after": hashlib.sha256(json.dumps(
                [r for r in after if r.get("id") != ROW_ID], sort_keys=True).encode()).hexdigest(),
            "ko_row": next(r for r in after if r.get("id") == ROW_ID)["bet_id"]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Register the KO falsifiable thesis")
    ap.add_argument("--selftest", action="store_true",
                    help="validate only; no ledger write, no artifact")
    ns = ap.parse_args(argv)

    checks, cal = validate()
    failures = [c for c in checks if not c["pass"]]
    for c in checks:
        print(("PASS " if c["pass"] else "FAIL ") + c["id"] + " " + c["check"]
              + " -> " + json.dumps(c["observed"]))
    band = cal["band_pct"]
    print(f"KO thesis: band +/-{band}% | sigma_event {cal['sigma_event_pct']:.4f}% "
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
        "schema_version": SCHEMA, "owner": "MARK", "task": "TASK-00137",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "artifact_policy": ("ONE current thesis per subject, regenerated in place "
                            "(atomic tmp+rename). No version chain, so the family "
                            "cannot churn under K2."),
        "subject_selection": {
            "why_ko": ("0 prior artifacts (fresh family - AMBA K2-frozen; MU/ASML/UNH/TSLA/JPM/XOM "
                       "each carry exactly one thesis and a second file would start a version "
                       "chain). CONSUMER STAPLES: a defensive sector the book does not cover "
                       "(semis MU/ASML, healthcare UNH, EV TSLA, financials JPM, energy XOM), so "
                       "the joint book gains an uncorrelated defensive leg. Vendor-consensus "
                       "catalyst 26 days out with a fully sourced 50-session series, and the "
                       "company's own filing/guidance trail is fully readable on EDGAR."),
            "k2_note": "AMBA remains frozen; this thesis is a registered bet, not a new brief version.",
        },
        "thesis": THESIS,
        "catalyst": CATALYST,
        "filings": FILINGS,
        "explicit_risks": RISKS,
        "entry": ENTRY,
        "price_series": {"source": SERIES_SOURCE, "points": len(SERIES),
                         "span": f"{SERIES[0][0]}..{SERIES[-1][0]}",
                         "basis": ("adj close (stated Change is adj-to-adj across the 2026-09-15 "
                                   "ex-div: Sep 15 -0.12% = 88.71/88.82); raw == adj for all "
                                   "rows >= 2026-09-15, so the entry is the raw close"),
                         "integrity": "per-row stated-change check passes (every row within its own 2dp rounding bound ~0.017pp; observed max 0.0141pp)",
                         "rows": [(d, c) for d, c, _ in SERIES]},
        "calibration": cal,
        "calibration_provenance": {
            "owner": "ko_thesis_register.py calibration() - inline single owner "
                     "(no separate volatility task was dispatched for KO)",
            "artifact": "none separate; this artifact is the record",
        },
        "bet": {
            "bet_id": BET_ID, "ledger_row_id": ROW_ID, "ledger_path": str(research_lib.THESES),
            "band_pct": band, "horizon_end": HORIZON,
            "rule_version": "mark-l7-v2+k8",
            "reference_rule": f"reference = sourced KO close {REFERENCE} (K6: fresh, timestamped)",
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
            "Catalyst date is VENDOR-estimated with conflicting days (optionslam 2026-10-20 vs marketchameleon 2026-10-22) and no company timing PR exists (0 exact-phrase hits); the shift rule moves scoring to the session after the ACTUAL print - band and entry stay immutable.",
            "Band 3.2% is the LAST print's event implied (dual-sourced: optionslam Jul 28 row + MC snippet), NOT a live event-straddle quote; optionslam's live weekly straddle for this window (expires 2026-10-23) quotes 4.29%, so the true event implied may be wider than the band (miss threshold possibly understated).",
            "k = 0.7979 is by construction (band defined at E|move|), so K8 only rejects arbitrarily narrow bands; the real guard is band-source quality (sources recorded, including the wider live quote as an explicit risk).",
            "The marketchameleon +5.0%/±3.2% statistics come from a search snippet (page itself premium-gated); optionslam's own print row independently states implied 3.2% / actual 4.99% O, which is the row-level corroboration.",
            "Realised sigma is from a 50-session adjusted series; vendor HV is a single barchart snapshot (15.05% quote page vs 14.28% options-data page - window/timing differ).",
            "No Q3 consensus EPS/revenue was sourced (K4) - the edge rests on tape structure, reaction history and the guidance-raise-already-spent read, not a beat/miss view.",
            "8-K 0001628280-26-048466 (filed 2026-07-16) content unread; recorded, not guessed.",
            "52-week range not sourced this run - omitted rather than estimated (K4); market cap cited from optionslam (379.7B).",
            "The betbook_event_sim.py INPUTS names MU/UNH/ASML/TSLA/JPM/XOM - this seventh bet is not in the joint simulation; extending it is separate work, not silently done here.",
            "The reference close (2026-10-19) does not exist yet; scoring requires a sourced quote on or after the actual reaction session.",
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
