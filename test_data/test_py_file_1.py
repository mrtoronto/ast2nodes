from Bio import Entrez
import json
from datetime import datetime
import time
from typing import List, Dict, Any
import logging
import requests
from urllib.error import HTTPError, URLError
import xml.etree.ElementTree as ET
from multiprocessing import Pool, cpu_count, Value, Lock
import os
from functools import partial
import argparse
import random
from tqdm.auto import tqdm
import sys

from settings import DEFAULT_EMAIL, DEFAULT_API_KEY

# Configure logging to work nicely with tqdm
class TqdmLoggingHandler(logging.Handler):
    def __init__(self, level=logging.NOTSET):
        super().__init__(level)

    def emit(self, record):
        try:
            msg = self.format(record)
            tqdm.write(msg)
            self.flush()
        except Exception:
            self.handleError(record)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(processName)s - %(message)s',
    handlers=[TqdmLoggingHandler()]
)
logger = logging.getLogger(__name__)

class RateLimiter:
    """Process-safe rate limiter with jitter"""
    def __init__(self, rate_per_second: float, safety_factor: float = 1.1):
        self.rate_per_second = rate_per_second
        self.safety_factor = safety_factor  # Add some randomness to prevent synchronization
        self.last_check = Value('d', time.time())
        self.lock = Lock()
        
    def acquire(self):
        with self.lock:
            current = time.time()
            time_passed = current - self.last_check.value
            target_wait = (1.0 / self.rate_per_second) * self.safety_factor
            
            # Add small random jitter (±10% of wait time)
            jitter = random.uniform(-0.1, 0.1) * target_wait
            wait_time = max(0, target_wait - time_passed + jitter)
            
            if wait_time > 0:
                time.sleep(wait_time)
            self.last_check.value = time.time()

def create_rate_limiter(rate_per_second: float) -> RateLimiter:
    """Factory function to create a new rate limiter instance"""
    return RateLimiter(rate_per_second)

class PubMedFetcher:
    def __init__(self, email: str = DEFAULT_EMAIL, api_key: str = DEFAULT_API_KEY, rate_per_second: float = None):
        self.email = email
        self.api_key = api_key
        # More conservative rate limits
        default_rate = 7 if api_key else 2  # Reduced from 9/2.5
        self.rate_limiter = create_rate_limiter(rate_per_second if rate_per_second else default_rate)
        self.max_retries = 3
        
        # Set up Entrez
        Entrez.email = email
        if api_key:
            Entrez.api_key = api_key

    def _respect_rate_limit(self):
        """Wait appropriate time to respect rate limit"""
        self.rate_limiter.acquire()

    def _handle_request_with_backoff(self, request_func, max_retries=3, initial_wait=1.0):
        """Execute a request with exponential backoff retry logic.
        
        Args:
            request_func: Callable that makes the actual request
            max_retries: Maximum number of retry attempts
            initial_wait: Initial wait time in seconds
            
        Returns:
            The result of the request_func call
            
        Raises:
            Exception: If all retry attempts fail
        """
        last_exception = None
        for attempt in range(max_retries + 1):
            try:
                # Respect rate limit before making request
                self.rate_limiter.acquire()
                
                # Make the request
                return request_func()
                
            except HTTPError as e:
                last_exception = e
                if e.code == 429:  # Too Many Requests
                    wait_time = initial_wait * (2 ** attempt) + random.uniform(0, 1)
                    logger.warning(f"Rate limit hit, waiting {wait_time:.2f}s before retry {attempt + 1}/{max_retries}")
                    time.sleep(wait_time)
                else:
                    logger.error(f"HTTP error {e.code} on attempt {attempt + 1}/{max_retries}: {str(e)}")
                    if attempt == max_retries:
                        break
                    time.sleep(initial_wait)
                    
            except URLError as e:
                last_exception = e
                logger.error(f"Network error on attempt {attempt + 1}/{max_retries}: {str(e)}")
                if attempt == max_retries:
                    break
                time.sleep(initial_wait)
                
            except Exception as e:
                last_exception = e
                logger.error(f"Unexpected error on attempt {attempt + 1}/{max_retries}: {str(e)}")
                if attempt == max_retries:
                    break
                time.sleep(initial_wait)
                
        if last_exception is not None:
            raise last_exception
        raise Exception("Request failed for unknown reason")

    def get_pmc_full_text(self, pmcid: str) -> str:
        """
        Attempt to fetch full text from PMC for open access articles.
        """
        try:
            def fetch_func():
                handle = Entrez.efetch(db="pmc", id=pmcid, rettype="xml")
                xml_content = handle.read()
                handle.close()
                return xml_content

            xml_content = self._handle_request_with_backoff(fetch_func)
            
            # Parse XML and extract text content
            root = ET.fromstring(xml_content)
            
            # Extract full text content
            text_elements = []
            
            # Get abstract
            abstract = root.findall(".//abstract")
            for abs_elem in abstract:
                text_elements.append(ET.tostring(abs_elem, encoding='unicode', method='text'))
                
            # Get body content
            body = root.findall(".//body")
            for body_elem in body:
                text_elements.append(ET.tostring(body_elem, encoding='unicode', method='text'))
                
            return '\n\n'.join(text_elements).strip()
        except Exception as e:
            logger.error(f"Error fetching PMC full text for {pmcid}: {e}")
            return ""

    def search_pubmed(self, mesh_term: str, max_results: int = 1000) -> List[str]:
        """
        Search PubMed for articles matching the MeSH term.
        Returns a list of PubMed IDs.
        """
        try:
            def search_func():
                logger.info(f"Searching PubMed for MeSH term: {mesh_term}")
                handle = Entrez.esearch(db="pubmed", term=mesh_term, retmax=max_results)
                results = Entrez.read(handle)
                handle.close()
                return results

            results = self._handle_request_with_backoff(search_func)
            return results["IdList"]
        except Exception as e:
            logger.error(f"Error searching PubMed: {e}")
            return []

    def fetch_article_details(self, pmid):
        """Fetch detailed information for a single PubMed article."""
        try:
            def fetch_func():
                handle = Entrez.efetch(db="pubmed", id=pmid, rettype="xml", retmode="xml")
                return handle.read().decode('utf-8')
                
            xml_data = self._handle_request_with_backoff(fetch_func)
            root = ET.fromstring(xml_data)
            
            # Check if we have any PubmedArticle records
            pubmed_article = root.find(".//PubmedArticle")
            if pubmed_article is None:
                logger.error(f"No PubmedArticle found for PMID {pmid}")
                return None
                
            # Extract article IDs (PMC and DOI)
            article_ids = pubmed_article.findall(".//ArticleId")
            pmc_id = None
            doi = None
            for id_elem in article_ids:
                id_type = id_elem.get('IdType', '').lower()
                if id_type == 'pmc':
                    pmc_id = id_elem.text.strip() if id_elem.text else None
                elif id_type == 'doi':
                    doi = id_elem.text.strip() if id_elem.text else None
            
            # Get MedlineCitation
            medline_citation = pubmed_article.find(".//MedlineCitation")
            if medline_citation is None:
                logger.error(f"No MedlineCitation found for PMID {pmid}")
                return None
            
            # Extract basic article info
            article = medline_citation.find(".//Article")
            if article is None:
                logger.error(f"No Article element found for PMID {pmid}")
                return None
            
            # Get title
            title_elem = article.find(".//ArticleTitle")
            title = title_elem.text.strip() if title_elem is not None and title_elem.text else ""
            
            # Get abstract
            abstract_text = []
            abstract = article.find(".//Abstract")
            if abstract is not None:
                # Handle structured abstracts
                abstract_texts = abstract.findall(".//AbstractText")
                for abs_elem in abstract_texts:
                    label = abs_elem.get('Label', '')
                    text = abs_elem.text.strip() if abs_elem.text else ''
                    if label:
                        abstract_text.append(f"{label}: {text}")
                    else:
                        abstract_text.append(text)
            
            # Get authors
            authors = []
            author_list = article.find(".//AuthorList")
            if author_list is not None:
                for author_elem in author_list.findall(".//Author"):
                    author_parts = []
                    
                    last_name = author_elem.find('LastName')
                    if last_name is not None and last_name.text:
                        author_parts.append(last_name.text.strip())
                        
                    fore_name = author_elem.find('ForeName')
                    if fore_name is not None and fore_name.text:
                        author_parts.append(fore_name.text.strip())
                        
                    if author_parts:  # Only add if we have at least one name part
                        authors.append(' '.join(author_parts))
            
            # Get journal info
            journal = article.find(".//Journal")
            journal_info = {}
            if journal is not None:
                journal_title = journal.find(".//Title")
                if journal_title is not None and journal_title.text:
                    journal_info['title'] = journal_title.text.strip()
                
                # Get publication date
                pub_date = journal.find(".//PubDate")
                if pub_date is not None:
                    year = pub_date.find('Year')
                    month = pub_date.find('Month')
                    day = pub_date.find('Day')
                    
                    date_parts = []
                    if year is not None and year.text:
                        date_parts.append(year.text.strip())
                    if month is not None and month.text:
                        date_parts.append(month.text.strip())
                    if day is not None and day.text:
                        date_parts.append(day.text.strip())
                        
                    if date_parts:
                        journal_info['pub_date'] = ' '.join(date_parts)
            
            # Get full text if available
            full_text = None
            if pmc_id:
                try:
                    full_text = self.get_pmc_full_text(pmc_id)
                except Exception as e:
                    logger.warning(f"Failed to fetch full text for PMC ID {pmc_id}: {str(e)}")
            
            return {
                'pmid': pmid,
                'pmc_id': pmc_id,
                'doi': doi,
                'title': title,
                'abstract': '\n'.join(abstract_text) if abstract_text else None,
                'authors': authors,
                'journal': journal_info,
                'full_text': full_text
            }
            
        except Exception as e:
            logger.error(f"Error fetching details for PMID {pmid}: {str(e)}")
            return None

def process_chunk(args: tuple) -> List[Dict[str, Any]]:
    """
    Process a chunk of PMIDs in a separate process.
    Args is a tuple of (pmids, email, api_key, rate_per_second, position)
    position is used to position the progress bar in multiprocessing
    """
    pmids, email, api_key, rate_per_second, position = args
    fetcher = PubMedFetcher(email=email, api_key=api_key, rate_per_second=rate_per_second)
    results = []
    
    # Create progress bar for this chunk
    pbar = tqdm(
        total=len(pmids),
        desc=f"Process {position}",
        position=position,
        leave=False
    )
    
    for pmid in pmids:
        try:
            article_data = fetcher.fetch_article_details(pmid)
            if article_data:
                results.append(article_data)
            pbar.update(1)
        except Exception as e:
            logger.error(f"Error processing PMID {pmid}: {e}")
            pbar.update(1)
    
    pbar.close()
    return results

def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
    """Split a list into chunks of specified size."""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]

def main(mesh_term: str, max_results: int = 1000, processes: int = None, api_key: str = None):
    """
    Main function to search PubMed and save results using multiprocessing.
    """
    # Calculate rate limit based on API key - more conservative limits
    requests_per_second = 7 if api_key else 2  # Reduced from 9/2.5
    
    # Initialize fetcher for the initial search
    fetcher = PubMedFetcher(email=DEFAULT_EMAIL, api_key=api_key, rate_per_second=requests_per_second)
    
    # Search for articles
    logger.info(f"Searching PubMed for MeSH term: {mesh_term}")
    pmids = fetcher.search_pubmed(mesh_term, max_results)
    total_articles = len(pmids)
    logger.info(f"Found {total_articles} articles")

    if total_articles == 0:
        logger.warning("No articles found. Exiting.")
        return

    # Determine number of processes - be more conservative
    if processes is None:
        processes = min(cpu_count(), 4)  # Use at most 4 processes
    
    # Calculate chunk size based on number of processes
    chunk_size = max(10, len(pmids) // (processes * 2))  # Increased minimum chunk size
    chunks = chunk_list(pmids, chunk_size)
    
    logger.info(f"Processing {total_articles} articles using {processes} processes")
    
    # Create progress bar for overall progress
    overall_pbar = tqdm(
        total=total_articles,
        desc="Overall Progress",
        position=0,
        leave=True
    )
    
    # Process chunks in parallel
    with Pool(processes) as pool:
        # Prepare arguments for each chunk
        chunk_args = [
            (chunk, DEFAULT_EMAIL, api_key, requests_per_second/processes, i+1)
            for i, chunk in enumerate(chunks)
        ]
        
        # Process chunks and update progress
        results = []
        for chunk_result in pool.imap_unordered(process_chunk, chunk_args):
            results.extend(chunk_result)
            overall_pbar.update(len(chunk_result))
    
    overall_pbar.close()
    
    # Move cursor to bottom of progress bars
    sys.stdout.write("\n" * (processes + 1))
    sys.stdout.flush()
    
    # Save results to JSON file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"data/pubmed_results_{timestamp}.json"
    
    logger.info(f"Saving {len(results)} articles to {filename}")
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump({
            'mesh_term': mesh_term,
            'total_results': len(results),
            'articles': results
        }, f, indent=2, ensure_ascii=False)
    
    logger.info("Done!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Scrape PubMed articles by MeSH term')
    parser.add_argument('mesh_term', help='MeSH term to search for')
    parser.add_argument('--max-results', type=int, default=1000,
                       help='Maximum number of results to retrieve (default: 1000)')
    parser.add_argument('--processes', type=int, default=None,
                       help='Number of processes to use (default: min(CPU_count, 4))')
    parser.add_argument('--api-key', type=str, default=os.getenv('NCBI_API_KEY'),
                       help='NCBI API key (can also be set via NCBI_API_KEY environment variable)')
    
    args = parser.parse_args()
    main(args.mesh_term, args.max_results, args.processes, args.api_key)