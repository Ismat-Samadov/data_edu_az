# Quick Start Guide - data.edu.az Scraper

## For the Impatient 🚀

```bash
# Activate environment
source venv/bin/activate

# Run monthly update (2-5 minutes)
python scripts/universal_scraper.py --mode auto

# Done! Check results
wc -l data/certificates.csv
```

---

## Common Tasks

### 📅 Monthly Update (Most Common)
```bash
python scripts/universal_scraper.py --mode auto
```
Updates all certificates, auto-discovers new patterns.

### 🔍 Discover New Patterns
```bash
python scripts/universal_scraper.py --mode discover
```
Find new certificate ranges without scraping.

### 📆 Scrape Specific Year
```bash
python scripts/universal_scraper.py --year 2025
```

### 🧪 Quick Test
```bash
python scripts/universal_scraper.py --mode test
```

---

## Available Scripts

### 🌟 **universal_scraper.py** (Recommended)
**The all-in-one solution**
- Auto-discovers new patterns
- Handles all ID ranges
- Future-proof (auto-checks new years)
- Smart skip of processed IDs

```bash
python scripts/universal_scraper.py --mode auto
```

### ⚙️ **scraper.py** (Low-level)
**Direct range scraping**
- For manual control
- Specific range targeting
- Called by universal_scraper

```bash
python scripts/scraper.py --start 20000 --end 21000
```

### 📦 **scrape_consolidated.py**
**Batch scraping all known ranges**
- Pre-defined range list
- Sequential execution
- Good for complete re-scraping

```bash
python scripts/scrape_consolidated.py
```

### 🔎 **smart_range_finder.py**
**Binary search for boundaries**
- Finds pattern start/end
- Efficient discovery
- Used by universal_scraper

```bash
python scripts/smart_range_finder.py
```

### 📋 **consolidate_and_rescrape.py**
**Historical data merger**
- Combines all old sources
- Deduplicates IDs
- One-time use

```bash
python scripts/consolidate_and_rescrape.py
```

---

## Which Script to Use?

### ✅ Use `universal_scraper.py` if:
- Monthly/regular updates ⭐ **Most common**
- You want automatic pattern discovery
- You want future-proof scraping
- You're not sure which to use → **Use this!**

### ⚙️ Use `scraper.py` if:
- You need precise control
- Scraping specific range only
- Debugging or testing

### 🔎 Use `smart_range_finder.py` if:
- Just discovering patterns
- Not ready to scrape yet
- Verifying range boundaries

### 📦 Use `scrape_consolidated.py` if:
- Complete re-scrape needed
- All known ranges in sequence

---

## Installation & Setup

### First Time Setup
```bash
# 1. Clone/navigate to project
cd /path/to/data_edu_az

# 2. Create virtual environment (if not exists)
python3 -m venv venv

# 3. Activate
source venv/bin/activate  # macOS/Linux
# OR
venv\Scripts\activate  # Windows

# 4. Install dependencies
pip install -r requirements.txt

# 5. Run!
python scripts/universal_scraper.py --mode auto
```

---

## Understanding the Data

### Output File
`data/certificates.csv`

### Structure
```csv
Certificate ID,Course Name,Student Name,Completion Date,Duration,Verification URL,Status,Scraped At,Retry Count
20241,Oracle Database SQL,Tural Garayev,30 Dekabr 2023,"3months, 12 weeks, 60 hours",https://data.edu.az/az/verified/20241/,Success,2026-01-11T13:49:59.321391,0
```

### Current Stats
- **Total Certificates:** 1,446
- **Years Covered:** 2013-2025
- **ID Patterns:** 5-digit, 6-digit, 7-digit systems

---

## Troubleshooting

### "No module named 'aiohttp'"
```bash
pip install -r requirements.txt
```

### "No new IDs to scrape"
✅ This is **normal**! Checkpoint system working correctly.

### Rate limiting errors
Reduce concurrency:
```bash
python scripts/universal_scraper.py --mode auto --concurrent 30
```

### Script takes too long
Check if you're re-scraping already processed IDs. The checkpoint system should skip them automatically.

---

## Scheduled Automation

### Cron Job (Monthly Update)
```bash
# Run on 1st of each month at 2 AM
0 2 1 * * cd /path/to/data_edu_az && source venv/bin/activate && python scripts/universal_scraper.py --mode auto >> logs/scrape.log 2>&1
```

### GitHub Actions (Weekly)
See `.github/workflows/scrape.yml` (if exists)

---

## Need More Details?

📖 **Full Documentation:**
- `docs/UNIVERSAL_SCRAPER_GUIDE.md` - Complete guide
- `docs/PATTERN_ANALYSIS.md` - ID pattern breakdown
- `docs/SCRAPING_COMPARISON.md` - Efficiency analysis
- `docs/SCRAPER_GUIDE.md` - Low-level scraper docs

💻 **Command Help:**
```bash
python scripts/universal_scraper.py --help
```

---

## Quick Reference Card

| Task | Command | Time |
|------|---------|------|
| Monthly update | `--mode auto` | 2-5 min |
| Find new patterns | `--mode discover` | 1 min |
| Scrape specific year | `--year 2025` | 30 sec |
| Test scraper | `--mode test` | 30 sec |
| Legacy only | `--mode legacy` | 1.5 min |
| New system only | `--mode new` | 1 min |
| Future years | `--mode future` | 1 min |

---

**Questions?** Check the docs or open an issue!

**Last Updated:** 2026-01-11
