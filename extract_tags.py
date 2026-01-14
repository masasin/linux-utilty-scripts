#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.13"
# dependencies = [
#   "pyyaml",
# ]
# ///
import argparse
import re
import sys
from pathlib import Path
from typing import Any, Iterator

import yaml

# A more precise regex for inline tags.
# It avoids matching tags within code blocks or URLs.
INLINE_TAG_REGEX = re.compile(r"(?<!\S)#{1}([a-zA-Z0-9_\/-]+)")


class TagNode:
    """Represents a node in the tag hierarchy tree."""

    def __init__(self, name: str, full_name: str):
        self.name = name
        self.full_name = full_name
        self.count = 0  # Occurrences of this exact tag
        self.files: set[str] = set()
        self.children: dict[str, "TagNode"] = {}
        self.total_count = 0  # Occurrences of this tag + all children


def stream_file_lines(path: Path) -> Iterator[str]:
    """Yields lines from a file, handling potential read errors."""
    try:
        with path.open("r", encoding="utf-8") as f:
            yield from f
    except (IOError, UnicodeDecodeError) as e:
        print(f"Warning: Could not read file {path}: {e}", file=sys.stderr)


def extract_tags(vault_path: Path) -> dict[str, dict[str, Any]]:
    """
    Extracts tags, counting occurrences and tracking files.
    Returns: {tag_name: {'count': int, 'files': set(filepaths)}}
    """
    tag_data: dict[str, dict[str, Any]] = {}
    md_files = vault_path.rglob("*.md")

    for file_path in md_files:
        file_path_str = str(file_path.relative_to(vault_path))
        lines = iter(stream_file_lines(file_path))
        in_code_block = False

        # --- Stage 1: Attempt to parse YAML frontmatter ---
        try:
            first_line = next(lines).strip()
            if first_line == "---":
                yaml_lines: list[str] = []
                in_frontmatter = True
                while in_frontmatter:
                    line = next(lines)
                    if line.strip() == "---":
                        in_frontmatter = False
                    else:
                        yaml_lines.append(line)

                try:
                    properties = yaml.safe_load("".join(yaml_lines))
                    if isinstance(properties, dict):
                        tags_property = properties.get("tags", [])

                        # Normalize to list of strings
                        tags_found = []
                        if isinstance(tags_property, list):
                            tags_found = [
                                t for t in tags_property if t and isinstance(t, str)
                            ]
                        elif isinstance(tags_property, str):
                            tags_found = tags_property.split()

                        for tag in tags_found:
                            clean_tag = tag.replace(" ", "-")
                            if clean_tag not in tag_data:
                                tag_data[clean_tag] = {"count": 0, "files": set()}
                            tag_data[clean_tag]["count"] += 1
                            tag_data[clean_tag]["files"].add(file_path_str)

                except yaml.YAMLError as e:
                    print(
                        f"Warning: Could not parse YAML in {file_path}: {e}",
                        file=sys.stderr,
                    )
        except StopIteration:
            continue

        # --- Stage 2: Parse inline tags from the rest of the file ---
        for line in lines:
            # Check for code block fence
            if line.strip().startswith("```"):
                in_code_block = not in_code_block
                continue

            # Skip lines inside code blocks
            if in_code_block:
                continue
                
            matches = INLINE_TAG_REGEX.findall(line)
            for match in matches:
                # Skip top-level, purely numeric tags
                if "/" not in match and match.isdigit():
                    continue
                    
                if match not in tag_data:
                    tag_data[match] = {"count": 0, "files": set()}
                tag_data[match]["count"] += 1
                tag_data[match]["files"].add(file_path_str)

    return tag_data


def build_tag_tree(tag_data: dict[str, dict[str, Any]]) -> TagNode:
    """Builds a hierarchy tree from flat tag data and calculates group totals."""
    root = TagNode("", "")

    # Insert all tags into the tree
    for tag, data in tag_data.items():
        parts = tag.split("/")
        current = root
        for i, part in enumerate(parts):
            if part not in current.children:
                full_name = "/".join(parts[: i + 1])
                current.children[part] = TagNode(part, full_name)
            current = current.children[part]

        # Set data on the leaf (which corresponds to the full tag)
        current.count = data["count"]
        current.files = data["files"]

    # Recursively calculate total counts (self + descendants)
    def calc_totals(node: TagNode) -> int:
        total = node.count
        for child in node.children.values():
            total += calc_totals(child)
        node.total_count = total
        return total

    calc_totals(root)
    return root


def write_tag_tree(node: TagNode, f, indent_level: int = 0):
    """
    Recursively writes the tag tree to the file using indented lists.
    """
    # Sort children by total_count descending
    sorted_children = sorted(
        node.children.values(), key=lambda x: x.total_count, reverse=True
    )

    # We do not print the dummy root node (which has no name)
    # The children of the root are the top-level tags (indent 0)
    if node.name:
        remainder = node.total_count - node.count
        indent = "    " * indent_level
        # Output: - **Tag** (Total, Self, Remainder)
        f.write(
            f"{indent}- **{node.name}** ({node.total_count}, {node.count}, {remainder})\n"
        )

        # Write files associated with this specific tag node
        # These are indented one level deeper than the tag itself
        file_indent = "    " * (indent_level + 1)
        for file_path in sorted(node.files):
            f.write(f"{file_indent}- `{file_path}`\n")

    # Determine indentation for children
    # If this is root, its children are top-level (indent 0).
    # If this is a normal node, its children are indented one level deeper (indent + 1).
    next_level = indent_level + 1 if node.name else 0

    for child in sorted_children:
        write_tag_tree(child, f, next_level)


def main():
    """Main entry point for the command-line tool."""
    parser = argparse.ArgumentParser(
        description="Extract all unique tags from an Obsidian vault."
    )
    parser.add_argument(
        "vault_path",
        type=Path,
        nargs="?",
        default=Path("."),
        help="Path to the Obsidian vault root directory. Defaults to the current directory.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("tags.md"),
        help="Path to the output file. Defaults to 'tags.md' in the current directory.",
    )
    args = parser.parse_args()

    if not args.vault_path.is_dir():
        print(
            f"Error: Provided path '{args.vault_path}' is not a valid directory.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Scanning for tags in '{args.vault_path}'...")

    # 1. Extract raw data
    tag_data = extract_tags(args.vault_path)

    # 2. Build Hierarchy
    root = build_tag_tree(tag_data)

    # 3. Write Recursive Tree
    try:
        with args.output.open("w", encoding="utf-8") as f:
            write_tag_tree(root, f)
    except IOError as e:
        print(
            f"Error: Could not write to output file '{args.output}': {e}",
            file=sys.stderr,
        )
        sys.exit(1)

    print("\nExtraction complete.")
    print(f"Found {len(tag_data)} unique tags.")
    print(f"Tag list has been saved to '{args.output}'")


if __name__ == "__main__":
    main()
