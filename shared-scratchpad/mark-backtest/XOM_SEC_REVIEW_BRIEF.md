# XOM — SEC Review Brief: Form 10-Q, quarter ended 2026-06-30

- **Task**: TASK-00136 (MARK continuous: sec-review)
- **Filing**: Exxon Mobil Corporation — Form 10-Q, period **2026-06-30**, filed **2026-08-03**, accession **0000034088-26-000093**, primary doc `xom-20260630.htm`, CIK 0000034088
- **Evidence base**: XBRL statement exhibits read directly from EDGAR — R2 (income), R5 (balance sheet), R7 (cash flows); the redomiciliation 8-K body read in full; 2026 form enumeration from data.sec.gov submissions
- **Observed at**: 2026-09-24T03:38:32Z
- **Fresh family**: `XOM_SEC_REVIEW*` = 0 prior files (K2-clean; AMBA stays frozen). This brief is the filing-evidence leg for the registered bet `XOM-Q3-2026-REACTION-20261030`.

## Filing map

| Filing | Filed | Content (identified this run) |
|---|---|---|
| 10-Q acc 0000034088-26-000093 | 2026-08-03 | Statements: R2 income, R5 balance sheet, R7 cash flows (all read) |
| 8-K acc 0001193125-26-291986 | 2026-07-01 | **Redomiciliation Merger completed** — Items 1.01/2.01/3.01/3.03/5.02/5.03/9.01 (body read) |
| 8-Ks 0000034088-26-000065 / -000069 / -000078 | 2026-05-01, 05-04, 05-29 | Q1-results era (05-01, 05-04) and meeting era (period 2026-05-27) — bodies unread |
| DEF 14A acc 0001193125-26-147614 (+ PRE 14A 2026-03-10) | 2026-04-08 | Redomiciliation proxy vote machinery; plus DEFA14A ×5 (May 8–26), PX14A6G (05-05), 13D/A (05-20) — form enumeration only, bodies unread |
| 25-NSE acc 0000876661-26-000593 | 2026-07-02 | NYSE delisting form for the old New Jersey entity (consistent with the listing transfer) |

**Key structural fact (8-K body read):** on **2026-07-01** Exxon Mobil Corporation (New Jersey) completed the previously announced **redomiciliation reorganization** (Merger Agreement dated 2026-04-08) into **ExxonMobil Holdings Corporation** (Texas) via Ensign LLC — each share exchanged **1-for-1**; NYSE suspended the old shares after the close on 2026-07-01 and Holdings shares began trading under the same ticker **XOM on 2026-07-02** (Item 3.01). Consequence for scoring: the price series and the registered entry (161.23 @2026-09-23) sit on one continuous tape — no share-count or price discontinuity.

## Catalyst signals

1. **The bet's hard catalyst**: Q3 2026 results vendor-consensus **2026-10-30, before open** (optionslam "Estimated on Oct. 30, 2026", window Oct 26–31; barchart "Earnings: 10/30/26"; public.com Oct 30) with BO timing per optionslam's 10-print history — registered bet horizon 2026-10-30, reference close 2026-10-29, band ±2.3% (K8-passed; this brief supplies its filings leg).
2. **The base is a price/volume spike, not M&A**: Q2 revenues **116,017** vs 81,506 (**+42.34%** YoY) while derived Q1 was only **+2.42%** (85,138 vs 83,130). Eliminated as consolidation by complete enumeration: no acquisition 8-K exists Apr–Jun 2026 (all 2026 8-Ks listed), total assets grew only **+3.45%** with no goodwill/cash-purchase signal, and investing outflows (12,325) ≈ capex (12,997). Sales +44.10% and crude/product purchases +49.58% — realized price × volume on existing assets. The Q3 lap therefore turns on whether the commodity spike persists (price levels not sourced — L6).
3. **FCF-funded distributions (a first in the filed comparison)**: 6M operating cash flow **32,260 vs 24,503 (+31.66%)**, capex 12,997 → **FCF 19,263 vs 12,322 (+56.3%)**, covering the **18,640** of dividends+buybacks at **1.033×** versus **0.670×** a year ago.
4. **Q2 print quality**: pre-tax **19,424 vs 10,705 (+81.4%)**, margin 16.74% vs 13.13% (+361bps), net income attributable to ExxonMobil **14,525 vs 7,082 (+105.1%)**, EPS **3.48 vs 1.64 (+112.2%)** — the growth mechanics identified below (tax + one-sided mix).
5. Proxy-era machinery on file (forms only): the redomiciliation PRE/DEF 14A pair plus a May cluster of DEFA14A ×5, a PX14A6G exempt solicitation and a 13D/A around the 2026-05-27 meeting-era 8-K — contents unread (L5), recorded as governance context, not a market catalyst.

## Balance-sheet signals

1. **Balance sheet barely moved while the P&A exploded**: total assets 448,980 → **464,482** (+3.45%); all component sums and A = L + E exact both periods (198,371 + 266,111 = 464,482).
2. **Working-capital build**: notes/accounts receivable 44,562 → **60,558 (+35.90%)** vs assets +3.45%; income taxes payable 2,123 → **4,200 (+97.8%)**; other current assets +122.3%; accounts payable & accrued +22.29% — current ratio slipped **1.153 → 1.135**.
3. **Equity flat, retention zero**: ExxonMobil share of equity 259,386 → **259,380 (−6)** — net income 18,708 minus dividends 8,633 = retained +10,075 (roll exact), less buybacks 9,881 and OCI −686 → flat; total equity 266,626 → 266,111 (−515 incl. NCI).
4. **Leverage up**: equity/assets **59.38% → 57.29% (−209bps)**; commercial paper issued +3,912 (vs +257); net debt (notes+LTD−cash) actually improved 32,856 → **31,780 (−1,076)**; the separate "Long-term obligations" line grew 26,720 → 28,698 (+7.4%, composition unread — L3).
5. **Capital return**: dividends 8,633 + buybacks **10,007** = **18,640** in 6M; treasury shares 3,840 → 3,907M (+67M); cash ended at 10,588 (−93, chain exact).
6. **Physical side shrinking**: inventories −2.8% despite the revenue surge (sold from stock); PP&E-net 299,373 → 296,298 (−1.0%) with 6M capex 12,997 below D&D 15,460; AOCI −10,863 → −11,549 (−686).

## Downside signals

1. **Tax gave the beat a lift — and the lift reverses**: Q2 ETR **23.39% (4,543/19,424) vs 31.30% (3,351/10,705) = −791bps**; at the prior-year rate Q2 net income would be 13,344 instead of 14,881 — the rate difference is **+1,537, i.e. 10.3% of quarter net income and ~20% of the +7,527 YoY growth**. The 6M rate is already 26.67% vs 31.02% (−435bps); normalization cuts straight into the Q3 YoY comparison (inverted version of the JPM/UNH ETR findings — there tax hurt, here tax helped).
2. **One-sided mix inside the top line**: income from equity affiliates fell **−38.92% (893 vs 1,462)** while sales rose +44% — the JV side shrank as the top line exploded. The connection to the "lost earnings from Middle East" RBC headline in the page's news rail (2026-09-22) is a labeled *inference*, not a fact read from the notes (L4).
3. **D&D jumped +42.4% in Q2 (8,689 vs 6,101) on a flat/shrinking PP&E base** — the line reads "(includes impairments)" and the impairment-vs-depletion split is not on the face (L2): an embedded impairment cannot be ruled out.
4. **Zero retention cushion**: 6M net income 18,708 ≈ distributions 18,640 (99.7%) while assets grew +3.45% — equity flat, leverage −209bps, growth funded outside retained earnings.
5. **No volume-growth investment**: capex +6.7% vs 6M revenue +22.18%, PP&E −1.0% — if the price spike fades there is no expanding productive base to fall back on.
6. **Funding-cost momentum**: 6M interest expense **+49.1% (522 vs 350)**, CP issuance +3,912, total cash interest paid 910 vs 876 — short-term funding reliance rising into the print.

## Arithmetic verification (all run this turn, 37/37 PASS)

- Income: revenue components → 116,017 / 81,506 / 201,155; cost components → 96,593 / 174,764; pre-tax = revenue − costs both periods; NI builds (incl. NCI and attributable) exact both periods both years; EPS-implied average shares 4,174 within the 4,112–4,179 outstanding range.
- Balance sheet: current-asset, total-asset, current-liability and total-liability component sums exact both periods (total liabilities requires the separate LT-obligations lines 549+28,149); equity components → 259,380 / 259,386; A = L + E exact both periods; retained-earnings roll exact (482,494 + 18,708 − 8,633 = 492,569).
- Cash flows: OCF, investing and financing chains exact; both period cash chains → ending cash 10,588 / 15,711; equity roll (common +486, treasury −9,881, OCI −686, retained +10,075) → −6 exact.

## Limitations

- **L1** Statements only: MD&A, notes, and segment/disaggregation not read — the Q2 step-up is narrowed by elimination (no M&A — full form enumeration plus balance-sheet evidence) but not split into price vs volume vs mix.
- **L2** D&D "(includes impairments)" — impairment vs depletion not separable from the face.
- **L3** "Long-term obligations" (28,698) composition not read — note unread; it is carried as a separate liability line only because that is required for the A = L + E identity to hold.
- **L4** The equity-affiliate collapse's cause is not read from the notes; the Middle-East narrative link is explicitly an inference from one headline.
- **L5** Bodies unread: the three non-redomiciliation 8-Ks, the DEF/PRE/DEFA14A proxy family, PX14A6G and 13D/A — form-type enumeration only; the meeting-era 8-K content is unknown.
- **L6** No fresh price taken this run (entry stays 161.23 @2026-09-23 from the thesis artifact); no commodity price levels sourced (K4) — the price-spike reading rests on statement-derived elimination, not a WTI quote.
- **L7** No Q3-2025 base exists in this filing, so the Q3 lap comparison requires the next print.
- **L8** Cash interest paid (910) exceeds P&L interest expense (522) and is not reconciled here — capitalized/timing components not read (disclosure as presented).

*Informational research; not financial advice.*
