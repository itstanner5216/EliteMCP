#!/usr/bin/env python3
"""
Directory Intelligence Tool
A .gitignore-aware directory structure analyzer that generates XML hierarchies
with intelligent summarization for large directories.
"""

import os
import sys
import pathspec
from pathlib import Path
from typing import Set, List, Tuple, Dict, Any
import xml.etree.ElementTree as ET
from xml.dom import minidom
from fastmcp import FastMCP


class DirectoryIntelligenceTool:
    """Main class for directory structure analysis and XML generation."""
    
    def __init__(self, root_path: str = "."):
        """Initialize the tool with a root path."""
        self.root_path = Path(root_path).resolve()
        self.visited_symlinks = set()
        self.warnings = []
        
    def load_gitignore_patterns(self, directory: Path) -> pathspec.PathSpec:
        """Load .gitignore patterns from a directory."""
        gitignore_path = directory / ".gitignore"
        patterns = []
        
        if gitignore_path.exists() and gitignore_path.is_file():
            try:
                with open(gitignore_path, 'r', encoding='utf-8') as f:
                    patterns = f.read().splitlines()
            except Exception as e:
                self.warnings.append(f"malformed_gitignore: {gitignore_path} - {str(e)}")
        
        # Add default patterns to ignore common build/venv directories
        default_patterns = [
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
        return pathspec.PathSpec.from_lines("gitwildmatch", patterns)
    
    def should_ignore_path(self, path: Path, ignore_spec: pathspec.PathSpec) -> bool:
        """Check if a path should be ignored based on gitignore patterns."""
        relative_path = path.relative_to(self.root_path)
        return ignore_spec.match_file(str(relative_path))
    
    def count_directory_files(self, directory: Path, ignore_spec: pathspec.PathSpec) -> int:
        """Count total files in a directory (recursively)."""
        count = 0
        try:
            for item in directory.iterdir():
                if item.is_file() and not self.should_ignore_path(item, ignore_spec):
                    count += 1
                elif item.is_dir() and not self.should_ignore_path(item, ignore_spec):
                    count += self.count_directory_files(item, ignore_spec)
        except PermissionError:
            self.warnings.append(f"unreadable: {directory}")
        except Exception as e:
            self.warnings.append(f"error_accessing: {directory} - {str(e)}")
        return count
    
    def scan_directory(self, directory: Path, ignore_spec: pathspec.PathSpec, 
                      expand_large: bool = False, depth: int = 0) -> ET.Element:
        """Scan a directory and create XML structure."""
        dir_element = ET.Element("dir")
        dir_element.set("name", directory.name)
        
        try:
            items = list(directory.iterdir())
            items.sort(key=lambda x: (x.is_file(), x.name.lower()))
            
            # Count files for summarization
            if not expand_large and depth > 0:  # Only summarize subdirectories
                total_files = self.count_directory_files(directory, ignore_spec)
                if total_files > 50:
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
                
                # Skip ignored paths
                if self.should_ignore_path(item, ignore_spec):
                    continue
                
                # Process files
                if item.is_file():
                    file_element = ET.Element("file")
                    file_element.text = item.name
                    dir_element.append(file_element)
                
                # Process subdirectories recursively
                elif item.is_dir():
                    try:
                        subdir_element = self.scan_directory(item, ignore_spec, expand_large, depth + 1)
                        dir_element.append(subdir_element)
                    except PermissionError:
                        self.warnings.append(f"unreadable: {item}")
                    except Exception as e:
                        self.warnings.append(f"error_processing: {item} - {str(e)}")
        
        except PermissionError:
            self.warnings.append(f"unreadable: {directory}")
        except Exception as e:
            self.warnings.append(f"error_accessing: {directory} - {str(e)}")
        
        return dir_element
    
    def generate_xml_structure(self, expand_large: bool = False) -> str:
        """Generate complete XML structure of the directory."""
        self.warnings = []
        self.visited_symlinks = set()
        
        # Create root element
        root = ET.Element("project_structure")
        
        # Load gitignore patterns
        ignore_spec = self.load_gitignore_patterns(self.root_path)
        
        # Scan directory
        structure = self.scan_directory(self.root_path, ignore_spec, expand_large)
        root.append(structure)
        
        # Add warnings if any
        if self.warnings:
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