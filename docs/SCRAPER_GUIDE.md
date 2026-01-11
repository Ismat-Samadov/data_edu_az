# Certificate Scraper Guide

## Quick Start

### 1. Activate Virtual Environment

```bash
source venv/bin/activate
```

### 2. Run the Scraper

**Default settings** (scans 1-10,000,000 with 50 concurrent requests):
```bash
python scripts/scraper.py
```

That's it! The scraper will automatically:
- Scan certificate IDs from 1 to 10,000,000
- Use 50 concurrent requests for maximum speed
- Save data to `data/certificates.csv`
- Create automatic backups and checkpoints
- Resume from where it left off if interrupted

## Customization

### Scan Specific Range
```bash
python scripts/scraper.py --start 2024000 --end 2025999
```

### Ultra-Fast Mode (100 concurrent)
```bash
python scripts/scraper.py --concurrent 100
```

### Conservative Mode (20 concurrent, safer)
```bash
python scripts/scraper.py --concurrent 20
```

### Custom Output File
```bash
python scripts/scraper.py --output data/my_certificates.csv
```

### Adjust Retry Attempts
```bash
python scripts/scraper.py --max-retries 10
```

## Crash Recovery

The scraper is **crash-proof**. You can interrupt it at any time (Ctrl+C) and it will:
1. Save all progress immediately
2. Create a checkpoint file
3. Create a backup of existing data

**To resume**, simply run the same command again:
```bash
python scripts/scraper.py
```

It will automatically:
- Load existing data
- Skip already-scraped IDs
- Continue from where it stopped

## Output Files

### Main Files
- `data/certificates.csv` - Main output file
- `data/certificates_backup.csv` - Automatic backup
- `data/.certificates_checkpoint.json` - Crash recovery checkpoint

### Data Structure
```csv
Certificate ID,Course Name,Student Name,Completion Date,Duration,Verification URL,Status,Scraped At,Retry Count
2024101,Analysis and Reporting with Excel,Turan Hasanova,27 Aprel 2024,"1 month, 4 weeks, 20 hours",https://data.edu.az/az/verified/2024101/,Success,2026-01-11T13:22:50.415136,0
```

## Performance

| Concurrent | Est. Speed | Time for 10M IDs |
|------------|-----------|------------------|
| 20 (safe) | ~48 cert/s | ~58 hours |
| 50 (default) | ~120 cert/s | ~23 hours |
| 100 (ultra-fast) | ~240 cert/s | ~12 hours |

**Note**: Actual certificates found will be much less than total IDs scanned (404s are skipped automatically).

## Crash Protection Features

✅ **Atomic File Operations** - Prevents file corruption
✅ **Exponential Backoff** - Smart retry with up to 5 attempts
✅ **Signal Handlers** - Graceful shutdown on Ctrl+C or kill
✅ **Data Validation** - Checks file integrity on every load
✅ **Checkpoint System** - Resume from exact point of interruption
✅ **Automatic Backups** - Creates backup before every write
✅ **Emergency Save** - Last-resort save on fatal crashes
✅ **Deduplication** - Removes duplicate certificate IDs automatically

## Monitoring Progress

While running, you'll see:
```
============================================================
STARTING CRASH-PROOF SCRAPE
============================================================
Range: 1 → 10000000
Concurrent requests: 50
Max retries per request: 5
Already scraped: 0 certificates
============================================================

IDs to process: 10000000 (skipping 0 already scraped)

Scraping: 45%|████▌     | 4500000/10000000 [12:34:56<15:43:21, 120.5cert/s]
```

## Help

View all options:
```bash
python scripts/scraper.py --help
```

## Troubleshooting

### Rate Limited (429 errors)
Reduce concurrent requests:
```bash
python scripts/scraper.py --concurrent 20
```

### Timeout Errors
Increase max retries:
```bash
python scripts/scraper.py --max-retries 10
```

### File Corrupted
The scraper will automatically recover from backup on next run.

### Out of Memory
Reduce concurrent requests:
```bash
python scripts/scraper.py --concurrent 10
```

## Deactivate Virtual Environment

When done:
```bash
deactivate
```
