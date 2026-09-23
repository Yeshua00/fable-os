#!/usr/bin/env python3
"""betbook_event_sim.py — reproducible event simulation over the registered bet book.

TASK-00079 (volatility-model). Simulates the joint outcome distribution of the
two registered, K8-calibrated thesis bets (MU horizon 2026-10-01, ASML horizon
2026-10-14) so the book's aggregate event risk is quantified before either
horizon arrives. Fresh family: 0 prior betbook files, so K2 does not bind.

Deliberately adds NO new market numbers: every input is read at run time from
the two committed thesis artifacts (MU_THESIS_ACTIVE.json,
ASML_THESIS_ACTIVE.json, both clean at git HEAD 3d103d7), each of which already
passed its own K8 band gate and carries sourced, timestamped quotes (K4/K6
inherited, not re-quoted).

What it does and nothing else:
  1. recomputes each bet's analytic outcome probabilities from its committed
     calibration and asserts they match the artifact's own stated values
  2. builds the joint 3x3 (hit / no_edge / miss) distribution under an
     explicit independence assumption, plus assumption-FREE
     Frechet-Hoeffding bounds for the headline events so the independence
     choice is never load-bearing
  3. validates the arithmetic with a seeded Monte Carlo of independent PAIR
     draws (Box-Muller from random.random(), which CPython guarantees stable
     across versions, so a fixed seed reproduces bit-for-bit)
  4. regenerates ONE artifact (BETBOOK_EVENT_SIM.json, atomic tmp+rename) -
     no version chain, so the family cannot churn under K2

Usage:
    python3 betbook_event_sim.py            # validate + simulate + write artifact
    python3 betbook_event_sim.py --selftest # validate + negative controls only; no artifact
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

DIR = Path(__file__).resolve().parent
OUT = DIR / "BETBOOK_EVENT_SIM.json"
SCHEMA = "betbook-event-sim.v1"
INPUTS = [DIR / "MU_THESIS_ACTIVE.json", DIR / "ASML_THESIS_ACTIVE.json"]
RUN_ON = "2026-09-23"
SEED = 20260923
N_DRAWS = 200_000
MC_Z = 3.0            # pass tolerance: |empirical - analytic| <= 3 * standard errors
BUCKETS = ("hit", "no_edge", "miss")


# ── helpers ──────────────────────────────────────────────────────────────────
def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def box_muller(rng: random.Random, n: int) -> list:
    """Standard normals from random.random() only (stable across CPython versions)."""
    out = []
    while len(out) < n:
        u1 = rng.random() or 1e-12
        u2 = rng.random()
        r = math.sqrt(-2.0 * math.log(u1))
        out.append(r * math.cos(2.0 * math.pi * u2))
        if len(out) < n:
            out.append(r * math.sin(2.0 * math.pi * u2))
    return out


def classify(ret: float, band: float) -> str:
    if ret <= 0.0:
        return "hit"      # thesis direction is "non-positive"; any decline confirms
    if ret < band:
        return "no_edge"
    return "miss"


def analytic(band: float, sigma: float) -> dict:
    """Per-bet buckets: hit is the 0.5 null convention inherited from each artifact."""
    k = band / sigma
    return {"k": k,
            "hit": 0.5,
            "no_edge": norm_cdf(k) - 0.5,
            "miss": 1.0 - norm_cdf(k)}


def frechet(p: float, q: float) -> dict:
    """Assumption-free bounds for P(A and B) / P(A or B) given marginals p, q."""
    return {"inter_lo": round(max(0.0, p + q - 1.0), 12),
            "inter_hi": round(min(p, q), 12),
            "inter_indep": round(p * q, 12),
            "union_lo": round(max(p, q), 12),
            "union_hi": round(min(1.0, p + q), 12),
            "union_indep": round(p + q - p * q, 12)}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_inputs() -> list:
    bets = []
    for p in INPUTS:
        d = json.loads(p.read_text())
        c, b = d["calibration"], d["bet"]
        bets.append({"file": p.name, "sha256": sha(p),
                     "schema": d["schema_version"], "bet_id": b["bet_id"],
                     "horizon_end": b["horizon_end"], "band_pct": b["band_pct"],
                     "sigma_event_pct": c["sigma_event_pct"],
                     "k_artifact": c["band_k_sigmas"],
                     "p_artifact": {"hit": c["expected_p_hit"],
                                    "no_edge": c["expected_p_no_edge"],
                                    "miss": c["expected_p_miss"]}})
    return bets


def run_mc(bets: list, seed: int, n: int) -> dict:
    """Seeded MC: n independent PAIR draws -> empirical margins + joint 3x3."""
    rng = random.Random(seed)
    idx = {name: i for i, name in enumerate(BUCKETS)}
    joint = [[0] * 3 for _ in range(3)]
    z1s = box_muller(rng, n)
    z2s = box_muller(rng, n)
    for z1, z2 in zip(z1s, z2s):
        m1 = classify(z1 * bets[0]["sigma_event_pct"], bets[0]["band_pct"])
        m2 = classify(z2 * bets[1]["sigma_event_pct"], bets[1]["band_pct"])
        joint[idx[m1]][idx[m2]] += 1
    # bet0 margins are row sums, bet1 margins are column sums
    margins = [
        {bk: (sum(joint[i][j] for j in range(3)) if bi == 0
              else sum(row[i] for row in joint)) / n
         for i, bk in enumerate(BUCKETS)}
        for bi in range(2)]
    digest = hashlib.sha256(json.dumps(
        [[round(c / n, 12) for c in row] for row in joint],
        sort_keys=True).encode()).hexdigest()
    return {"seed": seed, "n": n,
            "joint_counts": joint,
            "joint_prob": [[round(c / n, 6) for c in row] for row in joint],
            "margins": margins,
            "digest": digest}


def validate(bets: list, mc: dict, joint: list) -> list:
    checks = []

    def add(cid, check, observed, ok):
        checks.append({"id": cid, "check": check, "observed": observed,
                       "pass": bool(ok)})

    a0 = analytic(bets[0]["band_pct"], bets[0]["sigma_event_pct"])
    a1 = analytic(bets[1]["band_pct"], bets[1]["sigma_event_pct"])

    # V1 inputs parse with the expected schema and are the committed files
    add("V1", "both inputs parse as market-thesis-active.v1 with sha256 recorded",
        {b["file"]: {"schema": b["schema"], "sha256": b["sha256"][:16],
                     "bet_id": b["bet_id"]} for b in bets},
        len(bets) == 2 and all(b["schema"] == "market-thesis-active.v1" for b in bets))
    # V2 internal consistency k == band / sigma_event (per artifact)
    k_ok, k_obs = True, {}
    for b in bets:
        k = b["band_pct"] / b["sigma_event_pct"]
        k_obs[b["bet_id"]] = {"k_recomputed": round(k, 10),
                              "k_artifact": b["k_artifact"]}
        k_ok &= abs(k - b["k_artifact"]) < 1e-9
    add("V2", "k == band/sigma_event matches the artifact's stated k (1e-9)",
        k_obs, k_ok)
    # V3 recomputed analytic probabilities == artifact's stated expected_p_*
    p_ok, p_obs = True, {}
    for a, b in zip((a0, a1), bets):
        p_obs[b["bet_id"]] = {bk: {"recomputed": round(a[bk], 12),
                                   "artifact": b["p_artifact"][bk]} for bk in BUCKETS}
        for bk in BUCKETS:
            p_ok &= abs(a[bk] - b["p_artifact"][bk]) < 1e-9
    add("V3", "recomputed analytic p matches each artifact (1e-9)", p_obs, p_ok)
    # V4 per-bet partition sums to 1
    parts = {b["bet_id"]: round(sum(a[bk] for bk in BUCKETS), 12)
             for a, b in zip((a0, a1), bets)}
    add("V4", "per-bet hit/no_edge/miss partition sums to 1",
        parts, all(abs(v - 1.0) < 1e-12 for v in parts.values()))
    # V5 joint matrix sums to 1; row marginals = bet0 analytics, col = bet1
    total = round(sum(sum(r) for r in joint), 12)
    rows = [round(sum(joint[i][j] for j in range(3)), 12) for i in range(3)]
    cols = [round(sum(joint[i][j] for i in range(3)), 12) for j in range(3)]
    marg_ok = (all(abs(rows[i] - a0[BUCKETS[i]]) < 1e-12 for i in range(3))
               and all(abs(cols[j] - a1[BUCKETS[j]]) < 1e-12 for j in range(3)))
    add("V5", "joint sums to 1 and marginals equal the per-bet analytics",
        {"sum": total, "rows": rows, "cols": cols}, abs(total - 1.0) < 1e-12 and marg_ok)
    # V6 independence: every analytic cell == product of the per-bet analytics
    worst = 0.0
    for i, ba in enumerate(BUCKETS):
        for j, bb in enumerate(BUCKETS):
            worst = max(worst, abs(joint[i][j] - a0[ba] * a1[bb]))
    add("V6", "every analytic joint cell == product of per-bet analytics",
        {"max_abs_dev": worst}, worst < 1e-12)
    # V7 empirical (MC) margins AND joint cells within 3 SE of analytic
    mc_ok, mc_obs = True, {}
    for bi in range(2):
        a = (a0, a1)[bi]
        for j, bk in enumerate(BUCKETS):
            p = a[bk]
            se = math.sqrt(max(p * (1 - p), 1e-12) / mc["n"])
            dev = abs(mc["margins"][bi][bk] - p)
            mc_obs[f"{bids(bets, bi)}:{bk}"] = {
                "mc": round(mc["margins"][bi][bk], 6), "analytic": round(p, 6),
                "dev": round(dev, 6), "tol": round(MC_Z * se, 6)}
            mc_ok &= dev <= MC_Z * se + 1e-12
    worst_cell = 0.0
    for i, ba in enumerate(BUCKETS):
        for j, bb in enumerate(BUCKETS):
            p = a0[ba] * a1[bb]
            se = math.sqrt(max(p * (1 - p), 1e-12) / mc["n"])
            dev = abs(mc["joint_prob"][i][j] - p)
            worst_cell = max(worst_cell, dev / se if se > 0 else 0.0)
            mc_ok &= dev <= MC_Z * se + 1e-12
    mc_obs["worst_joint_cell_z"] = round(worst_cell, 3)
    add("V7", f"MC margins and joint cells within {MC_Z} SE of analytic (n={mc['n']})",
        mc_obs, mc_ok)
    # V8 Frechet bounds contain the independence estimates
    fr_ok, fr_obs = True, {}
    for b0, b1 in (("miss", "miss"), ("hit", "hit")):
        f = frechet(a0[b0], a1[b1])
        fr_obs[f"{b0}&{b1}"] = f
        fr_ok &= f["inter_lo"] - 1e-12 <= f["inter_indep"] <= f["inter_hi"] + 1e-12
    add("V8", "independence estimates lie inside the Frechet bounds",
        fr_obs, fr_ok)
    # V9 MC determinism: same seed reproduces the same joint digest
    mc2 = run_mc(bets, mc["seed"], mc["n"])
    add("V9", "MC is deterministic for a fixed seed (digest matches on re-run)",
        {"first": mc["digest"][:16], "second": mc2["digest"][:16]},
        mc["digest"] == mc2["digest"])
    # V10 both horizons are in the future relative to the run date (prospective)
    add("V10", "both horizons are after the run date (sim is prospective, unscored)",
        {b["bet_id"]: b["horizon_end"] for b in bets},
        all(b["horizon_end"] > RUN_ON for b in bets))
    return checks


def bids(bets: list, bi: int) -> str:
    return bets[bi]["bet_id"]


def negative_controls(bets: list, mc: dict) -> list:
    """Prove the checks can actually fail."""
    ncs = []

    def add(cid, check, observed, ok):
        ncs.append({"id": cid, "check": check, "observed": observed,
                    "pass": bool(ok)})

    # NC1 a planted +1% band must break the k cross-check (V2)
    b = bets[0]
    k_bad = (b["band_pct"] * 1.01) / b["sigma_event_pct"]
    add("NC1", "V2 catches a planted +1% band (k no longer matches the artifact)",
        {"k_planted": round(k_bad, 6), "k_artifact": b["k_artifact"],
         "abs_dev": round(abs(k_bad - b["k_artifact"]), 6)},
        abs(k_bad - b["k_artifact"]) >= 1e-9)
    # NC2 a different seed must change the MC digest (V9 is seed-sensitive)
    mc_other = run_mc(bets, mc["seed"] + 1, mc["n"])
    add("NC2", "V9 digest is seed-sensitive (seed+1 gives a different digest)",
        {"seed_a": mc["seed"], "seed_b": mc["seed"] + 1,
         "digest_a": mc["digest"][:16], "digest_b": mc_other["digest"][:16]},
        mc["digest"] != mc_other["digest"])
    # NC3 a planted +5% sigma must break the analytic-vs-artifact p check (V3)
    a_bad = analytic(b["band_pct"], b["sigma_event_pct"] * 1.05)
    dev = max(abs(a_bad[bk] - b["p_artifact"][bk]) for bk in BUCKETS)
    add("NC3", "V3 catches a planted +5% sigma_event (probabilities diverge)",
        {"max_abs_dev": dev}, dev >= 1e-9)
    return ncs


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Simulate the registered bet book")
    ap.add_argument("--selftest", action="store_true",
                    help="validate + negative controls only; no artifact write")
    ns = ap.parse_args(argv)

    bets = load_inputs()
    a0 = analytic(bets[0]["band_pct"], bets[0]["sigma_event_pct"])
    a1 = analytic(bets[1]["band_pct"], bets[1]["sigma_event_pct"])
    joint = [[a0[ba] * a1[bb] for bb in BUCKETS] for ba in BUCKETS]
    mc = run_mc(bets, SEED, N_DRAWS)

    checks = validate(bets, mc, joint)
    ncs = negative_controls(bets, mc)
    failures = [c for c in checks if not c["pass"]]
    for c in checks:
        print(("PASS " if c["pass"] else "FAIL ") + c["id"] + " " + c["check"]
              + " -> " + json.dumps(c["observed"])[:200])
    for c in ncs:
        print(("PASS " if c["pass"] else "FAIL ") + c["id"] + " " + c["check"]
              + " -> " + json.dumps(c["observed"])[:200])

    book = {
        "p_at_least_one_decisive_indep": 1.0 - a0["no_edge"] * a1["no_edge"],
        "p_at_least_one_miss_indep": 1.0 - (1 - a0["miss"]) * (1 - a1["miss"]),
        "p_both_miss_indep": a0["miss"] * a1["miss"],
        "p_both_hit_indep": a0["hit"] * a1["hit"],
        "p_at_least_one_hit_indep": 1.0 - (1 - a0["hit"]) * (1 - a1["hit"]),
    }
    print(f"book: P(>=1 decisive)={book['p_at_least_one_decisive_indep']:.4f} "
          f"P(>=1 miss)={book['p_at_least_one_miss_indep']:.4f} "
          f"P(both miss)={book['p_both_miss_indep']:.4f} "
          f"P(>=1 hit)={book['p_at_least_one_hit_indep']:.4f}")
    print(f"MC n={mc['n']} seed={mc['seed']} digest={mc['digest'][:16]}")

    bad_nc = [c for c in ncs if not c["pass"]]
    if failures or bad_nc:
        print(f"ABORT: {len(failures)} validation failure(s) "
              f"{[c['id'] for c in failures]}, {len(bad_nc)} negative-control "
              f"failure(s) {[c['id'] for c in bad_nc]}", file=sys.stderr)
        return 1
    if ns.selftest:
        print(f"selftest only: {len(checks)}/{len(checks)} checks + "
              f"{len(ncs)}/{len(ncs)} negative controls pass, no artifact")
        return 0

    f_both_miss = frechet(a0["miss"], a1["miss"])
    f_both_hit = frechet(a0["hit"], a1["hit"])
    f_both_dec = frechet(1 - a0["no_edge"], 1 - a1["no_edge"])
    doc = {
        "schema_version": SCHEMA, "owner": "MARK", "task": "TASK-00079",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "artifact_policy": ("ONE current simulation, regenerated in place "
                            "(atomic tmp+rename). No version chain (K2)."),
        "purpose": ("quantify the joint event risk of the registered bet book "
                    "before either horizon arrives; read-only simulation, no new "
                    "market numbers, no trades, no recommendations"),
        "inputs": bets,
        "assumptions": [
            "independence between the two bets (point estimates); never load-bearing because Frechet-Hoeffding bounds for the same events are reported alongside",
            "each bet's event return ~ Normal(0, sigma_event) with sigma_event taken from that artifact's own conservative K8 calibration (max of the vendor implied move read as 1 sigma vs as E|move|)",
            "hit = 0.5 per bet is the null convention inherited from each artifact (P(non-positive)=50%); it is NOT an edge claim - the claimed edges live in each thesis file",
            "no fat-tail overlay: Gaussian tails understate the mass of extreme earnings moves",
            "the two horizons are distinct sessions (2026-10-01 and 2026-10-14), so no session is double-counted",
        ],
        "analytic": {
            "per_bet": {
                bets[i]["bet_id"]: dict(
                    {bk: round(a[bk], 6) for bk in BUCKETS},
                    k=round(a["k"], 6),
                    band_pct=bets[i]["band_pct"],
                    sigma_event_pct=bets[i]["sigma_event_pct"],
                    horizon_end=bets[i]["horizon_end"])
                for i, a in enumerate((a0, a1))},
            "joint_independence": {
                ba: {bb: round(joint[i][j], 6) for j, bb in enumerate(BUCKETS)}
                for i, ba in enumerate(BUCKETS)},
            "book_headlines": {k: round(v, 6) for k, v in book.items()},
            "frechet_bounds": {"both_miss": f_both_miss,
                               "both_hit": f_both_hit,
                               "both_decisive": f_both_dec},
        },
        "monte_carlo": mc,
        "validation": checks,
        "negative_controls": ncs,
        "validation_summary": {"total": len(checks), "failed": 0,
                               "negative_controls": len(ncs), "nc_failed": 0},
        "limitations": [
            "n=2 bets: these are reproducible consequences of the two committed calibrations, not a measured distribution over a sample (K3 honesty - no hit rate is claimed until horizons score)",
            "Gaussian event returns: real earnings returns are fat-tailed, so tail numbers like P(both miss) are likely understated; the Frechet bounds are the assumption-free fallback",
            "sigma_event inputs inherit each vendor implied-move quote's convention risk (documented in each thesis artifact)",
            "the MC leg validates arithmetic only - it carries no information beyond the analytic result (V7/V9)",
            "cross-bet correlation in reality is not zero (shared semiconductor factor); bounds bracket it, the point estimate assumes independence",
            "simulation is prospective: both outcomes are unscored until 2026-10-01 and 2026-10-14 with sourced quotes",
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
