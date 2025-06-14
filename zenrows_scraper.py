"""
ZenRows API scraper for fallback web scraping.
Provides a reliable fallback when standard scraping methods fail due to anti-bot measures.
"""

import requests
import time
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup

from config_loader import ScrapingTarget, ScraperConfig


class ZenRowsScraper:
    """ZenRows API scraper for handling difficult-to-scrape websites."""
    
    def __init__(self, config: ScraperConfig, api_key: str):
        """
        Initialize ZenRows scraper.
        
        Args:
            config: Main scraper configuration
            api_key: ZenRows API key
        """
        self.config = config
        self.api_key = api_key
        self.base_url = "https://api.zenrows.com/v1/"
        
    def scrape_url(self, url: str, target: ScrapingTarget, use_premium: bool = False) -> Optional[Dict[str, Any]]:
        """
        Scrape a single URL using ZenRows API.
        
        Args:
            url: URL to scrape
            target: Target configuration for content extraction
            use_premium: Whether to use premium features (JS rendering, premium proxies)
            
        Returns:
            Scraped item dictionary or None if failed
        """
        print(f"  🚀 Using ZenRows fallback for: {url}")
        
        # Prepare ZenRows API parameters
        params = {
            'url': url,
            'apikey': self.api_key,
        }
        
        # Add premium features if requested
        if use_premium:
            params.update({
                'js_render': 'true',
                'premium_proxy': 'true',
                'wait': '2000',  # Wait 2 seconds for JS to load
            })
        
        try:
            # Make request to ZenRows API
            response = requests.get(
                self.base_url, 
                params=params, 
                timeout=self.config.timeout * 2  # Give ZenRows more time
            )
            response.raise_for_status()
            
            # Parse the HTML content
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract content using existing target configuration
            title = self._extract_title(soup, target)
            content = self._extract_content(soup, target)
            author = self._extract_author(soup, target)
            
            if not content:
                print(f"    ⚠️  ZenRows: No content found for {url}")
                return None
            
            print(f"    ✅ ZenRows: '{title}' ({len(content)} chars)")
            
            return {
                "title": title,
                "content": content,
                "content_type": target.type,
                "source_url": url,
                "author": author,
                "user_id": "",
                "scraped_with": "zenrows"  # Mark as scraped with ZenRows
            }
            
        except requests.exceptions.RequestException as e:
            print(f"    ❌ ZenRows API error: {e}")
            return None
        except Exception as e:
            print(f"    ❌ ZenRows processing error: {e}")
            return None
    
    def scrape_articles_from_page(self, page_url: str, target: ScrapingTarget, use_premium: bool = False) -> list:
        """
        Discover and scrape articles from a page using ZenRows.
        
        Args:
            page_url: URL of the page containing article links
            target: Target configuration
            use_premium: Whether to use premium features
            
        Returns:
            List of article URLs found
        """
        print(f"  🔍 ZenRows: Discovering articles from {page_url}")
        
        params = {
            'url': page_url,
            'apikey': self.api_key,
        }
        
        if use_premium:
            params.update({
                'js_render': 'true',
                'premium_proxy': 'true',
                'wait': '3000',
            })
        
        try:
            response = requests.get(self.base_url, params=params, timeout=self.config.timeout * 2)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find article links using target configuration
            links = soup.select(target.article_link_selector)
            article_urls = []
            
            for link in links:
                href = link.get('href')
                if href:
                    # Apply filter if specified
                    if target.article_link_filter and target.article_link_filter not in href:
                        continue
                    
                    # Convert to absolute URL
                    from urllib.parse import urljoin
                    full_url = urljoin(page_url, href)
                    article_urls.append(full_url)
            
            print(f"    📄 ZenRows: Found {len(article_urls)} article links")
            return article_urls
            
        except Exception as e:
            print(f"    ❌ ZenRows discovery error: {e}")
            return []
    
    def _extract_title(self, soup: BeautifulSoup, target: ScrapingTarget) -> str:
        """Extract title using target configuration."""
        title_element = soup.select_one(target.title_selector)
        if title_element:
            return title_element.get_text(strip=True)
        return "No Title Found"
    
    def _extract_content(self, soup: BeautifulSoup, target: ScrapingTarget) -> str:
        """Extract content using target configuration."""
        content_paragraphs = []
        
        # Try each content selector
        for selector in target.content_selectors:
            content_container = soup.select_one(selector)
            if content_container:
                # If specific content elements are defined, use them
                if target.content_elements:
                    elements = content_container.select(', '.join(target.content_elements))
                    for element in elements:
                        text = self._process_content_element(element)
                        if text and len(text) >= target.content_min_length:
                            if not self._should_exclude_content(text, target):
                                content_paragraphs.append(text)
                else:
                    # Extract all paragraphs and lists
                    elements = content_container.select('p, ul li, ol li, h2, h3, h4')
                    for element in elements:
                        text = self._process_content_element(element)
                        if text and len(text) >= target.content_min_length:
                            if not self._should_exclude_content(text, target):
                                content_paragraphs.append(text)
                
                # If we found content, break out of the selector loop
                if content_paragraphs:
                    break
        
        # Fallback: try to get content from the entire page
        if not content_paragraphs:
            all_paragraphs = soup.select('p')
            for p in all_paragraphs:
                text = p.get_text(strip=True)
                if (text and len(text) >= target.content_min_length * 2 and  # Higher threshold for fallback
                    not self._should_exclude_content(text, target)):
                    content_paragraphs.append(text)
        
        return "\n\n".join(content_paragraphs)
    
    def _process_content_element(self, element) -> str:
        """Process a single content element and return formatted text."""
        if element.name in ['h2', 'h3', 'h4']:
            # Format headings with markdown
            level = int(element.name[1])
            return f"{'#' * level} {element.get_text(strip=True)}"
        elif element.name == 'li':
            # Format list items
            return f"• {element.get_text(strip=True)}"
        else:
            # Regular content
            return element.get_text(strip=True)
    
    def _should_exclude_content(self, text: str, target: ScrapingTarget) -> bool:
        """Check if content should be excluded based on patterns."""
        text_lower = text.lower()
        for pattern in target.exclude_content_patterns:
            if pattern.lower() in text_lower:
                return True
        return False
    
    def _extract_author(self, soup: BeautifulSoup, target: ScrapingTarget) -> str:
        """Extract author information using target configuration."""
        # If default author is specified, use it
        if target.default_author:
            return target.default_author
        
        # If custom extraction method is specified
        if target.author_extraction == "byline_text":
            return self._extract_author_byline(soup)
        
        # Try the author selector
        if target.author_selector:
            author_element = soup.select_one(target.author_selector)
            if author_element:
                # Check if it's a meta tag
                if author_element.name == 'meta' and 'content' in author_element.attrs:
                    return author_element['content']
                else:
                    return author_element.get_text(strip=True)
        
        # Try common meta tags
        for meta_selector in ['meta[name="author"]', 'meta[property="article:author"]']:
            meta_element = soup.select_one(meta_selector)
            if meta_element and 'content' in meta_element.attrs:
                return meta_element['content']
        
        return ""
    
    def _extract_author_byline(self, soup: BeautifulSoup) -> str:
        """Extract author from byline text (custom method for interviewing.io)."""
        import re
        byline_element = soup.find(text=re.compile(r'By\s+'))
        if byline_element:
            byline_text = byline_element.strip()
            if "By " in byline_text and "|" in byline_text:
                return byline_text.split("By ")[1].split("|")[0].strip()
            elif "By " in byline_text:
                remaining = byline_text.split("By ")[1].strip()
                return remaining.split()[0] if remaining.split() else remaining
        return ""
    
    def check_api_status(self) -> Dict[str, Any]:
        """
        Check ZenRows API status and remaining credits.
        
        Returns:
            Dictionary with API status information
        """
        try:
            # Make a simple test request
            params = {
                'url': 'https://httpbin.org/ip',
                'apikey': self.api_key,
            }
            
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            
            # Check response headers for credit information
            headers = response.headers
            
            return {
                'status': 'active',
                'response_time': response.elapsed.total_seconds(),
                'remaining_credits': headers.get('X-RateLimit-Remaining', 'Unknown'),
                'credits_reset': headers.get('X-RateLimit-Reset', 'Unknown'),
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            } 