"""
Universal web scraper that dynamically detects content without hardcoded structures.
Uses heuristics and machine learning-like approaches to identify main content areas.
Enhanced to automatically scrape all sources from the original requirements.
Now includes ZenRows API fallback for reliable scraping.
"""

import re
import time
import json
import concurrent.futures
from typing import List, Dict, Any, Optional, Tuple, Set
from urllib.parse import urljoin, urlparse
from collections import Counter

import requests
from bs4 import BeautifulSoup, Tag, NavigableString


class ZenRowsIntegration:
    """Simple ZenRows integration for fallback scraping."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.zenrows.com/v1/"
        self.session = requests.Session()
    
    def scrape_with_zenrows(self, url: str, use_premium: bool = False) -> Optional[BeautifulSoup]:
        """Scrape URL using ZenRows API."""
        print(f"    🚀 Using ZenRows fallback for: {url}")
        
        try:
            params = {
                'url': url,
                'apikey': self.api_key,
                'js_render': 'true' if use_premium else 'false',
                'premium_proxy': 'true' if use_premium else 'false',
                'custom_headers': 'true'
            }
            
            response = self.session.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            
            if response.status_code == 200 and response.content:
                soup = BeautifulSoup(response.content, 'html.parser')
                print(f"    ✅ ZenRows successfully fetched content")
                return soup
            else:
                print(f"    ⚠️  ZenRows returned empty content")
                return None
                
        except Exception as e:
            print(f"    ❌ ZenRows error: {e}")
            return None


class ContentDetector:
    """Detects main content areas using heuristic analysis."""
    
    def __init__(self):
        self.content_indicators = [
            'article', 'main', '[role="main"]', '.content', '.post-content',
            '.article-content', '.blog-content', '.entry-content', '.post-body'
        ]
        
        self.exclude_tags = {'nav', 'footer', 'header', 'aside', 'script', 'style', 'noscript'}
        self.exclude_classes = {
            'nav', 'navigation', 'menu', 'sidebar', 'footer', 'header', 'advertisement',
            'ads', 'social', 'share', 'comment', 'related', 'recommended', 'popup'
        }
        
        self.content_tags = {'p', 'div', 'article', 'section', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li'}
        
    def find_main_content_area(self, soup: BeautifulSoup) -> Optional[Tag]:
        """Find the main content area using multiple heuristics."""
        candidates = []
        
        # Method 1: Look for semantic HTML5 elements
        for selector in self.content_indicators:
            elements = soup.select(selector)
            for element in elements:
                score = self._score_content_area(element)
                if score > 0:
                    candidates.append((element, score, 'semantic'))
        
        # Method 2: Find areas with highest text density
        all_containers = soup.find_all(['div', 'section', 'article'])
        for container in all_containers:
            if self._is_likely_content_container(container):
                score = self._score_content_area(container)
                if score > 0:
                    candidates.append((container, score, 'density'))
        
        # Method 3: Look for containers with multiple paragraphs
        paragraph_containers = []
        for container in all_containers:
            paragraphs = container.find_all('p', recursive=True)
            if len(paragraphs) >= 3:  # At least 3 paragraphs
                score = self._score_content_area(container)
                if score > 0:
                    candidates.append((container, score, 'paragraphs'))
        
        if not candidates:
            return None
        
        # Sort by score and return the best candidate
        candidates.sort(key=lambda x: x[1], reverse=True)
        best_candidate = candidates[0]
        
        return best_candidate[0]
    
    def _score_content_area(self, element: Tag) -> float:
        """Score a potential content area based on various heuristics."""
        if not element:
            return 0
        
        score = 0
        
        # Text content length (primary indicator)
        text_content = element.get_text(strip=True)
        text_length = len(text_content)
        score += min(text_length / 100, 50)  # Cap at 50 points
        
        # Number of paragraphs
        paragraphs = element.find_all('p')
        score += len(paragraphs) * 2
        
        # Presence of headings
        headings = element.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        score += len(headings) * 3
        
        # Lists (often contain structured content)
        lists = element.find_all(['ul', 'ol'])
        score += len(lists) * 1.5
        
        # Penalize if it's likely navigation or sidebar
        if self._is_likely_navigation(element):
            score -= 20
        
        # Penalize if it contains mostly links
        links = element.find_all('a')
        if len(links) > len(paragraphs) and len(links) > 5:
            score -= 10
        
        # Bonus for semantic HTML5 elements
        if element.name in ['article', 'main']:
            score += 10
        
        # Bonus for content-related class names
        class_names = element.get('class', [])
        for class_name in class_names:
            if any(content_word in class_name.lower() 
                   for content_word in ['content', 'post', 'article', 'blog', 'entry']):
                score += 5
                break
        
        return max(score, 0)
    
    def _is_likely_content_container(self, element: Tag) -> bool:
        """Check if element is likely to contain main content."""
        if element.name in self.exclude_tags:
            return False
        
        class_names = element.get('class', [])
        for class_name in class_names:
            if any(exclude_word in class_name.lower() for exclude_word in self.exclude_classes):
                return False
        
        # Must have substantial text content
        text_length = len(element.get_text(strip=True))
        return text_length > 100
    
    def _is_likely_navigation(self, element: Tag) -> bool:
        """Check if element is likely navigation."""
        class_names = element.get('class', [])
        id_name = element.get('id', '').lower()
        
        nav_indicators = ['nav', 'menu', 'navigation', 'sidebar', 'breadcrumb']
        
        for indicator in nav_indicators:
            if (any(indicator in class_name.lower() for class_name in class_names) or
                indicator in id_name):
                return True
        
        # Check if it's mostly links
        links = element.find_all('a')
        text_elements = element.find_all(text=True)
        non_empty_text = [t.strip() for t in text_elements if t.strip()]
        
        if len(links) > 0 and len(non_empty_text) > 0:
            link_ratio = len(links) / len(non_empty_text)
            return link_ratio > 0.7
        
        return False


class UniversalScraper:
    """Universal scraper that adapts to different website structures."""
    
    def __init__(self, headers: Optional[Dict[str, str]] = None, timeout: int = 15, 
                 zenrows_api_key: Optional[str] = None):
        self.headers = headers or {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.timeout = timeout
        self.content_detector = ContentDetector()
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # Initialize ZenRows if API key provided
        self.zenrows = None
        if zenrows_api_key:
            self.zenrows = ZenRowsIntegration(zenrows_api_key)
            print("🚀 ZenRows integration enabled")
    
    def scrape_url(self, url: str) -> Optional[Dict[str, Any]]:
        """Scrape a single URL using dynamic content detection."""
        print(f"  🔍 Scraping: {url}")
        
        soup = None
        
        # Try regular scraping first
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
        except requests.exceptions.RequestException as e:
            print(f"    ⚠️  Network error: {e}")
            
            # Try ZenRows fallback if available
            if self.zenrows:
                print(f"    🚀 Attempting ZenRows fallback...")
                soup = self.zenrows.scrape_with_zenrows(url, use_premium=True)
            
            if not soup:
                print(f"    ❌ All scraping methods failed")
                return None
                
        except Exception as e:
            print(f"    ❌ Processing error: {e}")
            return None
        
        # Process the scraped content
        try:
            # Extract title using multiple strategies
            title = self._extract_title(soup)
            
            # Find main content area dynamically
            content_area = self.content_detector.find_main_content_area(soup)
            if not content_area:
                print(f"    ⚠️  Could not identify main content area")
                
                # Try ZenRows with premium features if regular scraping failed to find content
                if self.zenrows:
                    print(f"    🚀 Trying ZenRows with premium features...")
                    soup = self.zenrows.scrape_with_zenrows(url, use_premium=True)
                    if soup:
                        content_area = self.content_detector.find_main_content_area(soup)
                
                if not content_area:
                    return None
            
            # Extract content from the identified area
            content = self._extract_content_from_area(content_area)
            if not content or len(content) < 50:
                print(f"    ⚠️  Insufficient content found ({len(content) if content else 0} chars)")
                
                # Try ZenRows one last time if content is insufficient
                if self.zenrows:
                    print(f"    🚀 Trying ZenRows for better content...")
                    soup = self.zenrows.scrape_with_zenrows(url, use_premium=True)
                    if soup:
                        content_area = self.content_detector.find_main_content_area(soup)
                        if content_area:
                            content = self._extract_content_from_area(content_area)
                
                if not content or len(content) < 50:
                    return None
            
            # Extract author using multiple strategies with improved validation
            author = self._extract_author(soup, url, title, content)
            if author:
                print(f"    👤 Author found: {author}")
            
            print(f"    ✅ '{title}' ({len(content)} chars)")
            
            return {
                "title": title,
                "content": content,
                "source_url": url,
                "author": author,
                "user_id": "",
            }
            
        except Exception as e:
            print(f"    ❌ Content processing error: {e}")
            return None
    
    def discover_article_urls(self, base_url: str, max_urls: int = 50) -> List[str]:
        """Discover article URLs from a page using heuristic link analysis."""
        print(f"  🔍 Discovering articles from: {base_url}")
        
        try:
            # Try regular scraping first
            response = self.session.get(base_url, timeout=self.timeout)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
        except requests.exceptions.RequestException as e:
            print(f"    ⚠️  Network error: {e}")
            
            # Try ZenRows fallback if available
            if self.zenrows:
                print(f"    🚀 Attempting ZenRows fallback for discovery...")
                soup = self.zenrows.scrape_with_zenrows(base_url, use_premium=True)
            
            if not soup:
                print(f"    ❌ All discovery methods failed")
                return []
                
        except Exception as e:
            print(f"    ❌ Discovery error: {e}")
            return []
        
        # Find all links
        all_links = soup.find_all('a', href=True)
        
        # Analyze and score links
        article_candidates = []
        for link in all_links:
            href = link['href']
            absolute_url = urljoin(base_url, href)
            
            # Skip external links, fragments, and common non-article URLs
            if not self._is_potential_article_link(href, base_url):
                continue
            
            score = self._score_article_link(link, href)
            if score > 0:
                article_candidates.append((absolute_url, score))
        
        # If no candidates found and ZenRows is available, try one more time
        if not article_candidates and self.zenrows:
            print(f"    🚀 No articles found, trying ZenRows with premium features...")
            soup = self.zenrows.scrape_with_zenrows(base_url, use_premium=True)
            if soup:
                all_links = soup.find_all('a', href=True)
                for link in all_links:
                    href = link['href']
                    absolute_url = urljoin(base_url, href)
                    if not self._is_potential_article_link(href, base_url):
                        continue
                    score = self._score_article_link(link, href)
                    if score > 0:
                        article_candidates.append((absolute_url, score))
        
        # Sort by score and remove duplicates
        article_candidates = list(set(article_candidates))
        article_candidates.sort(key=lambda x: x[1], reverse=True)
        
        # Return top candidates
        top_urls = [url for url, score in article_candidates[:max_urls]]
        print(f"    📄 Found {len(top_urls)} potential articles")
        
        return top_urls
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract title using multiple fallback strategies."""
        # Strategy 1: Meta title or og:title (often most reliable)
        for selector in ['meta[property="og:title"]', 'meta[name="title"]']:
            meta = soup.select_one(selector)
            if meta and meta.get('content'):
                title = meta['content'].strip()
                if len(title) > 5:
                    return title
        
        # Strategy 2: HTML title tag
        title_tag = soup.find('title')
        if title_tag:
            title = title_tag.get_text(strip=True)
            # Clean up common title suffixes
            title = re.sub(r'\s*[\|\-\–]\s*[^|]*$', '', title)
            if len(title) > 5:
                return title
        
        # Strategy 3: Look for h1 tags in content area
        h1_tags = soup.find_all('h1')
        if h1_tags:
            # Filter out h1s that are likely navigation or site titles
            content_h1s = []
            for h1 in h1_tags:
                text = h1.get_text(strip=True)
                if len(text) > 10 and not self._is_likely_site_title(h1, text):
                    content_h1s.append(h1)
            
            if content_h1s:
                # Choose the h1 with the most text
                best_h1 = max(content_h1s, key=lambda h: len(h.get_text(strip=True)))
                title = best_h1.get_text(strip=True)
                if len(title) > 5:
                    return title
        
        return "No Title Found"
    
    def _is_likely_site_title(self, h1_element: Tag, text: str) -> bool:
        """Check if h1 is likely a site title rather than article title."""
        # Check if it's in header or navigation
        if h1_element.find_parent(['header', 'nav']):
            return True
        
        # Check if it's very short (likely site name)
        if len(text) < 10:
            return True
        
        # Check if it contains common site title patterns
        site_patterns = [
            r'^(home|blog|news|articles?)$',
            r'^[a-z]+\.(com|io|org|net)$',
        ]
        
        for pattern in site_patterns:
            if re.search(pattern, text.lower()):
                return True
        
        return False
    
    def _extract_content_from_area(self, content_area: Tag) -> str:
        """Extract and format content from the identified content area."""
        content_parts = []
        
        # Get all relevant elements in order
        for element in content_area.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'blockquote']):
            text = element.get_text(strip=True)
            
            if not text or len(text) < 10:
                continue
            
            # Skip if it looks like navigation or metadata
            if self._is_likely_metadata(text):
                continue
            
            # Format based on element type
            if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                level = int(element.name[1])
                content_parts.append(f"{'#' * level} {text}")
            elif element.name == 'li':
                # Only add if it's not already added by its parent ul/ol
                if element.parent and element.parent.name in ['ul', 'ol']:
                    # Check if we haven't processed this list yet
                    content_parts.append(f"• {text}")
            elif element.name in ['ul', 'ol']:
                # Skip - we'll handle individual li elements
                continue
            elif element.name == 'blockquote':
                content_parts.append(f"> {text}")
            else:
                content_parts.append(text)
        
        return "\n\n".join(content_parts)
    
    def _extract_author(self, soup: BeautifulSoup, url: str = "", title: str = "", content: str = "") -> str:
        """Extract author using multiple strategies with reasonable validation."""
        
        # Get domain for special handling
        domain = self._get_domain_from_url(url)
        
        # Special handling for interviewing.io - prioritize credits section
        if 'interviewing.io' in domain:
            author = self._extract_author_from_credits(soup)
            if author and self._is_reasonable_author(author):
                print(f"    🎯 Author found in credits section (prioritized for interviewing.io): {author}")
                return author
        
        # Strategy 1: Enhanced CSS selectors (most common approach)
        author_selectors = [
            # Common author patterns
            '.author', '.by-author', '.post-author', '.article-author',
            '.author-name', '.author-link', '.post-meta .author', '.article-meta .author',
            '[class*="author"]', '[rel="author"]', '.byline', '.byline-author',
            
            # More specific patterns
            '.post-by-author', '.article-by-author', '.entry-author', '.writer',
            '.content-author', '.blog-author', '.story-author', '.news-author',
            
            # WordPress and common CMS patterns
            '.vcard .author', '.author.vcard', '.post-byline .author',
            'span[itemprop="author"]', '[itemprop="author"] .name',
            
            # Modern website patterns
            '[data-author]', '[data-testid*="author"]', '.author-profile .name',
            '.author-bio .name', '.signature .author', '.post-signature .author'
        ]
        
        for selector in author_selectors:
            elements = soup.select(selector)
            for element in elements:
                author = self._extract_clean_author_name(element)
                if author and self._is_reasonable_author(author):
                    print(f"    🎯 Author found via CSS selector '{selector}': {author}")
                    return author
        
        # Strategy 2: Meta tags (very reliable when present)
        meta_selectors = [
            'meta[name="author"]', 'meta[property="article:author"]', 
            'meta[name="article:author"]', 'meta[property="og:article:author"]',
            'meta[name="twitter:creator"]', 'meta[property="author"]'
        ]
        
        for selector in meta_selectors:
            meta = soup.select_one(selector)
            if meta and meta.get('content'):
                author = meta['content'].strip()
                if self._is_reasonable_author(author):
                    print(f"    🎯 Author found via meta tag '{selector}': {author}")
                    return author
        
        # Strategy 3: Structured data (JSON-LD) - very reliable
        author = self._extract_author_from_jsonld(soup)
        if author and self._is_reasonable_author(author):
            print(f"    🎯 Author found via JSON-LD: {author}")
            return author
        
        # Strategy 4: Enhanced "By" pattern matching in text
        author = self._extract_author_by_improved_pattern(soup)
        if author and self._is_reasonable_author(author):
            print(f"    🎯 Author found via text pattern: {author}")
            return author
        
        # Strategy 5: Look in common page areas (header, byline areas)
        author = self._extract_author_from_page_areas(soup)
        if author and self._is_reasonable_author(author):
            print(f"    🎯 Author found in page areas: {author}")
            return author
        
        # Strategy 6: Credits section (for non-interviewing.io sites)
        if 'interviewing.io' not in domain:
            author = self._extract_author_from_credits(soup)
            if author and self._is_reasonable_author(author):
                print(f"    🎯 Author found in credits section: {author}")
                return author
        
        # Strategy 7: Use fallback author based on domain if no author found
        fallback_author = self._get_fallback_author(domain)
        if fallback_author:
            print(f"    🔄 Using fallback author for {domain}: {fallback_author}")
            return fallback_author
        
        return ""
    
    def _is_reasonable_author(self, author_name: str) -> bool:
        """Check if author name is reasonable - less strict than the old validation."""
        if not author_name or len(author_name) < 2 or len(author_name) > 80:
            return False
        
        name = author_name.strip()
        name_lower = name.lower()
        
        # Reject obvious non-names (including technical terms)
        obvious_non_names = [
            'published', 'updated', 'posted', 'edited', 'created', 'modified',
            'tags:', 'category:', 'share', 'follow', 'subscribe', 'comments',
            'read more', 'continue reading', 'view all', 'see more',
            'admin', 'administrator', 'editor', 'moderator', 'staff',
            'guest author', 'guest writer', 'contributing writer',
            # Technical terms that often get extracted as "authors"
            'hash map', 'array', 'algorithm', 'function', 'method', 'variable',
            'parameter', 'return', 'loop', 'iteration', 'binary search',
            'sliding window', 'dynamic programming', 'data structure',
            'complexity', 'big o', 'leetcode', 'coding interview',
            'character', 'string', 'integer', 'boolean', 'given range',
            'occurrences', 'intensity', 'scanning', 'counting'
        ]
        
        if any(phrase in name_lower for phrase in obvious_non_names):
            return False
        
        # Must contain letters
        if not re.search(r'[A-Za-z]', name):
            return False
        
        # Reject if it's mostly technical punctuation
        if len(re.sub(r'[A-Za-z\s\.\-\']', '', name)) > len(name) * 0.5:
            return False
        
        # Should look like a name pattern (letters, spaces, common punctuation)
        if not re.match(r'^[A-Za-z\s\.\-\'\u00C0-\u017F]+$', name):
            return False
        
        # Should have at least one capital letter
        if not re.search(r'[A-Z]', name):
            return False
        
        return True
    
    def _get_domain_from_url(self, url: str) -> str:
        """Extract domain from URL."""
        if not url:
            return ""
        
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc.lower()
        except:
            return ""
    
    def _get_fallback_author(self, domain: str) -> str:
        """Get fallback author for a domain based on config."""
        if not domain:
            return ""
        
        # Try to load fallback authors from config
        try:
            import yaml
            with open('config.yml', 'r') as f:
                config = yaml.safe_load(f)
                fallback_authors = config.get('fallback_authors', {})
                return fallback_authors.get(domain, "")
        except:
            # Hardcoded fallbacks if config can't be loaded
            fallbacks = {
                'interviewing.io': 'interviewing.io team',
                'nilmamano.com': 'Nil Mamano',
                'quill.co': 'Quill team',
                'shreycation.substack.com': 'Shrey G'
            }
            return fallbacks.get(domain, "")

    def _validate_author_thoroughly(self, author_name: str, soup: BeautifulSoup, 
                                  url: str = "", title: str = "", content: str = "") -> bool:
        """Comprehensive validation to ensure extracted author is legitimate."""
        if not author_name or not self._is_valid_author_name(author_name):
            return False
        
        # Convert to lowercase for case-insensitive checks
        author_lower = author_name.lower().strip()
        title_lower = title.lower() if title else ""
        content_lower = content.lower() if content else ""
        url_lower = url.lower() if url else ""
        
        # STRICT REJECTION RULES
        
        # 1. Reject if author name appears to be technical content
        technical_indicators = [
            'hash map', 'array', 'algorithm', 'function', 'method', 'variable',
            'parameter', 'return', 'loop', 'iteration', 'binary search',
            'sliding window', 'dynamic programming', 'data structure',
            'complexity', 'big o', 'leetcode', 'coding interview',
            'javascript', 'python', 'java', 'c++', 'sql', 'golang',
            'character', 'string', 'integer', 'boolean', 'null', 'undefined',
            'given range', 'occurrences', 'intensity', 'scanning', 'counting'
        ]
        
        if any(indicator in author_lower for indicator in technical_indicators):
            return False
        
        # 2. Reject if it's clearly a company name or product
        company_indicators = [
            'amazon', 'google', 'microsoft', 'facebook', 'meta', 'apple',
            'netflix', 'uber', 'airbnb', 'spotify', 'twitter', 'linkedin',
            'interviewing.io', 'leetcode', 'hackerrank', 'codewars'
        ]
        
        if any(company in author_lower for company in company_indicators):
            return False
        
        # 3. Reject if it matches common metadata patterns
        metadata_patterns = [
            r'^(published|updated|posted|edited|created|modified)',
            r'^(tags?|categories?|topics?)',
            r'^(share|follow|subscribe|comments?)',
            r'^\d+\s+(min|hour|day|week|month|year)s?\s+(ago|read)',
            r'^(january|february|march|april|may|june|july|august|september|october|november|december)',
            r'^\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}',
            r'^(mon|tue|wed|thu|fri|sat|sun)',
            r'every month', r'monthly', r'weekly', r'daily'
        ]
        
        for pattern in metadata_patterns:
            if re.search(pattern, author_lower):
                return False
        
        # 4. Reject if it's a generic role or department
        generic_roles = [
            'admin', 'administrator', 'editor', 'moderator', 'staff', 'team',
            'support', 'customer service', 'marketing', 'sales', 'hr',
            'engineering', 'development', 'design', 'product', 'content',
            'guest author', 'guest writer', 'contributing writer', 'contributor'
        ]
        
        if any(role in author_lower for role in generic_roles):
            return False
        
        # 5. Reject if it's suspiciously related to the content topic
        # Check if author name contains keywords that also appear prominently in title/content
        author_words = set(re.findall(r'\b\w+\b', author_lower))
        title_words = set(re.findall(r'\b\w+\b', title_lower)) if title_lower else set()
        
        # If more than 50% of author words appear in title, it's suspicious
        if title_words and len(author_words.intersection(title_words)) > len(author_words) * 0.5:
            return False
        
        # 6. Reject if it appears in obviously wrong context
        author_context = self._find_author_context(author_name, soup)
        if author_context:
            context_lower = author_context.lower()
            suspicious_contexts = [
                'given range', 'hash map', 'character', 'occurrences', 'intensity',
                'algorithm', 'function', 'method', 'variable', 'every month',
                'monthly', 'scanning', 'counting', 'sliding window', 'dynamic programming',
                'binary search', 'time complexity', 'space complexity', 'big o notation'
            ]
            
            if any(suspicious in context_lower for suspicious in suspicious_contexts):
                return False
        
        # 7. Enhanced name pattern validation
        if not self._looks_like_real_name(author_name):
            return False
        
        # 8. Check frequency and context of appearance
        all_text = soup.get_text().lower()
        author_mentions = all_text.count(author_lower)
        
        # If author appears many times, check if it's in different contexts
        if author_mentions > 5:
            # Likely not a real author if it appears too frequently
            return False
        
        # If it appears only once, be extra cautious
        if author_mentions == 1:
            # Check if it's in a questionable context
            if author_context and any(tech_term in author_context.lower() for tech_term in [
                'algorithm', 'data structure', 'coding', 'programming', 'interview',
                'leetcode', 'hackerrank', 'complexity', 'optimization'
            ]):
                return False
        
        return True
    
    def _looks_like_real_name(self, name: str) -> bool:
        """Enhanced check if a string looks like a real person's name."""
        if not name or len(name) < 2 or len(name) > 80:
            return False
        
        name = name.strip()
        
        # Must contain only name-appropriate characters
        if not re.match(r'^[A-Za-z\s\.\-\'\u00C0-\u017F]+$', name):
            return False
        
        # Must have at least one capital letter (proper noun)
        if not re.search(r'[A-Z]', name):
            return False
        
        # Check word structure
        words = name.split()
        
        if len(words) == 1:
            # Single word must be at least 3 chars, start with capital, and not be common non-names
            word = words[0]
            if len(word) < 3:
                return False
            
            # Reject common single words that aren't names
            common_non_names = {
                'admin', 'editor', 'staff', 'team', 'guest', 'author', 'writer',
                'user', 'member', 'contributor', 'moderator', 'developer',
                'engineer', 'designer', 'manager', 'director', 'ceo', 'cto'
            }
            
            if word.lower() in common_non_names:
                return False
                
        elif len(words) > 6:
            # Too many words, probably not a name
            return False
        else:
            # Multiple words - each should be reasonable length and properly capitalized
            for word in words:
                if len(word) < 1:
                    return False
                # Allow common name particles like "de", "van", "von" to be lowercase
                if word.lower() not in ['de', 'van', 'von', 'la', 'le', 'du', 'da', 'del']:
                    if not word[0].isupper():
                        return False
        
        # Additional checks for suspicious patterns
        # Reject names that are too similar to common tech terms
        tech_similarity_check = [
            'algorithm', 'javascript', 'python', 'programming', 'function',
            'variable', 'parameter', 'method', 'class', 'object', 'array',
            'string', 'integer', 'boolean', 'database', 'server', 'client'
        ]
        
        name_lower = name.lower().replace(' ', '')
        for tech_term in tech_similarity_check:
            # Check if name is suspiciously similar to tech terms
            if len(name_lower) > 4 and tech_term in name_lower:
                return False
        
        return True
    
    def _extract_author_from_jsonld(self, soup: BeautifulSoup) -> str:
        """Extract author from JSON-LD structured data."""
        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            try:
                import json
                if not script.string:
                    continue
                    
                data = json.loads(script.string)
                
                # Handle both single objects and arrays
                if isinstance(data, list):
                    for item in data:
                        author = self._extract_author_from_jsonld_object(item)
                        if author:
                            return author
                elif isinstance(data, dict):
                    author = self._extract_author_from_jsonld_object(data)
                    if author:
                        return author
            except (json.JSONDecodeError, AttributeError):
                continue
        
        return ""
    
    def _extract_author_from_jsonld_object(self, data: dict) -> str:
        """Extract author from a JSON-LD object."""
        if 'author' in data:
            author = data['author']
            if isinstance(author, dict):
                if 'name' in author:
                    return author['name']
                elif '@type' in author and author.get('@type') == 'Person' and 'name' in author:
                    return author['name']
            elif isinstance(author, str):
                return author
            elif isinstance(author, list) and len(author) > 0:
                first_author = author[0]
                if isinstance(first_author, dict) and 'name' in first_author:
                    return first_author['name']
                elif isinstance(first_author, str):
                    return first_author
        
        return ""
    
    def _extract_author_by_improved_pattern(self, soup: BeautifulSoup) -> str:
        """Extract author using improved text patterns."""
        # More comprehensive patterns
        patterns = [
            r'By\s+([A-Za-z\s\.\-\'\u00C0-\u017F]+?)(?:\s*[\|\,\n\r\•]|\s*on\s|\s*\d{1,2}[\/\-]\d{1,2}|$)',
            r'Written by\s+([A-Za-z\s\.\-\'\u00C0-\u017F]+?)(?:\s*[\|\,\n\r\•]|\s*on\s|\s*\d{1,2}[\/\-]\d{1,2}|$)',
            r'Author:\s*([A-Za-z\s\.\-\'\u00C0-\u017F]+?)(?:\s*[\|\,\n\r\•]|\s*\d{1,2}[\/\-]\d{1,2}|$)',
            r'Posted by\s+([A-Za-z\s\.\-\'\u00C0-\u017F]+?)(?:\s*[\|\,\n\r\•]|\s*on\s|\s*\d{1,2}[\/\-]\d{1,2}|$)',
            r'Published by\s+([A-Za-z\s\.\-\'\u00C0-\u017F]+?)(?:\s*[\|\,\n\r\•]|\s*on\s|\s*\d{1,2}[\/\-]\d{1,2}|$)',
        ]
        
        # Search in text content more broadly
        for pattern in patterns:
            compiled_pattern = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
            
            # Search in all text nodes
            all_text = soup.get_text()
            match = compiled_pattern.search(all_text)
            if match:
                author_name = match.group(1).strip()
                if self._is_reasonable_author(author_name):
                    return author_name
            
            # Also search in specific elements that commonly contain bylines
            byline_elements = soup.find_all(['p', 'div', 'span', 'small'], 
                                          string=compiled_pattern)
            for element in byline_elements:
                text = element.get_text(strip=True) if hasattr(element, 'get_text') else str(element)
                match = compiled_pattern.search(text)
                if match:
                    author_name = match.group(1).strip()
                    if self._is_reasonable_author(author_name):
                        return author_name
        
        return ""
    
    def _extract_author_from_page_areas(self, soup: BeautifulSoup) -> str:
        """Extract author from common page areas like headers and article metadata."""
        # Look in article headers and metadata areas
        header_areas = soup.find_all(['header', '.post-header', '.article-header', 
                                    '.entry-header', '.content-header', '.blog-header'])
        
        for area in header_areas:
            # Look for author information in these areas
            author_elements = area.find_all(['span', 'div', 'p', 'a'], 
                                          string=re.compile(r'(by|author)', re.IGNORECASE))
            
            for element in author_elements[:3]:  # Limit to first few matches
                parent = element.parent if element.parent else element
                text = parent.get_text(strip=True)
                
                # Extract author from the text
                for pattern in [r'by\s+([A-Za-z\s\.\-\'\u00C0-\u017F]+)', 
                              r'author[:\s]+([A-Za-z\s\.\-\'\u00C0-\u017F]+)']:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        author_name = match.group(1).strip()
                        if self._is_reasonable_author(author_name):
                            return author_name
        
        return ""
    
    def _extract_author_from_credits(self, soup: BeautifulSoup) -> str:
        """Extract author from Credits section (interviewing.io style)."""
        # Look for Credits heading
        credits_headings = soup.find_all(['h4', 'h5', 'h6'], string=re.compile(r'credits', re.IGNORECASE))
        
        for heading in credits_headings:
            # Find the container that holds the credits information
            credits_container = heading.find_parent()
            if not credits_container:
                continue
            
            # Look for author-related labels in order of preference
            author_labels = [
                'creator and author',
                'author and creator', 
                'creator & author',
                'author & creator',
                'author',
                'creator',
                'written by',
                'by'
            ]
            
            for label in author_labels:
                # Find elements containing the label
                label_elements = credits_container.find_all(['h6', 'h5', 'h4', 'div', 'span'], 
                                                          string=re.compile(label, re.IGNORECASE))
                
                for label_element in label_elements:
                    # Look for the author name in the next sibling or child elements
                    author_name = self._find_author_name_near_label(label_element)
                    if author_name:
                        return author_name
        
        return ""
    
    def _find_author_name_near_label(self, label_element: Tag) -> str:
        """Find author name near a label element."""
        # Strategy 1: Check next sibling (interviewing.io pattern)
        next_sibling = label_element.find_next_sibling()
        if next_sibling:
            author_text = self._extract_clean_author_name(next_sibling)
            if author_text:
                return author_text
            
            # For interviewing.io: check nested div > div structure
            nested_div = next_sibling.find('div')
            if nested_div:
                author_text = self._extract_clean_author_name(nested_div)
                if author_text:
                    return author_text
        
        # Strategy 2: Check parent's next sibling
        parent = label_element.parent
        if parent:
            parent_next = parent.find_next_sibling()
            if parent_next:
                author_text = self._extract_clean_author_name(parent_next)
                if author_text:
                    return author_text
                
                # Check nested structure in parent's sibling too
                nested_div = parent_next.find('div')
                if nested_div:
                    author_text = self._extract_clean_author_name(nested_div)
                    if author_text:
                        return author_text
        
        # Strategy 3: Look for nested divs within the same container
        container = label_element.find_parent(['div', 'section'])
        if container:
            # Find all text-containing divs that aren't the label itself
            text_divs = container.find_all('div')
            for div in text_divs:
                if div != label_element and not label_element.find_parent(div):
                    author_text = self._extract_clean_author_name(div)
                    if author_text and author_text.lower() not in label_element.get_text().lower():
                        return author_text
        
        return ""
    
    def _extract_clean_author_name(self, element: Tag) -> str:
        """Extract and clean author name from an element."""
        if not element:
            return ""
        
        text = element.get_text(strip=True)
        if not text:
            return ""
        
        # Check data attributes first (often more reliable)
        if hasattr(element, 'get'):
            data_author = element.get('data-author')
            if data_author and self._is_reasonable_author(data_author):
                return data_author.strip()
            
            # Check title attribute
            title_attr = element.get('title')
            if title_attr and self._is_reasonable_author(title_attr):
                return title_attr.strip()
        
        # Clean prefixes and suffixes
        text = re.sub(r'^(by|author:?|written by|posted by|published by)\s*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\s*[\|\-\–]\s*.*$', '', text)  # Remove everything after | or -
        text = re.sub(r'\s*on\s+\d{1,2}[\/\-]\d{1,2}.*$', '', text, flags=re.IGNORECASE)  # Remove dates
        
        # Clean up extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Use the reasonable validation
        if self._is_reasonable_author(text):
            return text
        
        return ""
    
    def _is_valid_author_name(self, name: str) -> bool:
        """Check if a string looks like a valid author name."""
        if not name or len(name) < 2 or len(name) > 80:
            return False
        
        # Clean the name first
        name = name.strip()
        
        # Skip common non-name content
        skip_phrases = [
            'special thanks', 'editor', 'credits', 'published', 'updated',
            'tags:', 'category:', 'share', 'follow', 'subscribe', 'comments',
            'read more', 'continue reading', 'view all', 'see more',
            'january', 'february', 'march', 'april', 'may', 'june',
            'july', 'august', 'september', 'october', 'november', 'december',
            'interviewers', 'scanning', 'counting', 'hash map', 'character',
            'occurrences', 'given range', 'idea that', 'language', 'amazon',
            'amaz', 'microsoft', 'google', 'facebook', 'meta', 'netflix',
            'intensity', 'intense', 'month', 'every month'
        ]
        
        name_lower = name.lower()
        if any(skip in name_lower for skip in skip_phrases):
            return False
        
        # Skip if it looks like code or technical terms
        if any(pattern in name_lower for pattern in [
            'hash map', 'array', 'function', 'method', 'algorithm', 'data structure',
            'variable', 'parameter', 'return', 'loop', 'iteration', 'binary search',
            'sliding window', 'dynamic programming', 'big o', 'complexity',
            'javascript', 'python', 'java', 'c++', 'golang', 'sql'
        ]):
            return False
        
        # Skip if it's mostly lowercase (likely not a proper name)
        if name.islower() and len(name) > 3:
            return False
        
        # Skip if it contains technical punctuation
        if any(char in name for char in ['(', ')', '[', ']', '{', '}', '=', '+', '_']):
            return False
        
        # Must contain at least some letters
        if not re.search(r'[A-Za-z]', name):
            return False
        
        # Shouldn't be mostly numbers or symbols
        if len(re.sub(r'[A-Za-z\s\.\-\'\u00C0-\u017F]', '', name)) > len(name) * 0.3:
            return False
        
        # Should look like a name pattern
        if re.match(r'^[A-Za-z\s\.\-\'\u00C0-\u017F]+$', name):
            # Name should have at least one capital letter (proper noun)
            if not re.search(r'[A-Z]', name):
                return False
            
            # Should be either multiple words or a reasonable single name
            words = name.split()
            if len(words) == 1:
                # Single word must be at least 3 chars and look like a name
                return len(words[0]) >= 3 and words[0][0].isupper()
            else:
                # Multiple words should each be reasonable length
                return all(len(word) >= 2 for word in words if word)
        
        return False
    
    def _find_author_context(self, author_name: str, soup: BeautifulSoup) -> str:
        """Find the context around where author name appears."""
        # Find elements containing the author name
        import re
        pattern = re.compile(re.escape(author_name), re.IGNORECASE)
        
        for element in soup.find_all(text=pattern):
            if hasattr(element, 'parent') and element.parent:
                context = element.parent.get_text(strip=True)
                if len(context) < 200:  # Get broader context if too short
                    grandparent = element.parent.parent
                    if grandparent:
                        context = grandparent.get_text(strip=True)[:200]
                return context
        
        return ""
    
    def _is_potential_article_link(self, href: str, base_url: str) -> bool:
        """Check if a link is potentially an article."""
        # Skip fragments, mailto, tel, etc.
        if href.startswith(('#', 'mailto:', 'tel:', 'javascript:', 'data:')):
            return False
        
        # Skip common non-article extensions
        if re.search(r'\.(jpg|jpeg|png|gif|pdf|doc|docx|zip|mp3|mp4|css|js|ico|svg|woff|ttf)$', href, re.IGNORECASE):
            return False
        
        # Skip common non-article paths (expanded list)
        skip_patterns = [
            r'/search', r'/tag', r'/category', r'/archive', r'/about', r'/contact',
            r'/privacy', r'/terms', r'/feed', r'/rss', r'/sitemap', r'/login',
            r'/register', r'/signup', r'/logout', r'/admin', r'/dashboard',
            r'/api/', r'/ajax/', r'/json', r'/xml', r'/robots\.txt',
            r'/favicon', r'/static/', r'/assets/', r'/media/', r'/images/',
            r'/css/', r'/js/', r'/fonts/', r'\.(php|asp|jsp)$',
            r'/comment', r'/reply', r'/share', r'/print', r'/email',
            r'/subscribe', r'/unsubscribe', r'/newsletter'
        ]
        
        for pattern in skip_patterns:
            if re.search(pattern, href, re.IGNORECASE):
                return False
        
        # Skip if it's an external link (different domain)
        if href.startswith('http') and base_url:
            from urllib.parse import urlparse
            href_domain = urlparse(href).netloc
            base_domain = urlparse(base_url).netloc
            if href_domain != base_domain:
                return False
        
        # Must be a relative link or same domain
        return True
    
    def _score_article_link(self, link_element: Tag, href: str) -> float:
        """Score a link's likelihood of being an article."""
        score = 0
        
        # Link text analysis
        link_text = link_element.get_text(strip=True)
        if len(link_text) > 10:  # Substantial link text
            score += 5
        
        if len(link_text) > 30:  # Very descriptive
            score += 3
        
        # URL structure analysis
        if re.search(r'/(post|article|blog|news|story)/', href):
            score += 10
        
        # Substack-specific patterns
        if re.search(r'/p/[^/]+', href):  # Substack post pattern
            score += 15
        
        if re.search(r'/i/\d+', href):  # Substack item pattern
            score += 12
        
        if re.search(r'/\d{4}/', href):  # Likely date-based URL
            score += 5
        
        # Parent element analysis
        parent = link_element.parent
        if parent:
            parent_class = ' '.join(parent.get('class', []))
            if any(indicator in parent_class.lower() 
                   for indicator in ['post', 'article', 'entry', 'story', 'pencraft', 'preview']):
                score += 8
        
        # Check if link is in a heading
        if link_element.find_parent(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            score += 15
        
        # Substack-specific containers
        if link_element.find_parent(attrs={'data-testid': lambda x: x and 'post' in x}):
            score += 12
        
        return score
    
    def _is_likely_metadata(self, text: str) -> bool:
        """Check if text is likely metadata rather than content."""
        metadata_patterns = [
            r'^\d{1,2}/\d{1,2}/\d{4}',  # Dates
            r'^(published|updated|posted|by):?\s*',  # Metadata labels
            r'^(tags?|categories?|filed under):?\s*',  # Classification
            r'^share\s*(this|on)',  # Social sharing
            r'^(read more|continue reading)',  # Navigation
            r'^\d+\s*(comments?|replies?)',  # Comment counts
        ]
        
        text_lower = text.lower()
        for pattern in metadata_patterns:
            if re.search(pattern, text_lower):
                return True
        
        return False

    def _extract_author_from_footer(self, soup: BeautifulSoup) -> str:
        """Extract author from footer or sidebar areas - removed as too unreliable."""
        # This method has been disabled as it often returns false positives
        return ""
    
    def scrape_multiple_urls(self, urls: List[str], max_workers: int = 3) -> List[Dict[str, Any]]:
        """Scrape multiple URLs in parallel."""
        items = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_url = {executor.submit(self.scrape_url, url): url for url in urls}
            
            for future in concurrent.futures.as_completed(future_to_url):
                try:
                    result = future.result()
                    if result:
                        items.append(result)
                except Exception as exc:
                    url = future_to_url[future]
                    print(f"  ❌ Error scraping {url}: {exc}")
                
                # Rate limiting
                time.sleep(0.2)
        
        return items


class ComprehensiveScraper:
    """Orchestrates comprehensive scraping of all required sources."""
    
    def __init__(self, zenrows_api_key: Optional[str] = None):
        # Initialize ZenRows with API key from config if not provided
        if not zenrows_api_key:
            try:
                import yaml
                with open('config.yml', 'r') as f:
                    config = yaml.safe_load(f)
                    if config.get('zenrows', {}).get('enabled'):
                        zenrows_api_key = config['zenrows'].get('api_key')
                        print(f"🚀 Using ZenRows API key from config")
            except Exception as e:
                print(f"⚠️  Error loading ZenRows API key from config: {e}")
        
        self.scraper = UniversalScraper(zenrows_api_key=zenrows_api_key)
        self.all_items = []
        
        # Define all required sources
        self.sources = {
            'interviewing_io_blog': 'https://interviewing.io/blog',
            'interviewing_io_topics': 'https://interviewing.io/topics',
            'interviewing_io_learn': 'https://interviewing.io/learn',
            'nil_dsa_blog': 'https://nilmamano.com/blog/category/dsa',
            'shreycation_substack': 'https://shreycation.substack.com',
        }
        
        # Known company guide URLs (discovered from previous analysis)
        self.company_guide_urls = [
            'https://interviewing.io/guides/hiring-process/amazon',
            'https://interviewing.io/guides/hiring-process/meta-facebook',
            'https://interviewing.io/guides/hiring-process/apple',
            'https://interviewing.io/guides/hiring-process/netflix',
            'https://interviewing.io/guides/hiring-process/google',
            'https://interviewing.io/guides/hiring-process/microsoft'
        ]
        
        # Known interview guide URLs
        self.interview_guide_urls = [
            'https://interviewing.io/guides/system-design-interview',
            'https://interviewing.io/guides/leadership-principles',
            'https://interviewing.io/guides/hiring-process'  # Main FAANG guide
        ]
    
    def scrape_all_sources(self) -> List[Dict[str, Any]]:
        """Scrape all sources mentioned in the original requirements."""
        print("🚀 Starting comprehensive scraping of all required sources...")
        
        # 1. Scrape interviewing.io blog posts
        print("\n📰 Scraping interviewing.io blog posts...")
        blog_items = self._scrape_interviewing_io_blog()
        self.all_items.extend(blog_items)
        print(f"   ✅ Scraped {len(blog_items)} blog posts")
        
        # 2. Scrape company guides (the missing content!)
        print("\n🏢 Scraping company interview guides...")
        company_items = self._scrape_company_guides()
        self.all_items.extend(company_items)
        print(f"   ✅ Scraped {len(company_items)} company guides")
        
        # 3. Scrape interview guides from learn section
        print("\n📚 Scraping interview guides...")
        guide_items = self._scrape_interview_guides()
        self.all_items.extend(guide_items)
        print(f"   ✅ Scraped {len(guide_items)} interview guides")
        
        # 4. Scrape Nil's DS&A blog posts
        print("\n🧮 Scraping Nil's DS&A blog posts...")
        nil_items = self._scrape_nil_dsa_blog()
        self.all_items.extend(nil_items)
        print(f"   ✅ Scraped {len(nil_items)} DS&A posts")
        
        # 5. Scrape Shreycation Substack
        print("\n📰 Scraping Shreycation Substack...")
        substack_items = self._scrape_shreycation_substack()
        self.all_items.extend(substack_items)
        print(f"   ✅ Scraped {len(substack_items)} Substack posts")
        
        # 6. Discover and scrape additional interviewing.io content
        print("\n🔍 Discovering additional interviewing.io content...")
        additional_items = self._discover_additional_content()
        self.all_items.extend(additional_items)
        print(f"   ✅ Scraped {len(additional_items)} additional items")
        
        print(f"\n🎉 Total items scraped: {len(self.all_items)}")
        return self.all_items
    
    def _scrape_interviewing_io_blog(self) -> List[Dict[str, Any]]:
        """Scrape all blog posts from interviewing.io."""
        blog_urls = self._discover_blog_urls('https://interviewing.io/blog')
        
        # Add pagination to get more blog posts
        for page in range(2, 6):  # Check first few pages
            page_url = f'https://interviewing.io/blog?page={page}'
            page_urls = self._discover_blog_urls(page_url)
            blog_urls.extend(page_urls)
        
        # Remove duplicates
        blog_urls = list(set(blog_urls))
        
        print(f"   📄 Found {len(blog_urls)} blog post URLs")
        return self.scraper.scrape_multiple_urls(blog_urls[:50])  # Limit to avoid overwhelming
    
    def _scrape_company_guides(self) -> List[Dict[str, Any]]:
        """Scrape all company-specific interview guides."""
        print("   🎯 Scraping known company guide URLs...")
        
        # First scrape known URLs
        items = self.scraper.scrape_multiple_urls(self.company_guide_urls)
        
        # Discover additional company guides
        topics_page_urls = self._discover_from_topics_page()
        if topics_page_urls:
            print(f"   🔍 Found {len(topics_page_urls)} additional company URLs")
            additional_items = self.scraper.scrape_multiple_urls(topics_page_urls)
            items.extend(additional_items)
        
        return items
    
    def _scrape_interview_guides(self) -> List[Dict[str, Any]]:
        """Scrape interview guides from the learn section."""
        # Scrape known interview guides
        items = self.scraper.scrape_multiple_urls(self.interview_guide_urls)
        
        # Discover additional guides from the learn page
        learn_urls = self._discover_from_learn_page()
        if learn_urls:
            print(f"   📖 Found {len(learn_urls)} additional guide URLs")
            additional_items = self.scraper.scrape_multiple_urls(learn_urls)
            items.extend(additional_items)
        
        return items
    
    def _scrape_nil_dsa_blog(self) -> List[Dict[str, Any]]:
        """Scrape Nil's DS&A blog posts."""
        try:
            # Discover all DS&A posts
            dsa_urls = self._discover_nil_blog_urls()
            
            if not dsa_urls:
                print("   ⚠️  No DS&A blog URLs found, trying alternative approaches...")
                # Try different URL patterns
                alternative_urls = [
                    'https://nilmamano.com/blog/',
                    'https://nilmamano.com/posts/',
                    'https://nilmamano.com/articles/'
                ]
                
                for alt_url in alternative_urls:
                    alt_dsa_urls = self.scraper.discover_article_urls(alt_url, max_urls=20)
                    dsa_urls.extend(alt_dsa_urls)
            
            if dsa_urls:
                print(f"   🧮 Found {len(dsa_urls)} DS&A blog URLs")
                return self.scraper.scrape_multiple_urls(dsa_urls)
            else:
                print("   ❌ Could not find any DS&A blog posts")
                return []
                
        except Exception as e:
            print(f"   ❌ Error scraping Nil's blog: {e}")
            return []
    
    def _scrape_shreycation_substack(self) -> List[Dict[str, Any]]:
        """Scrape Shreycation Substack newsletter posts."""
        try:
            substack_url = 'https://shreycation.substack.com'
            
            # Discover all Substack posts
            substack_urls = self._discover_substack_urls(substack_url)
            
            if not substack_urls:
                print("   ⚠️  No Substack URLs found, trying general discovery...")
                # Fallback to general article discovery
                substack_urls = self.scraper.discover_article_urls(substack_url, max_urls=25)
            
            if substack_urls:
                print(f"   📰 Found {len(substack_urls)} Substack post URLs")
                return self.scraper.scrape_multiple_urls(substack_urls)
            else:
                print("   ❌ Could not find any Substack posts")
                return []
                
        except Exception as e:
            print(f"   ❌ Error scraping Shreycation Substack: {e}")
            return []
    
    def _discover_blog_urls(self, blog_url: str) -> List[str]:
        """Discover blog post URLs from the blog index page."""
        try:
            response = self.scraper.session.get(blog_url, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for blog post links using multiple strategies
            post_urls = set()
            
            # Strategy 1: Look for links in common blog post containers
            post_containers = soup.find_all(['article', '.post', '.blog-post', '.entry'])
            for container in post_containers:
                links = container.find_all('a', href=True)
                for link in links:
                    href = link['href']
                    if self._is_likely_blog_post_url(href):
                        full_url = urljoin(blog_url, href)
                        post_urls.add(full_url)
            
            # Strategy 2: Look for title links (h1, h2, h3 containing links)
            title_links = soup.find_all(['h1', 'h2', 'h3'])
            for title in title_links:
                link = title.find('a', href=True)
                if link:
                    href = link['href']
                    if self._is_likely_blog_post_url(href):
                        full_url = urljoin(blog_url, href)
                        post_urls.add(full_url)
            
            # Strategy 3: General article discovery
            discovered_urls = self.scraper.discover_article_urls(blog_url, max_urls=30)
            post_urls.update(discovered_urls)
            
            return list(post_urls)
            
        except Exception as e:
            print(f"   ❌ Error discovering blog URLs from {blog_url}: {e}")
            return []
    
    def _discover_from_topics_page(self) -> List[str]:
        """Discover company guide URLs from the topics page."""
        try:
            response = self.scraper.session.get('https://interviewing.io/topics', timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            company_urls = set()
            
            # Look for company-related links
            all_links = soup.find_all('a', href=True)
            for link in all_links:
                href = link['href']
                # Look for hiring process or company-specific URLs
                if any(pattern in href.lower() for pattern in [
                    '/guides/hiring-process/',
                    '/company/',
                    '/interview-process/',
                    'amazon', 'google', 'meta', 'facebook', 'apple', 'netflix', 'microsoft'
                ]):
                    if href.startswith('http') or href.startswith('/'):
                        full_url = urljoin('https://interviewing.io', href)
                        company_urls.add(full_url)
            
            return list(company_urls)
            
        except Exception as e:
            print(f"   ❌ Error discovering from topics page: {e}")
            return []
    
    def _discover_from_learn_page(self) -> List[str]:
        """Discover interview guide URLs from the learn page."""
        try:
            response = self.scraper.session.get('https://interviewing.io/learn', timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            guide_urls = set()
            
            # Look for guide-related links
            all_links = soup.find_all('a', href=True)
            for link in all_links:
                href = link['href']
                # Look for guide URLs
                if any(pattern in href.lower() for pattern in [
                    '/guides/',
                    '/guide-',
                    'interview-guide',
                    'system-design',
                    'leadership-principles',
                    'hiring-process'
                ]):
                    if href.startswith('http') or href.startswith('/'):
                        full_url = urljoin('https://interviewing.io', href)
                        guide_urls.add(full_url)
            
            return list(guide_urls)
            
        except Exception as e:
            print(f"   ❌ Error discovering from learn page: {e}")
            return []
    
    def _discover_nil_blog_urls(self) -> List[str]:
        """Discover DS&A blog post URLs from Nil's blog."""
        try:
            # Try the direct category URL first
            dsa_url = 'https://nilmamano.com/blog/category/dsa'
            response = self.scraper.session.get(dsa_url, timeout=15)
            
            if response.status_code == 404:
                # Try alternative URLs
                alternative_urls = [
                    'https://nilmamano.com/blog/',
                    'https://nilmamano.com/posts/category/dsa',
                    'https://nilmamano.com/category/dsa'
                ]
                
                for alt_url in alternative_urls:
                    try:
                        response = self.scraper.session.get(alt_url, timeout=15)
                        if response.status_code == 200:
                            dsa_url = alt_url
                            break
                    except:
                        continue
                else:
                    # If no category page works, try the main blog page
                    response = self.scraper.session.get('https://nilmamano.com/blog/', timeout=15)
                    dsa_url = 'https://nilmamano.com/blog/'
            
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            dsa_urls = set()
            
            # Look for DS&A related posts
            all_links = soup.find_all('a', href=True)
            for link in all_links:
                href = link['href']
                link_text = link.get_text(strip=True).lower()
                
                # Check if it's likely a DS&A post
                if any(keyword in link_text for keyword in [
                    'algorithm', 'data structure', 'leetcode', 'coding',
                    'binary search', 'dynamic programming', 'graph',
                    'tree', 'array', 'string', 'hash', 'sort'
                ]) or any(keyword in href.lower() for keyword in [
                    'algorithm', 'data-structure', 'leetcode', 'dsa'
                ]):
                    full_url = urljoin(dsa_url, href)
                    dsa_urls.add(full_url)
            
            # Also use general article discovery
            discovered_urls = self.scraper.discover_article_urls(dsa_url, max_urls=25)
            dsa_urls.update(discovered_urls)
            
            return list(dsa_urls)
            
        except Exception as e:
            print(f"   ❌ Error discovering Nil's blog URLs: {e}")
            return []
    
    def _discover_substack_urls(self, substack_url: str) -> List[str]:
        """Discover Substack post URLs with Substack-specific patterns."""
        try:
            response = self.scraper.session.get(substack_url, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            substack_urls = set()
            
            # Look for Substack-specific post patterns
            all_links = soup.find_all('a', href=True)
            for link in all_links:
                href = link['href']
                
                # Substack posts typically have patterns like:
                # - /p/post-title
                # - /i/12345678/some-title  
                if re.search(r'/p/[^/]+', href) or re.search(r'/i/\d+', href):
                    full_url = urljoin(substack_url, href)
                    substack_urls.add(full_url)
                
                # Also look for any link containing the substack domain
                elif 'substack.com' in href and '/p/' in href:
                    substack_urls.add(href)
            
            # Look in common Substack containers
            for container_selector in ['.post-preview', '.pencraft', '[data-testid*="post"]']:
                containers = soup.select(container_selector)
                for container in containers:
                    links = container.find_all('a', href=True)
                    for link in links:
                        href = link['href']
                        if '/p/' in href or '/i/' in href:
                            full_url = urljoin(substack_url, href)
                            substack_urls.add(full_url)
            
            return list(substack_urls)
            
        except Exception as e:
            print(f"   ❌ Error discovering Substack URLs: {e}")
            return []
    
    def _discover_additional_content(self) -> List[Dict[str, Any]]:
        """Discover additional content from interviewing.io."""
        additional_urls = set()
        
        # Discover from main navigation or sitemap
        try:
            response = self.scraper.session.get('https://interviewing.io', timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for navigation links to guides, resources, etc.
            nav_links = soup.find_all('a', href=True)
            for link in nav_links:
                href = link['href']
                if any(pattern in href.lower() for pattern in [
                    '/guides/', '/resources/', '/learn/', '/blog/',
                    'interview', 'guide', 'preparation'
                ]):
                    full_url = urljoin('https://interviewing.io', href)
                    additional_urls.add(full_url)
            
        except Exception as e:
            print(f"   ⚠️  Error discovering additional content: {e}")
        
        # Limit to avoid overwhelming
        additional_urls = list(additional_urls)[:20]
        
        if additional_urls:
            return self.scraper.scrape_multiple_urls(additional_urls)
        return []
    
    def _is_likely_blog_post_url(self, href: str) -> bool:
        """Check if URL is likely a blog post."""
        # Skip common non-blog URLs
        if any(pattern in href.lower() for pattern in [
            '/tag/', '/category/', '/archive/', '/page/',
            '/search', '/about', '/contact', '/privacy'
        ]):
            return False
        
        # Look for blog post patterns
        if any(pattern in href.lower() for pattern in [
            '/blog/', '/post/', '/article/', '/news/',
            '/guides/', '/interview'
        ]):
            return True
        
        # Check for date patterns in URL
        if re.search(r'/\d{4}/', href):
            return True
        
        return False
    
    def save_to_json(self, filename: str = 'comprehensive_scrape_output.json'):
        """Save all scraped items to JSON file."""
        print(f"\n💾 Saving {len(self.all_items)} items to {filename}...")
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.all_items, f, indent=2, ensure_ascii=False)
        
        print(f"   ✅ Saved to {filename}")
        
        # Print summary
        self._print_summary()
    
    def _print_summary(self):
        """Print a summary of scraped content."""
        print(f"\n📊 SCRAPING SUMMARY:")
        print(f"   Total items: {len(self.all_items)}")
        
        # Group by source domain
        domain_counts = {}
        for item in self.all_items:
            domain = urlparse(item.get('source_url', '')).netloc
            domain_counts[domain] = domain_counts.get(domain, 0) + 1
        
        for domain, count in sorted(domain_counts.items()):
            print(f"   {domain}: {count} items")
        
        # Check for specific required content
        required_keywords = [
            'amazon', 'google', 'meta', 'apple', 'netflix', 'microsoft',
            'system design', 'leadership principles', 'algorithm', 'data structure'
        ]
        
        print(f"\n🎯 CONTENT COVERAGE:")
        for keyword in required_keywords:
            count = sum(1 for item in self.all_items 
                       if keyword.lower() in item.get('title', '').lower() or 
                          keyword.lower() in item.get('content', '').lower())
            print(f"   {keyword}: {count} items")


def main():
    """Main function to run comprehensive scraping."""
    print("🚀 Starting comprehensive scraping of all required sources...")
    print("This will scrape:")
    print("  📰 All interviewing.io blog posts")
    print("  🏢 All company interview guides (Amazon, Google, Meta, Apple, Netflix, Microsoft)")
    print("  📚 All interview guides (System Design, Leadership Principles, etc.)")
    print("  🧮 All of Nil's DS&A blog posts")
    print("  🔍 Additional discovered content")
    print()
    
    # Get ZenRows API key from environment variable or config
    import os
    zenrows_api_key = os.getenv('ZENROWS_API_KEY')
    
    if not zenrows_api_key:
        try:
            import yaml
            with open('config.yml', 'r') as f:
                config = yaml.safe_load(f)
                if config.get('zenrows', {}).get('enabled'):
                    zenrows_api_key = config['zenrows'].get('api_key')
        except Exception as e:
            print(f"⚠️  Error loading ZenRows API key from config: {e}")
    
    if zenrows_api_key:
        print("🚀 ZenRows API key found - fallback scraping enabled")
    else:
        print("⚠️  No ZenRows API key found - using regular scraping only")
    
    scraper = ComprehensiveScraper(zenrows_api_key=zenrows_api_key)
    
    try:
        # Scrape all sources
        all_items = scraper.scrape_all_sources()
        
        # Save results
        scraper.save_to_json('output.json')
        
        print(f"\n🎉 SUCCESS! Scraped {len(all_items)} total items")
        print("Check 'output.json' for all the scraped content.")
        
    except KeyboardInterrupt:
        print("\n⏹️  Scraping interrupted by user")
        if scraper.all_items:
            scraper.save_to_json('partial_output.json')
            print("Partial results saved to 'partial_output.json'")
    except Exception as e:
        print(f"\n❌ Error during scraping: {e}")
        if scraper.all_items:
            scraper.save_to_json('error_output.json')
            print("Partial results saved to 'error_output.json'")


if __name__ == "__main__":
    main()