import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime
import logging

@dataclass
class ArticleContent:
    url: str
    title: Optional[str] = None
    author: Optional[str] = None
    date: Optional[datetime] = None
    content: Optional[str] = None
    raw_html: Optional[str] = None

class WebsiteScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def fetch_page(self, url: str) -> Optional[str]:
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logging.error(f"Error fetching {url}: {str(e)}")
            return None

    def parse_article(self, url: str) -> Optional[ArticleContent]:
        html_content = self.fetch_page(url)
        if not html_content:
            return None

        soup = BeautifulSoup(html_content, 'html.parser')
        article = ArticleContent(url=url, raw_html=html_content)

        # Try to extract title
        title_tag = soup.find(['h1', 'h2', 'title'])
        article.title = title_tag.text.strip() if title_tag else None

        # Try to extract author
        author_tag = soup.find(class_=['author', 'byline'])
        article.author = author_tag.text.strip() if author_tag else None

        # Try to extract date
        date_tag = soup.find(['time', 'meta[property="article:published_time"]'])
        if date_tag:
            try:
                if date_tag.name == 'time':
                    date_str = date_tag.get('datetime', '')
                else:
                    date_str = date_tag.get('content', '')
                article.date = datetime.fromisoformat(date_str.split('T')[0])
            except (ValueError, AttributeError):
                pass

        # Extract main content
        # This is a basic implementation - might need adjustment based on specific websites
        content_tags = soup.find_all(['p', 'article', 'section'])
        article.content = ' '.join([tag.text.strip() for tag in content_tags if tag.text.strip()])

        return article