# Certificate ID Pattern Analysis - data.edu.az

## Executive Summary

**CRITICAL FINDING:** There are **TWO SEPARATE ID SYSTEMS** used by data.edu.az!

1. **7-digit Legacy System** (2020-2024) - COMPLETE ✅
2. **5-6 digit New System** (2024-present) - ONGOING 🔄

---

## Pattern Breakdown

### 🔴 System 1: 7-Digit Legacy IDs (COMPLETE)

**Status:** All ranges fully scraped at 100% density

| Year | ID Range | Format | Count | Status |
|------|----------|--------|-------|--------|
| 2020 | 2,011,101 - 2,011,994 | `20-11-XXX` | 894 | ✅ Complete |
| 2021 | 2,103,599 - 2,103,717 | `21-03-XXX` | 119 | ✅ Complete |
| 2022 | 2,022,001 - 2,022,995 | `20-22-XXX` | 995 | ✅ Complete |
| 2023 | 2,023,101 - 2,023,999 | `20-23-XXX` | 899 | ✅ Complete |
| 2024 | 2,024,101 - 2,024,999 | `20-24-XXX` | 899 | ✅ Complete |

**Total Legacy Certificates:** 3,806

**Pattern Structure:**
- 2020: Year `20` + Month `11` (November) + Sequential `101-994`
- 2021: Year `21` + Month `03` (March) + Sequential `599-717`
- 2022-2024: Century `20` + Year `YY` + Sequential `XXX`

**Density:** 100% filled (no gaps, sequential numbering)

---

### 🟢 System 2: 5-6 Digit New IDs (ONGOING)

**Status:** Currently being issued, incomplete

**Discovered Ranges:**

| ID Length | Range | Sample IDs | Count |
|-----------|-------|------------|-------|
| 5-digit | 20,241 - 20,265 | 20241, 20242, 20243... | 22 |
| 6-digit | 202,410 - 202,599 | 202410, 202411, 202412... | 175 |

**Total New System Certificates Found:** 197

**Completion Dates:** 2022-2025 (actively issuing)

**Potential Patterns:**
- 5-digit: `202XX` or `20XXX`
- 6-digit: `202XXX` or `20XXXX`

**Unknown Boundaries:**
- Where does the 5-digit range start? (found from 20241)
- Where does the 6-digit range end? (found up to 202599)
- Are there 2025-specific ranges? (e.g., `2025XXX`?)

---

## Efficiency Analysis

### Brute Force vs. Pattern-Based Approach

| Approach | IDs to Check | Time Estimate | Efficiency |
|----------|--------------|---------------|------------|
| **Brute Force** (1 - 30M) | 30,000,000 | ~69 hours @ 120 req/s | ❌ Wasteful |
| **Legacy Pattern** (Known) | 3,806 | ~32 seconds | ✅ 7,882x faster |
| **New System** (Unknown) | ??? | ??? | 🔍 Need discovery |

**Recommendation:** Use hybrid approach
1. Skip legacy ranges (already complete)
2. Use smart search to find new system boundaries
3. Scrape only discovered ranges

---

## Recommended Scraping Strategy

### Phase 1: Discovery (Quick)
Use binary search to find boundaries for:

```bash
# Find 2025 ranges
python scripts/smart_range_finder.py --prefix 2025 --min 1 --max 999999
python scripts/smart_range_finder.py --prefix 202 --min 5100 --max 9999

# Find 2026 ranges (future-proof)
python scripts/smart_range_finder.py --prefix 2026 --min 1 --max 999999
```

### Phase 2: Targeted Scraping (Fast)

Once boundaries are found, scrape only those ranges:

```bash
# Example based on discovered ranges
python scripts/scraper.py --start 20001 --end 20999    # 5-digit range
python scripts/scraper.py --start 202001 --end 202999  # 6-digit range
python scripts/scraper.py --start 2025001 --end 2025999 # 2025 range
```

### Phase 3: Sampling (Validation)

Periodically sample random IDs to detect new patterns:
- Check every 10,000th ID from 1 to 10M
- If found, narrow down with binary search

---

## Pattern Predictions for 2025+

Based on observed patterns, likely formats for 2025:

### Option A: 7-digit continuation
```
2,025,101 - 2,025,999  (similar to 2023-2024)
```

### Option B: 6-digit new system
```
202,501 - 202,599  (month-based like 202410-202599)
202,600 - 202,699  (continuing sequence)
```

### Option C: New prefix
```
20251 - 20259       (5-digit)
202510 - 202599     (6-digit)
```

---

## Scraping Priority

1. **HIGH PRIORITY:** New system ranges (incomplete, actively growing)
   - 20,000 - 20,999
   - 202,000 - 203,000
   - 2025XXX variants

2. **MEDIUM PRIORITY:** 2025-specific patterns
   - Use smart_range_finder.py

3. **LOW PRIORITY:** Re-scraping legacy ranges
   - Already 100% complete
   - Only if database needs refresh

---

## Optimization Tips

### 1. Skip Known Gaps
Based on 100% density in legacy system, there are NO gaps. Sequential scraping is safe.

### 2. Use Checkpoint Resume
Your current scraper already has this. Keep using it!

### 3. Adaptive Concurrency
- Legacy ranges (dense): Use high concurrency (100-200)
- New system (sparse): Use moderate concurrency (50)
- Discovery mode: Use low concurrency (10-20)

### 4. Smart Exit Conditions
If you hit 1,000+ consecutive 404s, assume you've passed the end of a range.

---

## Next Steps

### Immediate Actions:

1. **Run Range Finder** to discover 2025 boundaries
   ```bash
   python scripts/smart_range_finder.py
   ```

2. **Update Scraper** to use discovered ranges instead of 1-30M

3. **Merge Historical Data**
   Combine old/2024 CSVs with current data for complete dataset

### Long-term Strategy:

- **Monthly Runs:** Check for new certificates in active ranges
- **Annual Updates:** Discover new year patterns (2026, 2027...)
- **Pattern Monitoring:** Watch for format changes

---

## Estimated Total Certificates

Based on patterns:
- **Legacy System (complete):** 3,806 certificates
- **New System (partial):** ~197 found, likely 500-2,000 total
- **Estimated Total:** 4,000-6,000 certificates

---

## Questions to Answer

1. ✅ Why are there two ID systems?
   → Likely system migration/redesign

2. 🔍 When did the new system start?
   → Need to check transition period (late 2023/early 2024)

3. 🔍 Will legacy system continue?
   → Appears frozen at 2024999

4. 🔍 What's the new system's numbering logic?
   → Still unclear, discovery needed

---

**Last Updated:** 2026-01-11
