# UNH — SEC Review Brief: Form 10-Q, quarter ended 2026-06-30

- **Task**: TASK-00096 (MARK continuous: sec-review)
- **Filing**: UnitedHealth Group, Inc. — Form 10-Q, period **2026-06-30**, filed **2026-08-10**, accession **0000731766-26-000197**, primary doc `unh-20260630.htm`, CIK 0000731766
- **Evidence base**: XBRL statement exhibits read directly from EDGAR — R2 (balance sheet), R3 (operations), R6 (cash flows) of this accession
- **Observed at**: 2026-09-23T22:44:46Z (all figures $M unless noted; column 1 = 2026-06-30 / Q2-26, column 2 = 2025-12-31 / Q2-25 as applicable)
- **Family**: first and only `UNH_SEC_REVIEW_BRIEF` artifact — no version chain (K2)

## 1. Catalyst signals

1. **Q3 2026 print: Tuesday 2026-10-13, before market open, 8:00am ET call** — 20 calendar days from observation; source: UNH newsroom announcement 2026-09-15, recorded in `UNH_THESIS_ACTIVE.json`. This filing is the last full balance sheet scored before that print.
2. **The Q2 base is a high bar**: Q2 diluted EPS **6.04 vs 3.74 (+61.5% YoY)**, operating earnings **7,991 vs 5,150 (+55.2%)**, on essentially flat revenue (+0.4%) — the earnings recovery came from cost (medical costs −4.1%), not growth, so Q3 tests its repeatability.
3. **Medical-cost ratio improvement is the swing factor**: computed Q2 MBR proxy **86.66% vs 89.40% YoY (−274 bps)**; 6M **85.29% vs 87.13% (−184 bps)**. Each sustained 100 bps is ≈ 870 of pretax on the Q2 premium run-rate (1% × 86,956 ≈ 870).
4. **Reg FD 8-K filed 2026-09-08** (Item 7.01, accession 0000731766-26-000205) sits between this 10-Q and the print — flagged, content not reviewed this run (limitation L5).

## 2. Balance-sheet signals

| Signal | 2026-06-30 | 2025-12-31 | Delta |
|---|---|---|---|
| Cash and equivalents | 28,585 | 24,365 | **+4,220** |
| Total debt (ST 3,827 + LT 69,501 vs 6,069 + 72,320) | 73,328 | 78,389 | **−5,061** |
| Net debt (debt − cash) | 44,743 | 54,024 | **−9,281 (−17.2%)** |
| Total equity | 104,513 | 100,090 | **+4,423** |
| Total assets | 309,727 | 309,581 | +146 (flat) |
| Total liabilities | 203,778 | 207,883 | −4,105 |
| Goodwill | 110,645 | 110,499 | +146 |
| Redeemable noncontrolling interests | 1,436 | 1,608 | −172 |

- **Deleveraging is the story**: −5,061 of debt retired in H1 with ST maturities cut from 6,069 to 3,827 (−37.1%) — refinancing pressure dropped materially; interest expense fell to 962 vs 1,027 (−6.3% YoY Q2).
- **Cash conversion strong**: 6M operating cash flow **19,964 vs 12,644 (+57.9%)**; capex only 1,562 (7.8% of OCF), so free cash flow **18,402 vs 10,860** covering dividends 4,092 at **4.5×**.
- **Balance sheet shrank by design**: assets flat (+146) while liabilities fell 4,105 — the equity build is retained earnings plus liability paydown, not asset growth.
- **Medical costs payable eased to 38,930 (from 39,337)** alongside −4.1% medical costs — claims liability stable, no build-up signal.

## 3. Downside signals

1. **Top line is stalled**: Q2 total revenues **112,032 vs 111,616 (+0.4%)** while **premiums fell −1.1% (86,956 vs 87,905)**; investment income (+115) masked the premium decline. Zero organic growth.
2. **Effective tax rate jumped +613 bps in Q2: 18.63% (1,298/6,968) vs 12.49% (510/4,082)** — at the prior rate Q2 net would be ≈ 5,911 vs actual 5,484, so **≈427 of the +2,078 YoY net gain (~21%) went to tax**. 6M ETR +104 bps (18.62% vs 17.57%).
3. **OCF surge is partly working-capital release**: other current receivables fell **−4,975** and accounts receivable **−1,445** (6,420 combined) during H1 while cash built only 4,220 — a repeat needs the receivable tailwind to persist (note-level decomposition not read, L1).
4. **Goodwill is 35.7% of total assets (110,645/309,727)** — impairment sensitivity to any unit writedown; the Optum segments carry it (segment notes not read).
5. **Liquidity mix deteriorated slightly**: current ratio **0.788 → 0.777** (86,860/111,820 vs 90,582/114,897) and short-term investments liquidated 3,756 → 2,883 (−873) while cash built — net current assets fell 3,722.
6. **Held-for-sale losses accelerating**: 6M loss on sale of subsidiary/held-for-sale **133 vs 56 (+137.5%)** — portfolio exit drag continues into H2.
7. **Share count only modestly reduced** (basic 907 → 902, −0.6%) despite 11,615 of financing outflow — capital went to debt paydown (5,061) and dividends (4,092) ahead of buybacks; a buyback re-acceleration would be a positive read-through not yet visible.

## 4. Arithmetic cross-checks (all recomputed from the filing's raw lines)

- Pretax identity Q2: 7,991 − 962 − 61 = **6,968** ✓; net: 6,968 − 1,298 = **5,670** ✓; attributable: 5,670 − 186 = **5,484** ✓
- 6M identity: 16,981 − 1,917 − 133 = **14,931** ✓; − 2,780 = **12,151** ✓; − 387 = **11,764** ✓
- Current liabilities: 38,930 + 39,741 + 3,827 + 2,986 + 26,336 = **111,820** ✓
- Liabilities + RNI + equity: 203,778 + 1,436 + 104,513 = **309,727** ✓ (2025: 207,883 + 1,608 + 100,090 = **309,581** ✓)
- Cash roll: 24,365 + 4,220 = **28,585** ✓
- Debt/net-debt/OCF deltas and all ratios above recomputed independently; zero identity failures.

## 5. Limitations

- L1: Condensed statements only — note-level detail (segment results, commitments/Note 7, healthcare-cost liability methodology, full OCF working-capital schedule) not read this run.
- L2: MBR is computed as medical costs ÷ premiums (proxy for the company's presentation); OCF working-capital decomposition is directional (receivable deltas read from the balance sheet, not the cash-flow WC schedule).
- L3: Q3-2025 comparatives are not in this filing (it reports Q2/6M only), so no Q3 YoY base is claimed.
- L4: This brief is filing-only — no fresh price quote taken; bet scoring unchanged (K4/K6 recorded, not worked around).
- L5: 8-K 2026-09-08 (Item 7.01) content not read; flagged as catalyst adjacency only.
- L6: Unaudited condensed interim statements (as filed).

## 6. Sources

1. SEC EDGAR — UNH 10-Q filing index, accession 0000731766-26-000197 (observed 2026-09-23T22:44:46Z): https://www.sec.gov/Archives/edgar/data/731766/000073176626000197/
2. SEC EDGAR — R2 Condensed Consolidated Balance Sheets: https://www.sec.gov/Archives/edgar/data/731766/000073176626000197/R2.htm (observed 2026-09-23T22:44:46Z)
3. SEC EDGAR — R3 Condensed Consolidated Statements of Operations: https://www.sec.gov/Archives/edgar/data/731766/000073176626000197/R3.htm (observed 2026-09-23T22:44:46Z)
4. SEC EDGAR — R6 Condensed Consolidated Statements of Cash Flows: https://www.sec.gov/Archives/edgar/data/731766/000073176626000197/R6.htm (observed 2026-09-23T22:44:46Z)
5. SEC EDGAR — UNH submissions JSON (form list, 8-K 2026-09-08 Item 7.01): https://data.sec.gov/submissions/CIK0000731766.json (observed 2026-09-23T22:44:46Z)
6. UNH newsroom, 2026-09-15 (Q3 date) via `UNH_THESIS_ACTIVE.json` sources block (cited, not re-fetched this run)

Read-only research. Informational; not financial advice, no trades or recommendations.
