import fitz  # PyMuPDF
import os
import re


def process_book_chapters(pdf_path: str):
    """
    Extracts content from the first 8 chapters of the provided PDF book.

    It identifies chapters by looking for specific text patterns ("Chapter X")
    and structures the output accordingly.

    Args:
        pdf_path (str): The file path to the PDF book.

    Returns:
        list: A list of dictionaries, where each dictionary represents a chapter.
    """
    print(f"\nProcessing PDF: {pdf_path}")
    if not os.path.exists(pdf_path):
        print(f"  - WARNING: PDF file not found at '{pdf_path}'. Skipping PDF processing.")
        print("  - To process the book, please download it and place it at the root of this project.")
        return []

    items = []
    try:
        doc = fitz.open(pdf_path)
        
        # This is a heuristic to find chapter breaks. We'll look for "Chapter X:"
        # and assume it has a larger font size. This may need tuning for the specific PDF.
        chapter_pattern = re.compile(r"^Chapter\s+\d+[:\s]")
        
        current_chapter_title = ""
        current_chapter_text = ""
        
        # Limit to first 8 chapters as per the assignment
        chapters_found = 0

        for page_num in range(len(doc)):
            if chapters_found >= 8:
                print("  - Reached chapter 8, stopping PDF processing as per requirements.")
                break

            page = doc.load_page(page_num)
            blocks = page.get_text("dict", flags=fitz.TEXTFLAGS_FONT)
            
            # Look for a chapter title on the page
            found_new_chapter = False
            for block in blocks["blocks"]:
                if "lines" in block:
                    for line in block["lines"]:
                        line_text = "".join([span["text"] for span in line["spans"]]).strip()
                        if chapter_pattern.match(line_text):
                            # Found a new chapter, save the previous one
                            if current_chapter_title and current_chapter_text:
                                items.append({
                                    "title": current_chapter_title,
                                    "content": current_chapter_text.strip(),
                                    "content_type": "book",
                                    "source_url": f"file://{os.path.abspath(pdf_path)}",
                                    "author": "Aline", # Assuming author
                                    "user_id": ""
                                })
                                print(f"  - Extracted: {current_chapter_title}")
                            
                            # Start the new chapter
                            chapters_found += 1
                            if chapters_found > 8:
                                break
                            current_chapter_title = line_text
                            current_chapter_text = ""
                            found_new_chapter = True
                            # Move to next page after finding chapter title
                            break 
                if found_new_chapter:
                    break
            
            # If we are in a chapter, append the page's text
            if current_chapter_title and not found_new_chapter:
                current_chapter_text += page.get_text() + "\n\n"

        # Add the last processed chapter
        if current_chapter_title and current_chapter_text and chapters_found <= 8:
            items.append({
                "title": current_chapter_title,
                "content": current_chapter_text.strip(),
                "content_type": "book",
                "source_url": f"file://{os.path.abspath(pdf_path)}",
                "author": "Aline",
                "user_id": ""
            })
            print(f"  - Extracted: {current_chapter_title}")

        print(f"Successfully extracted {len(items)} chapters from the PDF.")
        return items

    except Exception as e:
        print(f"  - ERROR: An unexpected error occurred while processing the PDF: {e}")
        return [] 