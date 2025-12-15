#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTML to Markdown Converter for Fab Metadata

Converts HTML descriptions in fab_metadata.json to Markdown format:
- Moves original HTML to 'raw_description' field
- Replaces 'description' field with cleaned Markdown
- Uses parallel processing for speed
"""
import json
import sys
import re
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Dict, List, Optional
from html.parser import HTMLParser
from bs4 import BeautifulSoup, Comment


class HTMLToMarkdownConverter(HTMLParser):
    """Convert HTML to clean Markdown format"""
    
    def __init__(self):
        super().__init__()
        self.markdown = []
        self.current_tag = None
        self.tag_stack = []
        self.list_stack = []
        self.in_link = False
        self.link_text = ""
        self.link_href = ""
        self.suppress_output = False
        
    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        
        # Skip navigation/UI elements (but allow divs)
        if tag in ['button', 'nav', 'section']:
            self.suppress_output = True
            return
        
        # Skip specific UI framework classes but allow divs with content
        class_str = attrs_dict.get('class', '')
        if class_str and any(skip in class_str for skip in ['fabkit-Button', 'fabkit-Tab', 'fabkit-Blades', 'fabkit-Badge', 'fabkit-Thumbnail']):
            self.suppress_output = True
            return
            
        self.tag_stack.append(tag)
        
        if tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            level = int(tag[1])
            self.markdown.append('\n' + '#' * level + ' ')
            self.current_tag = tag
        elif tag == 'p':
            if self.markdown and self.markdown[-1] != '\n':
                self.markdown.append('\n')
            self.current_tag = 'p'
        elif tag == 'strong' or tag == 'b':
            self.markdown.append('**')
        elif tag == 'em' or tag == 'i':
            self.markdown.append('*')
        elif tag == 'ul':
            self.list_stack.append('ul')
            if self.markdown and self.markdown[-1] != '\n':
                self.markdown.append('\n')
        elif tag == 'ol':
            self.list_stack.append('ol')
            if self.markdown and self.markdown[-1] != '\n':
                self.markdown.append('\n')
        elif tag == 'li':
            if self.list_stack:
                list_type = self.list_stack[-1]
                indent = '  ' * (len(self.list_stack) - 1)
                if list_type == 'ul':
                    self.markdown.append(f'{indent}- ')
                else:
                    # For ordered lists, just use 1. for simplicity
                    self.markdown.append(f'{indent}1. ')
        elif tag == 'a':
            self.in_link = True
            self.link_text = ""
            self.link_href = attrs_dict.get('href', '')
        elif tag == 'br':
            self.markdown.append('  \n')
        elif tag == 'code':
            self.markdown.append('`')
    
    def handle_endtag(self, tag):
        if self.suppress_output and tag in ['button', 'nav', 'section']:
            self.suppress_output = False
            return
        
        # Check if we should unsuppress for specific classes
        if self.suppress_output and len(self.tag_stack) > 0:
            # If the last tag matches, we might be exiting a suppressed region
            if self.tag_stack and self.tag_stack[-1] == tag:
                self.suppress_output = False
            
        if tag in self.tag_stack:
            self.tag_stack.pop()
        
        if tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            self.markdown.append('\n')
            self.current_tag = None
        elif tag == 'p':
            self.markdown.append('\n')
            self.current_tag = None
        elif tag == 'strong' or tag == 'b':
            self.markdown.append('**')
        elif tag == 'em' or tag == 'i':
            self.markdown.append('*')
        elif tag == 'ul' or tag == 'ol':
            if self.list_stack:
                self.list_stack.pop()
                if not self.list_stack:  # Exiting top-level list
                    self.markdown.append('\n')
        elif tag == 'li':
            self.markdown.append('\n')
        elif tag == 'a':
            if self.in_link:
                # Create markdown link
                if self.link_href:
                    self.markdown.append(f'[{self.link_text}]({self.link_href})')
                else:
                    self.markdown.append(self.link_text)
                self.in_link = False
                self.link_text = ""
                self.link_href = ""
        elif tag == 'code':
            self.markdown.append('`')
    
    def handle_data(self, data):
        if self.suppress_output:
            return
            
        # Clean up whitespace
        cleaned = data.strip()
        if not cleaned:
            return
        
        if self.in_link:
            self.link_text += cleaned
        else:
            # Add space before text if needed
            if self.markdown and self.markdown[-1] not in ['\n', ' ', '**', '*', '`', '- ', '. ']:
                if not self.markdown[-1].endswith(' '):
                    self.markdown.append(' ')
            self.markdown.append(cleaned)
    
    def get_markdown(self) -> str:
        """Get the final markdown output"""
        result = ''.join(self.markdown)
        
        # Clean up multiple newlines
        result = re.sub(r'\n{3,}', '\n\n', result)
        
        # Clean up spaces before newlines
        result = re.sub(r' +\n', '\n', result)
        
        # Clean up leading/trailing whitespace
        result = result.strip()
        
        return result


def html_to_markdown(html: str) -> str:
    """Convert HTML string to Markdown using BeautifulSoup"""
    if not html or not isinstance(html, str):
        return ""
    
    try:
        # Parse HTML
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove unwanted elements
        for element in soup.find_all(['button', 'nav', 'section', 'script', 'style']):
            element.decompose()
        
        # Remove elements with specific classes
        for element in soup.find_all(class_=lambda x: x and any(
            skip in x for skip in ['fabkit-Button', 'fabkit-Tab', 'fabkit-Blades', 
                                   'fabkit-Badge', 'fabkit-Thumbnail', 'fabkit-Icon',
                                   'fabkit-ScreenReaderOnly']
        )):
            element.decompose()
        
        # Convert to markdown-like text
        markdown_parts = []
        
        for element in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'ul', 'ol', 'li', 'a', 'strong', 'em', 'code']):
            if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                level = int(element.name[1])
                text = element.get_text(strip=True)
                if text:
                    markdown_parts.append(f"\n{'#' * level} {text}\n")
            elif element.name == 'p':
                text = _process_inline_elements(element)
                if text:
                    markdown_parts.append(f"\n{text}\n")
            elif element.name == 'ul':
                items = element.find_all('li', recursive=False)
                for item in items:
                    text = _process_inline_elements(item)
                    if text:
                        markdown_parts.append(f"- {text}\n")
            elif element.name == 'ol':
                items = element.find_all('li', recursive=False)
                for i, item in enumerate(items, 1):
                    text = _process_inline_elements(item)
                    if text:
                        markdown_parts.append(f"{i}. {text}\n")
        
        markdown = ''.join(markdown_parts)
        
        # Clean up
        markdown = re.sub(r'\n{3,}', '\n\n', markdown)  # Max 2 newlines
        markdown = re.sub(r' +', ' ', markdown)  # Multiple spaces to single
        markdown = markdown.strip()
        
        return markdown
    
    except Exception as e:
        print(f"Warning: HTML parsing error: {e}", file=sys.stderr)
        # Fallback: strip HTML tags
        return re.sub(r'<[^>]+>', '', html).strip()


def _process_inline_elements(element) -> str:
    """Process inline elements within a block element"""
    result = []
    
    for child in element.children:
        if isinstance(child, str):
            text = child.strip()
            if text:
                result.append(text)
        elif child.name == 'strong' or child.name == 'b':
            text = child.get_text(strip=True)
            if text:
                result.append(f"**{text}**")
        elif child.name == 'em' or child.name == 'i':
            text = child.get_text(strip=True)
            if text:
                result.append(f"*{text}*")
        elif child.name == 'code':
            text = child.get_text(strip=True)
            if text:
                result.append(f"`{text}`")
        elif child.name == 'a':
            text = child.get_text(strip=True)
            href = child.get('href', '')
            if text and href:
                result.append(f"[{text}]({href})")
            elif text:
                result.append(text)
        elif child.name == 'br':
            result.append('  ')
        else:
            # Recursively process other elements
            text = child.get_text(strip=True)
            if text:
                result.append(text)
    
    return ' '.join(result)


def convert_entry(entry: Dict) -> Dict:
    """Convert a single entry's description to markdown"""
    # Create a copy to avoid modifying the original
    converted = entry.copy()
    
    # Get the current description
    description = entry.get('description', '')
    
    if description:
        # Move original HTML to raw_description
        converted['raw_description'] = description
        
        # Convert to markdown
        markdown = html_to_markdown(description)
        converted['description'] = markdown
    else:
        # No description, keep it empty
        converted['raw_description'] = ''
        converted['description'] = ''
    
    return converted


def convert_metadata_file(
    input_file: Path,
    output_file: Optional[Path] = None,
    max_workers: int = 4,
    progress: bool = True
) -> None:
    """
    Convert all descriptions in a metadata file to markdown
    
    Args:
        input_file: Path to input JSON file
        output_file: Path to output JSON file (defaults to input_file if None)
        max_workers: Number of parallel workers
        progress: Show progress messages
    """
    # Load the data
    if progress:
        print(f"Loading {input_file}...", file=sys.stderr)
    
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if not isinstance(data, list):
        raise ValueError("Expected JSON file to contain a list of entries")
    
    total = len(data)
    if progress:
        print(f"Converting {total} entries using {max_workers} workers...", file=sys.stderr)
    
    # Process entries in parallel
    converted_entries = [None] * total  # Pre-allocate list to maintain order
    
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks with their original index
        future_to_index = {
            executor.submit(convert_entry, entry): i
            for i, entry in enumerate(data)
        }
        
        # Collect results as they complete
        completed = 0
        for future in as_completed(future_to_index):
            index = future_to_index[future]
            try:
                converted_entries[index] = future.result()
                completed += 1
                
                if progress and completed % 10 == 0:
                    print(f"Progress: {completed}/{total} ({100*completed//total}%)", file=sys.stderr)
            except Exception as e:
                print(f"Error converting entry {index}: {e}", file=sys.stderr)
                # Keep original entry on error
                converted_entries[index] = data[index]
    
    if progress:
        print(f"Completed: {completed}/{total} entries converted", file=sys.stderr)
    
    # Write output
    output_path = output_file or input_file
    if progress:
        print(f"Writing to {output_path}...", file=sys.stderr)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(converted_entries, f, indent=2, ensure_ascii=False)
    
    if progress:
        print(f"Done! Output written to {output_path}", file=sys.stderr)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Convert HTML descriptions to Markdown in fab_metadata.json'
    )
    parser.add_argument(
        'input_file',
        type=Path,
        help='Input JSON file path'
    )
    parser.add_argument(
        '-o', '--output',
        type=Path,
        help='Output JSON file path (defaults to overwriting input)'
    )
    parser.add_argument(
        '-w', '--workers',
        type=int,
        default=4,
        help='Number of parallel workers (default: 4)'
    )
    parser.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='Suppress progress messages'
    )
    
    args = parser.parse_args()
    
    if not args.input_file.exists():
        print(f"Error: Input file not found: {args.input_file}", file=sys.stderr)
        sys.exit(1)
    
    try:
        convert_metadata_file(
            args.input_file,
            args.output,
            args.workers,
            not args.quiet
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
