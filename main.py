"""
Legacy main.py - DEPRECATED
For the new configuration-driven approach, use: python cli.py scrape

This file is kept only for backward compatibility.
"""

import sys
import os

def main():
    """
    Legacy main function - redirects to new CLI approach.
    
    🚫 DEPRECATED: This approach is no longer maintained.
    ✅ Use the new CLI instead: python cli.py scrape
    """

    print("✅ Please use the new CLI approach instead:")
    print()
    print("  # Basic scraping:")
    print("  python cli.py scrape")
    print()
    print("  # Validate configuration:")
    print("  python cli.py validate")
    print()
    print("  # List all targets:")
    print("  python cli.py list-targets")
    print()
    print("  # Process a single PDF:")
    print("  python cli.py process-pdf 'path/to/file.pdf'")
    print()
    print("  # Scrape a single URL:")
    print("  python cli.py scrape-url 'https://example.com/article'")
    print()
    print("📖 The new approach uses config.yml for easy configuration.")
    print("🚀 Much more flexible and feature-rich!")
    print()
    
    # Ask if they want to run the new CLI
    try:
        choice = input("Would you like to run 'python cli.py scrape' now? (y/N): ").strip().lower()
        if choice in ['y', 'yes']:
            import subprocess
            sys.exit(subprocess.call([sys.executable, 'cli.py', 'scrape']))
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    
    sys.exit(1)

if __name__ == "__main__":
    main() 