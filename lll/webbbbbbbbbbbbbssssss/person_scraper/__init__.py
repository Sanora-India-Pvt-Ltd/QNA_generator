"""
Person Scraper Package
"""

from .scraper import PersonScraper
from .config import GOOGLE_CSE_API_KEY, GOOGLE_CSE_ID, MAX_URLS_TO_SCRAPE

__all__ = ['PersonScraper', 'GOOGLE_CSE_API_KEY', 'GOOGLE_CSE_ID', 'MAX_URLS_TO_SCRAPE']
