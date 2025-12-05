# Directory Intelligence Tool

A .gitignore-aware directory structure analyzer that generates XML hierarchies with intelligent summarization for large directories.

## Overview

The Directory Intelligence Tool provides a comprehensive solution for analyzing directory structures and generating structured XML output. It respects `.gitignore` patterns, handles edge cases gracefully, and provides intelligent summarization for large directories.

## Key Features

- **Git-aware**: Respects `.gitignore` patterns using the `pathspec` library
- **XML Output**: Generates structured XML with `<dir>`, `<file>`, and `<summary>` elements
- **Smart Summarization**: Automatically summarizes directories with more than 50 files
- **Robust Error Handling**: Gracefully handles unreadable files, broken symlinks, malformed .gitignore
- **Flexible Configuration**: Supports environment variables and config files
- **FastMCP Integration**: Available as a FastMCP tool for remote access
- **Symlink Loop Protection**: Detects and prevents infinite recursion from circular symlinks

## XML Structure

The Directory Intelligence Tool generates a structured XML hierarchy with specific element types and attributes.

### Schema Overview

```xml
<?xml version="1.0" ?>
<project_structure>
  <dir name="directory_name">
    <!-- Files are represented as text nodes -->
    <file>filename.py</file>
    <file>README.md</file>

    <!-- Subdirectories are recursively structured -->
    <dir name="subdirectory">
      <file>module.py</file>
    </dir>

    <!-- Large directories get summarized -->
    <dir name="large_directory">
      <summary count="127"/>
    </dir>
  </dir>

  <!-- Warnings are collected at the end -->
  <warnings>
    <warning>warning_message</warning>
  </warnings>
</project_structure>
```

### Element Reference

**`<project_structure>`** (root)
- Container for the entire directory analysis
- Always present as the root element

**`<dir name="...">`** (directory)
- Represents a directory in the hierarchy
- `name` attribute: Sanitized directory name (restricted to alphanumerics, dots, underscores, and hyphens)
- Contains child elements: `<file>`, `<dir>`, or `<summary>`

**`<file>`** (file)
- Represents a file within a directory
- Text content: Sanitized filename (see name restrictions above)
- No attributes

**`<summary count="..."/>`** (summarized directory)
- Replaces file listing when directory exceeds max_file_count threshold
- `count` attribute: Total number of files in the directory and its subdirectories
- Self-closing element with no children

**`<warnings>`** (warning container)
- Optional element present only when warnings occur
- Contains one or more `<warning>` elements
- Positioned at the end of the XML structure

**`<warning>`** (individual warning)
- Contains warning message text
- Follows the taxonomy format: `type: path - description`
- May appear more than 100 times (truncation notice is appended instead of truncating the list)

### Summary Element

When a directory contains more than the threshold number of files (default: 50), a `<summary>` element is generated instead of listing all files:

```xml
<dir name="large_directory">
  <summary count="127"/>
</dir>
```

This prevents XML bloat while still providing information about the directory contents.

**Summarization Behavior:**
- `max_file_count` controls the threshold (default: 50, configurable via environment or config)
- Only subdirectories (depth > 0) are summarized; the root directory is always fully expanded
- When `expand_large=True`, summarization is disabled and all files are listed

## Ignore Rules

The tool applies multiple layers of ignore rules in a deterministic order. Each layer is evaluated sequentially, and if a path matches any rule, it is ignored immediately.

### Ignore Precedence (Evaluation Order)

1. **Explicit ignore patterns (gitignore)** - Checked first
2. **Top-level dot-directory suppression** - Applied to directories starting with `.` at depth 1
3. **Normal scanning** - If no ignore rules match, the path is included

This deterministic order ensures predictable behavior across different environments.

### 1. Default Patterns

These patterns are always applied (included in every `.gitignore` evaluation):
- `.git` - Git metadata
- `.vscode` - VS Code configuration
- `.idea` - IntelliJ configuration
- `__pycache__` - Python cache directories
- `*.pyc`, `*.pyo`, `*.pyd` - Compiled Python files
- `.pytest_cache` - Pytest cache
- `.coverage` - Coverage.py data
- `.tox` - Tox environments
- `.venv`, `venv`, `env`, `ENV` - Virtual environments
- `node_modules` - Node.js dependencies
- `.DS_Store` - macOS metadata
- `Thumbs.db` - Windows thumbnail cache
- `*.egg-info` - Python egg metadata
- `dist`, `build` - Build directories
- `*.so`, `*.dylib`, `*.dll` - Compiled libraries

### 2. .gitignore Patterns

User-defined patterns from `.gitignore` files are read from the root directory and merged with default patterns. The tool uses gitwildmatch syntax, which is compatible with `.gitignore`.

### 3. Top-Level Dot Directories

By default, directories starting with `.` at the top level (depth 1) are ignored. This can be controlled via the `IGNORE_TOPLEVEL_DOTDIRS` constant. This rule applies after gitignore patterns are checked.

## Warning System

The tool generates warnings for various error conditions. All warnings follow the format:

```
<type>: <path> - <message>
```

### Warning Taxonomy

#### 1. **unreadable_file**: File cannot be opened or read

**When triggered:** I/O errors or permission denied when attempting to read files

**Primary use case:** .gitignore files that cannot be read due to permissions

**Example:**
```
unreadable_file: /path/to/.gitignore - Permission denied or I/O error: [details]
```

**Behavior:**
- Warning is added to the warnings list
- The file is skipped
- Processing continues with other items
- A default ignore spec (empty) is used

#### 2. **unreadable_directory**: Directory cannot be accessed

**When triggered:** Permission denied or I/O errors when attempting to list directory contents

**Example:**
```
unreadable_directory: /path/to/dir - Permission denied
```

**Behavior:**
- Warning is added to the warnings list
- The directory and its contents are skipped
- Processing continues with other directories
- Does not prevent analysis of accessible sibling directories

#### 3. **malformed_gitignore**: .gitignore patterns are invalid

**When triggered:** AFTER successfully reading the .gitignore file, pattern parsing fails

**This is different from unreadable_file:**
- **unreadable_file** = cannot open/read the file (I/O or permission error)
- **malformed_gitignore** = file was read successfully but contains invalid patterns

**Example:**
```
malformed_gitignore: /path/to/project - failed to parse .gitignore: [parsing error]
```

**Behavior:**
- Warning is added to the warnings list
- Default patterns are still applied
- The invalid .gitignore patterns are discarded
- Processing continues with default patterns only

#### 4. **symlink_loop**: Circular symlink reference detected

**When triggered:** A symlink resolves to a target that has already been visited in the current traversal path

**Example:**
```
symlink_loop: /path/to/link -> /path/to/target
```

**Behavior:**
- Warning is added to the warnings list
- The symlink is skipped (not followed)
- Prevents infinite recursion
- Processing continues with other items

#### 5. **broken_symlink**: Symlink points to non-existent target

**When triggered:** A symlink cannot be resolved to a valid target

**Example:**
```
broken_symlink: /path/to/link - [error details]
```

**Behavior:**
- Warning is added to the warnings list
- The symlink is skipped (not followed)
- Processing continues with other items

#### 6. **too_many_warnings**: Warning count exceeded threshold

**When triggered:** More than 100 warnings have been generated

**Example:**
```
too_many_warnings: truncated
```

**Behavior:**
- All 100+ warnings are preserved in the XML (not truncated)
- This final warning is appended to indicate truncation occurred
- Alerts users that the complete warning list is very long

### Warning Output in XML

Warnings are included in the XML output under a `<warnings>` element at the end of the structure:

```xml
<project_structure>
  <dir name="...">
    ...
  </dir>
  <warnings>
    <warning>unreadable_directory: /path/to/dir - Permission denied</warning>
    <warning>symlink_loop: /path/to/link -> /path/to/target</warning>
  </warnings>
</project_structure>
```

## Symlink Handling

### Symlink Loop Detection

The tool tracks resolved symlink targets to detect and prevent infinite loops. When a symlink pointing to an already-visited target is encountered:

1. A `symlink_loop` warning is generated
2. The symlink is skipped
3. Processing continues normally

### Broken Symlinks

When a symlink cannot be resolved:

1. A `broken_symlink` warning is generated
2. The symlink is skipped
3. Processing continues normally

## Configuration

### Environment Variables

- `DIRECTORY_TOOL_MAX_FILES`: Override the default file count threshold (default: 50)
- `DIRECTORY_TOOL_EXPAND_LARGE`: Set default expand_large behavior (true/false)

### Config File (Future)

Configuration can also be loaded from `config/config.json`:

```json
{
  "max_file_count": 50,
  "expand_large": false
}
```

## Usage

### As Python Module

```python
from directory_tool import get_codebase_structure

# Analyze current directory
xml_output = get_codebase_structure(".")
print(xml_output)

# Expand large directories
xml_output = get_codebase_structure(".", expand_large=True)
print(xml_output)
```

### As FastMCP Tool

The tool is exposed via the FastMCP server as `get_codebase_structure`:

```python
# Server must be running
# Call via HTTP or FastMCP client
```

### Command Line

```bash
python src/directory_tool.py /path/to/analyze --expand-large
```

## Error Handling

### Unreadable Directories

When a directory cannot be read:
- A warning is added to the warnings list
- The directory is skipped
- Processing continues with other items
- No exception is raised

### Unreadable Files

When a file cannot be read:
- A warning is added to the warnings list
- The file is skipped
- Processing continues with other items

### Malformed .gitignore

When a .gitignore file has invalid syntax:
- A warning is generated
- Default patterns are still applied
- Processing continues normally

## Performance Considerations

- **Directory Scanning**: Uses `os.listdir()` for efficient traversal
- **File Counting**: Recursively counts files for summarization decisions
- **Pattern Matching**: Uses compiled PathSpec for fast gitignore matching
- **Memory Usage**: Processes directories sequentially to minimize memory footprint

## Known Limitations

1. **Nested .gitignore**: Only reads `.gitignore` from the root directory
2. **Symbolic Links**: May miss symlink loops in complex scenarios
3. **Very Large Directories**: Directory traversal may be slow for directories with thousands of entries
4. **Case Sensitivity**: Pattern matching respects filesystem case sensitivity

## Examples

### Example 1: Simple Project Structure

```xml
<?xml version="1.0" ?>
<project_structure>
  <dir name="my_project">
    <file>README.md</file>
    <file>main.py</file>
    <dir name="src">
      <file>app.py</file>
      <file>utils.py</file>
    </dir>
    <dir name="tests">
      <file>test_app.py</file>
    </dir>
  </dir>
</project_structure>
```

### Example 2: Large Directory with Summary

```xml
<?xml version="1.0" ?>
<project_structure>
  <dir name="my_project">
    <dir name="logs">
      <summary count="1047"/>
    </dir>
    <file>main.py</file>
  </dir>
  <warnings>
    <warning>unreadable_directory: /path/to/restricted - Permission denied</warning>
  </warnings>
</project_structure>
```

### Example 3: Ignoring Common Patterns

When analyzing a Python project:

```xml
<project_structure>
  <dir name="my_app">
    <!-- __pycache__ is automatically ignored -->
    <!-- .git is automatically ignored -->
    <!-- node_modules is automatically ignored -->
    <file>app.py</file>
    <dir name="tests">
      <file>test_app.py</file>
    </dir>
  </dir>
</project_structure>
```

## Troubleshooting

### Directory Not Analyzed

**Problem**: Directory doesn't appear in output
**Solutions**:
- Check if directory matches ignore patterns
- Verify read permissions
- Check warning messages for errors

### Too Many Warnings

**Problem**: More than 100 warnings generated
**Solution**: Fix underlying issues (permissions, broken symlinks, etc.)
The tool will truncate warnings at 100 and add a truncation notice.

### Unexpected Files Included

**Problem**: Files you expected to be ignored are included
**Solutions**:
- Check .gitignore syntax
- Verify pattern matching with gitwildmatch rules
- Check default ignore patterns

### Performance Issues

**Problem**: Analysis is slow for large directories
**Solutions**:
- Use `expand_large=False` to enable summarization
- Exclude unnecessary directories with .gitignore
- Consider using ignore patterns for known-large directories

## API Reference

### Functions

#### `get_codebase_structure(root_path: str = ".", expand_large: bool = False) -> str`

Analyze directory structure and generate XML representation.

**Parameters:**
- `root_path`: Root directory to analyze (default: current directory)
- `expand_large`: Always expand directories regardless of file count (default: False)

**Returns:**
XML string representing the directory structure

### Classes

#### `DirectoryIntelligenceTool`

Main class for directory analysis.

**Methods:**

- `__init__(root_path: str = ".")`: Initialize tool
- `generate_xml_structure(expand_large: bool = None) -> str`: Generate complete XML structure
- `load_gitignore_patterns(directory: Path) -> pathspec.PathSpec`: Load and parse .gitignore patterns
- `scan_directory(directory: Path, ignore_spec: pathspec.PathSpec, expand_large: bool = False, depth: int = 0) -> ET.Element`: Scan directory recursively
- `count_directory_files(directory: Path, ignore_spec: pathspec.PathSpec, depth: int = 0) -> int`: Count files in directory
- `_should_ignore(path: Path, ignore_spec: pathspec.PathSpec, depth: int) -> bool`: Check if path should be ignored

## Requirements

- Python 3.11+
- pathspec>=0.11.0
- fastmcp>=0.4.0 (for MCP server integration)

## License

This tool is part of the Directory Intelligence Tool project.
