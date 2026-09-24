# JPM — SEC Review Brief: Form 10-Q, quarter ended 2026-06-30

- **Task**: TASK-00124 (MARK continuous: sec-review)
- **Filing**: JPMorgan Chase & Co. — Form 10-Q, period **2026-06-30**, filed **2026-08-06**, accession **0001628280-26-054343**, primary doc `jpm-20260630.htm`, CIK 0000019617
- **Evidence base**: XBRL statement exhibits read directly from EDGAR — R2 (income), R4 (balance sheet), R8 (cash flows) of this accession; filing map (8-K indexes) from EDGAR submissions/index.json
- **Observed at**: 2026-09-24T01:59:53Z
- **Fresh family**: `JPM_SEC_REVIEW*` = 0 prior files (K2-clean; AMBA stays frozen). This brief is the filing-evidence leg for the registered bet `JPM-Q3-2026-REACTION-20261013`.

## Filing map

| Filing | Filed | Content (identified this run) |
|---|---|---|
| 10-Q acc 0001628280-26-054343 | 2026-08-06 | Financial statements: R2 income, R4 balance sheet, R8 cash flows (all read) |
| 8-K acc 0001628280-26-048078 | 2026-07-14 06:30 ET | Q2 earnings release — ex-99.1 narrative, ex-99.2 supplement (titles from index; bodies unread) |
| 8-K acc 0001628280-26-048086 | 2026-07-14 09:52 ET | Q2 earnings presentation (title from index; body unread) |
| 8-K acc 0000019617-26-000288 | 2026-07-23 (event 2026-07-21) | By-laws amendment — governance, non-catalyst (filename `jpmcby-laws07212026.htm`; body unread) |

## Catalyst signals

1. **The bet's hard catalyst**: Q3 2026 results **2026-10-13, before market open (8:30am ET call)** — company-confirmed on JPM IR (sourced in the thesis run 2026-09-23). Registered bet horizon = the US session reacting to that print; reference close 2026-10-12; band ±5.64% (K8-passed calibration).
2. **Elevated base to lap**: Q2 net income **21,155** vs 14,987 (**+41.2%** YoY), diluted EPS **7.70** vs 5.24 (+46.9%), total net revenue **57,347** vs 44,912 (**+27.69%**) — the filing shows exactly where the blowout came from (one-time Visa gain, §Downside 2), so the Q3 bar is headline-high but partly flattered.
3. **Fee-cycle broadening (6M)**: investment banking fees 6,066 vs 4,677 (**+29.7%**), principal transactions 16,994 vs 14,763 (+15.1%), asset-management fees 11,173 vs 9,506 (+17.5%), commissions 5,096 vs 4,227 (+20.6%) — three independent fee engines compounding, not one-off.
4. **NII engine with deposit-cost relief**: 6M net interest income 50,877 vs 46,482 (**+9.46%**) while interest expense was flat (+0.67%, 48,938 vs 48,612) — funding costs already absorbed; Q3 NII guidance on the 10-13 call is the swing factor for the reaction.
5. Prior-quarter reaction context: the 2026-07-14 twin 8-Ks are the Q2 print this quarter's tape must digest from (release pre-market 06:30 ET, presentation 09:52 ET).

## Balance-sheet signals

1. **Balance sheet ballooning ahead of capital**: total assets 4,424,900 → **5,015,069** (+590,169, **+13.34%** in six months); stockholders' equity only 362,438 → **374,598** (+3.36%) → **equity/assets 8.19% → 7.47% (−72bps)**. Identity exact: 4,640,471 + 374,598 = 5,015,069; all 11 asset components and both equity components sum exactly.
2. **Funding mix shifting to wholesale**: deposits 2,559,320 → **2,713,700** (+6.03%) but repos 442,396 → **704,918** (**+59.34%**, +262,522); wholesale (repo + short-term borrow) share of dep+repo+ST-borrow funding **16.54% → 22.27% (+573bps)**.
3. **Growth is trading, not loans**: trading assets 802,873 → **1,062,072** (**+32.28%**, +259,199 = 44% of all asset growth); fed funds/resale +109,717 (+32.61%); securities borrowed +76,296 (+26.66%); loans only 1,493,429 → **1,542,462** (+3.28%).
4. **Working-capital swell**: accrued interest and accounts receivable 111,599 → **179,939** (**+61.24%**, +68,340), mirrored in the cash-flow statement's (69,352) working-capital line.
5. **Liquidity + capital actions**: cash and due from banks + deposits with banks 343,338 → 309,811 (−33,527, matches the CF chain exactly); 6M capital returned = buybacks 15,113 + common dividends 8,716 = **23,829**; preferred issued 3,000 / redeemed 2,000 (preferred line 20,045 → 21,040); treasury shares 1,408,661,319 → 1,446,747,700.
6. **Securities marks moving the wrong way**: AOCI −4,290 → **−7,693** (−3,403 worse in six months); long-term debt 435,206 → 460,523 (+5.82%).

## Downside signals

1. **Tax gave back the beat**: Q2 ETR **23.12%** (6,361/27,516) vs **18.03%** (3,297/18,284) — **+509bps**; 6M 21.56% vs 19.25% (+231bps). Pre-tax grew +50.5% but net income only +41.2% — tax surrendered 9.3pp of growth. If the higher rate persists into Q3 it cuts the EPS reaction directly.
2. **Headline revenue is flattered by a one-time gain**: the cash-flow statement adds back **"Initial gain on the Visa share exchange" (4,509, 6M)**; Q1 arithmetic proves it sits in Q2 (Q1 other income 1,671 vs 1,923 = −252 YoY while Q2 other income 7,549 vs 1,154 = +6,395). Ex-gain Q2: total revenue 52,838 = **+17.65%** (not +27.69%), noninterest revenue +25.91% (not +46.69%), pre-tax 23,007 = +25.83%. The Q3 lap therefore compares against a *core* +17.7% revenue quarter, not a +27.7% one.
3. **Leverage and wholesale-funding creep** (from §Balance 1–2): −72bps equity/assets and +573bps wholesale share in six months; the regulatory ratios (CET1/TLAC) that actually gate this live in MD&A/notes **not read this run** — direction is visible from the statements alone and points the wrong way.
4. **Credit-cost air pocket**: provision fell −11.72% YoY (2,515 vs 2,849) and ACL coverage slipped 1.725% → **1.695% (−3.0bps)** while loans grew +3.28% and assets +13.34% — reserves are not keeping pace with a rapidly expanding balance sheet; a Q3 charge-off surprise would land against a falling-provision base.
5. **Expense re-acceleration**: Q2 total noninterest expense **27,316 vs 23,779 (+14.87%)** — professional and outside services +28.39% (3,855 vs 3,006), marketing +30.57% (1,670 vs 1,279), compensation +10.57%. Efficiency still improved (Q2 47.63% vs 52.95%; 6M 50.54% vs 52.51%) but the cost trend is up.
6. **Expansion is funded, not earned**: 6M operating cash flow **(237,044)** vs (222,292); financing +419,479 carried the half, with repos alone contributing +262,558 in CF terms — normal bank mechanics, but it means wholesale markets (not deposit growth alone) funded the +13.34% asset build.

## Arithmetic verification (all run this turn, 22/22 PASS)

- Income: Q2 noninterest-revenue components → 31,836; revenue = NIR+NII → 57,347; pre-tax = rev−prov−exp → 27,516; NI = pre-tax−tax → 21,155 (and PY 14,987); EPS 20,752/2,694.2 → 7.70 diluted, 7.71 basic; expense components → 27,316; 6M revenue/pre-tax/NI → 107,183/47,995/37,649.
- Balance sheet: 11 asset components → 5,015,069 (2026) and 4,424,900 (2025); A = L + E exact both periods; 7 liability components → 4,640,471; equity components → 374,598 and 362,438.
- Cash flows: both period chains → ending cash 309,811 / 420,327; BS cash (24,720+285,091) = CF ending; BS 2025 cash (21,742+321,596) = CF beginning 343,338.

## Limitations

- **L1** Statements only: MD&A, CET1/TLAC ratios, and note-level detail (deposit composition, loan grades, commitments) not read — equity/assets is a proxy, not a regulatory ratio.
- **L2** No segment split in the summary statements — fee surges are firmwide, not attributable to CIB vs CB vs AWM.
- **L3** The Visa gain's specific tax treatment is not in the statements — only pre-tax ex-gain figures given; after-tax ex-gain NI deliberately not estimated.
- **L4** No fresh price taken this run — entry/band stay as registered (337.53 @2026-09-23, band ±5.64%).
- **L5** 8-K bodies unread (titles from EDGAR index only) — the earnings-release narrative and presentation contents were not reviewed.
- **L6** Comparison base is Q2/6M-2025 as filed; this filing carries no Q3-2025 figure, so the Q3 lap comparison will require the next print.
- **L7** AOCI direction (−3,403) not decomposed between rates and FX — no OCI note read.

*Informational research; not financial advice.*
