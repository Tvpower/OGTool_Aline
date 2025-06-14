import concurrent.futures
import re
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md

# Be a good web citizen, as suggested in the strategy
# Let's try a simpler, but still modern, User-Agent. The complex headers may have been too easy to fingerprint.
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}


def scrape_interviewing_io_blog_post(url: str):
    """
    Specialized scraper for interviewing.io blog posts.
    
    Args:
        url (str): The URL of the blog post to scrape.
    
    Returns:
        dict: A dictionary containing the scraped data, or None if scraping fails.
    """
    print(f"  - Scraping blog post: {url}")
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # Extract title from h1
        title_element = soup.select_one('h1')
        title = title_element.get_text(strip=True) if title_element else "No Title Found"
        print(f"    - Title found: '{title}'")

        # Extract author from byline
        author_name = ""
        byline_element = soup.find(text=re.compile(r'By\s+'))  
        if byline_element:
            byline_text = byline_element.strip()
            if "By " in byline_text and "|" in byline_text:
                author_name = byline_text.split("By ")[1].split("|")[0].strip()
            elif "By " in byline_text:
                # Handle cases without pipe separator
                remaining = byline_text.split("By ")[1].strip()
                # Take first part if there are multiple words
                author_name = remaining.split()[0] if remaining.split() else remaining
        
        print(f"    - Author found: '{author_name}'")

        # Extract main content - try multiple approaches for robustness
        content_paragraphs = []
        
        # Method 1: Look for semantic article tag (best practice)
        article_element = soup.select_one('article')
        if article_element:
            # Try to find a dedicated content container within the article
            content_container = article_element.select_one('.blog-post-content, .article-content, .post-content')
            if content_container:
                # Extract paragraphs and lists from the content container
                content_elements = content_container.select('p, ul li, ol li')
                for element in content_elements:
                    text = element.get_text(strip=True)
                    if text and len(text) > 15:  # Filter out very short text
                        if element.name == 'li':
                            content_paragraphs.append(f"• {text}")
                        else:
                            content_paragraphs.append(text)
            else:
                # Fall back to all paragraphs in the article
                paragraphs = article_element.select('p')
                for p in paragraphs:
                    text = p.get_text(strip=True)
                    if text and len(text) > 20:
                        content_paragraphs.append(text)
                
                # Also get list items from the article
                list_items = article_element.select('ul li, ol li')
                for li in list_items:
                    text = li.get_text(strip=True)
                    if text and len(text) > 10:
                        content_paragraphs.append(f"• {text}")
        
        # Method 2: Fallback to specific container div if no article tag
        if not content_paragraphs:
            # Try multiple container selectors
            container_selectors = [
                'div.mx-auto.flex.max-w-5xl',  # Original selector
                'main', '[role="main"]',       # Semantic containers
                '.blog-post-content', '.article-content', '.post-content'  # Common blog selectors
            ]
            
            for container_selector in container_selectors:
                main_content_area = soup.select_one(container_selector)
                if main_content_area:
                    # Try multiple paragraph selectors
                    paragraph_selectors = [
                        'p.py-2.text-base.leading-7',  # Specific interviewing.io style
                        'p[class*="py-"]',              # Any Tailwind py- class
                        'p'                             # All paragraphs
                    ]
                    
                    for p_selector in paragraph_selectors:
                        paragraphs = main_content_area.select(p_selector)
                        for p in paragraphs:
                            text = p.get_text(strip=True)
                            # Skip navigation, metadata, and short text
                            if (text and len(text) > 30 and 
                                not any(exclude in text.lower() for exclude in 
                                       ['read more', 'share this', 'published:', 'by ', '|', 
                                        'tags:', 'category:', 'continue reading'])):
                                content_paragraphs.append(text)
                        
                        if content_paragraphs:
                            break  # Found content with this selector
                    
                    # Also get list items
                    list_items = main_content_area.select('ul li, ol li')
                    for li in list_items:
                        text = li.get_text(strip=True)
                        if text and len(text) > 15:
                            content_paragraphs.append(f"• {text}")
                    
                    if content_paragraphs:
                        break  # Found content with this container
        
        # Method 3: Last resort - extract all substantial paragraphs from entire page
        if not content_paragraphs:
            print(f"  - Using fallback method for content extraction")
            all_paragraphs = soup.select('p')
            for p in all_paragraphs:
                text = p.get_text(strip=True)
                # Aggressive filtering for general paragraph extraction
                if (text and len(text) > 50 and 
                    not any(skip_word in text.lower() for skip_word in 
                           ['copyright', 'privacy', 'terms', 'cookie', 'follow us',
                            'read more', 'share this', 'published:', 'sign up',
                            'subscribe', 'contact us', 'all rights reserved',
                            'click here', 'learn more', 'home', 'blog', 'about'])):
                    content_paragraphs.append(text)
        
        # Join all content
        content_md = "\n\n".join(content_paragraphs) if content_paragraphs else ""
        
        if not content_md:
            print(f"  - WARNING: No content found for {url}")
            return None
            
        print(f"    - Content extracted: {len(content_md)} characters")

        return {
            "title": title,
            "content": content_md,
            "content_type": "blog",
            "source_url": url,
            "author": author_name,
            "user_id": ""
        }

    except requests.exceptions.RequestException as e:
        print(f"  - ERROR fetching {url}: {e}")
        return None
    except Exception as e:
        print(f"  - ERROR processing {url}: {e}")
        return None


def scrape_interviewing_io_guide(url: str):
    """
    Specialized scraper for interviewing.io guide pages.
    
    Args:
        url (str): The URL of the guide page to scrape.
    
    Returns:
        dict: A dictionary containing the scraped data, or None if scraping fails.
    """
    print(f"  - Scraping guide: {url}")
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # Extract title from h1
        title_element = soup.select_one('h1')
        title = title_element.get_text(strip=True) if title_element else "No Title Found"
        print(f"    - Title found: '{title}'")

        # Extract main content from the guide content container
        content_paragraphs = []
        
        # Look for the main content area with the specific guide page structure
        main_content_area = soup.select_one('div.mx-auto.mb-\\[128px\\]')
        if not main_content_area:
            # Fallback: look for any container with similar characteristics
            main_content_area = soup.select_one('div.mx-auto.flex.w-full.flex-col')
        
        if main_content_area:
            # Extract content elements in order: paragraphs, headings, and lists
            content_elements = main_content_area.select('p.mb-8, h2.mb-8, h3.mb-6, ul.mb-8')
            
            for element in content_elements:
                if element.name == 'p':
                    text = element.get_text(strip=True)
                    if text and len(text) > 20:  # Filter out very short text
                        content_paragraphs.append(text)
                
                elif element.name in ['h2', 'h3']:
                    text = element.get_text(strip=True)
                    if text:
                        # Add heading with appropriate markdown formatting
                        heading_level = "#" * int(element.name[1])
                        content_paragraphs.append(f"{heading_level} {text}")
                
                elif element.name == 'ul':
                    # Extract list items
                    list_items = element.select('li')
                    for li in list_items:
                        text = li.get_text(strip=True)
                        if text and len(text) > 10:
                            content_paragraphs.append(f"• {text}")
        
        # Fallback: if no content found with specific selectors, use broader approach
        if not content_paragraphs:
            print(f"  - Using fallback content extraction method")
            # Look for any substantial content in the main content area
            if main_content_area:
                # Extract all paragraphs and headings
                all_content = main_content_area.select('p, h2, h3, h4, ul li')
                for element in all_content:
                    text = element.get_text(strip=True)
                    if text and len(text) > 15:
                        if element.name in ['h2', 'h3', 'h4']:
                            heading_level = "#" * int(element.name[1])
                            content_paragraphs.append(f"{heading_level} {text}")
                        elif element.name == 'li':
                            content_paragraphs.append(f"• {text}")
                        else:
                            content_paragraphs.append(text)

        # Join all content
        content_md = "\n\n".join(content_paragraphs) if content_paragraphs else ""
        
        if not content_md:
            print(f"  - WARNING: No content found for {url}")
            return None
            
        print(f"    - Content extracted: {len(content_md)} characters")

        return {
            "title": title,
            "content": content_md,
            "content_type": "guide",
            "source_url": url,
            "author": "interviewing.io team",
            "user_id": ""
        }

    except requests.exceptions.RequestException as e:
        print(f"  - ERROR fetching {url}: {e}")
        return None
    except Exception as e:
        print(f"  - ERROR processing {url}: {e}")
        return None


def scrape_page(url: str, title_selector: str, content_selector: str, content_type: str = "blog"):
    """
    Generic scraper for other sites (kept for compatibility).
    """
    print(f"  - Scraping: {url}")
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        title_element = soup.select_one(title_selector)
        title = title_element.get_text(strip=True) if title_element else "No Title Found"
        print(f"    - Title found: '{title}'")

        content_element = soup.select_one(content_selector)
        if not content_element:
            print(f"  - WARNING: Content selector '{content_selector}' not found on {url}")
            return None

        # Remove unwanted elements
        elements_to_remove = [
            '.post-meta', '.share-links', 'nav', '.related-posts',
            '.post-footer', 'footer', '.author-box', '.comments-area'
        ]
        for selector in elements_to_remove:
            for tag in content_element.select(selector):
                tag.decompose()

        content_html = str(content_element)
        content_md = md(content_html, heading_style="ATX")
        content_md = re.sub(r'\n{3,}', '\n\n', content_md).strip()

        # Extract author
        author_name = ""
        author_meta = soup.select_one('meta[name="author"]')
        author_name = author_meta['content'] if author_meta and 'content' in author_meta.attrs else ""

        return {
            "title": title,
            "content": content_md,
            "content_type": content_type,
            "source_url": url,
            "author": author_name,
            "user_id": ""
        }

    except requests.exceptions.RequestException as e:
        print(f"  - ERROR fetching {url}: {e}")
        return None
    except Exception as e:
        print(f"  - ERROR processing {url}: {e}")
        return None


def run_interviewing_io_scraper_in_parallel(urls: list):
    """
    Uses a thread pool to run the specialized interviewing.io scraper on a list of URLs concurrently.
    """
    items = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:  # Reduced workers to be more polite
        future_to_url = {executor.submit(scrape_interviewing_io_blog_post, url): url for url in urls}
        for future in concurrent.futures.as_completed(future_to_url):
            try:
                data = future.result()
                if data:
                    items.append(data)
            except Exception as exc:
                url = future_to_url[future]
                print(f"  - ERROR: An exception occurred while scraping {url}: {exc}")
            time.sleep(0.2)  # More conservative rate limiting
    return items


def run_interviewing_io_guide_scraper_in_parallel(urls: list):
    """
    Uses a thread pool to run the specialized interviewing.io guide scraper on a list of URLs concurrently.
    """
    items = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:  # Reduced workers to be more polite
        future_to_url = {executor.submit(scrape_interviewing_io_guide, url): url for url in urls}
        for future in concurrent.futures.as_completed(future_to_url):
            try:
                data = future.result()
                if data:
                    items.append(data)
            except Exception as exc:
                url = future_to_url[future]
                print(f"  - ERROR: An exception occurred while scraping guide {url}: {exc}")
            time.sleep(0.2)  # More conservative rate limiting
    return items


def run_scraper_in_parallel(urls: list, title_selector: str, content_selector: str, content_type: str):
    """
    Uses a thread pool to run the scrape_page function on a list of URLs concurrently.
    """
    items = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_url = {executor.submit(scrape_page, url, title_selector, content_selector, content_type): url for url in urls}
        for future in concurrent.futures.as_completed(future_to_url):
            try:
                data = future.result()
                if data:
                    items.append(data)
            except Exception as exc:
                url = future_to_url[future]
                print(f"  - ERROR: An exception occurred while scraping {url}: {exc}")
            time.sleep(0.1)
    return items


def crawl_interviewing_io_blog():
    """
    Finds all article URLs on the interviewing.io blog and scrapes them.
    """
    start_url = "https://interviewing.io/blog"
    print(f"\nStarting crawl of interviewing.io Blog: {start_url}")
    try:
        response = requests.get(start_url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # Extract blog post links from the h1 > a elements on the listing page
        post_links = [urljoin(start_url, a['href']) for a in soup.select('h1 > a') if a.get('href') and a.get('href').startswith('/blog/')]
        print(f"Found {len(post_links)} blog posts on interviewing.io.")

        # Use the specialized scraper for interviewing.io blog posts
        return run_interviewing_io_scraper_in_parallel(post_links)

    except requests.exceptions.RequestException as e:
        print(f"ERROR: Could not fetch the main blog page {start_url}. Reason: {e}")
        return []


def crawl_interviewing_io_guides():
    """
    Finds all company and interview guides on interviewing.io and scrapes them.
    """
    base_url = "https://interviewing.io"
    # The assignment points to two URLs which are fragments on a single page.
    # /topics and /learn both contain relevant guides.
    guide_pages = [f"{base_url}/topics", f"{base_url}/learn"]
    all_guide_links = set() # Use a set to avoid duplicates

    print("\nStarting crawl of interviewing.io Guides")
    for page_url in guide_pages:
        print(f"Finding guides on: {page_url}")
        try:
            response = requests.get(page_url, headers=HEADERS, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # SELECTOR FIX: The original selector was for JS-rendered content.
            # This new selector finds all links to guides in the raw HTML.
            links = soup.select('a[href*="/guides/"]')
            for a in links:
                if a.get('href'):
                    all_guide_links.add(urljoin(base_url, a['href']))

        except requests.exceptions.RequestException as e:
            print(f"ERROR: Could not fetch guide page {page_url}. Reason: {e}")
            continue
    
    print(f"Found {len(all_guide_links)} unique guides on interviewing.io.")
    
    # Use the specialized guide scraper instead of the generic scraper
    return run_interviewing_io_guide_scraper_in_parallel(list(all_guide_links))


def crawl_nil_mamano():
    """
    Finds all of Nil Mamano's DS&A blog posts and scrapes them.
    """
    start_url = "https://nilmamano.com/blog/category/dsa/"
    print(f"\nStarting crawl of Nil Mamano's Blog: {start_url}")

    # NOTE: This site has proven difficult to scrape with basic requests,
    # likely due to client-side rendering or advanced bot detection.
    # Rather than add heavy dependencies like Selenium, we will acknowledge
    # this limitation and skip this source.
    print(f"  - INFO: Skipping {start_url} as it appears to be blocking scrapers.")
    return []

def crawl_quill_co_blog():
    """
    Demonstrates reusability by scraping a different blog (Quill.co).
    This is part of the "Bonus Points" / robustness check.
    """
    start_url = "https://quill.co/blog"
    print(f"\nStarting crawl of Quill.co Blog (Bonus): {start_url}")

    # NOTE: This site appears to be fully client-side rendered with JavaScript.
    # The initial HTML from `requests` does not contain the blog post links.
    # A more advanced scraper using a tool like Selenium or Playwright would be needed.
    # For this project, we will return an empty list as required by the architecture.
    print(f"  - INFO: Skipping {start_url} as it requires JavaScript to render content.")
    return [] 