"""
Configuration-driven generic scraper.
This module provides a flexible scraper that works with YAML configuration files.
It complements the UniversalScraper by offering structured, configuration-based scraping.
"""

import concurrent.futures
import re
import time
from urllib.parse import urljoin
from typing import List, Dict, Any, Optional

import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md

from config_loader import ScrapingTarget, ScraperConfig


class GenericScraper:
    """A configuration-driven scraper that can handle multiple sites."""
    
    def __init__(self, config: ScraperConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update(config.headers)
        self.zenrows_scraper = None
        
        # Initialize ZenRows scraper if enabled
        if config.zenrows_config.get('enabled', False):
            api_key = config.zenrows_config.get('api_key')
            if api_key:
                try:
                    from zenrows_scraper import ZenRowsScraper
                    self.zenrows_scraper = ZenRowsScraper(config, api_key)
                    print("🚀 ZenRows fallback scraper initialized")
                except ImportError:
                    print("⚠️  ZenRows scraper module not found. Fallback disabled.")
            else:
                print("⚠️  ZenRows API key not provided. Fallback disabled.")
    
    def scrape_target(self, target: ScrapingTarget) -> List[Dict[str, Any]]:
        """
        Scrape a single target based on its configuration.
        
        Args:
            target: The scraping target configuration
            
        Returns:
            List of scraped items
        """
        if not target.enabled:
            print(f"Skipping disabled target: {target.name}")
            return []
        
        print(f"\n🎯 Starting scrape of {target.name}: {target.url}")
        
        # Get article URLs
        article_urls = self._discover_article_urls(target)
        if not article_urls:
            print(f"  ⚠️  No articles found for {target.name}")
            return []
        
        print(f"  📄 Found {len(article_urls)} articles to scrape")
        
        # Scrape articles in parallel
        return self._scrape_articles_parallel(article_urls, target)
    
    def _discover_article_urls(self, target: ScrapingTarget) -> List[str]:
        """Discover article URLs from the main page or discovery pages."""
        all_urls = set()
        
        # If discovery pages are specified, use them
        if target.discovery_pages:
            search_urls = target.discovery_pages
        else:
            search_urls = [target.url]
        
        for search_url in search_urls:
            try:
                print(f"  🔍 Discovering articles from: {search_url}")
                response = self.session.get(search_url, timeout=self.config.timeout)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find article links
                links = soup.select(target.article_link_selector)
                for link in links:
                    href = link.get('href')
                    if href:
                        # Apply filter if specified
                        if target.article_link_filter and target.article_link_filter not in href:
                            continue
                        
                        # Convert to absolute URL
                        full_url = urljoin(search_url, href)
                        all_urls.add(full_url)
                
            except requests.exceptions.RequestException as e:
                print(f"  ❌ Error discovering from {search_url}: {e}")
                
                # Try ZenRows fallback for discovery if available and enabled
                if (self.zenrows_scraper and 
                    self.config.zenrows_config.get('fallback_for_discovery', True)):
                    print(f"  🚀 Trying ZenRows fallback for discovery...")
                    try:
                        use_premium = self.config.zenrows_config.get('use_premium_for_discovery', False)
                        zenrows_urls = self.zenrows_scraper.scrape_articles_from_page(
                            search_url, target, use_premium
                        )
                        all_urls.update(zenrows_urls)
                    except Exception as zenrows_e:
                        print(f"  ❌ ZenRows discovery also failed: {zenrows_e}")
                
                continue
        
        return list(all_urls)
    
    def _scrape_articles_parallel(self, urls: List[str], target: ScrapingTarget) -> List[Dict[str, Any]]:
        """Scrape multiple articles in parallel."""
        items = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            future_to_url = {
                executor.submit(self._scrape_single_article, url, target): url 
                for url in urls
            }
            
            for future in concurrent.futures.as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    result = future.result()
                    if result:
                        items.append(result)
                except Exception as exc:
                    print(f"  ❌ Error scraping {url}: {exc}")
                
                # Rate limiting
                time.sleep(self.config.request_delay)
        
        return items
    
    def _scrape_single_article(self, url: str, target: ScrapingTarget) -> Optional[Dict[str, Any]]:
        """Scrape a single article."""
        print(f"  📖 Scraping: {url}")
        
        try:
            response = self.session.get(url, timeout=self.config.timeout)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract title
            title = self._extract_title(soup, target)
            
            # Extract content
            content = self._extract_content(soup, target)
            if not content:
                print(f"    ⚠️  No content found for {url}")
                
                # Try ZenRows fallback if available and enabled
                if (self.zenrows_scraper and 
                    self.config.zenrows_config.get('fallback_for_articles', True)):
                    print(f"    🚀 Trying ZenRows fallback...")
                    use_premium = self.config.zenrows_config.get('use_premium_for_articles', False)
                    return self.zenrows_scraper.scrape_url(url, target, use_premium)
                
                return None
            
            # Extract author
            author = self._extract_author(soup, target)
            
            print(f"    ✅ Title: '{title}' ({len(content)} chars)")
            
            return {
                "title": title,
                "content": content,
                "content_type": target.type,
                "source_url": url,
                "author": author,
                "user_id": ""
            }
            
        except requests.exceptions.RequestException as e:
            print(f"    ❌ Network error: {e}")
            
            # Try ZenRows fallback if available and enabled
            if (self.zenrows_scraper and 
                self.config.zenrows_config.get('fallback_for_network_errors', True)):
                print(f"    🚀 Trying ZenRows fallback for network error...")
                use_premium = self.config.zenrows_config.get('use_premium_for_errors', True)
                return self.zenrows_scraper.scrape_url(url, target, use_premium)
            
            return None
        except Exception as e:
            print(f"    ❌ Processing error: {e}")
            return None
    
    def _extract_title(self, soup: BeautifulSoup, target: ScrapingTarget) -> str:
        """Extract the title from the page."""
        title_element = soup.select_one(target.title_selector)
        if title_element:
            return title_element.get_text(strip=True)
        return "No Title Found"
    
    def _extract_content(self, soup: BeautifulSoup, target: ScrapingTarget) -> str:
        """Extract the main content from the page."""
        content_paragraphs = []
        
        # Try each content selector until we find content
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
        """Extract author information."""
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
        byline_element = soup.find(text=re.compile(r'By\s+'))
        if byline_element:
            byline_text = byline_element.strip()
            if "By " in byline_text and "|" in byline_text:
                return byline_text.split("By ")[1].split("|")[0].strip()
            elif "By " in byline_text:
                remaining = byline_text.split("By ")[1].strip()
                return remaining.split()[0] if remaining.split() else remaining
        return ""


 