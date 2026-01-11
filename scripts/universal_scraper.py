#!/usr/bin/env python3
"""
Universal Certificate Scraper for data.edu.az
==============================================

A comprehensive, future-proof scraper that automatically discovers and scrapes
all certificate ID patterns, both known and unknown.

Features:
- Auto-discovers new ID patterns using binary search
- Scrapes all known legacy patterns (2020-2024)
- Automatically checks for new years (2025, 2026, etc.)
- Handles both 5-digit, 6-digit, and 7-digit ID systems
- Crash-proof with checkpoint recovery
- Smart skip of already-processed IDs
- Configurable for different use cases

Usage:
    # Full auto mode (recommended for monthly updates)
    python scripts/universal_scraper.py --mode auto

    # Discovery mode only (find new patterns without scraping)
    python scripts/universal_scraper.py --mode discover

    # Legacy ranges only (historical data)
    python scripts/universal_scraper.py --mode legacy

    # Specific year
    python scripts/universal_scraper.py --year 2025

    # Specific range
    python scripts/universal_scraper.py --start 20000 --end 21000

    # Quick test (sample IDs only)
    python scripts/universal_scraper.py --mode test
"""

import asyncio
import aiohttp
from bs4 import BeautifulSoup
import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Optional, Set
import subprocess

class UniversalScraper:
    """
    Universal scraper that handles all certificate ID patterns
    """

    def __init__(self, concurrent=50, output="data/certificates.csv"):
        self.concurrent = concurrent
        self.output = output
        self.base_url = "https://data.edu.az/az/verified"

        # Known pattern definitions
        self.legacy_7digit_patterns = [
            ("2020", 2011101, 2011994),
            ("2021", 2103599, 2103717),
            ("2022", 2022001, 2022995),
            ("2023", 2023101, 2023999),
            ("2024", 2024101, 2024999),
        ]

        self.new_system_patterns = [
            ("5-digit", 20000, 20999),
            ("6-digit 202XXX", 202000, 202999),
            ("6-digit 203XXX", 203000, 203999),
        ]

        # Additional discovered ranges
        self.discovered_patterns = [
            ("Excel range", 2021763, 2021929),
        ]

    def get_current_year(self):
        """Get current year for auto-discovery"""
        return datetime.now().year

    def generate_future_patterns(self, years_ahead=2):
        """
        Generate pattern ranges for future years
        Based on observed patterns: YYYY101 to YYYY999
        """
        current_year = self.get_current_year()
        patterns = []

        for i in range(years_ahead + 1):
            year = current_year + i
            year_short = year % 100  # Get last 2 digits
            start_id = int(f"20{year_short:02d}101")
            end_id = int(f"20{year_short:02d}999")
            patterns.append((f"{year}", start_id, end_id))

        return patterns

    async def quick_check_id(self, cert_id: int) -> bool:
        """Quickly check if a certificate ID exists"""
        url = f"{self.base_url}/{cert_id}/"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        course_name = soup.find('h1', {'style': 'color: #002347;font-size: 25px;'})
                        return course_name is not None
            return False
        except:
            return False

    async def binary_search_range(self, start: int, end: int, pattern_name: str) -> Optional[Tuple[int, int]]:
        """
        Use binary search to find the actual start and end of a certificate range
        """
        print(f"\n🔍 Discovering range for: {pattern_name}")
        print(f"   Searching {start:,} - {end:,}")

        # Find first valid ID
        first_id = await self._binary_search_first(start, end)
        if not first_id:
            print(f"   ❌ No certificates found in range")
            return None

        # Find last valid ID
        last_id = await self._binary_search_last(first_id, end)

        if first_id and last_id:
            print(f"   ✅ Found range: {first_id:,} - {last_id:,}")
            return (first_id, last_id)

        return None

    async def _binary_search_first(self, start: int, end: int) -> Optional[int]:
        """Find first valid ID using binary search"""
        left, right = start, end
        first_found = None

        while left <= right:
            mid = (left + right) // 2
            exists = await self.quick_check_id(mid)

            if exists:
                first_found = mid
                right = mid - 1
            else:
                left = mid + 1

        return first_found

    async def _binary_search_last(self, start: int, end: int) -> Optional[int]:
        """Find last valid ID using binary search"""
        left, right = start, end
        last_found = None

        while left <= right:
            mid = (left + right) // 2
            exists = await self.quick_check_id(mid)

            if exists:
                last_found = mid
                left = mid + 1
            else:
                right = mid - 1

        return last_found

    def run_scraper(self, start: int, end: int, name: str = "range") -> bool:
        """Run the crash-proof scraper for a specific range"""
        print(f"\n{'='*80}")
        print(f"📥 SCRAPING: {name}")
        print(f"   Range: {start:,} - {end:,}")
        print(f"{'='*80}")

        cmd = [
            sys.executable,
            "scripts/scraper.py",
            "--start", str(start),
            "--end", str(end),
            "--concurrent", str(self.concurrent),
            "--output", self.output
        ]

        try:
            result = subprocess.run(cmd, check=True)
            return result.returncode == 0
        except subprocess.CalledProcessError as e:
            print(f"❌ Error scraping {name}: {e}")
            return False
        except KeyboardInterrupt:
            print(f"\n⚠️  Interrupted! Progress saved.")
            return False

    def scrape_all_known_patterns(self):
        """Scrape all known certificate patterns"""
        print(f"\n{'='*80}")
        print("🌐 COMPREHENSIVE SCRAPING - ALL KNOWN PATTERNS")
        print(f"{'='*80}")

        all_patterns = (
            self.new_system_patterns +
            self.legacy_7digit_patterns +
            self.discovered_patterns +
            self.generate_future_patterns(years_ahead=2)
        )

        print(f"\nTotal patterns to scrape: {len(all_patterns)}")
        for name, start, end in all_patterns:
            count = end - start + 1
            print(f"  • {name:20s} {start:>10,} - {end:>10,}  ({count:>6,} IDs)")

        failed = []

        for i, (name, start, end) in enumerate(all_patterns, 1):
            print(f"\n[{i}/{len(all_patterns)}] Processing: {name}")

            success = self.run_scraper(start, end, name)

            if not success:
                failed.append((name, start, end))

        return failed

    async def discover_new_patterns(self):
        """
        Auto-discover new certificate patterns
        Checks for patterns that might exist but aren't in our known list
        """
        print(f"\n{'='*80}")
        print("🔎 PATTERN DISCOVERY MODE")
        print(f"{'='*80}")

        discoveries = []
        current_year = self.get_current_year()

        # Check future years (next 3 years)
        print(f"\n1️⃣  Checking future year patterns...")
        for year in range(current_year, current_year + 4):
            year_short = year % 100
            start_id = int(f"20{year_short:02d}001")
            end_id = int(f"20{year_short:02d}999")

            # Quick sample check
            sample_id = int(f"20{year_short:02d}101")
            exists = await self.quick_check_id(sample_id)

            if exists:
                print(f"   ✅ {year} pattern exists! Discovering range...")
                result = await self.binary_search_range(start_id, end_id, f"{year} pattern")
                if result:
                    discoveries.append((f"{year}", result[0], result[1]))
            else:
                print(f"   ❌ {year} pattern not found (yet)")

        # Check for new 5-digit patterns
        print(f"\n2️⃣  Checking 5-digit patterns...")
        for prefix in [20, 21, 22]:
            start_id = prefix * 1000
            end_id = (prefix + 1) * 1000 - 1

            sample_id = start_id + 241
            exists = await self.quick_check_id(sample_id)

            if exists:
                print(f"   ✅ {prefix}XXX pattern found! Discovering range...")
                result = await self.binary_search_range(start_id, end_id, f"{prefix}XXX pattern")
                if result:
                    discoveries.append((f"{prefix}XXX", result[0], result[1]))

        # Check for new 6-digit patterns
        print(f"\n3️⃣  Checking 6-digit patterns...")
        for prefix in [202, 203, 204, 205]:
            start_id = prefix * 1000
            end_id = (prefix + 1) * 1000 - 1

            sample_id = start_id + 410
            exists = await self.quick_check_id(sample_id)

            if exists:
                print(f"   ✅ {prefix}XXX pattern found! Discovering range...")
                result = await self.binary_search_range(start_id, end_id, f"{prefix}XXX pattern")
                if result:
                    discoveries.append((f"{prefix}XXX", result[0], result[1]))

        return discoveries

    def scrape_test_mode(self):
        """
        Test mode: Scrape small samples from each pattern to verify system works
        """
        print(f"\n{'='*80}")
        print("🧪 TEST MODE - Sampling from known patterns")
        print(f"{'='*80}")

        test_ranges = [
            ("2024 sample", 2024101, 2024150),
            ("2025 sample", 2025101, 2025150),
            ("5-digit sample", 20240, 20260),
            ("6-digit sample", 202400, 202450),
        ]

        for name, start, end in test_ranges:
            self.run_scraper(start, end, name)


def main():
    """Main entry point with comprehensive CLI"""
    parser = argparse.ArgumentParser(
        description="Universal Certificate Scraper for data.edu.az",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full automatic mode (recommended for updates)
  python scripts/universal_scraper.py --mode auto

  # Discover new patterns only (no scraping)
  python scripts/universal_scraper.py --mode discover

  # Legacy data only (2020-2024)
  python scripts/universal_scraper.py --mode legacy

  # Specific year
  python scripts/universal_scraper.py --year 2025

  # Custom range
  python scripts/universal_scraper.py --start 20000 --end 21000

  # Test mode (quick verification)
  python scripts/universal_scraper.py --mode test

  # Future-proof mode (current year + 2 years ahead)
  python scripts/universal_scraper.py --mode future
        """
    )

    parser.add_argument(
        '--mode',
        choices=['auto', 'discover', 'legacy', 'new', 'test', 'future'],
        default='auto',
        help='Scraping mode (default: auto)'
    )
    parser.add_argument(
        '--year',
        type=int,
        help='Scrape specific year (e.g., 2025)'
    )
    parser.add_argument(
        '--start',
        type=int,
        help='Custom start ID'
    )
    parser.add_argument(
        '--end',
        type=int,
        help='Custom end ID'
    )
    parser.add_argument(
        '--concurrent',
        type=int,
        default=50,
        help='Concurrent requests (default: 50)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='data/certificates.csv',
        help='Output file (default: data/certificates.csv)'
    )
    parser.add_argument(
        '--discover-first',
        action='store_true',
        help='Run pattern discovery before scraping'
    )

    args = parser.parse_args()

    scraper = UniversalScraper(
        concurrent=args.concurrent,
        output=args.output
    )

    print("""
╔═══════════════════════════════════════════════════════════════════════════╗
║              UNIVERSAL CERTIFICATE SCRAPER                                ║
║              data.edu.az - Future-Proof Edition                           ║
╚═══════════════════════════════════════════════════════════════════════════╝
    """)

    # Handle different modes
    if args.start and args.end:
        # Custom range mode
        print(f"🎯 Custom Range Mode")
        scraper.run_scraper(args.start, args.end, "Custom Range")

    elif args.year:
        # Specific year mode
        print(f"📅 Year-Specific Mode: {args.year}")
        year_short = args.year % 100
        start = int(f"20{year_short:02d}101")
        end = int(f"20{year_short:02d}999")
        scraper.run_scraper(start, end, f"{args.year}")

    elif args.mode == 'discover':
        # Discovery only mode
        print(f"🔎 Discovery Mode")
        discoveries = asyncio.run(scraper.discover_new_patterns())

        if discoveries:
            print(f"\n{'='*80}")
            print("✅ DISCOVERED PATTERNS")
            print(f"{'='*80}")
            for name, start, end in discoveries:
                print(f"  • {name:20s} {start:>10,} - {end:>10,}")
            print(f"\nTo scrape these ranges, run:")
            for name, start, end in discoveries:
                print(f"  python scripts/universal_scraper.py --start {start} --end {end}")
        else:
            print("\n❌ No new patterns discovered")

    elif args.mode == 'test':
        # Test mode
        scraper.scrape_test_mode()

    elif args.mode == 'legacy':
        # Legacy patterns only
        print(f"📚 Legacy Patterns Mode (2020-2024)")
        for name, start, end in scraper.legacy_7digit_patterns:
            scraper.run_scraper(start, end, name)

    elif args.mode == 'new':
        # New system patterns only
        print(f"🆕 New System Patterns Mode")
        for name, start, end in scraper.new_system_patterns:
            scraper.run_scraper(start, end, name)

    elif args.mode == 'future':
        # Future years only
        print(f"🔮 Future Patterns Mode")
        future_patterns = scraper.generate_future_patterns(years_ahead=2)
        for name, start, end in future_patterns:
            scraper.run_scraper(start, end, name)

    elif args.mode == 'auto':
        # Full automatic mode
        print(f"🤖 Automatic Mode - Comprehensive Scraping")

        if args.discover_first:
            print("\n🔎 Running discovery first...")
            discoveries = asyncio.run(scraper.discover_new_patterns())
            if discoveries:
                print(f"\nFound {len(discoveries)} new patterns!")
                # Add discoveries to patterns
                for name, start, end in discoveries:
                    scraper.discovered_patterns.append((name, start, end))

        failed = scraper.scrape_all_known_patterns()

        # Summary
        print(f"\n{'='*80}")
        print("🏁 SCRAPING COMPLETE")
        print(f"{'='*80}")

        if failed:
            print(f"\n⚠️  {len(failed)} range(s) had issues:")
            for name, start, end in failed:
                print(f"  • {name}: {start:,} - {end:,}")
        else:
            print("\n✅ All patterns scraped successfully!")

        print(f"\n📊 Results saved to: {args.output}")
        print(f"\n💡 Next steps:")
        print(f"  1. Check results: wc -l {args.output}")
        print(f"  2. View data: head -20 {args.output}")
        print(f"  3. Run analysis: python scripts/analyze_data.py")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n✓ Gracefully interrupted. Progress saved.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
