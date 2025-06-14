import fitz  # PyMuPDF
import os
import re
from collections import Counter
from typing import List, Dict, Optional, Tuple


def get_font_size_stats(page) -> Tuple[int, List[Tuple[int, int]]]:
    """
    Get font size statistics for a page.
    Returns: (base_font_size, [(font_size, count)] sorted by frequency)
    """
    spans = [s for b in page.get_text("dict")["blocks"] if b['type'] == 0 for l in b["lines"] for s in l["spans"]]
    if not spans:
        return 12, [(12, 1)]
    
    # Count occurrences of each font size, rounded to the nearest integer
    sizes = [round(s['size']) for s in spans]
    if not sizes:
        return 12, [(12, 1)]

    size_counts = Counter(sizes).most_common()
    base_font_size = size_counts[0][0]  # Most common font size
    
    return base_font_size, size_counts


def get_base_font_size(page) -> int:
    """
    Heuristic to find the most common font size on a page, likely the body text.
    """
    base_size, _ = get_font_size_stats(page)
    return base_size


def clean_text(text: str) -> str:
    """
    Clean extracted text by removing excessive whitespace and fixing common PDF artifacts.
    """
    # Remove excessive whitespace
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
    # Remove trailing spaces
    text = re.sub(r' +\n', '\n', text)
    # Fix common PDF line break issues
    text = re.sub(r'(?<!\n)\n(?!\n)(?![A-Z])', ' ', text)
    return text.strip()


def detect_content_type(text: str, title: str) -> str:
    """
    Detect the type of content based on text patterns.
    """
    text_lower = text.lower()
    title_lower = title.lower()
    
    if 'problem' in title_lower and ('solution' in text_lower or 'def ' in text):
        return 'coding_problem'
    elif 'interview' in title_lower or 'behavioral' in title_lower:
        return 'interview_guide'
    elif 'negotiation' in title_lower or 'offer' in title_lower or 'salary' in title_lower:
        return 'career_advice'
    elif any(keyword in text_lower for keyword in ['algorithm', 'complexity', 'o(', 'binary search', 'sliding window']):
        return 'technical_concept'
    else:
        return 'book'


def extract_code_blocks(text: str) -> List[Dict[str, str]]:
    """
    Extract code blocks from text content.
    """
    code_blocks = []
    
    # Pattern for function definitions
    function_pattern = r'(def \w+\([^)]*\):.*?)(?=\n\w|\n\n|$)'
    for match in re.finditer(function_pattern, text, re.DOTALL):
        code_blocks.append({
            'type': 'function',
            'code': match.group(1).strip()
        })
    
    # Pattern for code snippets with line numbers
    numbered_code_pattern = r'(\d+\s+.*?\n)+'
    for match in re.finditer(numbered_code_pattern, text):
        code_text = match.group(0)
        if any(keyword in code_text for keyword in ['def ', 'if ', 'for ', 'while ', 'return ']):
            code_blocks.append({
                'type': 'snippet',
                'code': code_text.strip()
            })
    
    return code_blocks


def process_book_chapters(pdf_path: str) -> List[Dict]:
    """
    Enhanced PDF processor for BCTCI books that properly extracts structured content.

    This function identifies chapters, sections, problems, and solutions with improved
    pattern matching and content type detection.

    Args:
        pdf_path (str): The file path to the PDF book.

    Returns:
        List[Dict]: A list of dictionaries representing extracted content items.
    """
    print(f"\nProcessing PDF: {pdf_path}")
    if not os.path.exists(pdf_path):
        print(f"  - WARNING: PDF file not found at '{pdf_path}'. Skipping PDF processing.")
        print(f"  - To process the book, please download it and place it at the root of this project.")
        return []

    items = []
    try:
        doc = fitz.open(pdf_path)
        
        # Enhanced patterns for BCTCI format
        chapter_patterns = [
            re.compile(r'^\s*Ch\s*\d+\.?\s*(.+)$', re.IGNORECASE),  # "Ch 1. Title"
            re.compile(r'^\s*Chapter\s*\d+\.?\s*(.+)$', re.IGNORECASE),  # "Chapter 1. Title"
            re.compile(r'^\s*Part\s*[IVX]+\.?\s*(.+)$', re.IGNORECASE),  # "Part I. Title"
            re.compile(r'^\s*CHAPTER\s*\d+\s*▸\s*(.+)$'),  # "CHAPTER 29 ▸ BINARY SEARCH"
            re.compile(r'^\s*CHAPTER\s*\d+\s*(.+)$'),  # "CHAPTER 29 BINARY SEARCH"
        ]
        
        problem_patterns = [
            re.compile(r'^\s*PROBLEM\s*[\d.]+\s*(.+)$', re.MULTILINE),
            re.compile(r'^\s*Problem\s*[\d.]+:?\s*(.+)$', re.MULTILINE),
        ]
        
        solution_patterns = [
            re.compile(r'^\s*SOLUTION\s*[\d.]+\s*(.+)$', re.MULTILINE),
            re.compile(r'^\s*Solution\s*[\d.]+:?\s*(.+)$', re.MULTILINE),
        ]
        
        current_chapter_title = ""
        current_content = ""
        items_found = 0
        base_font_size = None
        authors = ["Gayle L. McDowell", "Mike Mroczka", "Aline Lerner", "Nil Mamano"]
        
        # Process each page
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            page_text = page.get_text()
            
            # Skip pages with minimal content
            if len(page_text.strip()) < 50:
                continue
                
            # Determine base font size from pages with substantial text
            if base_font_size is None:
                base_font_size = get_base_font_size(page)
                print(f"  - Detected base font size: {base_font_size}")
                
            blocks = page.get_text("dict")["blocks"]
            
            # Look for chapter/section titles
            found_new_section = False
            for block in blocks:
                if "lines" not in block:
                    continue
                    
                for line in block["lines"]:
                    if not line["spans"]:
                        continue
                        
                    first_span = line["spans"][0]
                    span_size = round(first_span["size"])
                    line_text = "".join([s["text"] for s in line["spans"]]).strip()
                    
                    if not line_text:
                        continue
                    
                    # Check if this is a title based on font size or patterns
                    is_large_font = span_size > base_font_size * 1.4
                    is_chapter_pattern = any(pattern.match(line_text) for pattern in chapter_patterns)
                    is_problem_pattern = any(pattern.match(line_text) for pattern in problem_patterns)
                    is_solution_pattern = any(pattern.match(line_text) for pattern in solution_patterns)
                    
                    # Skip very short lines that are likely not real titles
                    if len(line_text.strip()) < 5:
                        continue
                        
                    # Skip single character titles (like "I") unless they're Roman numerals in context
                    if len(line_text.strip()) == 1 and line_text.strip() not in ['I', 'V', 'X']:
                        continue
                    
                    # Check for major section breaks
                    if ((is_large_font and len(line_text) < 100 and len(line_text) > 5) or is_chapter_pattern):
                        # Save previous content if exists
                        if current_chapter_title and current_content.strip():
                            cleaned_content = clean_text(current_content)
                            if len(cleaned_content) > 500:  # Only save substantial content
                                content_type = detect_content_type(cleaned_content, current_chapter_title)
                                code_blocks = extract_code_blocks(cleaned_content)
                                
                                item = {
                                    "title": current_chapter_title,
                                    "content": cleaned_content,
                                    "content_type": content_type,
                                    "source_url": f"file://{os.path.abspath(pdf_path)}",
                                    "author": ", ".join(authors),
                                    "user_id": "",
                                    "page_start": page_num,
                                    "font_size": span_size
                                }
                                
                                if code_blocks:
                                    item["code_blocks"] = code_blocks
                                    
                                items.append(item)
                                print(f"  - Extracted: {current_chapter_title} ({content_type})")
                                items_found += 1
                        
                        # Start new section
                        current_chapter_title = line_text
                        current_content = ""
                        found_new_section = True
                        break
                    
                    # Handle problems and solutions as separate items
                    elif is_problem_pattern or is_solution_pattern:
                        # Save previous content if it's substantial
                        if current_chapter_title and current_content.strip() and len(current_content.strip()) > 500:
                            cleaned_content = clean_text(current_content)
                            content_type = detect_content_type(cleaned_content, current_chapter_title)
                            code_blocks = extract_code_blocks(cleaned_content)
                            
                            item = {
                                "title": current_chapter_title,
                                "content": cleaned_content,
                                "content_type": content_type,
                                "source_url": f"file://{os.path.abspath(pdf_path)}",
                                "author": ", ".join(authors),
                                "user_id": "",
                                "page_start": page_num,
                                "font_size": span_size
                            }
                            
                            if code_blocks:
                                item["code_blocks"] = code_blocks
                                
                            items.append(item)
                            print(f"  - Extracted: {current_chapter_title} ({content_type})")
                            items_found += 1
                        
                        # Start new problem/solution
                        current_chapter_title = line_text
                        current_content = ""
                        found_new_section = True
                        break
                        
                if found_new_section:
                    break
            
            # Add page content to current section
            if not found_new_section:
                current_content += page_text + "\n\n"
        
        # Handle the final section
        if current_chapter_title and current_content.strip() and len(current_content.strip()) > 500:
            cleaned_content = clean_text(current_content)
            content_type = detect_content_type(cleaned_content, current_chapter_title)
            code_blocks = extract_code_blocks(cleaned_content)
            
            item = {
                "title": current_chapter_title,
                "content": cleaned_content,
                "content_type": content_type,
                "source_url": f"file://{os.path.abspath(pdf_path)}",
                "author": ", ".join(authors),
                "user_id": "",
                "page_start": len(doc),
                "font_size": 0
            }
            
            if code_blocks:
                item["code_blocks"] = code_blocks
                
            items.append(item)
            print(f"  - Extracted: {current_chapter_title} ({content_type})")
            items_found += 1
        
        doc.close()
        print(f"Successfully extracted {len(items)} content sections from the PDF.")
        
        # Print summary of content types
        content_types = {}
        for item in items:
            content_type = item['content_type']
            content_types[content_type] = content_types.get(content_type, 0) + 1
        
        print(f"  - Content breakdown: {dict(content_types)}")
        return items

    except Exception as e:
        print(f"  - ERROR: An unexpected error occurred while processing the PDF: {e}")
        import traceback
        traceback.print_exc()
        return [] 