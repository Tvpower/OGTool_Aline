import json
import scrapers
import pdf_processor

# Define the name for the output file and the path for the PDF.
# The user should place the PDF with this name in the project root.
OUTPUT_FILENAME = "output.json"
PDF_BOOK_PATH = "Aline_Book.pdf" 

def main():
    """
    Main function to orchestrate the scraping process.
    
    It calls all the crawler functions, processes the PDF,
    aggregates the results, and saves them to a JSON file.
    """
    all_items = []

    # --- Run Scrapers ---
    # Each crawler function is responsible for a specific source.
    # They run scraping tasks in parallel internally for efficiency.
    all_items.extend(scrapers.crawl_interviewing_io_blog())
    all_items.extend(scrapers.crawl_interviewing_io_guides())
    all_items.extend(scrapers.crawl_nil_mamano())

    # --- Process Local Files ---
    # The PDF processor handles local document extraction.
    all_items.extend(pdf_processor.process_book_chapters(PDF_BOOK_PATH))

    # --- Bonus: Demonstrate Reusability ---
    # This call shows that our generic scraper setup can handle other blogs.
    all_items.extend(scrapers.crawl_quill_co_blog())

    # --- Assemble Final Output ---
    # The final JSON structure is created as per the assignment's requirements.
    final_output = {
        "team_id": "aline123",
        "items": all_items
    }

    # --- Save to File ---
    # The results are written to a JSON file.
    try:
        with open(OUTPUT_FILENAME, 'w', encoding='utf-8') as f:
            json.dump(final_output, f, indent=2, ensure_ascii=False)
        print(f"\n✅ Success! All content has been scraped and saved to '{OUTPUT_FILENAME}'")
        print(f"Total items scraped: {len(all_items)}")
    except IOError as e:
        print(f"\n❌ Error saving output to file: {e}")

if __name__ == "__main__":
    main() 