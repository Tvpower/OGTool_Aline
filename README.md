# Web Scraper

A modular, concurrent web scraping solution designed for rapid development and maximum reusability. Built to extract content from multiple sources and compile them into a structured knowledge base within 24 hours.

## Strategy

This project prioritizes development speed and robustness over raw execution performance. Since network latency is typically the primary bottleneck in web scraping, we achieve high performance through concurrent requests rather than low-level optimizations.

The solution uses Python's world-class ecosystem for web scraping and data processing, enabling rapid development while maintaining professional-grade reliability.

## Features

- **Concurrent Processing**: Parallel HTTP requests to minimize total execution time
- **Modular Architecture**: Easy to extend with new sources (Substack, blogs, etc.)
- **Multi-Format Support**: Handles both web content and PDF processing
- **Professional Web Etiquette**: Includes rate limiting and proper User-Agent headers
- **Clean Output**: Converts HTML to structured Markdown format
- **Chapter-Aware PDF Processing**: Intelligently extracts and structures book content

## Technology Stack

- **Python 3.9+**: Core language
- **requests**: Fast HTTP requests
- **BeautifulSoup4**: Robust HTML parsing
- **PyMuPDF (fitz)**: High-performance PDF text extraction
- **markdownify**: HTML to Markdown conversion
- **concurrent.futures**: Built-in parallelization

## Installation

```bash
pip install requests beautifulsoup4 PyMuPDF markdownify
```

Or use the provided requirements file:

```bash
pip install -r requirements.txt
```

## Project Structure

```
├── main.py              # Main controller script
├── scrapers.py          # Core scraping logic
├── pdf_processor.py     # PDF processing specialist
├── requirements.txt     # Dependencies
└── output.json         # Generated knowledge base
```

### Module Responsibilities

- **main.py**: Orchestrates the entire process, dispatches tasks, aggregates results
- **scrapers.py**: Contains all web scraping functions
  - `scrape_blog_post(url)`: Generic article scraping
  - `crawl_interviewing_io_blog()`: Blog post discovery and scraping
  - `crawl_interviewing_io_guides()`: Company/interview guide extraction
  - `crawl_nil_mamano()`: DSA posts scraping
- **pdf_processor.py**: Specialized PDF handling
  - `process_book_chapters(pdf_path)`: Chapter-aware content extraction

## Usage

1. **Run the complete scraper**:
   ```bash
   python main.py
   ```

2. **Scrape a single article**:
   ```python
   from scrapers import scrape_blog_post
   article_data = scrape_blog_post("https://example.com/article")
   ```

3. **Process a PDF**:
   ```python
   from pdf_processor import process_book_chapters
   chapters = process_book_chapters("book.pdf")
   ```

## Implementation Guide

### Phase 1: Single Article Scraping
- Create generic `scrape_blog_post()` function
- Handle title extraction and content parsing
- Convert HTML to clean Markdown format

### Phase 2: Website Crawling
- Implement site-specific crawler functions
- Use concurrent processing for parallel requests
- Aggregate results from multiple sources

### Phase 3: PDF Processing
- Extract text with chapter-aware parsing
- Identify chapter breaks using font size heuristics
- Structure content by chapters for better organization

### Phase 4: Final Assembly
- Combine all scraped content
- Generate structured JSON output
- Apply final content cleaning and formatting

## Output Format

The scraper generates a structured JSON file:

```json
{
  "team_id": "aline123",
  "items": [
    {
      "title": "Article Title",
      "content": "Markdown content...",
      "content_type": "article",
      "source_url": "https://example.com/article",
      "author": "Author Name"
    }
  ]
}
```

## Extending the Scraper

Adding new sources is straightforward:

1. Create a new crawler function in `scrapers.py`:
   ```python
   def crawl_new_source():
       # Implementation here
       pass
   ```

2. Call it from `main.py`:
   ```python
   new_items = crawl_new_source()
   all_items.extend(new_items)
   ```

## Best Practices

- **Rate Limiting**: Includes delays to avoid overwhelming servers
- **Professional Headers**: Uses appropriate User-Agent identification
- **Error Handling**: Robust handling of network and parsing errors
- **Content Cleaning**: Removes navigation artifacts and unwanted elements
- **Metadata Extraction**: Captures author information and publication dates when available

## Performance Considerations

- Uses `ThreadPoolExecutor` for I/O-bound concurrent operations
- Configurable worker limits to balance speed and server respect
- Network latency optimization through parallel processing
- Efficient PDF parsing with PyMuPDF

## Contributing

The modular architecture makes it easy to:
- Add new content sources
- Enhance parsing logic for specific sites
- Improve content cleaning algorithms
- Extend metadata extraction capabilities

## License

This project is designed as a reusable tool for building knowledge bases from web content and documents.