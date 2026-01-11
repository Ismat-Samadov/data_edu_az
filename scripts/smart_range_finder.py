#!/usr/bin/env python3
"""
Smart Certificate Range Finder
Efficiently discovers certificate ID ranges using binary search
"""
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from typing import Optional, Tuple
import sys

class SmartRangeFinder:
    """Find certificate ID ranges using binary search"""

    def __init__(self):
        self.base_url = "https://data.edu.az/az/verified"
        self.found_ids = []

    async def check_id(self, session: aiohttp.ClientSession, cert_id: int) -> bool:
        """Check if a certificate ID exists (returns True if found, False if 404)"""
        url = f"{self.base_url}/{cert_id}/"
        try:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'lxml')
                    # Check if it's a valid certificate page (has course name)
                    has_content = bool(soup.find(['h1', 'h2', 'h3']))
                    if has_content:
                        print(f"✓ Found: {cert_id}")
                        return True
                return False
        except Exception as e:
            print(f"✗ Error checking {cert_id}: {e}")
            return False

    async def binary_search_first(self, session: aiohttp.ClientSession,
                                  start: int, end: int) -> Optional[int]:
        """Find the first valid certificate ID in range using binary search"""
        print(f"\n🔍 Searching for FIRST valid ID in range {start:,} - {end:,}")

        left, right = start, end
        first_found = None

        while left <= right:
            mid = (left + right) // 2
            print(f"  Checking {mid:,}...", end=" ")

            exists = await self.check_id(session, mid)

            if exists:
                first_found = mid
                right = mid - 1  # Look for earlier IDs
                print(f"→ Found! Searching lower...")
            else:
                left = mid + 1   # Search higher
                print(f"→ Not found, searching higher...")

        return first_found

    async def binary_search_last(self, session: aiohttp.ClientSession,
                                 start: int, end: int) -> Optional[int]:
        """Find the last valid certificate ID in range using binary search"""
        print(f"\n🔍 Searching for LAST valid ID in range {start:,} - {end:,}")

        left, right = start, end
        last_found = None

        while left <= right:
            mid = (left + right) // 2
            print(f"  Checking {mid:,}...", end=" ")

            exists = await self.check_id(session, mid)

            if exists:
                last_found = mid
                left = mid + 1   # Look for later IDs
                print(f"→ Found! Searching higher...")
            else:
                right = mid - 1  # Search lower
                print(f"→ Not found, searching lower...")

        return last_found

    async def find_range_boundaries(self, year_prefix: str,
                                   min_suffix: int = 1,
                                   max_suffix: int = 999999) -> Optional[Tuple[int, int]]:
        """
        Find the first and last certificate IDs for a given year prefix

        Args:
            year_prefix: E.g., "202" for 2020s, "2024" for 2024
            min_suffix: Minimum suffix to check (default: 1)
            max_suffix: Maximum suffix to check (default: 999999)
        """
        start_id = int(f"{year_prefix}{min_suffix}")
        end_id = int(f"{year_prefix}{max_suffix}")

        print(f"\n{'='*80}")
        print(f"🎯 Finding range for prefix '{year_prefix}'")
        print(f"{'='*80}")

        async with aiohttp.ClientSession() as session:
            # Find first valid ID
            first_id = await self.binary_search_first(session, start_id, end_id)

            if not first_id:
                print(f"\n❌ No certificates found with prefix {year_prefix}")
                return None

            # Find last valid ID (search from first_id to end)
            last_id = await self.binary_search_last(session, first_id, end_id)

            if first_id and last_id:
                count = last_id - first_id + 1
                print(f"\n✅ RANGE FOUND:")
                print(f"   First ID: {first_id:,}")
                print(f"   Last ID:  {last_id:,}")
                print(f"   Count:    ~{count:,} IDs to scan")
                return (first_id, last_id)

            return None

async def main():
    """Main function to discover certificate ranges"""
    finder = SmartRangeFinder()

    print("""
╔═══════════════════════════════════════════════════════════════╗
║     Smart Certificate Range Finder for data.edu.az           ║
║     Uses binary search to efficiently find ID boundaries     ║
╚═══════════════════════════════════════════════════════════════╝
""")

    # Known patterns to verify/discover
    patterns_to_check = [
        # Year 2025 - discover new range
        {"year": "2025", "prefix": "2025", "min_suffix": 1, "max_suffix": 99999},
        {"year": "2025", "prefix": "202", "min_suffix": 5001, "max_suffix": 9999},

        # Year 2024 - verify existing pattern
        {"year": "2024", "prefix": "2024", "min_suffix": 1, "max_suffix": 99999},
        {"year": "2024", "prefix": "202", "min_suffix": 4001, "max_suffix": 4999},

        # Year 2023 - verify
        {"year": "2023", "prefix": "2023", "min_suffix": 1, "max_suffix": 99999},

        # Check for 2026 pattern
        {"year": "2026", "prefix": "2026", "min_suffix": 1, "max_suffix": 99999},
        {"year": "2026", "prefix": "202", "min_suffix": 6001, "max_suffix": 6999},
    ]

    results = []

    for pattern in patterns_to_check:
        result = await finder.find_range_boundaries(
            pattern["prefix"],
            pattern["min_suffix"],
            pattern["max_suffix"]
        )

        if result:
            results.append({
                "year": pattern["year"],
                "prefix": pattern["prefix"],
                "range": result
            })

        # Small delay between searches
        await asyncio.sleep(1)

    # Print summary
    print(f"\n\n{'='*80}")
    print("📊 SUMMARY OF DISCOVERED RANGES")
    print(f"{'='*80}\n")

    if results:
        print("Add these ranges to your scraper:\n")
        for r in results:
            start, end = r["range"]
            print(f"# {r['year']} (prefix: {r['prefix']})")
            print(f"  --start {start} --end {end}\n")
    else:
        print("No ranges discovered. Try adjusting the search parameters.")

if __name__ == "__main__":
    asyncio.run(main())
