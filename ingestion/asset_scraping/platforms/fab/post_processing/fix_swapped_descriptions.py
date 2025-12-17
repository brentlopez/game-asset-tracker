#!/usr/bin/env python3
"""
Fix entries where raw_description contains markdown and description is blank.
This happens when the conversion script was run multiple times.
"""
import json
import sys
from pathlib import Path


def fix_metadata_file(input_file: Path, output_file: Path = None) -> None:
    """
    Fix swapped descriptions in metadata file
    
    Args:
        input_file: Path to input JSON file
        output_file: Path to output JSON file (defaults to input_file if None)
    """
    print(f"Loading {input_file}...")
    
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if not isinstance(data, list):
        raise ValueError("Expected JSON file to contain a list of entries")
    
    total = len(data)
    fixed = 0
    
    print(f"Analyzing {total} entries...")
    
    for entry in data:
        raw_description = entry.get('raw_description', '')
        description = entry.get('description', '')
        
        # If raw_description has content but description is blank
        if raw_description and not description:
            # Swap them back
            entry['description'] = raw_description
            entry['raw_description'] = ''
            fixed += 1
    
    print(f"Fixed {fixed} entries")
    
    # Write output
    output_path = output_file or input_file
    print(f"Writing to {output_path}...")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"Done! Fixed {fixed}/{total} entries")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Fix swapped descriptions in fab_metadata.json'
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
    
    args = parser.parse_args()
    
    if not args.input_file.exists():
        print(f"Error: Input file not found: {args.input_file}", file=sys.stderr)
        sys.exit(1)
    
    try:
        fix_metadata_file(args.input_file, args.output)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
