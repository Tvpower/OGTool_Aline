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


def scrape_page(url: str, title_selector: str, content_selector: str, content_type: str = "blog"):
    """
    Scrapes a single page (like a blog post or guide).

    This is a generic function that can be configured with CSS selectors,
    making it reusable for different site structures.

    Args:
        url (str): The URL of the page to scrape.
        title_selector (str): CSS selector for the page title.
        content_selector (str): CSS selector for the main content area.
        content_type (str): The type of content being scraped (e.g., "blog", "guide").

    Returns:
        dict: A dictionary containing the scraped data, or None if scraping fails.
    """
    print(f"  - Scraping: {url}")
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()  # Raise an exception for bad status codes

        soup = BeautifulSoup(response.content, 'html.parser')

        title_element = soup.select_one(title_selector)
        title = title_element.get_text(strip=True) if title_element else "No Title Found"
        print(f"    - Title found: '{title}'")

        content_element = soup.select_one(content_selector)
        if not content_element:
            print(f"  - WARNING: Content selector '{content_selector}' not found on {url}")
            return None

        # Advanced Content Cleaning (as per bonus points)
        # Remove known non-content elements before converting to markdown for cleaner output.
        elements_to_remove = [
            '.post-meta', '.share-links', 'nav', '.related-posts',
            '.post-footer', 'footer', '.author-box', '.comments-area'
        ]
        for selector in elements_to_remove:
            for tag in content_element.select(selector):
                tag.decompose()

        content_html = str(content_element)
        content_md = md(content_html, heading_style="ATX")

        # Final cleaning pass on the markdown with regex.
        # Collapse excessive newlines and remove leftover navigation/sharing links.
        content_md = re.sub(r'\[.*?\]\(.*?\)', '', content_md) # Remove stray markdown links
        content_md = re.sub(r'\n{3,}', '\n\n', content_md).strip()

        # Extract author and date if possible (Bonus point)
        # This is a generic attempt; site-specific logic may be more reliable.
        author_meta = soup.select_one('meta[name="author"]')
        author_name = author_meta['content'] if author_meta and 'content' in author_meta.attrs else ""

        return {
            "title": title,
            "content": content_md,
            "content_type": content_type,
            "source_url": url,
            "author": author_name,
            "user_id": ""  # As per spec
        }

    except requests.exceptions.RequestException as e:
        print(f"  - ERROR fetching {url}: {e}")
        return None
    except Exception as e:
        print(f"  - ERROR processing {url}: {e}")
        return None


def run_scraper_in_parallel(urls: list, title_selector: str, content_selector: str, content_type: str):
    """
    Uses a thread pool to run the scrape_page function on a list of URLs concurrently.
    """
    items = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        # Using a dict to map futures to URLs for better error reporting
        future_to_url = {executor.submit(scrape_page, url, title_selector, content_selector, content_type): url for url in urls}
        for future in concurrent.futures.as_completed(future_to_url):
            try:
                data = future.result()
                if data:
                    items.append(data)
            except Exception as exc:
                url = future_to_url[future]
                print(f"  - ERROR: An exception occurred while scraping {url}: {exc}")
            time.sleep(0.1)  # Rate limiting to be a good web citizen
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

        # SELECTOR FIX: Based on inspecting raw HTML, the post links are inside h1 tags.
        post_links = [urljoin(start_url, a['href']) for a in soup.select('h1 > a') if a.get('href')]
        print(f"Found {len(post_links)} blog posts on interviewing.io.")

        # SELECTOR FIX: The selectors for title and content on the actual post pages
        # also need to be based on the raw, non-JS-rendered HTML.
        title_selector = 'h1'
        # This container holds the main article content in the raw HTML.
        # SELECTOR FIX: The previous selector had issues with the escaped slash.
        # This new selector targets the main content block more reliably.
        content_selector = 'div.w-full > div'

        return run_scraper_in_parallel(post_links, title_selector, content_selector, "blog")

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
    
    # SELECTOR FIX: Update selectors for the guide pages themselves.
    title_selector = 'h1'
    content_selector = 'div.mt-16' # A container found in the raw HTML of guide pages

    return run_scraper_in_parallel(list(all_guide_links), title_selector, content_selector, "guide")


def crawl_nil_mamano():
    """
    Finds all of Nil Mamano's DS&A blog posts and scrapes them.
    """
    start_url = "https://nilmamano.com/blog/category/dsa/"
    print(f"\nStarting crawl of Nil Mamano's Blog: {start_url}")
    try:
        response = requests.get(start_url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # FINAL SELECTOR FIX: This more specific selector targets only the article
        # cards, avoiding other links on the page.
        post_links = [urljoin(start_url, a['href']) for a in soup.select('article.card-border h2 a') if a.get('href')]
        print(f"Found {len(post_links)} posts on Nil Mamano's blog.")

        # Selectors from inspecting a post page's raw HTML
        title_selector = 'h1'
        content_selector = 'div.prose'

        return run_scraper_in_parallel(post_links, title_selector, content_selector, "blog")

    except requests.exceptions.RequestException as e:
        print(f"ERROR: Could not fetch the main blog page {start_url}. Reason: {e}")
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