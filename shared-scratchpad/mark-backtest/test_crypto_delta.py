#!/usr/bin/env python3
"""test_crypto_delta.py — persisted regression suite for crypto_delta.py.

Consolidates the adversarial groups that previously lived only in
scrollback (flagged twice in audits as "verification not repeatable").
Stdlib asserts; every stateful test runs against tmp copies of the real
ledger/outbox — real stores are never mutated (sha256-verified in the
ritual, not here).

Run: python3 test_crypto_delta.py        (exit 0 = all pass)
"""
import fcntl
import importlib.util
import json
import shutil
import sys
import tempfile
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
LEDGER = Path.home() / ".freebuff/market-research/theses.jsonl"
REAL_BASELINES = HERE / "crypto_baselines.json"


def load_module():
    """Import crypto_delta via importlib.

    Register in sys.modules BEFORE exec — py3.9 dataclasses resolve
    cls.__module__ through sys.modules and blow up otherwise.
    """
    spec = importlib.util.spec_from_file_location(
        "crypto_delta", str(HERE / "crypto_delta.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["crypto_delta"] = mod
    spec.loader.exec_module(mod)
    return mod


def tmp_stores(cd):
    """Context manager-ish helper: patched THESES/OUTBOX/REPORT on tmp
    copies, restored on exit. Returns (td_path, restore_fn) via with-block."""
    class _Ctx:
        """Patched THESES/OUTBOX/REPORT on tmp copies; BASELINES_PATH is
        snapshotted too so tests may override it freely — restore always
        happens on exit (success or failure)."""
        def __enter__(self):
            self.td = tempfile.TemporaryDirectory()
            self.p = Path(self.td.name)
            self.led = self.p / "theses.jsonl"
            self.OUTBOX_PATH = self.p / "outbox.jsonl"
            self.REPORT_PATH = self.p / "R.md"
            shutil.copy(LEDGER, self.led)
            self.orig = (cd.research_lib.THESES, cd.OUTBOX_PATH, cd.REPORT_PATH,
                         cd.BASELINES_PATH, cd.research_lib.load_theses,
                         cd.fbr.now_iso)
            cd.research_lib.THESES = self.led
            cd.OUTBOX_PATH = self.OUTBOX_PATH
            cd.REPORT_PATH = self.REPORT_PATH
            return self

        def __exit__(self, *exc):
            (cd.research_lib.THESES, cd.OUTBOX_PATH, cd.REPORT_PATH,
             cd.BASELINES_PATH, cd.research_lib.load_theses,
             cd.fbr.now_iso) = self.orig
            self.td.cleanup()
            return False
    return _Ctx()


def args3(day="2026-09-22", task="T-TEST"):
    """CLI args for the canonical three quotes (each with its --price flag)."""
    out = ["--task", task, "--verdict", "v"]
    for spec in (f"BTC=85968|Forbes|{day}",
                 f"ETH=2762|MetaMask|{day}",
                 f"SOL=117.00|Paybis|{day}"):
        out += ["--price", spec]
    return out


# ── groups ──────────────────────────────────────────────────────────

def test_parse_boundary(cd):
    """Non-finite/impossible/malformed specs rejected; sane spec parses."""
    bad_specs = (
        "BTC=inf|s|2026-09-22", "BTC=nan|s|2026-09-22",
        "BTC=1e999|s|2026-09-22", "BTC=-5|s|2026-09-22",
        "BTC=10|s|2026-13-45", "BTC=10|s|2026-9-222",
        "BTC=10|s|not-a-date", "BTC85968",
        "BTC=abc|s|2026-09-22", "=10|s|2026-09-22",
    )
    for spec in bad_specs:
        try:
            cd.parse_quote(spec)
            raise AssertionError(f"accepted bad spec {spec!r}")
        except ValueError:
            pass
    q = cd.parse_quote("btc=85968|Forbes; PT=$90|2026-09-22")
    assert (q.symbol, q.price) == ("BTC", 85968.0)


def test_compute_deltas_and_control(cd):
    """Delta math matches the audit-verified numbers; control fails for the
    right reason so we trust the suite's passes."""
    quotes = [cd.Quote("BTC", 85968.0, "t", "2026-09-22"),
              cd.Quote("ETH", 2762.0, "t", "2026-09-22"),
              cd.Quote("SOL", 117.0, "t", "2026-09-22")]
    bl = [cd.Baseline("2026-09-10", {"BTC": 78850.0, "ETH": 2501.0, "SOL": 104.76}, "a"),
          cd.Baseline("2026-09-20", {"BTC": 81235.0, "ETH": 2502.0, "SOL": 110.73}, "b")]
    d = cd.compute_deltas(quotes, bl)
    assert round(d["BTC"]["2026-09-20"], 1) == 5.8
    assert round(d["BTC"]["2026-09-10"], 1) == 9.0
    assert round(d["ETH"]["2026-09-20"], 1) == 10.4
    assert round(d["SOL"]["2026-09-10"], 1) == 11.7
    try:
        assert round(d["BTC"]["2026-09-20"], 1) == 6.0
    except AssertionError:
        pass  # control fails for the right reason: wrong expectation detected
    else:
        raise AssertionError("control passed when it must not — suite cannot fail")


def test_dup_symbol_zero_write(cd):
    """Duplicate symbols (post-case-normalization) fail BEFORE any write."""
    with tmp_stores(cd) as t:
        before = t.led.stat().st_size
        r = cd.main(["--task", "T-DUP",
                     "--price", "BTC=85968|s|2026-09-22",
                     "--price", "btc=999|typo|2026-09-22"])
        assert not r[0] and "duplicate symbol" in r[1], r
        assert not t.OUTBOX_PATH.exists() and not t.REPORT_PATH.exists()
        assert t.led.stat().st_size == before, "ledger written despite rejection"


def test_missing_store(cd):
    """Unreadable/missing baseline store → (False, msg), not a traceback,
    and zero writes anywhere."""
    with tmp_stores(cd) as t:
        cd.BASELINES_PATH = t.p / "missing_store.json"
        before = t.led.stat().st_size
        r = cd.main(["--price", "BTC=1|s|2026-09-22"])
        assert not r[0] and "No such file" in r[1], r
        assert t.led.stat().st_size == before
        assert not t.OUTBOX_PATH.exists()


def test_seams_call_time(cd):
    """Rebound module constants actually redirect (None-default call-time
    resolution — the def-capture trap)."""
    with tmp_stores(cd) as t:
        ok, why = cd.emit_completion(
            "T-SEAM", "s", t.REPORT_PATH, "2026-09-22T05:00:00Z")
        assert ok and t.OUTBOX_PATH.exists() and len(
            t.OUTBOX_PATH.read_text().splitlines()) == 1, (ok, why)
        store = t.p / "b.json"
        store.write_text(
            '{"baselines":[{"date":"2026-01-01","prices":{"BTC":1}}]}')
        cd.BASELINES_PATH = store
        assert cd.load_baselines()[0].date == "2026-01-01"


def test_lock_serializes(cd):
    """Guard at the source: a real upsert BLOCKS while ledger_tx is held,
    completes after release (lock proven free via non-blocking flock),
    and a delta check appended afterwards survives alongside the upsert's
    check — the reverse-clobber pair, both real entry points."""
    with tmp_stores(cd) as t:
        done = threading.Event()

        def run_upsert():
            # market-research.v1: quotes live under "tickers" (schema shape)
            cd.research_lib.upsert_theses(
                {"tickers": {"BTC": {"price": 65000.0,
                                     "context": "lock probe"}}})
            done.set()

        with cd.research_lib.ledger_tx():
            th = threading.Thread(target=run_upsert)
            th.start()
            time.sleep(0.15)
            assert not done.is_set(), "upsert did NOT block on held lock"
        th.join(timeout=5)
        assert done.is_set(), "upsert never completed after release"
        with open(str(t.led) + ".lock", "a") as f:
            try:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise AssertionError("lock not released after ledger_tx")
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        cd.append_ledger_checks(
            [cd.Quote("BTC", 65432.0, "s", "2026-09-26")], "lock test",
            "2026-09-26T10:00:00Z")
        btc = next(r for r in cd.research_lib.load_theses()
                   if r["symbol"] == "BTC")
        notes = [c.get("note", "") for c in btc["checks"]]
        assert any("lock probe" in n for n in notes), "upsert check lost"
        assert any("delta-check 2026-09-26" in n for n in notes), "delta check lost"


def test_upsert_entry(cd):
    """The worker's entry point (upsert_theses) runs through the atomic
    save on a tmp ledger: appends the check, file parses, no .tmp."""
    with tmp_stores(cd) as t:
        # market-research.v1: quotes live under "tickers" (schema shape)
        cd.research_lib.upsert_theses(
            {"tickers": {"BTC": {"price": 64000.0,
                                 "context": "upsert probe"}}})
        btc = next(r for r in cd.research_lib.load_theses()
                   if r["symbol"] == "BTC")
        assert any(c.get("note") == "upsert probe" and c.get("price") == 64000.0
                   for c in btc["checks"]), btc["checks"][-3:]
        assert not Path(str(t.led) + ".tmp").exists()


def test_idempotency(cd):
    """Same (symbol, UTC day, price) suppressed; genuinely new price appends."""
    with tmp_stores(cd) as t:
        rows = cd.research_lib.load_theses()
        _, a1 = cd.apply_checks(
            rows, [cd.Quote("BTC", 85968.0, "s", "2026-09-25")],
            "v1", "2026-09-25T10:00:00Z")
        btc = next(r for r in rows if r["symbol"] == "BTC")
        n0 = len(btc["checks"])
        assert a1 and len(btc["checks"]) == n0
        lines, a2 = cd.apply_checks(
            rows, [cd.Quote("BTC", 85968.0, "s", "2026-09-25")],
            "v2", "2026-09-25T11:00:00Z")
        assert not a2 and "suppressed" in lines[0]
        assert len(btc["checks"]) == n0
        _, a3 = cd.apply_checks(
            rows, [cd.Quote("BTC", 86100.0, "s", "2026-09-25")],
            "v3", "2026-09-25T12:00:00Z")
        assert a3 and len(btc["checks"]) == n0 + 1


def test_completion_contract(cd):
    """Typed outcome at the source: emitted/suppressed both ok=True with
    distinct detail; no-task-id and write failure are (False, msg);
    envelope carries bl-40 fields; later date re-emits."""
    with tempfile.TemporaryDirectory() as td:
        ob = Path(td) / "o.jsonl"
        art = Path("/x/CRYPTO_PORTFOLIO_DELTA.md")
        ok1, why1 = cd.emit_completion(
            "T-C", "s", art, "2026-09-22T01:00:00Z", outbox=ob)
        assert ok1 and "emitted" in why1, (ok1, why1)
        n1 = len(ob.read_text().splitlines())
        ok2, why2 = cd.emit_completion(
            "T-C", "s", art, "2026-09-22T02:00:00Z", outbox=ob)
        assert ok2 and "suppressed" in why2, (ok2, why2)
        assert len(ob.read_text().splitlines()) == n1, "duplicate wrote bytes"
        ok3, _ = cd.emit_completion(
            "T-C", "s", art, "2026-09-23T01:00:00Z", outbox=ob)
        assert ok3 and len(ob.read_text().splitlines()) == 2
        row = json.loads(ob.read_text().splitlines()[0])
        assert row["schema_version"] == "1.0.0"
        assert row["correlation_id"] and row["ts"]
        ok4, why4 = cd.emit_completion(
            None, "s", art, "2026-09-22T03:00:00Z", outbox=ob)
        assert not ok4 and "no task id" in why4
        # write failure (outbox path is a directory) → (False, msg), typed
        with tempfile.TemporaryDirectory() as td2:
            ok5, why5 = cd.emit_completion(
                "T-C", "s", art, "2026-09-24T01:00:00Z", outbox=Path(td2))
            assert not ok5 and "outbox write failed" in why5, (ok5, why5)


def test_render(cd):
    """Report shows computed pcts, labels caller judgment, and never
    asserts unsourced comparatives; concision guard from the audit."""
    quotes = [cd.Quote("BTC", 85968.0, "t", "2026-09-22"),
              cd.Quote("ETH", 2762.0, "t", "2026-09-22"),
              cd.Quote("SOL", 117.0, "t", "2026-09-22")]
    bl = [cd.Baseline("2026-09-10", {"BTC": 78850.0, "ETH": 2501.0, "SOL": 104.76}, "a"),
          cd.Baseline("2026-09-20", {"BTC": 81235.0, "ETH": 2502.0, "SOL": 110.73}, "b")]
    d = cd.compute_deltas(quotes, bl)
    rep = cd.render_report("ts", "T", quotes, [b.date for b in bl], d,
                           "Test verdict.",
                           ["BTC: appended check to thesis_x",
                            "XRP: no active ledger row — nothing appended"])
    assert "+5.8%" in rep and "+9.0%" in rep and "+11.7%" in rep
    assert "first time" not in rep
    assert "Test verdict" in rep
    assert "caller-supplied judgment, not computed" in rep
    assert "no active ledger row" in rep
    assert len(rep.splitlines()) < 45


def test_full_flow_rerun(cd):
    """End-to-end main() twice on one frozen UTC day: run1 appends once +
    emits once; run2 leaves BOTH ledger and outbox untouched."""
    with tmp_stores(cd) as t:
        cd.fbr.now_iso = lambda: "2026-09-25T15:00:00Z"
        a = args3(day="2026-09-25", task="T-FLOW")
        r1 = cd.main(list(a))
        assert r1[0] and t.REPORT_PATH.exists(), r1
        assert "+9.0%" in t.REPORT_PATH.read_text()
        assert len(t.OUTBOX_PATH.read_text().splitlines()) == 1
        n1 = _flow_checks(cd)
        r2 = cd.main(list(a))
        assert r2[0]
        assert len(t.OUTBOX_PATH.read_text().splitlines()) == 1, "completion not deduped"
        assert _flow_checks(cd) == n1 == 1, f"ledger double-append: {_flow_checks(cd)}"


def _flow_checks(cd):
    """Count frozen-day flow checks on the BTC thesis (test helper)."""
    btc = next(r for r in cd.research_lib.load_theses()
               if r["symbol"] == "BTC")
    return sum(1 for c in btc["checks"]
               if c.get("note", "").startswith("delta-check 2026-09-25"))


def test_real_store(cd):
    """Live read of the owned baseline store (read-only — no mutation)."""
    real = cd.load_baselines(REAL_BASELINES)
    assert len(real) >= 2
    assert real == sorted(real, key=lambda b: b.date)
    assert real[0].prices["BTC"] == 78850.0


def test_no_baseline_no_task(cd):
    """No stored baseline + no active thesis + no --task: honest report
    lines, no completion attempted; a bad spec still writes zero bytes.
    (Paths previously proved only inline — now persisted.)"""
    with tmp_stores(cd) as t:
        r = cd.main(["--price", "XRP=2.50|mystery|2026-09-22"])
        txt = t.REPORT_PATH.read_text()
        assert r[0], r
        assert "No stored baseline for: XRP" in txt
        assert "no active ledger row" in txt
        assert "| XRP | $2.50 |" in txt
        assert not t.OUTBOX_PATH.exists()
        n = t.led.stat().st_size
        r2 = cd.main(["--price", "GARBAGE"])
        assert not r2[0] and t.led.stat().st_size == n


def test_save_theses_roundtrip(cd):
    """save_theses(load_theses()) reproduces the ledger byte-for-byte —
    the atomic rewrite cannot drift worker.py's format — and leaves no
    .tmp behind."""
    with tmp_stores(cd) as t:
        before = t.led.read_bytes()
        cd.research_lib.save_theses(cd.research_lib.load_theses())
        assert t.led.read_bytes() == before, "byte drift in save_theses"
        assert not Path(str(t.led) + ".tmp").exists(), ".tmp left behind"


def test_tx_lifecycle_and_interleave(cd):
    """ledger_tx cleanup + both writers interleaved: an exception inside
    the tx releases the lock; upsert->delta->upsert keeps all three
    checks (the proven reverse-clobber pair through both real entry
    points); a deleted ledger is recreated by the delegated atomic save.
    """
    with tmp_stores(cd) as t:
        led = t.led

        def raiser():
            try:
                with cd.research_lib.ledger_tx():
                    raise ValueError("boom")
            except ValueError:
                pass

        th = threading.Thread(target=raiser, daemon=True)
        th.start()
        th.join(3)
        with open(str(led) + ".lock", "a") as f:
            try:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            except BlockingIOError:
                raise AssertionError("lock not released after exception in tx")
        cd.research_lib.upsert_theses(
            {"tickers": {"BTC": {"price": 65500.0, "context": "leg-A"}}})
        cd.append_ledger_checks(
            [cd.Quote("BTC", 65600.0, "s", "2026-09-27")],
            "leg-B", "2026-09-27T10:00:00Z")
        cd.research_lib.upsert_theses(
            {"tickers": {"BTC": {"price": 65700.0, "context": "leg-C"}}})
        btc = next(r for r in cd.research_lib.load_theses()
                   if r["symbol"] == "BTC")
        ns = [c.get("note", "") for c in btc["checks"]]
        assert sum("leg-A" in n for n in ns) == 1, ns[-5:]
        assert sum("delta-check 2026-09-27" in n for n in ns) == 1, ns[-5:]
        assert sum("leg-C" in n for n in ns) == 1, ns[-5:]
        led.unlink()
        cd.research_lib.upsert_theses(
            {"tickers": {"SOL": {"price": 160.0, "context": "fresh"}}})
        assert led.exists(), "atomic save did not recreate missing ledger"
        assert any(r["symbol"] == "SOL"
                   for r in cd.research_lib.load_theses())
        assert not Path(str(led) + ".tmp").exists()


# ── runner ──────────────────────────────────────────────────────────

def main():
    """Run every test_* group; print one line each; exit non-zero on fail."""
    cd = load_module()
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t(cd)
            print(f"PASS {t.__name__}")
        except SystemExit as e:
            # argparse exits 2 on bad CLI args — report, don't kill the suite
            failed += 1
            print(f"FAIL {t.__name__}: SystemExit({e.code})")
        except Exception as e:  # suite boundary: report and continue
            failed += 1
            print(f"FAIL {t.__name__}: {type(e).__name__}: {e}")
    print(f"{len(tests) - failed}/{len(tests)} groups pass")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
