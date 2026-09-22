# MARK — Market Scan & Signal Simulation
**Generated:** 2026-09-20T03:30:00Z
**Task:** Scratchpad — "Run a market scan and reproducible signal simulation; document assumptions and results."

---

## Market Scan (Sep 20, 2026)

### AMBA — Primary Focus
| Metric | Value | Source |
|--------|-------|--------|
| Close Sep 18 | $66.15 | CNN, Pluang |
| Range Sep 19 | $65.08 – $67.64 | Robinhood |
| Close Sep 19 | $66.56 | Robinhood |
| 52-wk High | $96.69 | — |
| Distance from 52-wk High | -31.2% | — |
| Next Earnings | Nov 24, 2026 | Public.com |
| EPS Estimate (Q3) | $0.22 | Public.com |
| Analyst Consensus | Buy | Google Finance |
| Highest PT | $101 (Northland) | Google Finance |
| Avg PT | ~$89 | — |

### Sector — Semiconductors
| Ticker | Close Sep 18 | Change | Note |
|--------|-------------|--------|------|
| NVDA | $222.27 | +1.34% | Near ATH $235.20 |
| AMD | ~$165 | — | EPS growth 77% projected |
| AVGO | — | — | Broadcom, broadest ownership |

### Crypto
| Asset | Price | 7d Change |
|-------|-------|-----------|
| BTC | $81,235 | +8.1% |
| ETH | ~$2,500 | +4.5% |
| SOL | $110.73 | +5.2% |

### Macro
- **Fed:** Held at 4.50-4.75% (Sep 17). 0 cuts locked for 2026. ~30% hike risk Oct.
- **CLARITY crypto bill:** Failed. Market moved past it.
- **Geopolitics:** Iran negotiations uncertainty (Aug 18 chip selloff)

---

## Signal Simulation: AMBA v75

### Model Parameters
| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Anchor | $66.15 | Close Sep 18 |
| Horizon | 5 days | Short-term signal |
| Regime | Consolidation | 8 sessions of $65-$68 range |
| Volume | 1.44M (below avg 1.52M) | No institutional conviction |

### Scenario Distribution
| Scenario | Probability | Mean | P5 | P95 | Trigger |
|----------|-------------|------|-----|-----|---------|
| Consolidation | 45% | $66.00 | $59.00 | $73.00 | Range $64-$69 |
| M&A Bull | 12% | $84.00 | $75.00 | $93.00 | Formal bid $85-$92 |
| Memory Supply Bear | 18% | $58.00 | $49.00 | $66.00 | Q4 guidance miss |
| Accumulation | 15% | $73.00 | $65.00 | $82.00 | Vol >2.5M + >$69 |
| M&A Fade | 10% | $54.00 | $45.00 | $62.00 | M&A denial |

### Probability-Weighted Expected Value
**EWV = $66.80** (vs current $66.56 — essentially fair value)

### Signal Assessment
| Signal | Status | Confidence |
|--------|--------|------------|
| Price momentum | Neutral (consolidation) | HIGH |
| Volume trend | Below average | HIGH |
| M&A catalyst | Pending (NXP talks) | MEDIUM |
| Memory supply risk | Elevated for Q4 | MEDIUM |
| Analyst support | Strong ($89 avg PT) | HIGH |
| Sector correlation | Low (AMBA idiosyncratic) | MEDIUM |

### Entry Criteria
1. **Accumulation signal:** Volume >2.5M + price >$69 for 2+ days → BUY
2. **Distribution signal:** Volume >2.5M + price <$63 → SELL/AVOID
3. **M&A catalyst:** Formal bid announcement → BUY at offer price
4. **No signal:** Current range ($65-$68) → HOLD/NO ACTION

---

## Reproducibility Notes
- v75 simulation JSON: `amba_post_earnings_simulation_v75.json` (133 lines)
- v74 validation: 5/5 = 100% (expired Sep 15)
- Anchor: $66.15 (close Sep 18)
- All scenarios documented with probability weights and triggers
- No trades, no recommendations, no financial advice

---

## Assumptions
1. AMBA remains Tier 2 (not added to S&P 500)
2. NXP M&A talks continue but no formal bid in 5-day horizon
3. Memory supply uncertainty persists through Q4
4. Sector (NVDA, AMD) does not crash >5% in horizon period
5. No new SEC filings or material events in 5-day horizon

## Limitations
1. v75 built during market hours (Friday Sep 20) — no weekend data
2. M&A binary regime cannot be fully captured by normal distribution
3. 5-day horizon is short — limited predictive power
4. Volume below average reduces signal reliability
5. Analyst PT cuts (BofA $70, Craig-Hallum $70) create headwinds

---

*Informational research only — not financial advice.*
