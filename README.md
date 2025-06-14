# OGTool_Aline - Web Scraper Tool

A powerful, configuration-driven web scraping tool that can extract content from multiple websites and process PDF documents.

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the scraper with default configuration
python cli.py scrape

# Validate your configuration
python cli.py validate

# See all available commands
python cli.py --help
```

## ✨ Features

- **Configuration-driven**: Easy-to-modify YAML configuration
- **Multiple scrapers**: Built-in support for blogs, guides, and newsletters
- **PDF processing**: Extract and process content from PDF documents
- **ZenRows integration**: Premium API fallback for difficult sites
- **Parallel processing**: Efficient concurrent scraping
- **Flexible selectors**: CSS selector-based content extraction
- **Rich CLI**: Colorful, informative command-line interface

## 📁 Project Structure

```
├── cli.py                 # Main CLI interface (USE THIS)
├── config.yml            # Configuration file
├── config_loader.py      # Configuration parser
├── generic_scraper.py    # Main scraping engine
├── zenrows_scraper.py    # Premium API fallback
├── pdf_processor.py      # PDF content extraction
├── main.py              # Legacy script (DEPRECATED)
├── scrapers.py          # Legacy scrapers (partial use)
├── test_pdf_processor.py # PDF testing utilities
├── Books_PDF/           # PDF files directory
└── requirements.txt     # Python dependencies
```

## 🎯 Current Active Targets

- ✅ **Interviewing.io Blog** - Tech interview articles
- ✅ **Interviewing.io Guides** - Interview preparation guides  
- ✅ **Shreycation Substack** - Newsletter content
- ✅ **PDF Processing** - Extract content from Books_PDF directory
- ❌ **Nil Mamano DSA** - Disabled (site blocks scrapers)
- ❌ **Quill.co Blog** - Disabled (structure issues)

## 🛠️ Usage Examples

### Basic Scraping
```bash
# Scrape all enabled targets
python cli.py scrape

# Scrape only a specific target
python cli.py scrape --target "Interviewing.io Blog"

# Skip PDF processing
python cli.py scrape --skip-pdf

# Dry run (show what would be scraped)
python cli.py scrape --dry-run
```

### Single URL Scraping
```bash
# Scrape a single URL
python cli.py scrape-url "https://example.com/article"

# With custom selectors
python cli.py scrape-url "https://site.com/post" \
  --title-selector "h1.title" \
  --content-selector ".post-content"

# Force ZenRows for difficult sites
python cli.py scrape-url "https://difficult-site.com" --force-zenrows
```

### PDF Processing
```bash
# Process a single PDF
python cli.py process-pdf "path/to/document.pdf"

# Test PDF processor with existing files
python test_pdf_processor.py
```

### Configuration Management
```bash
# Validate configuration
python cli.py validate

# List all targets
python cli.py list-targets

# Check ZenRows API status
python cli.py zenrows-status
```

## ⚙️ Configuration

Edit `config.yml` to:
- Add new scraping targets
- Modify CSS selectors
- Adjust rate limiting
- Configure ZenRows API
- Set output preferences

### Adding a New Target

```yaml
targets:
  - name: "My Blog"
    url: "https://myblog.com"
    type: "blog"
    enabled: true
    article_link_selector: "a.post-link"
    title_selector: "h1"
    content_selectors:
      - "article .content"
      - "div.post-body"
    author_selector: ".author-name"
    content_min_length: 100
```

## 🔧 Advanced Features

### ZenRows Fallback
- Automatically retries failed requests with premium proxy service
- Handles JavaScript-heavy sites
- Configurable fallback scenarios

### Content Filtering
- Minimum content length requirements
- Pattern-based content exclusion
- Duplicate content detection

### Parallel Processing
- Configurable worker threads
- Rate limiting protection
- Graceful error handling

## 📊 Output Format

Results are saved as JSON with this structure:
```json
{
  "team_id": "aline123",
  "items": [
    {
      "title": "Article Title",
      "content": "Article content...",
      "content_type": "blog",
      "source_url": "https://...",
      "author": "Author Name",
      "user_id": ""
    }
  ]
}
```

## 🚫 Deprecated Components

- **main.py**: Legacy hardcoded approach - use `python cli.py scrape` instead
- **Direct scraper imports**: Use CLI interface rather than importing scrapers directly

## 📝 Dependencies

Core dependencies are in `requirements.txt`:
- `requests` - HTTP client
- `beautifulsoup4` - HTML parsing
- `PyMuPDF` - PDF processing
- `click` - CLI framework
- `colorama` - Terminal colors
- `pyyaml` - Configuration parsing
- `markdownify` - HTML to Markdown conversion

## 🤝 Contributing

1. Test changes with `python cli.py validate`
2. Add new targets via `config.yml`
3. Use the CLI interface for all operations
4. Test PDF processing with `python test_pdf_processor.py`

## 📈 Performance Tips

1. **Adjust rate limiting**: Modify `request_delay` in config.yml
2. **Use targeted selectors**: More specific CSS selectors = better performance
3. **Enable ZenRows for problem sites**: Handles complex JavaScript sites
4. **Batch operations**: Process multiple targets in one run

---

**Note**: This tool is designed for educational and research purposes. Always respect robots.txt and website terms of service.