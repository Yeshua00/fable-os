# TSLA — SEC Review Brief: Form 10-Q, quarter ended 2026-06-30

- **Task**: TASK-00110 (MARK continuous: sec-review)
- **Filing**: Tesla, Inc. — Form 10-Q, period **2026-06-30**, filed **2026-07-23**, accession **0001628280-26-049270**, CIK 0001318605
- **Evidence base**: XBRL statement exhibits read directly from EDGAR — R2 (balance sheet), R4 (operations), R8 (cash flows), R38 (EPS details) of this accession
- **Observed at**: 2026-09-24T00:25:12Z (all figures $M unless noted; column 1 = 2026 / Q2-26, column 2 = 2025 / Q2-25 or Dec-31-2025 as applicable)
- **Family**: first and only `TSLA_SEC_REVIEW_BRIEF` artifact — no version chain (K2). The brief is the missing filings leg behind the registered bet `TSLA-Q3-2026-REACTION-20261022`, which cited this accession but had never read the statements.

## 1. Catalyst signals

1. **Q3 2026 print — date UNCONFIRMED with a live vendor conflict**: wallstreethorizon (UNCONFIRMED Wed 10/21 AMC), optionslam (OS estimate 10/21, window 10/19–24) and public.com say **2026-10-21**; barchart ("Earnings: 10/28/26") and unusualwhales say **2026-10-28**; Tesla's IR page posted no date in observed snippets. The bet's reaction session (horizon 2026-10-22) carries a scoring-shift rule to the session after the actual print (source: `TSLA_THESIS_ACTIVE.json`, observed 2026-09-23).
2. **Deliveries pre-release ~2026-10-02**: Q2 deliveries shipped as 8-K 0001628280-26-046717 on **2026-07-02 — two days after quarter close, 20 days before results** (0001628280-26-049213, 2026-07-22). The Q3 volume/top-line news therefore lands in the tape weeks before the print (EDGAR submissions JSON, observed 2026-09-23/24).
3. **This filing's own release was met with −14.52%** (close 374.01 → 319.69 on 2026-07-23, volume 115.6M ≈ 3.8× the 30M norm; sourced series in `TSLA_THESIS_ACTIVE.json`). The Q2 results the market sold: revenue **+25.5%** but operating income **−56.9%** — Q3 must clear that quality-of-earnings bar.
4. **R&D trajectory is the new narrative line**: Q2 R&D **2,371 vs 1,589 (+49.2%)**, 6M 4,317 vs 2,998 (+44.0%) — the AI/robotics spend step-up is visible in this statement and will be the first thing read at the print.

## 2. Balance-sheet signals

| Signal | 2026-06-30 | 2025-12-31 | Delta |
|---|---|---|---|
| Cash and cash equivalents | 15,219 | 16,513 | −1,294 |
| Short-term investments | 28,305 | 27,546 | +759 |
| **Total liquidity (cash+STI)** | **43,524** | **44,059** | **−535** |
| Inventory | 13,752 | 12,392 | **+1,360 (+11.0%)** |
| PP&E, net | 47,255 | 40,643 | **+6,612 (+16.3%)** |
| Digital assets (BTC) | 674 | 1,008 | −334 (−33.1%) |
| Total assets | 148,524 | 137,806 | +10,718 |
| Total debt (cur 1,418 + LT 7,924 vs 1,640 + 6,736) | 9,342 | 8,376 | +966 |
| **Net cash (debt − cash)** | **−5,877** | **−8,137** | **eroded 2,260** |
| Current ratio (68,758/35,425 vs 68,642/31,714) | 1.941 | 2.164 | −0.223 |
| Total liabilities | 61,005 | 54,941 | +6,064 |
| Total stockholders' equity | 86,858 | 82,137 | **+4,721** |

- **Still comfortably net cash**: liquidity 43,524 vs debt 9,342 → **net +34,182**; equity +4,721 of which retained earnings +1,591 and paid-in capital +3,089.
- **Capex is rewriting the balance sheet**: PP&E +6,612 in six months (+16.3%) against 6M capex 8,282 (+113.1% YoY) — the build (AI capacity/fabs/robots) is the asset-side story.
- **6M operating cash flow 8,634 vs 4,696 (+83.9%)** — strong conversion, but see downside #3: nearly all of it is reinvested.
- **Claims/payables funding the build**: AP +1,953 and accrued liabilities +1,977 while inventory grew +1,360 — working capital is being stretched, not releasing.

## 3. Downside signals

1. **Operating income collapsed despite growth**: Q2 income from operations **398 vs 923 (−56.9%)** on total revenues **28,236 vs 22,496 (+25.5%)** — total opex +47.3% (R&D +49.2%, SG&A +45.1%) outran a gross profit that only grew +22.5%. Q2 gross margin **16.83% vs 17.24% (−41 bps)** even though the 6M margin improved (18.71% vs 16.81%, +190 bps) — Q2 specifically gave back the margin story.
2. **Regulatory credits — the highest-margin revenue — is collapsing**: **146 vs 439 (−66.7%)** in Q2; 6M 526 vs 1,034 (−49.1%). The pure-margin subsidy stream is shrinking toward zero.
3. **Free cash flow halved**: 6M FCF (OCF − capex) **352 vs 810 (−56.5%)**; capex now absorbs **95.9% of OCF** (vs 82.8% a year ago) — the company is one step from FCF-negative at this capex pace, and financing already flipped to net issuance (+1,209 vs −554; debt raised 4,679 vs repaid 3,922).
4. **Quality of earnings: the 6M bottom line leans on a non-cash gain.** The cash-flow statement's own reconciliation subtracts a **SpaceX equity investment unrealized gain of 1,005** — i.e. that non-cash gain sits inside net income, and equals **48.4% of 6M pretax (1,005/2,077)** (Q1/Q2 split not disclosed in the summary statements — limitation L5). Digital-asset unrealized **losses of 334** and FX unrealized losses of 599 also flow through net income non-cash.
5. **Pretax fell while net income merely dipped — tax flattered it**: Q2 pretax **1,329 vs 1,549 (−14.2%)** but net income 1,128 vs 1,190 (−5.2%) because the effective rate fell to **15.1% vs 23.2% (−811 bps)**. At last year's rate Q2 net would be ≈974, i.e. **−18.6% YoY**.
6. **Dilution accelerating**: stock-based compensation 6M **2,181 vs 1,208 (+80.5%)**; shares outstanding **3,949 vs 3,751 (+198, +5.3% in six months)**; basic weighted shares 3,237 vs 3,223.
7. **Inventory build with write-downs persisting**: inventory +11.0% on the balance sheet, −1,663 cash drag in OCF, and inventory write-downs of 187 in 6M (vs 248) — the write-down line has not cleared.

## 4. Arithmetic cross-checks (all recomputed from the filing's raw lines)

- Balance identity: 61,005 + 54 + 86,858 + 607 = **148,524** ✓; 54,941 + 58 + 82,137 + 670 = **137,806** ✓ (exact, both periods)
- Q2 ops: 4,751 − 4,353 = **398** ✓; 398 + 422 − 81 + 590 = **1,329** ✓; − 201 = **1,128** ✓; − 14 = **1,114** ✓
- 6M ops: 9,471 − 8,132 = **1,339** ✓; 1,339 + 856 − 173 + 55 = **2,077** ✓; − 458 = **1,619** ✓; − 28 = **1,591** ✓
- OCF roll (6M): net income 1,619 + non-cash adj 5,238 + working-capital Δ 1,778 = **8,634** ✓ (delta 0 vs filed)
- **EPS boundary self-caught and resolved**: simple division 1,114/3,540 = 0.3147 would round to 0.31, not the filed 0.32 — the filing's own EPS schedule (R38) shows the numerator is **1,116** (NI to common 1,114 adjusted for buy-outs of NCI −2): 1,116/3,540 = **0.3153 → 0.32** ✓; basic 1,116/3,237 = 0.3448 → 0.34 ✓; 6M diluted 1,593/3,538 = 0.4503 → 0.45 ✓
- All ratios above (GM, ETR, current ratio, capex/OCF, FCF, net debt/liquidity, credits deltas) recomputed independently; zero identity failures.

## 5. Limitations

- L1: Condensed statements only — note-level detail (debt schedule, commitments/Note 11, segment disagg below the rows read, SpaceX/autonomy disclosures) not read this run.
- L2: R&D step-up causality (AI training vs robots vs semi) not attributed — the spend figure is read, its composition is not.
- L3: Q3-2025 comparatives are not in this filing (Q2/6M only); YoY claims are Q2 or 6M as labeled.
- L4: Guidance/consensus not sourced this run; catalyst dates and the −14.52% reaction come from `TSLA_THESIS_ACTIVE.json` sources (observed 2026-09-23), cited not re-fetched.
- L5: The 1,005 SpaceX unrealized gain is proven inside net income by the OCF reconciliation, but its Q1/Q2 P&L placement is not isolated in the summary statements — the 48.4% claim is made on the 6M basis only.
- L6: Depreciation and impairment are presented combined (3,209) — impairment-only cannot be split from the summary cash-flow statement.
- L7: Unaudited condensed interim statements (as filed); no fresh price quote taken (this brief is filing-only).

## 6. Sources

1. SEC EDGAR — Tesla 10-Q filing index, accession 0001628280-26-049270 (filed 2026-07-23, period 2026-06-30) via data.sec.gov/submissions/CIK0001318605.json (observed 2026-09-23/24)
2. SEC EDGAR — R2 Consolidated Balance Sheets: https://www.sec.gov/Archives/edgar/data/1318605/000162828026049270/R2.htm (observed 2026-09-24T00:25:12Z)
3. SEC EDGAR — R4 Consolidated Statements of Operations: .../000162828026049270/R4.htm (observed 2026-09-24T00:25:12Z)
4. SEC EDGAR — R8 Consolidated Statements of Cash Flows: .../000162828026049270/R8.htm (observed 2026-09-24T00:25:12Z)
5. SEC EDGAR — R38 EPS details schedule: .../000162828026049270/R38.htm (observed 2026-09-24T00:25:12Z)
6. SEC EDGAR — FilingSummary.xml for report-file mapping (observed 2026-09-24T00:25:12Z)
7. Catalyst/reaction context: `TSLA_THESIS_ACTIVE.json` sources block (wallstreethorizon, optionslam, public.com, barchart, unusualwhales, marketchameleon; 8-K accessions 0001628280-26-046717 and 0001628280-26-049213; stockanalysis.com series for the −14.52% print) — observed 2026-09-23

Read-only research. Informational; not financial advice, no trades or recommendations.
