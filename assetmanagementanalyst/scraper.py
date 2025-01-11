import trafilatura
import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy.signalmanager import dispatcher
from scrapy import signals
import logging
from typing import Optional, Dict
from dataclasses import dataclass
from datetime import datetime
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('scraper.log')
    ]
)

@dataclass
class ArticleContent:
    url: str
    content: Optional[str] = None
    raw_html: Optional[str] = None
    title: Optional[str] = None
    author: Optional[str] = None
    date: Optional[datetime] = None

class ArticleSpider(scrapy.Spider):
    name = 'article_spider'
    
    def __init__(self, url: str, *args, **kwargs):
        super(ArticleSpider, self).__init__(*args, **kwargs)
        self.start_urls = [url]
        self.results: Dict = {}

    def clean_text(self, text: str) -> str:
        """Clean extracted text by removing extra whitespace and unwanted characters."""
        if not text:
            return ""
        text = re.sub(r'\s+', ' ', text.strip())
        text = re.sub(r'(cookie|privacy|subscribe|advertisement)', '', text, flags=re.IGNORECASE)
        return text

    def parse(self, response):
        try:
            # Title extraction with priority
            title = None
            title_selectors = [
                'h1::text',
                'meta[property="og:title"]::attr(content)',
                'meta[name="twitter:title"]::attr(content)',
                'title::text',
                '.article-title::text',
                '.post-title::text'
            ]
            
            for selector in title_selectors:
                title = response.css(selector).get()
                if title:
                    title = self.clean_text(title)
                    break

            # Author extraction with priority
            author = None
            author_selectors = [
                'meta[name="author"]::attr(content)',
                'meta[property="article:author"]::attr(content)',
                '.author::text',
                '.byline::text',
                '[rel="author"]::text'
            ]
            
            for selector in author_selectors:
                author = response.css(selector).get()
                if author:
                    author = self.clean_text(author)
                    break

            # Date extraction
            date = None
            date_selectors = [
                'meta[property="article:published_time"]::attr(content)',
                'meta[name="publication-date"]::attr(content)',
                'time::attr(datetime)',
                '.date::text',
                '.published-date::text'
            ]
            
            for selector in date_selectors:
                date_str = response.css(selector).get()
                if date_str:
                    try:
                        date = datetime.fromisoformat(date_str.split('T')[0])
                        break
                    except ValueError:
                        continue

            # Content extraction with main content area detection
            content = ""
            main_content_selectors = [
                'article',
                'main',
                '#main-content',
                '.main-content',
                '.article-content',
                '.post-content'
            ]
            
            for selector in main_content_selectors:
                text_elements = response.css(
                    f'{selector} p::text, '
                    f'{selector} li::text, '
                    f'{selector} h1::text, '
                    f'{selector} h2::text, '
                    f'{selector} h3::text'
                ).getall()
                
                if text_elements:
                    content = ' '.join([
                        self.clean_text(text) for text in text_elements
                        if self.clean_text(text) and len(self.clean_text(text)) > 30
                    ])
                    break
            
            # Fallback to all text if no content found in main selectors
            if not content:
                text_elements = response.css('p::text, li::text, h1::text, h2::text, h3::text').getall()
                content = ' '.join([
                    self.clean_text(text) for text in text_elements
                    if self.clean_text(text) and len(self.clean_text(text)) > 30
                ])

            self.results = {
                'title': title,
                'author': author,
                'date': date,
                'content': content,
                'raw_html': response.text
            }
            
        except Exception as e:
            logging.error(f"Scrapy parsing error: {str(e)}")

class WebsiteScraper:
    def __init__(self):
        self.process = CrawlerProcess({
            'USER_AGENT': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'LOG_LEVEL': 'ERROR',
            'ROBOTSTXT_OBEY': True,
            'COOKIES_ENABLED': True,
            'MEMUSAGE_ENABLED': True,
            'MEMUSAGE_LIMIT_MB': 512,
            'CONCURRENT_REQUESTS': 1,
            'DOWNLOAD_DELAY': 1,
            'RETRY_ENABLED': True,
            'RETRY_TIMES': 3,
            'RETRY_HTTP_CODES': [500, 502, 503, 504, 522, 524, 408, 429]
        })

    def _run_scrapy(self, url: str) -> Optional[Dict]:
        """Run Scrapy spider with proper error handling and retries."""
        try:
            spider = ArticleSpider
            results = {}
            
            def crawler_results(signal, sender, item, response, spider):
                results.update(item)
            
            dispatcher.connect(crawler_results, signal=signals.item_scraped)
            
            self.process.crawl(spider, url=url)
            self.process.start(stop_after_crawl=True)
            
            return results
        except Exception as e:
            logging.error(f"Scrapy extraction failed: {str(e)}")
            return None

    def parse_article(self, url: str) -> Optional[ArticleContent]:
        """Main method to parse articles with fallback mechanisms."""
        if not url:
            logging.error("No URL provided")
            return None

        try:
            urlparse(url)
        except Exception as e:
            logging.error(f"Invalid URL format: {str(e)}")
            return None

        article = ArticleContent(url=url)
        
        # First attempt: Trafilatura
        try:
            downloaded = trafilatura.fetch_url(url)
            if downloaded:
                # Extract metadata first
                metadata = trafilatura.extract_metadata(downloaded)
                if metadata and isinstance(metadata, dict):
                    article.title = metadata.get('title')
                    article.author = metadata.get('author')
                    if metadata.get('date'):
                        try:
                            article.date = datetime.fromisoformat(metadata.get('date').split('T')[0])
                        except ValueError:
                            logging.warning(f"Could not parse date: {metadata.get('date')}")
                
                # Extract content
                content = trafilatura.extract(
                    downloaded,
                    include_comments=False,
                    include_tables=True,
                    no_fallback=False,
                    include_links=False,
                    include_images=False
                )
                
                if content and len(content.strip()) > 100:
                    article.content = content
                    article.raw_html = downloaded
                    logging.info(f"Successfully extracted content using Trafilatura: {len(content)} chars")
                    return article
                else:
                    logging.warning("Trafilatura found no substantial content")
                    
        except Exception as e:
            logging.warning(f"Trafilatura extraction failed: {str(e)}")

        # Fallback: Scrapy
        logging.info("Falling back to Scrapy extraction...")
        try:
            results = self._run_scrapy(url)
            if results and results.get('content'):
                article.content = results.get('content')
                article.title = results.get('title')
                article.author = results.get('author')
                article.raw_html = results.get('raw_html')
                if results.get('date'):
                    article.date = results.get('date')
                logging.info(f"Successfully extracted content using Scrapy: {len(results['content'])} chars")
                return article
                
        except Exception as e:
            logging.error(f"Scrapy extraction failed: {str(e)}")

        logging.error(f"All content extraction methods failed for {url}")
        return None

    def validate_content(self, article: ArticleContent) -> bool:
        """Validate extracted content."""
        if not article.content or len(article.content.strip()) < 100:
            logging.warning("Content validation failed: Content too short or empty")
            return False
            
        if not article.title:
            logging.warning("Content validation failed: No title found")
            return False
            
        return True