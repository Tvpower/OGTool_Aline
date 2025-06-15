import pdfplumber
import os
import re
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading


def clean_text(text: str) -> str:
    """
    Clean extracted text by removing excessive whitespace and fixing common PDF artifacts.
    """
    if not text:
        return ""
    
    # Remove excessive whitespace
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
    # Remove trailing spaces
    text = re.sub(r' +\n', '\n', text)
    # Remove leading/trailing spaces from lines
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    text = '\n'.join(lines)
    # Fix hyphenated words at line breaks
    text = re.sub(r'-\n([a-z])', r'\1', text)
    # Fix spacing issues
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r' \n', '\n', text)
    
    return text.strip()


def detect_content_type(text: str, title: str) -> str:
    """
    Detect the type of content based on text patterns.
    """
    text_lower = text.lower()
    title_lower = title.lower()
    
    if 'problem' in title_lower:
        return 'coding_problem'
    elif 'solution' in title_lower:
        return 'coding_problem'
    elif 'chapter' in title_lower and any(keyword in text_lower for keyword in ['binary search', 'algorithm', 'code', 'def ', 'return']):
        return 'technical_concept'
    elif 'interview' in title_lower or 'behavioral' in title_lower:
        return 'interview_guide'
    elif 'negotiation' in title_lower or 'offer' in title_lower or 'salary' in title_lower:
        return 'career_advice'
    elif any(keyword in text_lower for keyword in ['algorithm', 'complexity', 'o(', 'binary search', 'sliding window', 'def ', 'return']):
        return 'technical_concept'
    elif 'hello world' in title_lower or 'hello reader' in title_lower:
        return 'interview_guide'
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
    
    # Pattern for numbered code lines (common in coding books)
    numbered_lines = re.findall(r'\n\s*\d+\s+[^\n]+', text)
    if len(numbered_lines) >= 3:  # If we have several numbered lines, it's likely code
        code_text = '\n'.join([line.strip() for line in numbered_lines])
        if any(keyword in code_text for keyword in ['def ', 'if ', 'for ', 'while ', 'return ', '=', '(', ')']):
            code_blocks.append({
                'type': 'snippet',
                'code': code_text
            })
    
    return code_blocks


def is_likely_header(text: str) -> bool:
    """
    Determine if a text line is likely a header/title.
    """
    if not text or len(text.strip()) < 3:
        return False
    
    text = text.strip()
    
    # Check for common header patterns
    header_patterns = [
        r'^\s*Ch\s*\d+\.?\s*.+$',  # "Ch 1. Title"
        r'^\s*Chapter\s*\d+\.?\s*.+$',  # "Chapter 1. Title"
        r'^\s*Part\s*[IVX]+\.?\s*.+$',  # "Part I. Title"
        r'^\s*CHAPTER\s*\d+\s*▸\s*.+$',  # "CHAPTER 29 ▸ BINARY SEARCH"
        r'^\s*CHAPTER\s*\d+\s*.+$',  # "CHAPTER 29 BINARY SEARCH"
        r'^\s*PROBLEM\s*[\d.]+\s*.+$',  # "PROBLEM 1.1 Title"
        r'^\s*Problem\s*[\d.]+:?\s*.+$',  # "Problem 1.1: Title"
        r'^\s*SOLUTION\s*[\d.]+\s*.+$',  # "SOLUTION 1.1 Title"
        r'^\s*Solution\s*[\d.]+:?\s*.+$',  # "Solution 1.1: Title"
        r'^\s*[IVX]+\.\s*.+$',  # "I. Title", "II. Title"
        r'^\s*\d+\.\s*.+$',  # "1. Title", "2. Title" (but not standalone numbers)
    ]
    
    for pattern in header_patterns:
        if re.match(pattern, text, re.IGNORECASE):
            return True
    
    # Check if text is all caps and reasonable length (likely a section header)
    if text.isupper() and 10 <= len(text) <= 100 and not text.isdigit():
        # Avoid false positives for things like page numbers or ISBNs
        if not re.match(r'^\d+$', text) and not re.match(r'^\d+-\d+-\d+.*$', text):
            return True
    
    # Check for specific known headers from the debug output
    if text in ['WHAT\'S INSIDE', 'HELLO WORLD. HELLO READER.', 'README']:
        return True
    
    return False


def extract_chapter_number(title: str) -> Optional[int]:
    """
    Extract chapter number from title text.
    """
    patterns = [
        r'Ch\s*(\d+)',
        r'Chapter\s*(\d+)',
        r'CHAPTER\s*(\d+)',
        r'CHAPTER\s*(\d+)\s*▸',  # "CHAPTER 29 ▸ BINARY SEARCH"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, title, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


def process_book_chapters(pdf_path: str, max_chapters: int = 8) -> List[Dict]:
    """
    Enhanced PDF processor using pdfplumber for better text extraction.
    Now limited to first N chapters only, but handles sneak peek PDFs better.
    
    Args:
        pdf_path (str): The file path to the PDF book.
        max_chapters (int): Maximum number of chapters to extract (default: 8)
        
    Returns:
        List[Dict]: A list of dictionaries representing extracted content items.
    """
    print(f"\nProcessing PDF: {pdf_path} (limiting to first {max_chapters} chapters)")
    if not os.path.exists(pdf_path):
        print(f"  - WARNING: PDF file not found at '{pdf_path}'. Skipping PDF processing.")
        print(f"  - To process the book, please download it and place it at the root of this project.")
        return []

    items = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            all_content = []
            
            # Check if this is a sneak peek PDF based on filename
            is_sneak_peek = "sneak" in os.path.basename(pdf_path).lower()
            
            # First pass: extract all text and identify potential headers
            for page_num, page in enumerate(pdf.pages):
                page_text = page.extract_text()
                if page_text and len(page_text.strip()) > 50:
                    lines = page_text.split('\n')
                    for line in lines:
                        clean_line = line.strip()
                        if clean_line:
                            all_content.append({
                                'text': clean_line,
                                'page': page_num + 1,
                                'is_header': is_likely_header(clean_line)
                            })
            
            print(f"  - Extracted {len(all_content)} lines from {len(pdf.pages)} pages")
            
            # Second pass: group content by headers, with smarter chapter limiting
            current_section = None
            authors = ["Gayle L. McDowell", "Mike Mroczka", "Aline Lerner", "Nil Mamano"]
            chapters_found = set()  # Track unique chapter numbers
            substantial_content_sections = 0  # Track sections with good content
            
            for i, line_info in enumerate(all_content):
                if line_info['is_header']:
                    # Check if this is a chapter header
                    chapter_num = extract_chapter_number(line_info['text'])
                    if chapter_num:
                        chapters_found.add(chapter_num)
                        # For sneak peek PDFs, be more lenient with chapter limits
                        # since they may have sample content from later chapters
                        if not is_sneak_peek and chapter_num > max_chapters:
                            print(f"  - Reached chapter {chapter_num}, stopping at {max_chapters} chapters")
                            break
                    
                    # Save previous section if it exists and has substantial content
                    if current_section and len(current_section['content']) > 300:
                        cleaned_content = clean_text(current_section['content'])
                        if len(cleaned_content) > 300:
                            content_type = detect_content_type(cleaned_content, current_section['title'])
                            code_blocks = extract_code_blocks(cleaned_content)
                            
                            item = {
                                "title": current_section['title'],
                                "content": cleaned_content,
                                "content_type": content_type,
                                "source_url": f"file://{os.path.abspath(pdf_path)}",
                                "author": ", ".join(authors),
                                "user_id": "",
                                "page_start": current_section['start_page'],
                                "page_end": line_info['page']
                            }
                            
                            if code_blocks:
                                item["code_blocks"] = code_blocks
                            
                            items.append(item)
                            substantial_content_sections += 1
                            print(f"    - Extracted: {current_section['title'][:50]}... ({len(cleaned_content)} chars, {content_type})")
                            
                            # For sneak peek PDFs, stop after getting enough substantial content
                            if is_sneak_peek and substantial_content_sections >= 10:
                                print(f"  - Sneak peek PDF: extracted {substantial_content_sections} substantial sections")
                                break
                    
                    # Start new section
                    current_section = {
                        'title': line_info['text'],
                        'content': '',
                        'start_page': line_info['page']
                    }
                else:
                    # Add content to current section
                    if current_section:
                        current_section['content'] += line_info['text'] + '\n'
            
            # Handle the final section
            if current_section and len(current_section['content']) > 300:
                cleaned_content = clean_text(current_section['content'])
                if len(cleaned_content) > 300:
                    content_type = detect_content_type(cleaned_content, current_section['title'])
                    code_blocks = extract_code_blocks(cleaned_content)
                    
                    item = {
                        "title": current_section['title'],
                        "content": cleaned_content,
                        "content_type": content_type,
                        "source_url": f"file://{os.path.abspath(pdf_path)}",
                        "author": ", ".join(authors),
                        "user_id": "",
                        "page_start": current_section['start_page'],
                        "page_end": len(pdf.pages)
                    }
                    
                    if code_blocks:
                        item["code_blocks"] = code_blocks
                    
                    items.append(item)
                    print(f"    - Extracted: {current_section['title'][:50]}... ({len(cleaned_content)} chars, {content_type})")
        
        pdf_type = "sneak peek" if is_sneak_peek else "regular"
        print(f"Successfully extracted {len(items)} content sections from the {pdf_type} PDF.")
        print(f"  - Chapters found: {sorted(chapters_found) if chapters_found else 'None detected'}")
        
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


def process_multiple_pdfs_threaded(pdf_paths: List[str], max_chapters: int = 8, max_workers: int = 4) -> List[Dict]:
    """
    Process multiple PDF files concurrently using ThreadPoolExecutor.
    
    Args:
        pdf_paths (List[str]): List of PDF file paths to process
        max_chapters (int): Maximum number of chapters to extract per PDF
        max_workers (int): Maximum number of concurrent threads
        
    Returns:
        List[Dict]: Combined list of extracted content from all PDFs
    """
    print(f"\nStarting multithreaded PDF processing with {max_workers} workers...")
    print(f"Processing {len(pdf_paths)} PDF files, limiting to first {max_chapters} chapters each")
    
    all_results = []
    
    # Filter existing files
    existing_files = [path for path in pdf_paths if os.path.exists(path)]
    missing_files = [path for path in pdf_paths if not os.path.exists(path)]
    
    if missing_files:
        print(f"Warning: {len(missing_files)} PDF files not found:")
        for path in missing_files:
            print(f"  - {path}")
    
    if not existing_files:
        print("No PDF files found to process.")
        return []
    
    # Process files concurrently
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_path = {
            executor.submit(process_book_chapters, pdf_path, max_chapters): pdf_path 
            for pdf_path in existing_files
        }
        
        # Collect results as they complete
        for future in as_completed(future_to_path):
            pdf_path = future_to_path[future]
            try:
                results = future.result()
                all_results.extend(results)
                print(f"✓ Completed processing: {os.path.basename(pdf_path)} ({len(results)} items)")
            except Exception as e:
                print(f"✗ Error processing {pdf_path}: {e}")
    
    print(f"\n{'='*80}")
    print(f"MULTITHREADED PROCESSING COMPLETE")
    print(f"Successfully processed {len(existing_files)} PDF files")
    print(f"Total extracted items: {len(all_results)}")
    print(f"{'='*80}")
    
    return all_results 