#!/usr/bin/env python3
"""
Scrape all consolidated certificate IDs efficiently
Uses optimized range-based scraping with the existing crash-proof scraper
"""

import subprocess
import sys
from pathlib import Path

def main():
    """Execute comprehensive rescrape of all consolidated IDs"""

    print("""
╔═══════════════════════════════════════════════════════════════════════════╗
║              COMPREHENSIVE RESCRAPE OF ALL CERTIFICATES                   ║
║                                                                           ║
║  This will scrape ALL known certificate ID ranges efficiently            ║
║  Using the crash-proof scraper with checkpoint recovery                  ║
╚═══════════════════════════════════════════════════════════════════════════╝
    """)

    # Define all ranges to scrape
    scrape_ranges = [
        # New system ranges (high priority - actively growing)
        ("5-digit range", 20000, 20999),
        ("6-digit range (202XXX)", 202000, 202999),
        ("6-digit range (203XXX)", 203000, 203999),

        # 2025-2026 ranges
        ("2025 pattern", 2025001, 2025999),
        ("2026 pattern", 2026001, 2026999),

        # Missing range from Excel file
        ("Excel missing range", 2021763, 2021929),

        # Legacy 7-digit patterns (2020-2024)
        ("2020 legacy", 2011101, 2011994),
        ("2021 legacy", 2103599, 2103717),
        ("2022 legacy", 2022001, 2022995),
        ("2023 legacy", 2023101, 2023999),
        ("2024 legacy", 2024101, 2024999),
    ]

    total_ids = sum(end - start + 1 for _, start, end in scrape_ranges)

    print(f"📊 SCRAPING PLAN")
    print(f"{'='*80}")
    print(f"Total ranges: {len(scrape_ranges)}")
    print(f"Total IDs to check: {total_ids:,}")
    print(f"Estimated time: ~{total_ids / 120 / 60:.1f} minutes @ 120 req/s")
    print(f"\nRanges:")
    for name, start, end in scrape_ranges:
        count = end - start + 1
        print(f"  • {name:30s} {start:>10,} - {end:>10,}  ({count:>6,} IDs)")

    print(f"\n{'='*80}")

    # Ask for confirmation
    response = input("\n🚀 Start comprehensive scraping? (y/N): ").strip().lower()

    if response != 'y':
        print("❌ Scraping cancelled")
        return

    print(f"\n{'='*80}")
    print("🏃 STARTING SCRAPING")
    print(f"{'='*80}\n")

    failed_ranges = []

    for i, (name, start, end) in enumerate(scrape_ranges, 1):
        print(f"\n{'='*80}")
        print(f"Range {i}/{len(scrape_ranges)}: {name}")
        print(f"{start:,} → {end:,}")
        print(f"{'='*80}\n")

        # Run scraper for this range
        cmd = [
            sys.executable,
            "scripts/scraper.py",
            "--start", str(start),
            "--end", str(end),
            "--concurrent", "50",
            "--output", "data/certificates.csv"
        ]

        try:
            result = subprocess.run(cmd, check=True)

            if result.returncode == 0:
                print(f"\n✅ Completed: {name}")
            else:
                print(f"\n⚠️  Warning: {name} returned code {result.returncode}")
                failed_ranges.append((name, start, end))

        except subprocess.CalledProcessError as e:
            print(f"\n❌ Error scraping {name}: {e}")
            failed_ranges.append((name, start, end))

        except KeyboardInterrupt:
            print(f"\n\n⚠️  Interrupted by user!")
            print(f"Progress has been saved. You can resume by running:")
            print(f"  python scripts/scrape_consolidated.py")
            sys.exit(0)

    # Final summary
    print(f"\n{'='*80}")
    print("🎉 COMPREHENSIVE SCRAPING COMPLETE")
    print(f"{'='*80}")

    if failed_ranges:
        print(f"\n⚠️  {len(failed_ranges)} range(s) had issues:")
        for name, start, end in failed_ranges:
            print(f"  • {name}: {start:,} - {end:,}")
        print("\nTo retry failed ranges:")
        for name, start, end in failed_ranges:
            print(f"  python scripts/scraper.py --start {start} --end {end} --concurrent 50")
    else:
        print("\n✅ All ranges scraped successfully!")

    print(f"\n📊 Results:")
    print(f"  Data file: data/certificates.csv")
    print(f"  Backup: data/certificates_backup.csv")
    print(f"  Checkpoint: data/.certificates_checkpoint.json")

    print(f"\n💡 Next steps:")
    print(f"  1. Check results: wc -l data/certificates.csv")
    print(f"  2. Analyze data: python scripts/analyze_data.py")
    print(f"  3. View summary: head -20 data/certificates.csv")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n✓ Gracefully interrupted. All progress saved.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
