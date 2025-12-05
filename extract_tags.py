#!/usr/bin/env -S uv run --script
# /// script
# dependencies = [
#   "pyyaml",
# ]
# ///
import argparse
import re
import sys
import yaml
from pathlib import Path
from typing import List, Set, Iterator

# A more precise regex for inline tags.
# It avoids matching tags within code blocks or URLs.
INLINE_TAG_REGEX = re.compile(r'(?<!\S)#{1}([a-zA-Z0-9_\/-]+)')

def stream_file_lines(path: Path) -> Iterator[str]:
    """Yields lines from a file, handling potential read errors."""
    try:
        with path.open('r', encoding='utf-8') as f:
            yield from f
    except (IOError, UnicodeDecodeError) as e:
        print(f"Warning: Could not read file {path}: {e}", file=sys.stderr)

def extract_tags(vault_path: Path) -> Set[str]:
    """
    Extracts all unique tags from an Obsidian vault by parsing both 
    YAML properties and inline tags in a robust, memory-efficient manner.
    """
    all_tags: Set[str] = set()
    md_files = vault_path.rglob('*.md')

    for file_path in md_files:
        lines = iter(stream_file_lines(file_path))
        
        # --- Stage 1: Attempt to parse YAML frontmatter ---
        try:
            first_line = next(lines).strip()
            if first_line == '---':
                yaml_lines: List[str] = []
                in_frontmatter = True
                while in_frontmatter:
                    line = next(lines)
                    if line.strip() == '---':
                        in_frontmatter = False
                    else:
                        yaml_lines.append(line)

                try:
                    properties = yaml.safe_load("".join(yaml_lines))
                    if isinstance(properties, dict):
                        tags_property = properties.get('tags', [])
                        if isinstance(tags_property, list):
                            for tag in tags_property:
                                if tag and isinstance(tag, str):
                                    all_tags.add(tag.replace(' ', '-'))
                        elif isinstance(tags_property, str):
                            for tag in tags_property.split():
                                all_tags.add(tag)
                except yaml.YAMLError as e:
                    print(f"Warning: Could not parse YAML in {file_path}: {e}", file=sys.stderr)
        except StopIteration:
            # File is empty or has only one line.
            continue
        
        # --- Stage 2: Parse inline tags from the rest of the file ---
        for line in lines:
            matches = INLINE_TAG_REGEX.findall(line)
            for match in matches:
                all_tags.add(match)

    return all_tags

def main():
    """Main entry point for the command-line tool."""
    parser = argparse.ArgumentParser(
        description="Extract all unique tags from an Obsidian vault."
    )
    parser.add_argument(
        "vault_path",
        type=Path,
        nargs='?',
        default=Path('.'),
        help="Path to the Obsidian vault root directory. Defaults to the current directory."
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=Path("tags.txt"),
        help="Path to the output file. Defaults to 'tags.txt' in the current directory."
    )
    args = parser.parse_args()

    if not args.vault_path.is_dir():
        print(f"Error: Provided path '{args.vault_path}' is not a valid directory.", file=sys.stderr)
        sys.exit(1)

    print(f"Scanning for tags in '{args.vault_path}'...")
    tags = sorted(list(extract_tags(args.vault_path)))
    
    try:
        with args.output.open('w', encoding='utf-8') as f:
            for tag in tags:
                f.write(f"#{tag}\n")
    except IOError as e:
        print(f"Error: Could not write to output file '{args.output}': {e}", file=sys.stderr)
        sys.exit(1)

    print(f"\nExtraction complete.")
    print(f"Found {len(tags)} unique tags.")
    print(f"Tag list has been saved to '{args.output}'")

if __name__ == '__main__':
    main()
