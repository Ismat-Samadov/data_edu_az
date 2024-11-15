import asyncio
import aiohttp
from bs4 import BeautifulSoup, SoupStrainer
import pandas as pd
import time
import logging
from datetime import datetime
import os
import random
from aiohttp import ClientTimeout
from typing import Dict, List, Optional, Set
import ujson  # Faster JSON parser
import concurrent.futures
from itertools import islice
import multiprocessing
from functools import partial
import numpy as np
from collections import deque
import signal

class MaxSpeedScraper:
    def __init__(self, base_url: str, start_id: int, end_id: int):
        self.base_url = base_url
        self.start_id = start_id
        self.end_id = end_id
        
        # Optimization settings
        self.chunk_size = 50_000  # Size of chunks for parallel processing
        self.batch_size = 100  # Size of batches within chunks
        self.max_concurrent = 50  # Maximum concurrent requests
        self.retry_attempts = 2  # Reduced retry attempts for speed
        self.parser_processes = max(1, multiprocessing.cpu_count() - 1)  # Leave one CPU core free
        
        # Performance optimizations
        self.session = None
        self.successful_ids: Set[int] = set()
        self.failed_ids: Set[int] = set()
        self.results_queue = asyncio.Queue()
        self.parse_strainer = SoupStrainer(['h1', 'h3', 'p', 'input'])  # Parse only needed tags
        
        # Setup
        self.setup_logging()
        self.setup_checkpointing()
        self.setup_signal_handlers()

    def setup_logging(self):
        """Configure minimal logging for performance"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(message)s',
            handlers=[logging.FileHandler('scraping.log'), logging.StreamHandler()]
        )
        self.logger = logging.getLogger(__name__)

    def setup_checkpointing(self):
        """Setup checkpoint directory and load existing progress"""
        self.checkpoint_dir = "checkpoints"
        os.makedirs(self.checkpoint_dir, exist_ok=True)
        self.checkpoint_file = f"{self.checkpoint_dir}/progress.ujson"
        self.load_progress()

    def setup_signal_handlers(self):
        """Setup graceful shutdown handlers"""
        signal.signal(signal.SIGINT, self.handle_shutdown)
        signal.signal(signal.SIGTERM, self.handle_shutdown)

    def handle_shutdown(self, signum, frame):
        """Handle graceful shutdown"""
        self.logger.info("Shutdown signal received. Saving progress...")
        self.save_progress()
        exit(0)

    async def init_session(self):
        """Initialize optimized aiohttp session"""
        timeout = ClientTimeout(total=10, connect=5)  # Reduced timeout for faster failure
        connector = aiohttp.TCPConnector(
            limit=self.max_concurrent,
            ttl_dns_cache=600,
            force_close=False,
            enable_cleanup_closed=True
        )
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            json_serialize=ujson.dumps,  # Faster JSON serialization
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html',
                'Accept-Encoding': 'gzip'
            }
        )

    def parse_html(self, html: str) -> Optional[Dict]:
        """Optimized HTML parsing"""
        try:
            soup = BeautifulSoup(html, 'lxml', parse_only=self.parse_strainer)
            
            # Fast tag finding with CSS selectors
            course_title = soup.select_one('h1[style*="color: #002347"]')
            if not course_title:
                return None
            
            completed_by_tag = soup.select_one('h3.H3_1qzapvr-o_O-weightNormal_s9jwp5-o_O-fontHeadline_1uu0gyz')
            if not completed_by_tag:
                return None

            # Fast text extraction
            return {
                "Course_Title": course_title.text.strip(),
                "Completed_by": completed_by_tag.text.replace('Completed by', '').strip(),
                "Completion_Date": next((p.text.strip() for p in completed_by_tag.find_next_siblings('p', limit=1)), "N/A"),
                "Duration": next((p.text.strip() for p in completed_by_tag.find_next_siblings('p')[1:2]), "N/A"),
                "Shareable_Link": next((i.get('value') for i in soup.select('#copyInput')), "N/A")
            }
        except Exception:
            return None

    async def fetch_url(self, id_num: int) -> Optional[Dict]:
        """Optimized URL fetching with minimal retry logic"""
        if id_num in self.successful_ids:
            return None
        
        if id_num in self.failed_ids:
            return None

        for _ in range(self.retry_attempts):
            try:
                url = f"{self.base_url}{id_num}/"
                async with self.session.get(url) as response:
                    if response.status == 200:
                        html = await response.text()
                        result = self.parse_html(html)
                        if result:
                            result['ID'] = id_num
                            self.successful_ids.add(id_num)
                            return result
                    elif response.status == 404:
                        self.failed_ids.add(id_num)
                        return None
                    await asyncio.sleep(0.1)  # Minimal delay
            except Exception:
                continue
        
        self.failed_ids.add(id_num)
        return None

    async def process_batch(self, batch_ids: List[int]) -> List[Dict]:
        """Process a batch of IDs concurrently"""
        tasks = [self.fetch_url(id_num) for id_num in batch_ids]
        results = await asyncio.gather(*tasks)
        return [r for r in results if r is not None]

    def save_progress(self):
        """Save progress using ujson for speed"""
        progress = {
            'successful_ids': list(self.successful_ids),
            'failed_ids': list(self.failed_ids)
        }
        with open(self.checkpoint_file, 'w') as f:
            ujson.dump(progress, f)

    def load_progress(self):
        """Load previous progress"""
        try:
            with open(self.checkpoint_file, 'r') as f:
                progress = ujson.load(f)
                self.successful_ids = set(progress.get('successful_ids', []))
                self.failed_ids = set(progress.get('failed_ids', []))
        except FileNotFoundError:
            self.successful_ids = set()
            self.failed_ids = set()

    async def process_chunk(self, chunk_start: int, chunk_end: int):
        """Process a chunk of IDs"""
        await self.init_session()
        try:
            for batch_start in range(chunk_start, chunk_end, self.batch_size):
                batch_end = min(batch_start + self.batch_size, chunk_end)
                batch_ids = list(range(batch_start, batch_end))
                results = await self.process_batch(batch_ids)
                
                if results:
                    # Save results immediately
                    df = pd.DataFrame(results)
                    chunk_file = f"{self.checkpoint_dir}/chunk_{chunk_start}_{batch_start}.csv"
                    df.to_csv(chunk_file, index=False)
                
                # Periodic progress save
                if random.random() < 0.1:  # 10% chance to save progress
                    self.save_progress()
                
        finally:
            await self.session.close()

    async def scrape_data(self) -> pd.DataFrame:
        """Main scraping method with chunked processing"""
        chunks = [
            (i, min(i + self.chunk_size, self.end_id + 1))
            for i in range(self.start_id, self.end_id + 1, self.chunk_size)
        ]
        
        for chunk_start, chunk_end in chunks:
            await self.process_chunk(chunk_start, chunk_end)
        
        # Merge all chunk files
        all_files = [f for f in os.listdir(self.checkpoint_dir) if f.startswith("chunk_") and f.endswith(".csv")]
        if not all_files:
            return pd.DataFrame()
        
        dfs = []
        for file in all_files:
            df = pd.read_csv(os.path.join(self.checkpoint_dir, file))
            dfs.append(df)
        
        return pd.concat(dfs, ignore_index=True)

def run_max_speed_scraper(base_url: str, start_id: int, end_id: int, output_file: str = 'output.csv'):
    """Run the maximum speed scraper"""
    start_time = time.time()
    
    scraper = MaxSpeedScraper(base_url, start_id, end_id)
    df = asyncio.run(scraper.scrape_data())
    
    if not df.empty:
        df.to_csv(output_file, index=False)
    
    elapsed_time = time.time() - start_time
    print(f"Scraping completed in {elapsed_time:.2f} seconds")
    print(f"Total records found: {len(df)}")
    print(f"Data saved to {output_file}")
    return df

if __name__ == "__main__":
    BASE_URL = "https://data.edu.az/en/verified/"
    START_ID = 2022
    END_ID = 2022100  
    
    df = run_max_speed_scraper(BASE_URL, START_ID, END_ID)