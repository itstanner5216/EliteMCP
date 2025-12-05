#!/usr/bin/env python3
"""
Directory Intelligence Tool
A .gitignore-aware directory structure analyzer that generates XML hierarchies
with intelligent summarization for large directories.

Warning Taxonomy:
- unreadable_file: File cannot be opened or read due to permissions or I/O errors
- unreadable_directory: Directory cannot be accessed due to permissions or I/O errors
- malformed_gitignore: .gitignore file was read successfully but contains invalid patterns
- broken_symlink: Symbolic link cannot be resolved to a valid target
- symlink_loop: Circular symlink reference detected
- too_many_warnings: Warning count exceeded threshold, additional warnings appended
"""

import os
import sys
import pathspec
from pathlib import Path
from typing import Set, List, Tuple, Dict, Any
import xml.etree.ElementTree as ET
from xml.dom import minidom
from fastmcp import FastMCP
import logging

logger = logging.getLogger(__name__)


IGNORE_TOPLEVEL_DOTDIRS = True


MAX_FILE_COUNT = 50


class DirectoryIntelligenceTool:
    """Main class for directory structure analysis and XML generation."""

    def __init__(self, root_path: str = "."):
        """Initialize the tool with a root path."""
        self.root_path = Path(root_path).resolve()
        self.visited_symlinks = set()
        self.warnings = []
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from environment or config file."""
        config = {
            'max_file_count': MAX_FILE_COUNT,
            'expand_large': False,
        }

        # Try to load from environment variables
        import os
        max_files_str = os.environ.get('DIRECTORY_TOOL_MAX_FILES')
        if max_files_str:
            try:
                config['max_file_count'] = int(max_files_str)
            except ValueError:
                pass

        expand_large_str = os.environ.get('DIRECTORY_TOOL_EXPAND_LARGE')
        if expand_large_str:
            config['expand_large'] = expand_large_str.lower() in ('true', '1', 'yes')

        return config

    def _sanitize_xml_name(self, name: str) -> str:
        """Sanitize a name for safe use as XML attribute value."""
        # Intentionally restricts filenames/directories to alnum + ._- to guarantee XML attribute safety.
        # Nonconforming names become "unnamed" due to strictness.
        # If name is already valid, return it
        if name and all(c.isalnum() or c in ('.', '_', '-') for c in name):
            return name
        # Otherwise, use a safe placeholder
        return "unnamed"

    def _should_ignore(self, path: Path, ignore_spec: pathspec.PathSpec,
                       depth: int) -> bool:
        """Determine if a path should be ignored based on all rules."""
        # Check gitignore patterns
        if self.should_ignore_path(path, ignore_spec):
            return True

        # Check top-level dot directories
        if IGNORE_TOPLEVEL_DOTDIRS and depth == 1 and path.is_dir() and path.name.startswith('.'):
            return True

        return False

    def load_gitignore_patterns(self, directory: Path) -> pathspec.PathSpec:
        """Load .gitignore patterns from a directory."""
        # Check if directory is readable
        try:
            if not os.access(directory, os.R_OK):
                self.warnings.append(f"unreadable_directory: {directory} - Permission denied")
        except Exception as e:
            self.warnings.append(f"unreadable_directory: {directory} - {str(e)}")

        gitignore_path = directory / ".gitignore"
        patterns = []

        # Note: An unreadable .gitignore (I/O or permission failure) is classified under
        # the "unreadable file" category. A syntactically valid but unparsable pattern set
        # triggers the "malformed ignore file" category during pattern parsing.
        if gitignore_path.exists() and gitignore_path.is_file():
            try:
                with open(gitignore_path, 'r', encoding='utf-8') as f:
                    patterns = f.read().splitlines()
            except Exception as e:
                self.warnings.append(f"unreadable_file: {gitignore_path} - Permission denied or I/O error: {str(e)}")

        # Add default patterns to ignore common build/venv directories
        default_patterns = [
            ".git",
            ".vscode",
            ".idea",
            "__pycache__",
            "*.pyc",
            "*.pyo",
            "*.pyd",
            ".pytest_cache",
            ".coverage",
            "htmlcov",
            ".tox",
            ".venv",
            "venv",
            "env",
            "ENV",
            "node_modules",
            ".DS_Store",
            "Thumbs.db",
            "*.egg-info",
            "dist",
            "build",
            "*.so",
            "*.dylib",
            "*.dll"
        ]

        patterns.extend(default_patterns)
        try:
            return pathspec.PathSpec.from_lines("gitwildmatch", patterns)
        except Exception as e:
            self.warnings.append(f"malformed_gitignore: {directory} — failed to parse .gitignore: {str(e)}")
            return pathspec.PathSpec.from_lines("gitwildmatch", [])
    
    def should_ignore_path(self, path: Path, ignore_spec: pathspec.PathSpec) -> bool:
        """Check if a path should be ignored based on gitignore patterns."""
        relative_path = path.relative_to(self.root_path)
        return ignore_spec.match_file(str(relative_path))
    
    def count_directory_files(self, directory: Path, ignore_spec: pathspec.PathSpec,
                              depth: int = 0) -> int:
        """Count total files in a directory (recursively)."""
        count = 0
        try:
            for item in directory.iterdir():
                if self._should_ignore(item, ignore_spec, depth):
                    logger.debug(f"Skipping ignored path: {item}")
                    continue
                if item.is_file():
                    count += 1
                elif item.is_dir():
                    count += self.count_directory_files(item, ignore_spec, depth + 1)
        except PermissionError:
            self.warnings.append(f"unreadable_directory: {directory} - Permission denied")
        except Exception as e:
            self.warnings.append(f"unreadable_directory: {directory} - {str(e)}")
        return count
    
    def scan_directory(self, directory: Path, ignore_spec: pathspec.PathSpec,
                      expand_large: bool = False, depth: int = 0) -> ET.Element:
        """Scan a directory and create XML structure."""
        dir_element = ET.Element("dir")
        dir_name = self._sanitize_xml_name(directory.name)
        dir_element.set("name", dir_name)

        try:
            items = list(directory.iterdir())
            items.sort(key=lambda x: (x.is_file(), x.name.lower()))

            # Count files for summarization
            max_file_count = self.config.get('max_file_count', MAX_FILE_COUNT)
            if not expand_large and depth > 0:  # Only summarize subdirectories
                total_files = self.count_directory_files(directory, ignore_spec, depth)
                if total_files > max_file_count:
                    logger.debug(f"Directory {directory} has {total_files} files (threshold: {max_file_count}), adding summary")
                    summary = ET.Element("summary")
                    summary.set("count", str(total_files))
                    dir_element.append(summary)
                    return dir_element

            # Process items in directory
            for item in items:
                # Check for symlink loops
                if item.is_symlink():
                    try:
                        target = item.resolve()
                        if target in self.visited_symlinks:
                            self.warnings.append(f"symlink_loop: {item} -> {target}")
                            continue
                        self.visited_symlinks.add(target)
                    except Exception as e:
                        self.warnings.append(f"broken_symlink: {item} - {str(e)}")
                        continue

                # Skip ignored paths using consolidated logic
                if self._should_ignore(item, ignore_spec, depth):
                    logger.debug(f"Skipping ignored path: {item}")
                    continue

                # Process files
                if item.is_file():
                    try:
                        # Try to check if file is readable
                        if not os.access(item, os.R_OK):
                            self.warnings.append(f"unreadable_file: {item} - Permission denied")
                            continue
                    except Exception as e:
                        self.warnings.append(f"unreadable_file: {item} - {str(e)}")
                        continue

                    file_element = ET.Element("file")
                    safe_name = self._sanitize_xml_name(item.name)
                    file_element.text = safe_name
                    dir_element.append(file_element)

                # Process subdirectories recursively
                elif item.is_dir():
                    try:
                        subdir_element = self.scan_directory(item, ignore_spec, expand_large, depth + 1)
                        dir_element.append(subdir_element)
                    except PermissionError:
                        self.warnings.append(f"unreadable_directory: {item} - Permission denied")
                    except Exception as e:
                        self.warnings.append(f"unreadable_directory: {item} - {str(e)}")

        except PermissionError:
            self.warnings.append(f"unreadable_directory: {directory} - Permission denied")
        except Exception as e:
            self.warnings.append(f"unreadable_directory: {directory} - {str(e)}")

        return dir_element
    
    def generate_xml_structure(self, expand_large: bool = None) -> str:
        """Generate complete XML structure of the directory."""
        self.warnings = []
        self.visited_symlinks = set()

        # Use config default if expand_large not explicitly provided
        if expand_large is None:
            expand_large = self.config.get('expand_large', False)

        # Create root element
        root = ET.Element("project_structure")

        # Load gitignore patterns
        ignore_spec = self.load_gitignore_patterns(self.root_path)

        # Scan directory
        structure = self.scan_directory(self.root_path, ignore_spec, expand_large)
        root.append(structure)

        # Add warnings if any
        if self.warnings:
            # Check if too many warnings
            # Over-100 warnings are not truncated. Instead, a final warning
            # "too_many_warnings: truncated" is appended. This behavior matches
            # the test suite's expectations.
            if len(self.warnings) > 100:
                self.warnings.append("too_many_warnings: truncated")

            warnings_element = ET.Element("warnings")
            for warning in self.warnings:
                warning_element = ET.Element("warning")
                warning_element.text = warning
                warnings_element.append(warning_element)
            root.append(warnings_element)
        
        # Convert to pretty XML
        xml_str = ET.tostring(root, encoding='unicode')
        dom = minidom.parseString(xml_str)
        return dom.toprettyxml(indent="  ")


# Initialize FastMCP
mcp = FastMCP("Directory Intelligence Tool")

# Note: MCP passes an explicit boolean for expand_large.
# Therefore environment/config defaults do not affect calls from MCP unless the wrapper is changed.
@mcp.tool()
def get_codebase_structure(root_path: str = ".", expand_large: bool = False) -> str:
    """
    Analyze directory structure and generate XML representation.
    
    Args:
        root_path: Root directory path to analyze (default: current directory)
        expand_large: If True, always expand directories regardless of file count
    
    Returns:
        XML string representing the directory structure
    """
    try:
        tool = DirectoryIntelligenceTool(root_path)
        return tool.generate_xml_structure(expand_large)
    except Exception as e:
        error_xml = f"""<?xml version="1.0" ?>
<project_structure>
  <error>{str(e)}</error>
</project_structure>"""
        return error_xml


def main():
    """Main function for command-line usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Directory Intelligence Tool")
    parser.add_argument("path", nargs="?", default=".", help="Directory path to analyze")
    parser.add_argument("--expand-large", action="store_true", 
                       help="Expand all directories regardless of file count")
    parser.add_argument("--output", "-o", help="Output file path (default: stdout)")
    
    args = parser.parse_args()
    
    try:
        tool = DirectoryIntelligenceTool(args.path)
        xml_output = tool.generate_xml_structure(args.expand_large)
        
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(xml_output)
            print(f"XML structure saved to: {args.output}")
        else:
            print(xml_output)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()