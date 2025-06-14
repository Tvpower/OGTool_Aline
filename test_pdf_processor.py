#!/usr/bin/env python3
"""
Test script to demonstrate the improved PDF processor capabilities.
"""

from pdf_processor import process_book_chapters
import json
import os

def test_pdf_processing():
    """Test the PDF processor with both BCTCI files."""
    
    pdf_files = [
        "/home/tvpower/PycharmProjects/OGTool_Aline/Books_PDF/Sneak Peak BCTCI - Sliding Windows & Binary Search.pdf",
        "/home/tvpower/PycharmProjects/OGTool_Aline/Books_PDF/Sneak Peek BCTCI - First 7 Chapters - What's Broken About Coding Interviews, What Recruiters Won't Tell You, How to Get In the Door, and more.pdf"
    ]
    
    all_results = []
    
    for pdf_path in pdf_files:
        if os.path.exists(pdf_path):
            print(f"\n{'='*80}")
            print(f"Processing: {os.path.basename(pdf_path)}")
            print(f"{'='*80}")
            
            results = process_book_chapters(pdf_path)
            all_results.extend(results)
            
            # Show detailed breakdown
            content_types = {}
            for item in results:
                content_type = item['content_type']
                content_types[content_type] = content_types.get(content_type, 0) + 1
            
            print(f"\nContent breakdown:")
            for content_type, count in content_types.items():
                print(f"  - {content_type}: {count} items")
            
            # Show sample content for each type
            for content_type in content_types:
                sample = next((item for item in results if item['content_type'] == content_type), None)
                if sample:
                    print(f"\nSample {content_type} content:")
                    print(f"  Title: {sample['title']}")
                    print(f"  Length: {len(sample['content'])} characters")
                    print(f"  Preview: {sample['content'][:200]}...")
                    
                    if 'code_blocks' in sample and sample['code_blocks']:
                        print(f"  Code blocks: {len(sample['code_blocks'])}")
                        for i, block in enumerate(sample['code_blocks'][:1]):
                            print(f"    Block {i+1}: {block['code'][:100]}...")
        else:
            print(f"PDF not found: {pdf_path}")
    
    print(f"\n{'='*80}")
    print(f"SUMMARY: Successfully extracted {len(all_results)} content items total")
    print(f"{'='*80}")
    
    # Overall content type distribution
    overall_types = {}
    for item in all_results:
        content_type = item['content_type']
        overall_types[content_type] = overall_types.get(content_type, 0) + 1
    
    print("\nOverall content distribution:")
    for content_type, count in sorted(overall_types.items()):
        print(f"  - {content_type}: {count} items")
    
    # Find items with the most substantial content
    substantial_items = sorted([item for item in all_results if len(item['content']) > 2000], 
                              key=lambda x: len(x['content']), reverse=True)
    
    print(f"\nMost substantial content items (>2000 chars):")
    for i, item in enumerate(substantial_items[:5]):
        print(f"  {i+1}. {item['title'][:60]}... ({len(item['content'])} chars, {item['content_type']})")
    
    return all_results

if __name__ == "__main__":
    results = test_pdf_processing()