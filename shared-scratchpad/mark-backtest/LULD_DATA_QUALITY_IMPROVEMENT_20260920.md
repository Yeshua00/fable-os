# LULD Data-Quality Improvement: Volume-Weighted Proximity Scoring
**Author:** MARK | **Date:** 2026-09-20 | **Status:** COMPLETE

---

## Problem
The existing LULD monitor (`luld_monitor.py`) computed halt risk based solely on price proximity to band edges. This missed a critical signal: **high volume near band edges is far more dangerous than low volume.** Institutional orders near bands are larger, harder to absorb, and historically precede halts.

## Improvement Implemented

### 1. Volume-Weighted Halt Risk (`volume_weighted_halt_risk()`)
Combines proximity + volume to produce a more accurate halt probability:

| Volume Ratio (vol/avg) | Multiplier | Effect |
|------------------------|------------|--------|
| > 2.0x | 1.5x | Institutional pressure — halt risk amplified |
| > 1.5x | 1.25x | Above-average participation |
| 1.0x | 1.0x | Baseline |
| 0.5x | 0.75x | Low participation — risk dampened |
| < 0.25x | 0.5x | Ghost market — minimal halt risk |

**Key rule:** If price is AT or BEYOND the band (base prob = 100%), volume dampening is disabled — a band breach is a halt regardless of volume.

### 2. Band-Edge Volume Ratio (`band_edge_volume_ratio()`)
Measures what fraction of trading volume occurs within 2% of band edges:

| Ratio | Assessment | Signal |
|-------|------------|--------|
| > 50% | CRITICAL | Institutional pushing toward bands — halt imminent |
| 30-50% | HIGH | Significant edge activity |
| 15-30% | ELEVATED | Moderate edge pressure |
| 5-15% | NORMAL | Typical distribution |
| < 5% | LOW | No edge pressure |

### 3. New Analysis Function (`run_volume_weighted_analysis()`)
Full analysis combining standard bands + volume-weighted risk + band-edge volume ratio in a single call.

## Validation Results

**14/14 tests pass:**

| Category | Tests | Status |
|----------|-------|--------|
| Historical LULD scenarios | 5/5 | ✅ |
| Volume-weighted halt risk | 5/5 | ✅ |
| Band-edge volume ratio | 4/4 | ✅ |

### Key Test Cases
- **High vol at band edge:** 500K vol / 200K avg → 1.5x multiplier → 40% base → 60% adjusted = HIGH
- **Low vol at band edge:** 50K vol / 200K avg → 0.5x multiplier → 40% base → 20% adjusted = MODERATE
- **At band (halt certain):** 100% base → volume dampening DISABLED → stays HALT
- **100% volume near edges:** ratio = 1.0 → CRITICAL assessment
- **Mixed center/edge:** ratio = 9.1% → NORMAL assessment

## Artifacts

| File | Lines | Description |
|------|-------|-------------|
| `luld_monitor.py` | ~490 | Updated with 3 new functions + 9 new tests |
| `LULD_DATA_QUALITY_IMPROVEMENT_20260920.md` | This report |

## Usage Example
```python
from luld_monitor import run_volume_weighted_analysis

# With volume data
result, report = run_volume_weighted_analysis(
    "AMBA", 81.00, 73.73, "tier2",
    volume=500000, avg_volume=200000,
    trades=[{"price": 80.9, "volume": 100}, {"price": 81.0, "volume": 200}]
)

# result["volume_weighted_halt_risk"] → {"probability": 0.60, "level": "HIGH", ...}
# result["band_edge_volume"] → {"ratio": 1.0, "assessment": "CRITICAL", ...}
```

## Impact
- **Before:** Halt risk was proximity-only — a stock 1% from the band with 5x normal volume got the same score as one with 0.1x volume
- **After:** Volume context amplifies or dampens halt risk by up to 1.5x, giving a more accurate picture of institutional pressure

## Risk
Low — new functions are additive, existing code untouched. All 14 validation tests pass.
