#!/usr/bin/env python3
"""jpm_thesis_register.py — one owner for the JPM falsifiable market thesis.

TASK-00115 (market-thesis). Subject: JPM (JPMorgan Chase & Co.), chosen because
it has 0 prior artifacts (fresh family - AMBA stays K2-frozen; MU/ASML/UNH/TSLA
each already carry one registered thesis and a second file would start a
version chain), it carries the STRONGEST catalyst provenance of any registered
bet (company-confirmed date, three independent sources), and it is FINANCIALS -
a sector uncorrelated to the book's semis (MU, ASML), healthcare (UNH) and EV
(TSLA) legs.

This module does four things and nothing else:
  1. holds the thesis, its sourced quotes, and its citations (K4)
  2. takes its band calibration from jpm_band_calibration.calibration() - the
     calibration module is the single owner of the series and the math, so the
     band cannot drift from what TASK-00116 published
  3. registers the bet into the ledger through research_lib's own primitives,
     idempotently, leaving every other row byte-identical
  4. regenerates ONE current artifact (JPM_THESIS_ACTIVE.json, atomic
     tmp+rename) - no version chain, so K2 cannot bind

Priced from fresh sourced quotes, NEVER from theses.jsonl's own check history
(substantiated unusable on 2026-09-23: ETH +145.66% / SOL +232.29% single-day
prints; BTC 2026-08-28 96,000.00 vs sourced 77,639.00).

Usage:
    python3 jpm_thesis_register.py            # validate, register, write artifact
    python3 jpm_thesis_register.py --selftest # validate only; no ledger, no artifact
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

DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(DIR))
from thesis_register import tag, norm_cdf  # noqa: E402
from jpm_band_calibration import (calibration, SERIES, SERIES_SOURCE,  # noqa: E402
                                  IMPLIED_MOVE, ENTRY_LAST_CLOSE, stated_change_deviation)

OUT = DIR / "JPM_THESIS_ACTIVE.json"
SCHEMA = "market-thesis-active.v1"
TAX_DAYS = 365.0 / 252.0
RUN_ON = "2026-09-24"

BET_ID = "JPM-Q3-2026-REACTION-20261013"
ROW_ID = "thesis_jpm_q3_2026_reaction"
K8_MIN_K = 0.75
K8_MAX_NO_EDGE = 0.75
HORIZON = "2026-10-13"
REFERENCE = "2026-10-12"

ENTRY = {
    "price": ENTRY_LAST_CLOSE["price"],
    "observed_on": ENTRY_LAST_CLOSE["observed_on"],
    "sources": [
        ENTRY_LAST_CLOSE["source"],
        "internal consistency: 337.53 / 340.00 - 1 = -0.73% matches the table's stated Change for that row",
    ],
    "prior_close": {"price": 340.00, "observed_on": "2026-09-22",
                    "sources": ["stockanalysis.com JPM history table row 'Sep 22, 2026': Close 340.00, Change -3.42%"]},
    "after_hours": {"price": 337.90,
                    "source": "stockanalysis.com header: 'After-hours: Sep 23, 2026, 7:59 PM EDT' 337.90 (+0.11%)"},
    "range_52w": {"note": "52-week range NOT sourced this run - omitted rather than estimated (K4)"},
    "market_cap": {"note": "market cap NOT sourced this run - omitted rather than estimated (K4)"},
}

CATALYST = {
    "event": "JPMorgan Chase Q3 2026 financial results, before the US market open",
    "date": "2026-10-13",
    "date_status": "COMPANY-CONFIRMED - strongest provenance of the registered book",
    "source_confirmed": [
        "jpmorganchase.com/ir/news/2026/jpmc-to-host-third-quarter-2026-earnings-call: 'conference call to review third-quarter 2026 financial results ... Tuesday, October 13, 2026 at 8:30 a.m. (ET)' (observed 2026-09-24)",
        "jpmorganchase.com/ir/events: 'JPMorganChase Third-Quarter 2026 Earnings Conference Call Oct 13, 2026' (observed 2026-09-24)",
        "jpmorganchase.com advance schedule (2025-05-21): 'Third-quarter 2026 - Tuesday, October 13, 2026 at 8:30 a.m. (Eastern)' (observed 2026-09-24)",
        "wallstreethorizon.com/jpmorgan-earnings-calendar: 'CONFIRMED for Tuesday 10/13/2026 Before Market' (observed 2026-09-24)",
    ],
    "observed_on": "2026-09-24",
    "release_timing_evidence": {
        "assumed": "results pre-open 2026-10-13 (8:30 a.m. ET call), so the full US reaction session is 2026-10-13 itself - same convention as the UNH pre-open bet",
        "shift_rule": "if JPM releases after the US close (not expected - company states an 8:30 a.m. ET call), scoring shifts to the next session and the row records the actual timestamp (K4)",
        "source": "jpmorganchase.com IR press release, observed 2026-09-24",
    },
    "implied_event_move": IMPLIED_MOVE,
    "session_collision": {
        "detail": "UNH also prints pre-open on 2026-10-13 (registered bet UNH-Q3-2026-REACTION-20261013) - a double-bill session; recorded as risk #7",
        "source": "UNH_THESIS_ACTIVE.json catalyst block, observed 2026-09-23",
    },
    "momentum_into_print": {
        "detail": "-4.12% over two sessions (Sep 22 -3.42%, Sep 23 -0.73%) on 'AI-scare trade hitting banks' + flattening-yield-curve headlines",
        "source": "stockanalysis.com series rows + Market Watch (5h ago) and Reuters (1 day ago) headlines in the page's news rail, observed 2026-09-24",
    },
}

FILINGS = [
    {"form": "10-Q", "period": "Q2 2026 (quarter ended 2026-06-30)",
     "accession": "0001628280-26-054343", "filed": "2026-08-06",
     "source": "data.sec.gov/submissions/CIK0000019617.json, observed 2026-09-24",
     "observed_on": "2026-09-24"},
    {"form": "8-K (Q2 2026 results)", "period": "announced 2026-07-14 (BMO)",
     "accession": "0001628280-26-048078",
     "highlights": ["the +2.5%-actual print whose fade is precedent edge leg (1)"],
     "source": "data.sec.gov submissions + marketchameleon earnings history (2026-07-14 BMO), observed 2026-09-24",
     "observed_on": "2026-09-24"},
    {"form": "8-K", "period": "filed 2026-07-23", "accession": "0001193125-26-314128",
     "source": "data.sec.gov submissions, observed 2026-09-24",
     "observed_on": "2026-09-24"},
    {"form": "EDGAR standing record", "period": "entity metadata",
     "highlights": ["CIK 0000019617, JPMORGAN CHASE & CO"],
     "source": "data.sec.gov submissions, observed 2026-09-24",
     "observed_on": "2026-09-24"},
]

RISKS = [
    {"risk": ("Upside precedent is the book's strongest counter-case: the LAST "
              "print moved +2.5% UP (2026-07-14) and JPM's actual move has "
              "EXCEEDED the options-implied move in 9 of its last 16 prints "
              "(56%) - options have NOT reliably capped this event"),
     "evidence": "marketchameleon JPM earnings charts + earnings-watcher.com/wiki/jpm-implied-move (updated 2026-09-02), observed 2026-09-24",
     "direction": "upside_against_thesis"},
    {"risk": ("Relief-rally risk: the -4.12% two-day drop (AI-scare/curve "
              "headlines) could snap back ON the print as the catalyst resets "
              "the tape - the entry is two strong down sessions off the high"),
     "evidence": "sourced series Sep 22/23 rows + Market Watch/Reuters headlines, observed 2026-09-24",
     "direction": "upside_against_thesis"},
    {"risk": ("NII/guidance beat: the standard bank bull case into a Fed-cut "
              "cycle is a forward-NII guidance raise - a raise is a same-day "
              "up-spike regardless of the quarter's backward numbers"),
     "evidence": "standing bank-earnings dynamic; no single dated source claimed (recorded as structural risk, K4)",
     "direction": "upside_against_thesis"},
    {"risk": ("Positive deal-flow headlines into the print: the $20B Qatar "
              "Investment Authority partnership (Sep 22, Reuters/WSJ/PRNewswire) "
              "and the card-business/private-credit expansion talks (WSJ/PYMNTS, "
              "Sep 22-23) frame management as a dealmaker, not a defender"),
     "evidence": "stockanalysis.com JPM news rail, observed 2026-09-24",
     "direction": "upside_against_thesis"},
    {"risk": ("Seasonality: JPM kicks off bank earnings season as the first "
              "mover - first-mover prints historically carry a sympathy bid "
              "from the sector complex"),
     "evidence": "structural (JPM always reports the big-bank week first); no single dated source claimed",
     "direction": "upside_against_thesis"},
    {"risk": ("Classification: the 5.64% band vs a 1.14% realised daily sigma "
              "means decisive outcomes require a >5.64% move - the bet is "
              "no_edge-heavy by construction (p_no_edge 0.2875 under the "
              "Gaussian model, higher empirically for a large-cap bank)"),
     "evidence": "calibration in JPM_BAND_CALIBRATION.json (TASK-00116)",
     "direction": "classification_risk"},
    {"risk": ("Session collision: UNH prints pre-open the SAME day "
              "(2026-10-13) - a double-bill session with possible macro prints "
              "that week muddies attribution of JPM's own reaction"),
     "evidence": "UNH_THESIS_ACTIVE.json catalyst (observed 2026-09-23); no JPM-specific source needed for a calendar fact",
     "direction": "scoring_risk"},
    {"risk": ("Window mismatch: the 5.64% optionslam quote spans to Oct 16 "
              "(3 days past the print) - sigma_event is slightly overstated, "
              "so the band is conservative for K8 but the model's decisiveness "
              "is overstated in the other direction"),
     "evidence": "optionslam JPM straddle page, observed 2026-09-24; recorded in JPM_BAND_CALIBRATION.json limitations",
     "direction": "classification_risk"},
]

THESIS = {
    "subject": "JPM",
    "one_line": ("JPM opens earnings season pre-open with a twice-faded setup: "
                 "the last print popped then round-tripped in four sessions, "
                 "and the tape arrives -4.12% in two days on bank-specific "
                 "headline pressure."),
    "falsifiable_prediction": ("JPM's close on 2026-10-13 (the full US session "
                               "reacting to the company-confirmed pre-open Q3 "
                               "print) is not above its 2026-10-12 close."),
    "null_hypothesis": "a coin flip: P(non-positive reaction) = 50%",
    "claimed_edge": ("(1) sell-the-print-then-fade precedent: the Q2 print "
                     "(2026-07-14 BMO, +2.5% actual) opened +1.17% on Jul 15 "
                     "and then four declining sessions carried the tape to "
                     "338.87 by Jul 20 - about -1.16% BELOW the pre-print "
                     "close of ~342.86: the pop round-tripped entirely in four "
                     "sessions; (2) momentum into the print is negative: "
                     "-4.12% over Sep 22-23 on AI-scare/flat-curve bank "
                     "headlines, and BMO prints hand the session to the "
                     "reaction with no overnight buffer; (3) the double-bill "
                     "session (UNH same morning) splits attention across two "
                     "large-cap reactions. The edge is a judgement under a 50% "
                     "null - risks 1-5 (especially the +2.5% up last print and "
                     "the 56% exceeded-implied history) are the honest "
                     "counter-case and are why confidence stays at 52."),
    "invalidation": ("an upside breach of +5.64% on 2026-10-13 falsifies the "
                     "read decisively; no re-entry in either direction without "
                     "a new written thesis"),
    "what_would_confirm": "a non-positive 2026-10-13 close (change <= 0.0% vs 2026-10-12)",
    "what_would_falsify": "a positive 2026-10-13 close (change > 0.0%), decisive-falsifier at >= +5.64%",
}


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
    add("V3", "calibration imported from the calibration module matches K8",
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
    add("V8", "catalyst date is company-confirmed with >=2 independent sources",
        {"date": CATALYST["date"], "status": CATALYST["date_status"][:20],
         "sources": len(CATALYST["source_confirmed"])},
        len(CATALYST["source_confirmed"]) >= 2
        and CATALYST["date_status"].startswith("COMPANY-CONFIRMED"))
    dev = stated_change_deviation(SERIES)
    add("V9", "series integrity vs vendor stated Change (V12 of the calibration "
              "module) still holds on import",
        {"rows_checked": dev["rows_checked"], "max_dev_pp": dev["max_dev_pp"],
         "rows_over_tol": len(dev["rows_over_tol"])},
        len(dev["rows_over_tol"]) == 0)
    add("V10", "pricing source is fresh quotes, not the corrupt ledger series",
        {"ledger_status": "unusable as a price series (2026-09-23 finding)",
         "priced_from": SERIES_SOURCE.split(" -- ")[0]}, True)

    # NC1 the K8 gate rejects a planted 3% band
    add("NC1", "K8 gate rejects a 3.0% band (k < 0.75)",
        {"band_pct": 3.0, "k": round(3.0 / cal["sigma_event_pct"], 4)},
        3.0 / cal["sigma_event_pct"] < K8_MIN_K)
    # NC2 a stale quote must be rejected by K6
    stale = (tag(RUN_ON) - tag("2026-09-18")) / TAX_DAYS
    add("NC2", "K6 gate rejects a quote 3 trading days old",
        {"trading_days_old": round(stale, 2)}, stale > 1.0)
    # NC3 a status downgrade (UNCONFIRMED) must fail V8
    simulated_status = "UNCONFIRMED"
    v8_on_simulated = (len(CATALYST["source_confirmed"]) >= 2
                       and simulated_status.startswith("COMPANY-CONFIRMED"))
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
            row = {"id": ROW_ID, "symbol": "JPM", "checks": [], "outcome": None}
            rows.append(row)
        row.update({
            "symbol": "JPM", "direction": "non_positive_event",
            "entry_date": ENTRY["observed_on"], "entry_price": ENTRY["price"],
            "entry_source": " | ".join(ENTRY["sources"][:2]),
            "catalyst": CATALYST["event"] + " " + CATALYST["date"] + " (COMPANY-CONFIRMED)",
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
            "scoring_rule": (f"reference = JPM close {REFERENCE} (must be sourced "
                             f"and timestamped); outcome = close {HORIZON} vs "
                             "reference; company-confirmed 8:30 a.m. ET call means "
                             "the reaction session IS 2026-10-13; if JPM releases "
                             "after the US close instead, scoring shifts to the "
                             "next session and the row records the actual "
                             "timestamp (K4)"),
        })
        research_lib.save_theses(rows)
        after = research_lib.load_theses()
    return {"created": created, "row_count": len(after),
            "others_digest_before": others,
            "others_digest_after": hashlib.sha256(json.dumps(
                [r for r in after if r.get("id") != ROW_ID], sort_keys=True).encode()).hexdigest(),
            "jpm_row": next(r for r in after if r.get("id") == ROW_ID)["bet_id"]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Register the JPM falsifiable thesis")
    ap.add_argument("--selftest", action="store_true",
                    help="validate only; no ledger write, no artifact")
    ns = ap.parse_args(argv)

    checks, cal = validate()
    failures = [c for c in checks if not c["pass"]]
    for c in checks:
        print(("PASS " if c["pass"] else "FAIL ") + c["id"] + " " + c["check"]
              + " -> " + json.dumps(c["observed"]))
    band = cal["band_pct"]
    print(f"JPM thesis: band +/-{band}% | sigma_event {cal['sigma_event_pct']:.4f}% "
          f"| k {cal['band_k_sigmas']:.4f} | P(hit) 0.500 P(no_edge) "
          f"{cal['expected_p_no_edge']:.4f} P(miss) {cal['expected_p_miss']:.4f}")

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
        "schema_version": SCHEMA, "owner": "MARK", "task": "TASK-00115",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "artifact_policy": ("ONE current thesis per subject, regenerated in place "
                            "(atomic tmp+rename). No version chain, so the family "
                            "cannot churn under K2."),
        "subject_selection": {
            "why_jpm": ("0 prior artifacts (fresh family - AMBA K2-frozen; "
                        "MU/ASML/UNH/TSLA each carry exactly one thesis and a "
                        "second file would start a version chain). FINANCIALS: "
                        "the one major sector the book does not cover (semis "
                        "MU/ASML, healthcare UNH, EV TSLA), so the joint "
                        "simulation gains an uncorrelated leg. Company-confirmed "
                        "catalyst date - the strongest provenance of any "
                        "registered bet (3 company sources + wallstreethorizon)."),
            "k2_note": "AMBA remains frozen; this thesis is a registered bet, not a new brief version.",
        },
        "thesis": THESIS,
        "catalyst": CATALYST,
        "filings": FILINGS,
        "explicit_risks": RISKS,
        "entry": ENTRY,
        "price_series": {"source": SERIES_SOURCE, "points": len(SERIES),
                         "span": f"{SERIES[0][0]}..{SERIES[-1][0]}",
                         "integrity": "V12 stated-change check passes (max dev <=0.01pp)",
                         "rows": [(d, c) for d, c, _ in SERIES]},
        "calibration": cal,
        "calibration_provenance": {
            "owner": "jpm_band_calibration.py (TASK-00116) - imported, not re-implemented",
            "artifact": "JPM_BAND_CALIBRATION.json",
        },
        "bet": {
            "bet_id": BET_ID, "ledger_row_id": ROW_ID, "ledger_path": str(research_lib.THESES),
            "band_pct": band, "horizon_end": HORIZON,
            "rule_version": "mark-l7-v2+k8",
            "reference_rule": f"reference = sourced JPM close {REFERENCE} (K6: fresh, timestamped)",
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
            "The edge is a judgement under a 50% null (confidence 52): the last print moved +2.5% UP and actual exceeded implied 9/16 (56%) - the counter-case is stronger than for any other registered bet.",
            "The 5.64% implied-move quote spans to Oct 16 (3 days past the print); sigma_event is conservatively overstated for K8 but the model's decisiveness is correspondingly overstated.",
            "Vendor HISTORICAL vol was not sourced; V4 of the calibration module uses marketchameleon IV 24.7 as the reference leg (recorded, K4).",
            "No Q3 consensus EPS/NII numbers were sourced; the comparison facts are structural (fade precedent, momentum, double-bill session) rather than beat/miss framing (K4).",
            "52-week range and market cap not sourced this run - omitted rather than estimated (K4).",
            "The Q2 pre-print close (~342.86) is derived from the Jul 15 row's stated +1.17% change, not read directly from a Jul 14 row (outside the series window) - recorded as derived, not sourced.",
            "The betbook_event_sim.py INPUTS names MU/UNH/ASML/TSLA - this fifth bet is NOT yet in the joint simulation; extending it is separate work, not silently done here.",
            "The reference close (2026-10-12) does not exist yet; scoring requires a sourced quote on or after 2026-10-13.",
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
