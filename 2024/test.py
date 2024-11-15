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
from typing import Dict, List, Optional, Set, Any
import ujson
import concurrent.futures
from itertools import islice
import multiprocessing
from functools import partial
import numpy as np
from collections import deque
import signal
import logging.handlers
import traceback
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
import aiofiles
import asyncio.exceptions
import platform
from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn
from rich.console import Console
from rich.logging import RichHandler

from dataclasses import dataclass, field
from collections import deque
from typing import Deque

@dataclass
class ScraperStats:
    """Data class to track scraping statistics"""
    start_time: float = time.time()
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_retries: int = 0
    parse_errors: int = 0
    network_errors: int = 0
    request_times: Deque[float] = field(default_factory=lambda: deque(maxlen=1000))

class MaxSpeedScraper:
    def __init__(self, base_url: str, start_id: int, end_id: int, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the scraper with enhanced configuration options
        """
        self.base_url = base_url
        self.start_id = start_id
        self.end_id = end_id
        
        # Load configuration with defaults
        self.config = {
            'chunk_size': 50_000,
            'batch_size': 100,
            'max_concurrent': 50,
            'retry_attempts': 2,
            'request_timeout': 10,
            'connect_timeout': 5,
            'delay_between_requests': 0.1,
            'checkpoint_interval': 0.1,  # 10% chance to checkpoint
            'log_level': logging.INFO,
            'max_log_size': 10 * 1024 * 1024,  # 10MB
            'max_log_backups': 5,
            'progress_bar': True
        }
        if config:
            self.config.update(config)
        
        # Initialize statistics
        self.stats = ScraperStats()
        
        # Setup core components
        self.session = None
        self.successful_ids: Set[int] = set()
        self.failed_ids: Set[int] = set()
        self.results_queue = asyncio.Queue()
        self.parse_strainer = SoupStrainer(['h1', 'h3', 'p', 'input'])
        
        # Setup rich console for better output
        self.console = Console()
        
        # Initialize directories and components
        self.setup_directories()
        self.setup_logging()
        self.setup_checkpointing()
        self.setup_signal_handlers()

    def setup_checkpointing(self):
        """Setup checkpoint system for saving progress"""
        try:
            # Load previous progress if it exists
            checkpoint_file = self.checkpoint_dir / 'progress.ujson'
            if checkpoint_file.exists():
                with open(checkpoint_file, 'r') as f:
                    progress = ujson.load(f)
                    self.successful_ids = set(progress.get('successful_ids', []))
                    self.failed_ids = set(progress.get('failed_ids', []))
                    
                    # Restore statistics if available
                    stats = progress.get('stats', {})
                    self.stats.total_requests = stats.get('total_requests', 0)
                    self.stats.successful_requests = stats.get('successful_requests', 0)
                    self.stats.failed_requests = stats.get('failed_requests', 0)
                    self.stats.total_retries = stats.get('total_retries', 0)
                    self.stats.parse_errors = stats.get('parse_errors', 0)
                    self.stats.network_errors = stats.get('network_errors', 0)
                    
                    self.logger.info(f"Loaded checkpoint with {len(self.successful_ids)} successful and {len(self.failed_ids)} failed IDs")
            else:
                self.logger.info("No checkpoint found, starting fresh")
                self.successful_ids = set()
                self.failed_ids = set()
                
        except Exception as e:
            self.logger.error(f"Error loading checkpoint: {str(e)}\n{traceback.format_exc()}")
            self.successful_ids = set()
            self.failed_ids = set()
    
    def setup_directories(self):
        """Setup directory structure for the scraper"""
        self.base_dir = Path("scraper_data")
        self.logs_dir = self.base_dir / "logs"
        self.checkpoint_dir = self.base_dir / "checkpoints"
        self.output_dir = self.base_dir / "output"
        
        for directory in [self.logs_dir, self.checkpoint_dir, self.output_dir]:
            directory.mkdir(parents=True, exist_ok=True)

    def setup_logging(self):
        """Enhanced logging setup with rich handler and multiple outputs"""
        # Create formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - [%(name)s] - %(message)s - {%(filename)s:%(lineno)d}'
        )
        
        # Configure root logger
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(self.config['log_level'])
        
        # Rich console handler
        console_handler = RichHandler(
            console=self.console,
            show_time=True,
            show_path=False
        )
        console_handler.setLevel(logging.INFO)
        
        # File handlers
        handlers = {
            'main': (self.logs_dir / 'scraper.log', logging.DEBUG),
            'error': (self.logs_dir / 'error.log', logging.ERROR),
            'performance': (self.logs_dir / 'performance.log', logging.INFO)
        }
        
        for name, (path, level) in handlers.items():
            handler = logging.handlers.RotatingFileHandler(
                path,
                maxBytes=self.config['max_log_size'],
                backupCount=self.config['max_log_backups']
            )
            handler.setLevel(level)
            handler.setFormatter(detailed_formatter)
            self.logger.addHandler(handler)
        
        self.logger.addHandler(console_handler)
        
        # Create performance logger
        self.perf_logger = logging.getLogger(f"{__name__}.performance")
        self.perf_logger.setLevel(logging.INFO)

    @contextmanager
    def log_execution_time(self, operation: str):
        """Context manager for timing operations"""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.stats.request_times.append(duration)
            self.perf_logger.debug(f"{operation} completed in {duration:.3f}s")

    async def init_session(self):
        """Initialize optimized aiohttp session with enhanced error handling"""
        timeout = ClientTimeout(
            total=self.config['request_timeout'],
            connect=self.config['connect_timeout']
        )
        
        connector = aiohttp.TCPConnector(
            limit=self.config['max_concurrent'],
            ttl_dns_cache=600,
            force_close=False,
            enable_cleanup_closed=True
        )
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            json_serialize=ujson.dumps,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html',
                'Accept-Encoding': 'gzip'
            }
        )

    async def fetch_url(self, id_num: int) -> Optional[Dict]:
        """Enhanced URL fetching with comprehensive error handling and logging"""
        if id_num in self.successful_ids or id_num in self.failed_ids:
            return None

        self.stats.total_requests += 1
        
        for attempt in range(self.config['retry_attempts']):
            try:
                with self.log_execution_time(f"Fetch URL {id_num}"):
                    url = f"{self.base_url}{id_num}/"
                    async with self.session.get(url) as response:
                        if response.status == 200:
                            html = await response.text()
                            result = self.parse_html(html)
                            if result:
                                result['ID'] = id_num
                                self.successful_ids.add(id_num)
                                self.stats.successful_requests += 1
                                return result
                            self.stats.parse_errors += 1
                        elif response.status == 404:
                            self.failed_ids.add(id_num)
                            self.stats.failed_requests += 1
                            return None
                        else:
                            self.logger.warning(f"Status {response.status} for ID {id_num}")
                            
                        await asyncio.sleep(self.config['delay_between_requests'])
                        
            except (aiohttp.ClientError, asyncio.exceptions.TimeoutError) as e:
                self.stats.network_errors += 1
                self.logger.error(f"Network error for ID {id_num}: {str(e)}")
                self.stats.total_retries += 1
                continue
            except Exception as e:
                self.logger.error(f"Unexpected error for ID {id_num}: {str(e)}\n{traceback.format_exc()}")
                break

        self.failed_ids.add(id_num)
        self.stats.failed_requests += 1
        return None

    def parse_html(self, html: str) -> Optional[Dict]:
        """Enhanced HTML parsing with detailed error logging"""
        try:
            with self.log_execution_time("HTML Parsing"):
                soup = BeautifulSoup(html, 'lxml', parse_only=self.parse_strainer)
                
                # Enhanced selector error handling
                course_title = soup.select_one('h1[style*="color: #002347"]')
                completed_by_tag = soup.select_one('h3.H3_1qzapvr-o_O-weightNormal_s9jwp5-o_O-fontHeadline_1uu0gyz')
                
                if not (course_title and completed_by_tag):
                    return None
                
                result = {
                    "Course_Title": course_title.text.strip(),
                    "Completed_by": completed_by_tag.text.replace('Completed by', '').strip(),
                    "Completion_Date": next((p.text.strip() for p in completed_by_tag.find_next_siblings('p', limit=1)), "N/A"),
                    "Duration": next((p.text.strip() for p in completed_by_tag.find_next_siblings('p')[1:2]), "N/A"),
                    "Shareable_Link": next((i.get('value') for i in soup.select('#copyInput')), "N/A")
                }
                
                # Validate result
                if not all(result.values()):
                    self.logger.warning("Incomplete data parsed from HTML")
                    return None
                    
                return result
                
        except Exception as e:
            self.logger.error(f"HTML parsing error: {str(e)}\n{traceback.format_exc()}")
            return None

    async def process_batch(self, batch_ids: List[int]) -> List[Dict]:
        """Process a batch of IDs with enhanced error handling"""
        tasks = [self.fetch_url(id_num) for id_num in batch_ids]
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            valid_results = [r for r in results if isinstance(r, dict)]
            return valid_results
        except Exception as e:
            self.logger.error(f"Batch processing error: {str(e)}\n{traceback.format_exc()}")
            return []

    async def process_chunk(self, chunk_start: int, chunk_end: int, progress: Optional[Progress] = None):
        """Enhanced chunk processing with progress tracking"""
        self.logger.info(f"Processing chunk: {chunk_start} to {chunk_end}")
        await self.init_session()
        
        try:
            task_id = None
            if progress:
                task_id = progress.add_task(
                    f"Chunk {chunk_start}-{chunk_end}",
                    total=(chunk_end - chunk_start) // self.config['batch_size']
                )
            
            for batch_start in range(chunk_start, chunk_end, self.config['batch_size']):
                batch_end = min(batch_start + self.config['batch_size'], chunk_end)
                batch_ids = list(range(batch_start, batch_end))
                
                results = await self.process_batch(batch_ids)
                
                if results:
                    await self.save_results(results, chunk_start, batch_start)
                
                if random.random() < self.config['checkpoint_interval']:
                    self.log_performance_metrics()
                    await self.save_progress()
                
                if progress and task_id is not None:
                    progress.advance(task_id)
                
        except Exception as e:
            self.logger.error(f"Chunk processing error: {str(e)}\n{traceback.format_exc()}")
        finally:
            await self.session.close()

    async def save_results(self, results: List[Dict], chunk_start: int, batch_start: int):
        """Asynchronous results saving"""
        df = pd.DataFrame(results)
        chunk_file = self.checkpoint_dir / f"chunk_{chunk_start}_{batch_start}.csv"
        
        try:
            async with aiofiles.open(chunk_file, 'w') as f:
                await f.write(df.to_csv(index=False))
        except Exception as e:
            self.logger.error(f"Error saving results: {str(e)}")

    async def save_progress(self):
        """Asynchronous progress saving with error handling"""
        progress = {
            'successful_ids': list(self.successful_ids),
            'failed_ids': list(self.failed_ids),
            'stats': {
                'total_requests': self.stats.total_requests,
                'successful_requests': self.stats.successful_requests,
                'failed_requests': self.stats.failed_requests,
                'total_retries': self.stats.total_retries,
                'parse_errors': self.stats.parse_errors,
                'network_errors': self.stats.network_errors
            }
        }
        
        try:
            checkpoint_file = self.checkpoint_dir / 'progress.ujson'
            async with aiofiles.open(checkpoint_file, 'w') as f:
                await f.write(ujson.dumps(progress))
        except Exception as e:
            self.logger.error(f"Error saving progress: {str(e)}")

    def log_performance_metrics(self):
        """Enhanced performance metrics logging"""
        elapsed_time = time.time() - self.stats.start_time
        request_times = list(self.stats.request_times)
        
        metrics = {
            'Elapsed Time': f"{elapsed_time:.2f}s",
            'Total Requests': self.stats.total_requests,
            'Successful Requests': self.stats.successful_requests,
            'Failed Requests': self.stats.failed_requests,
            'Success Rate': f"{(self.stats.successful_requests/max(1, self.stats.total_requests))*100:.2f}%",
            'Average Request Time': f"{np.mean(request_times):.3f}s" if request_times else "N/A",
            'Median Request Time': f"{np.median(request_times):.3f}s" if request_times else "N/A",
            'Requests/Second': f"{self.stats.total_requests/elapsed_time:.2f}",
            'Network Errors': self.stats.network_errors,
            'Parse Errors': self.stats.parse_errors,
            'Total Retries': self.stats.total_retries
        }
        
        self.perf_logger.info("Performance Metrics:\n" + 
                            "\n".join(f"- {k}: {v}" for k, v in metrics.items()))

    async def scrape_data(self) -> pd.DataFrame:
            """Enhanced main scraping method with progress bar"""
            chunks = [
                (i, min(i + self.config['chunk_size'], self.end_id + 1))
                for i in range(self.start_id, self.end_id + 1, self.config['chunk_size'])
            ]
            
            with Progress(
                SpinnerColumn(),
                *Progress.get_default_columns(),
                TimeElapsedColumn(),
                console=self.console
            ) as progress:
                for chunk_start, chunk_end in chunks:
                    await self.process_chunk(chunk_start, chunk_end, progress)
            
            # Final performance metrics
            self.log_performance_metrics()
            
            # Merge all chunk files with error handling
            return await self.merge_results()

    async def merge_results(self) -> pd.DataFrame:
        """Merge all chunk files with enhanced error handling"""
        try:
            all_files = list(self.checkpoint_dir.glob("chunk_*.csv"))
            if not all_files:
                self.logger.warning("No result files found to merge")
                return pd.DataFrame()
            
            self.logger.info(f"Merging {len(all_files)} chunk files")
            
            dfs = []
            for file in all_files:
                try:
                    df = pd.read_csv(file)
                    dfs.append(df)
                except Exception as e:
                    self.logger.error(f"Error reading chunk file {file}: {str(e)}")
            
            if not dfs:
                return pd.DataFrame()
            
            final_df = pd.concat(dfs, ignore_index=True)
            
            # Remove duplicates if any
            final_df = final_df.drop_duplicates(subset=['ID'], keep='last')
            
            # Sort by ID for consistency
            final_df = final_df.sort_values('ID').reset_index(drop=True)
            
            return final_df
            
        except Exception as e:
            self.logger.error(f"Error merging results: {str(e)}\n{traceback.format_exc()}")
            return pd.DataFrame()

    def handle_shutdown(self, signum, frame):
        """Enhanced shutdown handler with final metrics and cleanup"""
        self.logger.warning(f"Received shutdown signal {signum}")
        self.console.print("[yellow]Shutdown signal received. Cleaning up...[/yellow]")
        
        # Log final metrics
        self.log_performance_metrics()
        
        # Save final progress
        asyncio.run(self.save_progress())
        
        # Clean up session if active
        if self.session and not self.session.closed:
            asyncio.run(self.session.close())
        
        self.console.print("[green]Cleanup completed. Exiting...[/green]")
        exit(0)

    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        # Handle SIGINT (Ctrl+C) and SIGTERM
        signal.signal(signal.SIGINT, self.handle_shutdown)
        signal.signal(signal.SIGTERM, self.handle_shutdown)
        
        # Handle SIGBREAK on Windows
        if platform.system() == 'Windows':
            signal.signal(signal.SIGBREAK, self.handle_shutdown)

def run_max_speed_scraper(
    base_url: str,
    start_id: int,
    end_id: int,
    output_file: str = 'output.csv',
    config: Optional[Dict[str, Any]] = None
) -> pd.DataFrame:
    """Enhanced runner function with configuration options and error handling"""
    console = Console()
    
    try:
        start_time = time.time()
        
        console.print(f"[bold blue]Starting scraper for IDs {start_id} to {end_id}[/bold blue]")
        console.print(f"Base URL: {base_url}")
        
        scraper = MaxSpeedScraper(base_url, start_id, end_id, config)
        df = asyncio.run(scraper.scrape_data())
        
        if not df.empty:
            # Save to both CSV and Excel for convenience
            output_path = scraper.output_dir / output_file
            df.to_csv(output_path.with_suffix('.csv'), index=False)
            df.to_excel(output_path.with_suffix('.xlsx'), index=False)
            
            console.print(f"[green]Data saved to {output_path.with_suffix('.csv')} and {output_path.with_suffix('.xlsx')}[/green]")
        else:
            console.print("[yellow]No data was collected[/yellow]")
        
        elapsed_time = time.time() - start_time
        console.print(f"[bold green]Scraping completed in {elapsed_time:.2f} seconds[/bold green]")
        console.print(f"Total records found: {len(df)}")
        
        return df
        
    except Exception as e:
        console.print(f"[bold red]Error running scraper: {str(e)}[/bold red]")
        console.print(traceback.format_exc())
        return pd.DataFrame()

if __name__ == "__main__":
    # Example configuration
    config = {
        'chunk_size': 50_000,
        'batch_size': 100,
        'max_concurrent': 50,
        'retry_attempts': 2,
        'request_timeout': 10,
        'connect_timeout': 5,
        'delay_between_requests': 0.1,
        'checkpoint_interval': 0.1,
        'log_level': logging.INFO,
        'max_log_size': 10 * 1024 * 1024,
        'max_log_backups': 5,
        'progress_bar': True
    }
    
    BASE_URL = "https://data.edu.az/en/verified/"
    START_ID = 2022
    END_ID = 2022100
    
    df = run_max_speed_scraper(
        base_url=BASE_URL,
        start_id=START_ID,
        end_id=END_ID,
        output_file='scraped_data.csv',
        config=config
    )