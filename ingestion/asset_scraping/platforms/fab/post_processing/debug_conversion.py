#!/usr/bin/env python3
"""
Debug script to diagnose HTML to Markdown conversion issues
"""
import json
import sys
from pathlib import Path
from convert_html_to_markdown import html_to_markdown

def analyze_conversions(input_file: Path, sample_count: int = 10):
    """Analyze conversion results for diagnostics"""
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"Total entries: {len(data)}\n")
    
    # Count issues
    empty_descriptions = 0
    blank_after_conversion = 0
    successful_conversions = 0
    
    # Track samples
    blank_samples = []
    
    for i, entry in enumerate(data):
        description = entry.get('description', '')
        raw_description = entry.get('raw_description', '')
        
        # Check if entry has already been converted
        if raw_description and not description:
            # This is the problem state: raw has content, description is blank
            blank_after_conversion += 1
            if len(blank_samples) < sample_count:
                blank_samples.append({
                    'index': i,
                    'title': entry.get('title', 'N/A'),
                    'raw_len': len(raw_description),
                    'desc_len': len(description)
                })
        elif description and not raw_description:
            # Original state or successful conversion
            # Try converting to see if it would produce blank output
            markdown = html_to_markdown(description)
            if not markdown.strip():
                if len(blank_samples) < sample_count:
                    blank_samples.append({
                        'index': i,
                        'title': entry.get('title', 'N/A'),
                        'html_preview': description[:200],
                        'would_be_blank': True
                    })
            successful_conversions += 1
        elif not description and not raw_description:
            empty_descriptions += 1
        else:
            successful_conversions += 1
    
    print(f"Statistics:")
    print(f"  Empty descriptions (before conversion): {empty_descriptions}")
    print(f"  Blank after conversion: {blank_after_conversion}")
    print(f"  Successful conversions: {successful_conversions}")
    
    if blank_samples:
        print(f"\n\nSample problematic entries:")
        for sample in blank_samples:
            print(f"\n  Entry #{sample['index']}:")
            print(f"    Title: {sample['title']}")
            if 'would_be_blank' in sample:
                print(f"    HTML preview: {sample['html_preview']}")
                print(f"    Would convert to blank!")
            else:
                print(f"    Raw description length: {sample['raw_len']}")
                print(f"    Description length: {sample['desc_len']}")
    
    # Test conversion on a sample
    if blank_samples and 'html_preview' in blank_samples[0]:
        print(f"\n\nTesting conversion on first problematic entry:")
        test_html = data[blank_samples[0]['index']]['description']
        print(f"\nOriginal HTML (first 500 chars):")
        print(test_html[:500])
        print(f"\n\nConverted Markdown:")
        markdown = html_to_markdown(test_html)
        print(f"'{markdown}'")
        print(f"\nMarkdown length: {len(markdown)}")

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Debug HTML to Markdown conversion issues')
    parser.add_argument('input_file', type=Path, help='JSON file to analyze')
    parser.add_argument('-n', '--samples', type=int, default=10, help='Number of samples to show')
    
    args = parser.parse_args()
    
    if not args.input_file.exists():
        print(f"Error: File not found: {args.input_file}", file=sys.stderr)
        sys.exit(1)
    
    analyze_conversions(args.input_file, args.samples)
