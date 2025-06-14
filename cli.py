"""
Command-line interface for the web scraper tool.
Provides a modern CLI with multiple commands and options.
"""

import json
import os
import glob
import sys
from pathlib import Path
from typing import List, Optional

import click
from colorama import init, Fore, Style

from config_loader import ConfigLoader, ScraperConfig
from generic_scraper import GenericScraper, LegacyScraper
import pdf_processor

# Initialize colorama for cross-platform colored output
init(autoreset=True)

# Default configuration file
DEFAULT_CONFIG = "config.yml"


def print_success(message: str):
    """Print a success message in green."""
    click.echo(f"{Fore.GREEN}✅ {message}{Style.RESET_ALL}")


def print_warning(message: str):
    """Print a warning message in yellow."""
    click.echo(f"{Fore.YELLOW}⚠️  {message}{Style.RESET_ALL}")


def print_error(message: str):
    """Print an error message in red."""
    click.echo(f"{Fore.RED}❌ {message}{Style.RESET_ALL}")


def print_info(message: str):
    """Print an info message in blue."""
    click.echo(f"{Fore.BLUE}ℹ️  {message}{Style.RESET_ALL}")


@click.group()
@click.version_option(version="2.1.0", prog_name="Web Scraper Tool")
def cli():
    """
    🚀 Configuration-Driven Web Scraper Tool
    
    A flexible and reusable web scraping tool that works with YAML configuration files.
    You can scrape multiple websites, process PDFs, and more without touching the code!
    
    ✨ New: ZenRows API integration for reliable fallback scraping!
    """
    pass


@cli.command()
@click.option(
    '--config', '-c', 
    default=DEFAULT_CONFIG, 
    help='Path to configuration file (default: config.yml)'
)
@click.option(
    '--output', '-o', 
    help='Output file path (overrides config file setting)'
)
@click.option(
    '--target', '-t', 
    help='Scrape only a specific target by name'
)
@click.option(
    '--skip-pdf', 
    is_flag=True, 
    help='Skip PDF processing'
)
@click.option(
    '--dry-run', 
    is_flag=True, 
    help='Show what would be scraped without actually doing it'
)
def scrape(config: str, output: Optional[str], target: Optional[str], skip_pdf: bool, dry_run: bool):
    """
    🎯 Scrape content from configured websites and process PDFs.
    
    This is the main command that runs the full scraping pipeline based on your configuration file.
    
    Examples:
        python cli.py scrape
        python cli.py scrape --config my-config.yml
        python cli.py scrape --target "Interviewing.io Blog"
        python cli.py scrape --skip-pdf --dry-run
    """
    try:
        # Load configuration
        print_info(f"Loading configuration from: {config}")
        scraper_config = ConfigLoader.load_config(config)
        
        # Validate configuration
        errors = ConfigLoader.validate_config(scraper_config)
        if errors:
            print_error("Configuration validation failed:")
            for error in errors:
                click.echo(f"  • {error}", err=True)
            sys.exit(1)
        
        # Override output file if specified
        if output:
            scraper_config.output_file = output
        
        # Get targets to scrape
        if target:
            # Scrape specific target
            target_config = ConfigLoader.get_target_by_name(scraper_config, target)
            if not target_config:
                print_error(f"Target '{target}' not found in configuration")
                sys.exit(1)
            targets = [target_config]
        else:
            # Scrape all enabled targets
            targets = ConfigLoader.get_enabled_targets(scraper_config)
        
        if not targets:
            print_warning("No targets enabled for scraping")
            return
        
        # Show what will be scraped
        print_info(f"Targets to scrape: {len(targets)}")
        for t in targets:
            status = "✅ Enabled" if t.enabled else "❌ Disabled"
            click.echo(f"  • {t.name} ({t.type}) - {status}")
        
        if dry_run:
            print_info("Dry run completed - no actual scraping performed")
            return
        
        # Perform scraping
        all_items = []
        generic_scraper = GenericScraper(scraper_config)
        legacy_scraper = LegacyScraper(scraper_config)
        
        for target_config in targets:
            # Check if we should use legacy scraper
            if legacy_scraper.use_legacy_scraper(target_config):
                print_info(f"Using specialized scraper for {target_config.name}")
                items = legacy_scraper.scrape_with_legacy(target_config)
            else:
                items = generic_scraper.scrape_target(target_config)
            
            all_items.extend(items)
            print_info(f"Scraped {len(items)} items from {target_config.name}")
        
        # Process PDFs if enabled
        if not skip_pdf and scraper_config.pdf_processing.get('enabled', True):
            pdf_items = process_pdfs(scraper_config)
            all_items.extend(pdf_items)
        
        # Save results
        save_results(all_items, scraper_config)
        
        print_success(f"Scraping completed! Total items: {len(all_items)}")
        
    except FileNotFoundError as e:
        print_error(str(e))
        sys.exit(1)
    except Exception as e:
        print_error(f"Scraping failed: {e}")
        sys.exit(1)


@cli.command()
@click.argument('pdf_path', type=click.Path(exists=True))
@click.option(
    '--output', '-o', 
    help='Output file path (default: output.json)'
)
@click.option(
    '--config', '-c', 
    default=DEFAULT_CONFIG, 
    help='Path to configuration file for PDF processing settings'
)
def process_pdf(pdf_path: str, output: Optional[str], config: str):
    """
    📄 Process a single PDF file and extract its content.
    
    This command processes a specific PDF file and extracts its content into chapters.
    
    Examples:
        python cli.py process-pdf "path/to/book.pdf"
        python cli.py process-pdf "book.pdf" --output "book_content.json"
    """
    try:
        # Load configuration for PDF processing settings
        scraper_config = ConfigLoader.load_config(config) if os.path.exists(config) else ScraperConfig()
        
        print_info(f"Processing PDF: {pdf_path}")
        items = pdf_processor.process_book_chapters(pdf_path)
        
        if not items:
            print_warning("No content extracted from PDF")
            return
        
        # Prepare output
        output_file = output or "pdf_output.json"
        final_output = {
            "team_id": scraper_config.team_id,
            "items": items
        }
        
        # Save results
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(final_output, f, indent=2, ensure_ascii=False)
        
        print_success(f"PDF processed! {len(items)} items saved to {output_file}")
        
    except Exception as e:
        print_error(f"PDF processing failed: {e}")
        sys.exit(1)


@cli.command()
@click.argument('url')
@click.option(
    '--title-selector', 
    default='h1', 
    help='CSS selector for the title element'
)
@click.option(
    '--content-selector', 
    default='article, main, .content', 
    help='CSS selector for the content container'
)
@click.option(
    '--output', '-o', 
    help='Output file path (default: single_page_output.json)'
)
@click.option(
    '--config', '-c', 
    default=DEFAULT_CONFIG, 
    help='Path to configuration file for request settings'
)
@click.option(
    '--force-zenrows', 
    is_flag=True, 
    help='Force use of ZenRows instead of regular scraping'
)
@click.option(
    '--use-premium', 
    is_flag=True, 
    help='Use ZenRows premium features (JS rendering, premium proxies)'
)
def scrape_url(url: str, title_selector: str, content_selector: str, output: Optional[str], 
               config: str, force_zenrows: bool, use_premium: bool):
    """
    🔗 Scrape a single URL with custom selectors.
    
    This command allows you to quickly scrape a single page without modifying the configuration file.
    Optionally force ZenRows usage for difficult sites.
    
    Examples:
        python cli.py scrape-url "https://example.com/blog/post"
        python cli.py scrape-url "https://site.com/article" --title-selector "h1.title" --content-selector ".post-content"
        python cli.py scrape-url "https://difficult-site.com/page" --force-zenrows --use-premium
    """
    try:
        # Load configuration for request settings
        scraper_config = ConfigLoader.load_config(config) if os.path.exists(config) else ScraperConfig()
        
        print_info(f"Scraping URL: {url}")
        
        # Create a temporary target configuration
        from config_loader import ScrapingTarget
        temp_target = ScrapingTarget(
            name="Single URL",
            url=url,
            type="article",
            title_selector=title_selector,
            content_selectors=[content_selector]
        )
        
        result = None
        
        # Force ZenRows if requested
        if force_zenrows:
            if not scraper_config.zenrows_config.get('enabled', False):
                print_error("ZenRows is not enabled in configuration")
                sys.exit(1)
            
            api_key = scraper_config.zenrows_config.get('api_key')
            if not api_key:
                print_error("ZenRows API key not configured")
                sys.exit(1)
            
            try:
                from zenrows_scraper import ZenRowsScraper
                zenrows = ZenRowsScraper(scraper_config, api_key)
                result = zenrows.scrape_url(url, temp_target, use_premium)
            except ImportError:
                print_error("ZenRows scraper module not found")
                sys.exit(1)
        else:
            # Regular scraping (with potential ZenRows fallback)
            generic_scraper = GenericScraper(scraper_config)
            result = generic_scraper._scrape_single_article(url, temp_target)
        
        if not result:
            print_warning("No content extracted from URL")
            return
        
        # Prepare output
        output_file = output or "single_page_output.json"
        final_output = {
            "team_id": scraper_config.team_id,
            "items": [result]
        }
        
        # Save results
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(final_output, f, indent=2, ensure_ascii=False)
        
        scraper_method = result.get('scraped_with', 'regular')
        print_success(f"URL scraped with {scraper_method}! Content saved to {output_file}")
        
    except Exception as e:
        print_error(f"URL scraping failed: {e}")
        sys.exit(1)


@cli.command()
@click.option(
    '--config', '-c', 
    default=DEFAULT_CONFIG, 
    help='Path to configuration file to validate'
)
def validate(config: str):
    """
    ✅ Validate the configuration file.
    
    This command checks your configuration file for errors and shows what targets are configured.
    
    Examples:
        python cli.py validate
        python cli.py validate --config my-config.yml
    """
    try:
        print_info(f"Validating configuration: {config}")
        scraper_config = ConfigLoader.load_config(config)
        
        # Validate configuration
        errors = ConfigLoader.validate_config(scraper_config)
        if errors:
            print_error("Configuration validation failed:")
            for error in errors:
                click.echo(f"  • {error}", err=True)
            sys.exit(1)
        
        print_success("Configuration is valid!")
        
        # Show configuration summary
        print_info("Configuration Summary:")
        click.echo(f"  • Team ID: {scraper_config.team_id}")
        click.echo(f"  • Output File: {scraper_config.output_file}")
        click.echo(f"  • PDF Directory: {scraper_config.pdf_directory}")
        click.echo(f"  • Max Workers: {scraper_config.max_workers}")
        click.echo(f"  • Request Delay: {scraper_config.request_delay}s")
        
        # Show targets
        enabled_targets = ConfigLoader.get_enabled_targets(scraper_config)
        disabled_targets = [t for t in scraper_config.targets if not t.enabled]
        
        click.echo(f"\n  📋 Targets ({len(scraper_config.targets)} total):")
        for target in enabled_targets:
            click.echo(f"    ✅ {target.name} ({target.type}) - {target.url}")
        
        for target in disabled_targets:
            click.echo(f"    ❌ {target.name} ({target.type}) - DISABLED")
        
        if scraper_config.pdf_processing.get('enabled', True):
            click.echo(f"\n  📄 PDF Processing: Enabled (directory: {scraper_config.pdf_directory})")
        else:
            click.echo(f"\n  📄 PDF Processing: Disabled")
        
    except Exception as e:
        print_error(f"Configuration validation failed: {e}")
        sys.exit(1)


@cli.command()
@click.option(
    '--config', '-c', 
    default=DEFAULT_CONFIG, 
    help='Path to configuration file'
)
def list_targets(config: str):
    """
    📋 List all configured scraping targets.
    
    Shows all targets defined in the configuration file and their status.
    
    Examples:
        python cli.py list-targets
        python cli.py list-targets --config my-config.yml
    """
    try:
        scraper_config = ConfigLoader.load_config(config)
        
        if not scraper_config.targets:
            print_warning("No targets configured")
            return
        
        print_info(f"Scraping Targets ({len(scraper_config.targets)} total):")
        
        for i, target in enumerate(scraper_config.targets, 1):
            status = f"{Fore.GREEN}✅ Enabled" if target.enabled else f"{Fore.RED}❌ Disabled"
            click.echo(f"{i:2d}. {target.name}")
            click.echo(f"     Type: {target.type}")
            click.echo(f"     URL: {target.url}")
            click.echo(f"     Status: {status}{Style.RESET_ALL}")
            if target.article_link_selector:
                click.echo(f"     Link Selector: {target.article_link_selector}")
            if target.content_selectors:
                click.echo(f"     Content Selectors: {', '.join(target.content_selectors[:2])}{'...' if len(target.content_selectors) > 2 else ''}")
            click.echo()
            
    except Exception as e:
        print_error(f"Failed to list targets: {e}")
        sys.exit(1)


@cli.command()
@click.option(
    '--config', '-c', 
    default=DEFAULT_CONFIG, 
    help='Path to configuration file'
)
def zenrows_status(config: str):
    """
    🚀 Check ZenRows API status and configuration.
    
    Shows the current ZenRows configuration and API status including remaining credits.
    
    Examples:
        python cli.py zenrows-status
        python cli.py zenrows-status --config my-config.yml
    """
    try:
        scraper_config = ConfigLoader.load_config(config)
        zenrows_config = scraper_config.zenrows_config
        
        print_info("ZenRows Configuration:")
        
        # Show configuration status
        if zenrows_config.get('enabled', False):
            click.echo(f"  Status: {Fore.GREEN}✅ Enabled{Style.RESET_ALL}")
            
            api_key = zenrows_config.get('api_key', '')
            if api_key:
                masked_key = f"{api_key[:8]}...{api_key[-4:]}" if len(api_key) > 12 else "***"
                click.echo(f"  API Key: {masked_key}")
                
                # Initialize ZenRows scraper and check status
                try:
                    from zenrows_scraper import ZenRowsScraper
                    zenrows = ZenRowsScraper(scraper_config, api_key)
                    status_info = zenrows.check_api_status()
                    
                    if status_info['status'] == 'active':
                        click.echo(f"  API Status: {Fore.GREEN}✅ Active{Style.RESET_ALL}")
                        click.echo(f"  Response Time: {status_info['response_time']:.2f}s")
                        if status_info['remaining_credits'] != 'Unknown':
                            click.echo(f"  Remaining Credits: {status_info['remaining_credits']}")
                        if status_info['credits_reset'] != 'Unknown':
                            click.echo(f"  Credits Reset: {status_info['credits_reset']}")
                    else:
                        click.echo(f"  API Status: {Fore.RED}❌ Error{Style.RESET_ALL}")
                        click.echo(f"  Error: {status_info['error']}")
                        
                except ImportError:
                    print_error("ZenRows scraper module not found")
                except Exception as e:
                    print_error(f"Failed to check API status: {e}")
            else:
                print_warning("API key not configured")
        else:
            click.echo(f"  Status: {Fore.RED}❌ Disabled{Style.RESET_ALL}")
        
        # Show fallback settings
        print_info("\nFallback Settings:")
        fallback_settings = [
            ('Discovery Pages', 'fallback_for_discovery'),
            ('Article Content', 'fallback_for_articles'),
            ('Network Errors', 'fallback_for_network_errors'),
        ]
        
        for name, key in fallback_settings:
            enabled = zenrows_config.get(key, False)
            status = f"{Fore.GREEN}✅" if enabled else f"{Fore.RED}❌"
            click.echo(f"  {name}: {status} {Style.RESET_ALL}")
        
        # Show premium features
        print_info("\nPremium Features:")
        premium_settings = [
            ('Discovery', 'use_premium_for_discovery'),
            ('Articles', 'use_premium_for_articles'),
            ('Error Fallback', 'use_premium_for_errors'),
        ]
        
        for name, key in premium_settings:
            enabled = zenrows_config.get(key, False)
            status = f"{Fore.GREEN}✅" if enabled else f"{Fore.RED}❌"
            click.echo(f"  {name}: {status} {Style.RESET_ALL}")
            
    except Exception as e:
        print_error(f"Failed to check ZenRows status: {e}")
        sys.exit(1)


def process_pdfs(config: ScraperConfig) -> List[dict]:
    """Process all PDFs in the configured directory."""
    pdf_files = glob.glob(os.path.join(config.pdf_directory, '*.pdf'))
    
    if not pdf_files:
        print_warning(f"No PDFs found in '{config.pdf_directory}' directory")
        return []
    
    print_info(f"Processing {len(pdf_files)} PDF(s)")
    all_items = []
    
    for pdf_path in pdf_files:
        print_info(f"Processing: {os.path.basename(pdf_path)}")
        items = pdf_processor.process_book_chapters(pdf_path)
        all_items.extend(items)
        print_info(f"Extracted {len(items)} items from {os.path.basename(pdf_path)}")
    
    return all_items


def save_results(items: List[dict], config: ScraperConfig):
    """Save scraping results to a JSON file."""
    final_output = {
        "team_id": config.team_id,
        "items": items
    }
    
    try:
        with open(config.output_file, 'w', encoding='utf-8') as f:
            json.dump(final_output, f, indent=2, ensure_ascii=False)
        print_success(f"Results saved to: {config.output_file}")
    except IOError as e:
        print_error(f"Failed to save results: {e}")
        raise


if __name__ == '__main__':
    cli() 