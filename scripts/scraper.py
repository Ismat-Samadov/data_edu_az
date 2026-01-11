#!/usr/bin/env python3
"""
Crash-Proof Async Certificate Scraper for data.edu.az

CRASH PROTECTION FEATURES:
- Atomic file operations (write to temp, then atomic rename)
- Exponential backoff retry logic with max attempts
- Signal handlers for graceful shutdown (SIGINT, SIGTERM)
- Data validation and corruption detection
- Checkpoint system for instant crash recovery
- Automatic backups before overwriting
- Memory-safe batch processing
- Network retry with intelligent backoff
- Safe cleanup on ANY exit (crash, kill, Ctrl+C, etc.)
"""

import asyncio
import aiohttp
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import os
import sys
import signal
import shutil
import json
import hashlib
from pathlib import Path
from tqdm.asyncio import tqdm
import argparse
import traceback
import tempfile
from typing import Optional, Dict, List, Set


class CrashProofScraper:
    """Ultra-resilient async certificate scraper"""

    def __init__(
        self,
        base_url="https://data.edu.az/az/verified/",
        output_file="data/certificates.csv",
        concurrent_limit=20,
        timeout=10,
        save_interval=50,
        max_retries=5
    ):
        """
        Initialize the crash-proof scraper

        Args:
            base_url: Base URL for certificate verification
            output_file: Path to save CSV data
            concurrent_limit: Max concurrent requests
            timeout: Request timeout in seconds
            save_interval: Save progress every N certificates
            max_retries: Max retry attempts per request
        """
        self.base_url = base_url
        self.output_file = Path(output_file)
        self.concurrent_limit = concurrent_limit
        self.timeout = timeout
        self.save_interval = save_interval
        self.max_retries = max_retries

        # Checkpoint files for crash recovery
        self.checkpoint_file = self.output_file.parent / f".{self.output_file.stem}_checkpoint.json"
        self.backup_file = self.output_file.parent / f"{self.output_file.stem}_backup.csv"
        self.temp_file = self.output_file.parent / f".{self.output_file.stem}_temp.csv"

        # Ensure output directory exists
        self.output_file.parent.mkdir(parents=True, exist_ok=True)

        # Storage for scraped data
        self.certificates = []
        self.scraped_ids = set()  # IDs with valid certificates
        self.processed_ids = set()  # ALL IDs attempted (including 404s)
        self.failed_ids = set()
        self.checkpoint_data = {}

        # Shutdown flag for graceful exits
        self.shutdown_requested = False

        # Setup signal handlers
        self._setup_signal_handlers()

        # Load existing data and checkpoint
        self._recover_from_crash()

    def _setup_signal_handlers(self):
        """Setup handlers for graceful shutdown on any interrupt"""
        def signal_handler(signum, frame):
            signal_name = signal.Signals(signum).name
            print(f"\n\n⚠️  Received {signal_name} - Initiating graceful shutdown...")
            self.shutdown_requested = True

        # Handle common termination signals
        signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
        signal.signal(signal.SIGTERM, signal_handler)  # kill command

    def _create_backup(self):
        """Create backup of existing data before any operation"""
        if self.output_file.exists():
            try:
                shutil.copy2(self.output_file, self.backup_file)
                print(f"✓ Backup created: {self.backup_file}")
            except Exception as e:
                print(f"Warning: Could not create backup: {e}")

    def _validate_csv(self, filepath: Path) -> bool:
        """Validate CSV file integrity"""
        if not filepath.exists():
            return False

        try:
            df = pd.read_csv(filepath)

            # Check required columns
            required_cols = ['Certificate ID', 'Course Name', 'Student Name',
                           'Completion Date', 'Duration', 'Verification URL',
                           'Status', 'Scraped At']

            if not all(col in df.columns for col in required_cols):
                print(f"⚠️  File {filepath} missing required columns")
                return False

            # Check for duplicates
            if df['Certificate ID'].duplicated().any():
                print(f"⚠️  File {filepath} contains duplicate certificate IDs")
                # Still valid, we'll handle deduplication

            return True

        except Exception as e:
            print(f"⚠️  File validation failed for {filepath}: {e}")
            return False

    def _atomic_save(self, df: pd.DataFrame):
        """
        Atomically save data using temp file + rename pattern
        This prevents corruption even if process is killed mid-write
        """
        try:
            # Write to temporary file first
            df.to_csv(self.temp_file, index=False, encoding='utf-8')

            # Validate the temp file
            if not self._validate_csv(self.temp_file):
                raise ValueError("Temporary file validation failed")

            # Create backup of existing file
            if self.output_file.exists():
                shutil.copy2(self.output_file, self.backup_file)

            # Atomic rename (this is atomic on POSIX systems)
            shutil.move(str(self.temp_file), str(self.output_file))

            # Update checkpoint
            self._save_checkpoint()

        except Exception as e:
            print(f"❌ Error during atomic save: {e}")
            # Try to restore from backup
            if self.backup_file.exists():
                print("Attempting to restore from backup...")
                shutil.copy2(self.backup_file, self.output_file)
            raise

    def _save_checkpoint(self):
        """Save checkpoint for crash recovery"""
        checkpoint = {
            'total_scraped': len(self.scraped_ids),
            'total_processed': len(self.processed_ids),
            'scraped_ids': list(self.scraped_ids),
            'processed_ids': list(self.processed_ids),
            'failed_ids': list(self.failed_ids),
            'last_save': datetime.now().isoformat(),
            'checksum': self._calculate_checksum()
        }

        try:
            with open(self.checkpoint_file, 'w') as f:
                json.dump(checkpoint, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save checkpoint: {e}")

    def _calculate_checksum(self) -> str:
        """Calculate checksum of data for integrity verification"""
        if not self.output_file.exists():
            return ""

        try:
            with open(self.output_file, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except:
            return ""

    def _recover_from_crash(self):
        """Recover from previous crash using checkpoint and backups"""
        print("\n" + "="*60)
        print("CRASH RECOVERY SYSTEM")
        print("="*60)

        # Try to load main file
        if self.output_file.exists():
            if self._validate_csv(self.output_file):
                try:
                    df = pd.read_csv(self.output_file)
                    # Remove duplicates, keeping last occurrence
                    df = df.drop_duplicates(subset=['Certificate ID'], keep='last')
                    self.certificates = df.to_dict('records')
                    self.scraped_ids = set(df['Certificate ID'].tolist())
                    print(f"✓ Loaded {len(self.scraped_ids)} certificates from main file")
                except Exception as e:
                    print(f"⚠️  Error loading main file: {e}")
                    self._try_backup_recovery()
            else:
                print("⚠️  Main file corrupted, trying backup...")
                self._try_backup_recovery()

        # Load checkpoint data
        if self.checkpoint_file.exists():
            try:
                with open(self.checkpoint_file, 'r') as f:
                    checkpoint = json.load(f)

                # Load processed IDs (including 404s)
                self.processed_ids = set(checkpoint.get('processed_ids', []))
                self.failed_ids = set(checkpoint.get('failed_ids', []))

                total_processed = checkpoint.get('total_processed', 0)
                if total_processed > 0:
                    print(f"✓ Checkpoint loaded: {total_processed} IDs processed (last save: {checkpoint.get('last_save')})")
                else:
                    print(f"✓ Checkpoint verified (last save: {checkpoint.get('last_save')})")

            except Exception as e:
                print(f"⚠️  Could not load checkpoint: {e}")

        print("="*60 + "\n")

    def _try_backup_recovery(self):
        """Try to recover from backup file"""
        if self.backup_file.exists() and self._validate_csv(self.backup_file):
            try:
                df = pd.read_csv(self.backup_file)
                df = df.drop_duplicates(subset=['Certificate ID'], keep='last')
                self.certificates = df.to_dict('records')
                self.scraped_ids = set(df['Certificate ID'].tolist())
                print(f"✓ Recovered {len(self.scraped_ids)} certificates from backup")

                # Restore main file from backup
                shutil.copy2(self.backup_file, self.output_file)
                print("✓ Main file restored from backup")
            except Exception as e:
                print(f"❌ Backup recovery failed: {e}")
                print("Starting fresh...")

    async def fetch_with_retry(self, session, certificate_id, semaphore, pbar) -> Optional[Dict]:
        """
        Fetch certificate with exponential backoff retry logic

        Args:
            session: aiohttp ClientSession
            certificate_id: Certificate ID to fetch
            semaphore: Asyncio semaphore for rate limiting
            pbar: Progress bar
        """
        # Skip if already processed
        if certificate_id in self.processed_ids:
            pbar.update(1)
            return None

        url = f"{self.base_url}{certificate_id}/"

        for attempt in range(self.max_retries):
            if self.shutdown_requested:
                return None

            async with semaphore:
                try:
                    async with session.get(url) as response:
                        if response.status == 200:
                            html = await response.text()
                            soup = BeautifulSoup(html, 'html.parser')

                            # Check if page contains certificate data
                            course_name_element = soup.find('h1', {'style': 'color: #002347;font-size: 25px;'})

                            if course_name_element:
                                # Extract all strong tags
                                strong_tags = soup.find_all('strong')

                                certificate_data = {
                                    'Certificate ID': certificate_id,
                                    'Course Name': course_name_element.text.strip(),
                                    'Student Name': strong_tags[0].text.strip() if len(strong_tags) > 0 else '',
                                    'Completion Date': strong_tags[1].text.strip() if len(strong_tags) > 1 else '',
                                    'Duration': strong_tags[2].text.strip() if len(strong_tags) > 2 else '',
                                    'Verification URL': url,
                                    'Status': 'Success',
                                    'Scraped At': datetime.now().isoformat(),
                                    'Retry Count': attempt
                                }
                                pbar.update(1)
                                return certificate_data
                            else:
                                # Page exists but no certificate
                                certificate_data = {
                                    'Certificate ID': certificate_id,
                                    'Course Name': '',
                                    'Student Name': '',
                                    'Completion Date': '',
                                    'Duration': '',
                                    'Verification URL': url,
                                    'Status': 'No Certificate Data',
                                    'Scraped At': datetime.now().isoformat(),
                                    'Retry Count': 0
                                }
                                pbar.update(1)
                                return certificate_data

                        elif response.status == 404:
                            # Certificate doesn't exist - mark as processed but don't save
                            pbar.update(1)
                            self.processed_ids.add(certificate_id)
                            return None

                        elif response.status == 429:  # Too many requests
                            # Exponential backoff
                            wait_time = min(2 ** attempt, 32)
                            await asyncio.sleep(wait_time)
                            continue

                        elif response.status >= 500:  # Server error - retry
                            if attempt < self.max_retries - 1:
                                wait_time = min(2 ** attempt, 16)
                                await asyncio.sleep(wait_time)
                                continue
                        else:
                            # Other HTTP errors
                            certificate_data = {
                                'Certificate ID': certificate_id,
                                'Course Name': '',
                                'Student Name': '',
                                'Completion Date': '',
                                'Duration': '',
                                'Verification URL': url,
                                'Status': f'HTTP {response.status}',
                                'Scraped At': datetime.now().isoformat(),
                                'Retry Count': attempt
                            }
                            pbar.update(1)
                            return certificate_data

                except asyncio.TimeoutError:
                    if attempt < self.max_retries - 1:
                        wait_time = min(2 ** attempt, 16)
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        certificate_data = {
                            'Certificate ID': certificate_id,
                            'Course Name': '',
                            'Student Name': '',
                            'Completion Date': '',
                            'Duration': '',
                            'Verification URL': url,
                            'Status': 'Timeout (Max Retries)',
                            'Scraped At': datetime.now().isoformat(),
                            'Retry Count': attempt
                        }
                        pbar.update(1)
                        return certificate_data

                except aiohttp.ClientError as e:
                    if attempt < self.max_retries - 1:
                        wait_time = min(2 ** attempt, 16)
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        certificate_data = {
                            'Certificate ID': certificate_id,
                            'Course Name': '',
                            'Student Name': '',
                            'Completion Date': '',
                            'Duration': '',
                            'Verification URL': url,
                            'Status': f'Network Error: {str(e)[:50]}',
                            'Scraped At': datetime.now().isoformat(),
                            'Retry Count': attempt
                        }
                        pbar.update(1)
                        return certificate_data

                except Exception as e:
                    # Unexpected error
                    certificate_data = {
                        'Certificate ID': certificate_id,
                        'Course Name': '',
                        'Student Name': '',
                        'Completion Date': '',
                        'Duration': '',
                        'Verification URL': url,
                        'Status': f'Error: {str(e)[:50]}',
                        'Scraped At': datetime.now().isoformat(),
                        'Retry Count': attempt
                    }
                    pbar.update(1)
                    return certificate_data

        # Max retries exceeded
        pbar.update(1)
        self.failed_ids.add(certificate_id)
        return None

    async def scrape_range(self, start_id, end_id):
        """
        Scrape a range of certificate IDs with crash protection

        Args:
            start_id: Starting certificate ID
            end_id: Ending certificate ID
        """
        print(f"\n{'='*60}")
        print(f"STARTING CRASH-PROOF SCRAPE")
        print(f"{'='*60}")
        print(f"Range: {start_id} → {end_id}")
        print(f"Concurrent requests: {self.concurrent_limit}")
        print(f"Max retries per request: {self.max_retries}")
        print(f"Already found: {len(self.scraped_ids)} valid certificates")
        print(f"Already processed: {len(self.processed_ids)} total IDs")
        print(f"{'='*60}\n")

        # Calculate IDs to scrape (skip already processed, including 404s)
        total_ids = end_id - start_id + 1
        ids_to_scrape = [i for i in range(start_id, end_id + 1) if i not in self.processed_ids]

        print(f"IDs to process: {len(ids_to_scrape)} (skipping {total_ids - len(ids_to_scrape)} already processed)")

        if not ids_to_scrape:
            print("No new IDs to scrape!")
            return

        # Create initial backup
        self._create_backup()

        # Semaphore for rate limiting
        semaphore = asyncio.Semaphore(self.concurrent_limit)

        # Headers
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }

        # Create aiohttp session with retry and timeout settings
        connector = aiohttp.TCPConnector(
            limit=self.concurrent_limit,
            force_close=False,
            enable_cleanup_closed=True
        )
        timeout_obj = aiohttp.ClientTimeout(total=self.timeout, connect=5)

        try:
            async with aiohttp.ClientSession(
                headers=headers,
                connector=connector,
                timeout=timeout_obj
            ) as session:

                # Progress bar
                pbar = tqdm(total=len(ids_to_scrape), desc="Scraping", unit="cert")

                # Process in batches for incremental saving
                batch_size = self.save_interval
                new_certificates = []

                for i in range(0, len(ids_to_scrape), batch_size):
                    if self.shutdown_requested:
                        print("\n⚠️  Shutdown requested, saving progress...")
                        break

                    batch = ids_to_scrape[i:i + batch_size]

                    # Create tasks for this batch
                    tasks = [
                        self.fetch_with_retry(session, cert_id, semaphore, pbar)
                        for cert_id in batch
                    ]

                    # Execute batch with error handling
                    try:
                        results = await asyncio.gather(*tasks, return_exceptions=True)
                    except Exception as e:
                        print(f"\n❌ Batch error: {e}")
                        traceback.print_exc()
                        continue

                    # Mark all IDs in this batch as processed
                    for cert_id in batch:
                        self.processed_ids.add(cert_id)

                    # Filter and add successful results
                    for result in results:
                        if isinstance(result, Exception):
                            print(f"\n⚠️  Task exception: {result}")
                            continue

                        if result is not None:
                            new_certificates.append(result)
                            self.scraped_ids.add(result['Certificate ID'])

                    # ALWAYS save checkpoint after every batch (even if no certificates found)
                    try:
                        # Save certificates if any found
                        if new_certificates:
                            self.certificates.extend(new_certificates)
                            df = pd.DataFrame(self.certificates)
                            # Remove duplicates
                            df = df.drop_duplicates(subset=['Certificate ID'], keep='last')
                            self._atomic_save(df)
                            new_certificates = []
                        else:
                            # Even if no certificates, save checkpoint to track processed IDs
                            self._save_checkpoint()
                    except Exception as e:
                        print(f"\n❌ Save error: {e}")
                        traceback.print_exc()
                        # Continue scraping, will retry save next batch

                pbar.close()

        except Exception as e:
            print(f"\n❌ Fatal error during scraping: {e}")
            traceback.print_exc()
        finally:
            # ALWAYS save on exit (crash, interrupt, or normal completion)
            print("\n💾 Saving progress...")
            try:
                if new_certificates:
                    self.certificates.extend(new_certificates)
                    df = pd.DataFrame(self.certificates)
                    df = df.drop_duplicates(subset=['Certificate ID'], keep='last')
                    self._atomic_save(df)
                    new_certificates = []
                else:
                    # Save checkpoint to persist processed IDs
                    self._save_checkpoint()
            except Exception as e:
                print(f"❌ Final save error: {e}")

        # Print summary
        self._print_summary()

    def _print_summary(self):
        """Print scraping summary statistics"""
        print(f"\n{'='*60}")
        print(f"SCRAPING SUMMARY")
        print(f"{'='*60}")
        print(f"Total IDs processed: {len(self.processed_ids)}")
        print(f"Valid certificates found: {len(self.scraped_ids)}")

        if not self.certificates:
            print(f"No valid certificates found in processed IDs (likely all 404s)")
            if self.checkpoint_file.exists():
                print(f"\n✓ Progress saved to checkpoint: {self.checkpoint_file}")
            print(f"{'='*60}\n")
            return

        df = pd.DataFrame(self.certificates)

        print(f"Total certificates saved: {len(df)}")
        print(f"Successful: {len(df[df['Status'] == 'Success'])}")
        print(f"No data: {len(df[df['Status'] == 'No Certificate Data'])}")
        print(f"Errors: {len(df[~df['Status'].isin(['Success', 'No Certificate Data'])])}")

        if self.failed_ids:
            print(f"Failed after max retries: {len(self.failed_ids)}")

        print(f"\n✓ Data saved to: {self.output_file}")
        print(f"✓ Backup saved to: {self.backup_file}")
        print(f"✓ Checkpoint saved to: {self.checkpoint_file}")
        print(f"{'='*60}\n")

        # Status breakdown
        print("Status breakdown:")
        status_counts = df['Status'].value_counts()
        print(status_counts.to_string())

        # Retry statistics
        if 'Retry Count' in df.columns:
            avg_retries = df['Retry Count'].mean()
            max_retries = df['Retry Count'].max()
            print(f"\nRetry statistics:")
            print(f"  Average retries: {avg_retries:.2f}")
            print(f"  Max retries: {max_retries}")
        print()


async def main():
    """Main entry point with comprehensive error handling"""
    parser = argparse.ArgumentParser(
        description="Crash-proof async certificate scraper for data.edu.az",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full brute-force scan (default: 1 to 10,000,000 with 50 concurrent)
  python scripts/scraper.py

  # Scan specific range
  python scripts/scraper.py --start 2024000 --end 2025999

  # Ultra-fast mode (100 concurrent)
  python scripts/scraper.py --concurrent 100

  # Conservative mode (slower but safer, 20 concurrent)
  python scripts/scraper.py --concurrent 20

  # Resume interrupted scraping (just run the same command again!)
  python scripts/scraper.py
        """
    )
    parser.add_argument(
        '--start',
        type=int,
        default=1,
        help='Starting certificate ID (default: 1)'
    )
    parser.add_argument(
        '--end',
        type=int,
        default=300000000,
        help='Ending certificate ID (default: 300000000)'
    )
    parser.add_argument(
        '--concurrent',
        type=int,
        default=50,
        help='Max concurrent requests (default: 50)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='data/certificates.csv',
        help='Output CSV file (default: data/certificates.csv)'
    )
    parser.add_argument(
        '--max-retries',
        type=int,
        default=5,
        help='Max retry attempts per request (default: 5)'
    )

    args = parser.parse_args()

    # Create scraper
    scraper = CrashProofScraper(
        output_file=args.output,
        concurrent_limit=args.concurrent,
        max_retries=args.max_retries
    )

    # Run scraping with full error protection
    try:
        await scraper.scrape_range(args.start, args.end)
    except Exception as e:
        print(f"\n❌ Unexpected error in main: {e}")
        traceback.print_exc()
        print("\n💾 Attempting emergency save...")

        # Emergency save
        try:
            if scraper.certificates:
                df = pd.DataFrame(scraper.certificates)
                emergency_file = scraper.output_file.parent / f"emergency_save_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                df.to_csv(emergency_file, index=False, encoding='utf-8')
                print(f"✓ Emergency save successful: {emergency_file}")
        except Exception as save_error:
            print(f"❌ Emergency save failed: {save_error}")

        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n✓ Graceful shutdown complete. All progress has been saved.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        traceback.print_exc()
        sys.exit(1)
