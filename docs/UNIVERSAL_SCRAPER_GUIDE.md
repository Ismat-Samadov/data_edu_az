# Universal Scraper Guide

## Overview

The **Universal Scraper** is a comprehensive, future-proof tool that handles all certificate scraping needs for data.edu.az, both current and future.

## Features

✅ **Auto-Discovery** - Finds new certificate patterns automatically
✅ **Future-Proof** - Automatically checks upcoming years (2025, 2026, etc.)
✅ **Legacy Support** - Handles all historical patterns (2020-2024)
✅ **Crash-Proof** - Uses checkpoint system for recovery
✅ **Smart Skip** - Avoids re-scraping already processed IDs
✅ **Binary Search** - Efficiently finds range boundaries
✅ **Flexible Modes** - Multiple operation modes for different use cases

---

## Quick Start

### Monthly Update (Recommended)
```bash
python scripts/universal_scraper.py --mode auto
```
This scrapes ALL known patterns and automatically checks for new years.

### Discover New Patterns
```bash
python scripts/universal_scraper.py --mode discover
```
Finds new certificate ID patterns without scraping.

### Scrape Specific Year
```bash
python scripts/universal_scraper.py --year 2025
```

---

## All Modes

### 🤖 `--mode auto` (Default)
**Full automatic mode** - Scrapes all known patterns and future years

```bash
python scripts/universal_scraper.py --mode auto
```

**What it does:**
- Scrapes new 5-digit system (20XXX)
- Scrapes new 6-digit system (202XXX, 203XXX)
- Scrapes legacy 7-digit patterns (2020-2024)
- Automatically checks 2025, 2026, 2027
- Uses checkpoint system to skip already-processed IDs

**Use when:**
- Monthly data updates
- First-time comprehensive scraping
- After discovering new patterns

---

### 🔎 `--mode discover`
**Pattern discovery only** - Finds new ranges without scraping

```bash
python scripts/universal_scraper.py --mode discover
```

**What it does:**
- Uses binary search to find certificate boundaries
- Checks future years (current + 3 years)
- Checks new 5-digit patterns (20XXX, 21XXX, 22XXX)
- Checks new 6-digit patterns (202XXX - 205XXX)
- Returns discovered ranges for manual scraping

**Use when:**
- You want to see what's new without scraping
- Planning scraping strategy
- Verifying pattern assumptions

---

### 📚 `--mode legacy`
**Legacy patterns only** - Scrapes 2020-2024 7-digit patterns

```bash
python scripts/universal_scraper.py --mode legacy
```

**Patterns scraped:**
- 2020: 2,011,101 - 2,011,994
- 2021: 2,103,599 - 2,103,717
- 2022: 2,022,001 - 2,022,995
- 2023: 2,023,101 - 2,023,999
- 2024: 2,024,101 - 2,024,999

**Use when:**
- Verifying historical data
- Re-scraping legacy ranges
- Checking for updates to old certificates

---

### 🆕 `--mode new`
**New system only** - Scrapes 5-digit and 6-digit patterns

```bash
python scripts/universal_scraper.py --mode new
```

**Patterns scraped:**
- 5-digit: 20,000 - 20,999
- 6-digit 202XXX: 202,000 - 202,999
- 6-digit 203XXX: 203,000 - 203,999

**Use when:**
- Focusing on recent certificates
- Quick updates of active ranges

---

### 🔮 `--mode future`
**Future years only** - Scrapes current year + 2 years ahead

```bash
python scripts/universal_scraper.py --mode future
```

**What it does:**
- Automatically generates patterns for 2025, 2026, 2027
- Uses format: 2025101 - 2025999, etc.

**Use when:**
- New year arrives
- Checking for early certificate issuance
- Future-proofing data collection

---

### 🧪 `--mode test`
**Test mode** - Quick samples from each pattern

```bash
python scripts/universal_scraper.py --mode test
```

**What it does:**
- Scrapes small samples (50 IDs) from each pattern
- Verifies system works correctly
- Fast execution (~30 seconds)

**Use when:**
- Testing after code changes
- Verifying scraper works
- Quick system check

---

## Advanced Usage

### Scrape Specific Year
```bash
python scripts/universal_scraper.py --year 2025
```
Scrapes only 2025 pattern (2025101 - 2025999)

### Custom Range
```bash
python scripts/universal_scraper.py --start 20000 --end 21000
```
Scrapes exact ID range specified

### Adjust Concurrency
```bash
python scripts/universal_scraper.py --mode auto --concurrent 100
```
Increase concurrent requests for faster scraping (use carefully!)

### Custom Output File
```bash
python scripts/universal_scraper.py --mode auto --output data/new_scrape.csv
```
Save to different file

### Discover Then Scrape
```bash
python scripts/universal_scraper.py --mode auto --discover-first
```
Runs pattern discovery before scraping automatically

---

## Use Cases & Recommended Workflows

### Monthly Data Update
```bash
# Run on the 1st of each month
python scripts/universal_scraper.py --mode auto
```
This will:
1. Skip already-processed IDs
2. Get new certificates from active ranges
3. Automatically check for new year patterns
4. Take ~2-5 minutes depending on new data

---

### New Year Setup (January)
```bash
# When new year arrives (e.g., 2026)
python scripts/universal_scraper.py --mode discover
# Review discovered patterns
python scripts/universal_scraper.py --mode future
```

---

### First-Time Complete Scraping
```bash
python scripts/universal_scraper.py --mode auto --concurrent 50
```
Takes ~5-10 minutes for complete historical + current data

---

### Verification After Changes
```bash
python scripts/universal_scraper.py --mode test
```
Quick 30-second test to verify everything works

---

## Pattern Coverage

### Current Patterns (Auto-Detected)

| Pattern | Range | Count | Status |
|---------|-------|-------|--------|
| 5-digit | 20,000 - 20,999 | 1,000 | ✅ Active |
| 6-digit 202XXX | 202,000 - 202,999 | 1,000 | ✅ Active |
| 6-digit 203XXX | 203,000 - 203,999 | 1,000 | ✅ Active |
| 2020 legacy | 2,011,101 - 2,011,994 | 894 | ✅ Complete |
| 2021 legacy | 2,103,599 - 2,103,717 | 119 | ✅ Complete |
| 2021 Excel | 2,021,763 - 2,021,929 | 167 | ✅ Complete |
| 2022 legacy | 2,022,001 - 2,022,995 | 995 | ✅ Complete |
| 2023 legacy | 2,023,101 - 2,023,999 | 899 | ✅ Complete |
| 2024 legacy | 2,024,101 - 2,024,999 | 899 | ✅ Complete |
| 2025 | 2,025,001 - 2,025,999 | 999 | ✅ Auto-checked |
| 2026 | 2,026,001 - 2,026,999 | 999 | ✅ Auto-checked |

---

## Performance

### Speed Estimates

| Mode | IDs Checked | Time @ 50 concurrent | Time @ 100 concurrent |
|------|-------------|----------------------|-----------------------|
| Test | ~200 | 30 seconds | 15 seconds |
| New | ~3,000 | 1 minute | 30 seconds |
| Legacy | ~3,800 | 1.5 minutes | 45 seconds |
| Future | ~3,000 | 1 minute | 30 seconds |
| Auto | ~9,000 | 2-5 minutes | 1-3 minutes |

*Note: With checkpoint system, only new/unprocessed IDs are scraped*

---

## Troubleshooting

### "No new IDs to scrape"
**Cause:** All IDs in range already processed
**Solution:** This is normal! Checkpoint system working correctly.

### Rate limiting (429 errors)
**Cause:** Too many concurrent requests
**Solution:** Reduce concurrency: `--concurrent 30`

### Connection timeouts
**Cause:** Network issues or server load
**Solution:** Script auto-retries. If persists, run again later.

### Missing certificates
**Cause:** Certificates deleted or pattern not in known list
**Solution:** Run `--mode discover` to find new patterns

---

## Integration with Other Scripts

### After Universal Scraper
```bash
# 1. Run universal scraper
python scripts/universal_scraper.py --mode auto

# 2. Verify results
wc -l data/certificates.csv

# 3. Analyze data (create this next!)
python scripts/analyze_data.py

# 4. Generate reports
jupyter notebook analysis/reports.ipynb
```

---

## Output Files

### Generated Files
- `data/certificates.csv` - Main output (all certificates)
- `data/certificates_backup.csv` - Automatic backup
- `data/.certificates_checkpoint.json` - Checkpoint for recovery

### CSV Structure
```
Certificate ID, Course Name, Student Name, Completion Date,
Duration, Verification URL, Status, Scraped At, Retry Count
```

---

## Future Maintenance

### When to Update

**Monthly (Recommended):**
```bash
python scripts/universal_scraper.py --mode auto
```

**New Year:**
```bash
python scripts/universal_scraper.py --mode discover
# Check output, then:
python scripts/universal_scraper.py --mode future
```

**Major Platform Changes:**
```bash
python scripts/universal_scraper.py --mode discover
# Review patterns, update script if needed
```

---

## Tips & Best Practices

1. **Use auto mode for regular updates** - It's smart and comprehensive
2. **Run discovery annually** - Check for new patterns in January
3. **Keep checkpoint files** - Never delete `.certificates_checkpoint.json`
4. **Monitor for 404 spikes** - May indicate pattern changes
5. **Adjust concurrency based on network** - Start with 50, increase if stable
6. **Back up data regularly** - Script creates backups, but external backups recommended
7. **Use test mode after code changes** - Verify nothing broke
8. **Check output file size** - Sudden changes may indicate issues

---

## Support & Updates

### Logs Location
All output is displayed in terminal. Redirect to save:
```bash
python scripts/universal_scraper.py --mode auto 2>&1 | tee scrape.log
```

### Getting Help
```bash
python scripts/universal_scraper.py --help
```

---

**Last Updated:** 2026-01-11
**Version:** 1.0.0
**Tested With:** Python 3.10+, data.edu.az (as of Jan 2026)
