# Directory Intelligence Tool

A comprehensive toolkit for analyzing directory structures and executing code in secure sandboxes. This project combines intelligent directory analysis with a secure execution environment for Programmatic Tool Calling (PTC).

## Project Overview

This project consists of three main components:

1. **Directory Intelligence Tool** - Analyzes directory structures and generates XML representations
2. **FastMCP Server** - Exposes the directory tool as a FastMCP service
3. **Sandbox Execution Engine** - Securely executes Python code with Daytona/Docker backends

## Components

### 1. Directory Intelligence Tool (`src/directory_tool.py`)

A .gitignore-aware directory structure analyzer that generates XML hierarchies with intelligent summarization for large directories.

**Key Features:**
- Respects `.gitignore` patterns using `pathspec` library
- Generates structured XML output with `<dir>`, `<file>`, and `<summary>` tags
- Automatically summarizes directories with more than 50 files
- Handles edge cases: symlink loops, permission errors, malformed .gitignore
- Provides both FastMCP tool interface and command-line usage

**Main Function:**
```python
def get_codebase_structure(root_path: str = ".", expand_large: bool = False) -> str:
    """Analyze directory structure and return XML representation."""
```

### 2. FastMCP Server (`src/mcp_server.py`)

Exposes the Directory Intelligence Tool as a FastMCP service with HTTP transport.

**Key Features:**
- Configurable server settings via `config/config.json`
- Automatic Daytona/Docker backend detection
- HTTP transport for network accessibility
- Comprehensive error handling and logging
- Graceful shutdown handling

**Usage:**
```bash
python src/mcp_server.py
```

### 3. Sandbox Execution Engine (`src/execute_code.py`)

Secure Python code execution environment with Daytona primary backend and Docker fallback.

**Key Features:**
- Sequential execution with threading locks
- Persistent workspace maintains state between calls
- Dependency installation support
- Complete host filesystem isolation
- Comprehensive error handling

**Main Function:**
```python
def execute_python(script: str, requirements: List[str] = None) -> Dict[str, Any]:
    """Execute Python code in sandboxed environment."""
```

### 4. Development Environment (`.devcontainer/devcontainer.json`)

Pre-configured development environment with:
- Python 3.11 with required dependencies
- Docker-in-Docker support
- VS Code extensions for Python development
- Port forwarding for FastMCP server
- Reproducible environment setup

### 5. Test Suite (`test/test.py`)

Comprehensive test suite covering:
- Basic script execution and output capture
- Persistent workspace behavior
- Error handling and edge cases
- Sequential execution verification
- Dependency installation testing

## Installation

### Prerequisites

- Python 3.11+
- Either Daytona SDK or Docker SDK (for sandbox execution)
- Git (for directory analysis)

### Setup Steps

1. **Clone the repository:**
```bash
git clone <repository-url>
cd directory-intelligence-tool
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Optional: Install Daytona SDK for primary sandbox backend:**
```bash
pip install daytona-sdk
# Configure Daytona API key in environment
export DAYTONA_API_KEY="your-api-key"
```

4. **Optional: Install Docker SDK for fallback sandbox backend:**
```bash
pip install docker
# Ensure Docker daemon is running
```

## Usage

### Running the FastMCP Server

```bash
python src/mcp_server.py
```

The server will start and print:
```
FastMCP server running on 127.0.0.1:8000
```

### Using the Directory Intelligence Tool

**As a Python module:**
```python
from src.directory_tool import get_codebase_structure

# Analyze current directory
xml_result = get_codebase_structure(".")
print(xml_result)

# Analyze with large directories expanded
xml_result = get_codebase_structure(".", expand_large=True)
print(xml_result)
```

**Command line usage:**
```bash
python src/directory_tool.py /path/to/analyze --expand-large
```

### Using the Sandbox Execution Engine

```python
from src.execute_code import execute_python

# Simple execution
result = execute_python("""
print("Hello from sandbox!")
for i in range(3):
    print(f"Count: {i}")
""")

print(f"Exit code: {result['exit_code']}")
print(f"Output: {result['stdout']}")

# With dependencies
result = execute_python("""
import requests
response = requests.get('https://api.example.com')
print(f'Status: {response.status_code}')
""", requirements=["requests"])
```

### Development Environment

**Using VS Code DevContainer:**
1. Open project in VS Code
2. Install DevContainer extension
3. Click "Reopen in Container" when prompted
4. Environment will be set up automatically

**Manual development setup:**
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install optional backends
pip install daytona-sdk docker
```

## End-to-End Example

Here's a complete example combining both tools:

```python
import os
import tempfile
from src.directory_tool import get_codebase_structure
from src.execute_code import execute_python

# Step 1: Create a test directory structure
test_dir = tempfile.mkdtemp()
os.makedirs(f"{test_dir}/src")
os.makedirs(f"{test_dir}/tests")

with open(f"{test_dir}/README.md", "w") as f:
    f.write("# Test Project\n")

with open(f"{test_dir}/src/app.py", "w") as f:
    f.write("print('Hello World')\n")

# Step 2: Analyze the directory structure
print("=== Directory Analysis ===")
xml_structure = get_codebase_structure(test_dir)
print(xml_structure)

# Step 3: Process the structure in sandbox
print("\\n=== Processing in Sandbox ===")
result = execute_python(f"""
import xml.etree.ElementTree as ET
import os

# Parse the XML structure
xml_data = """{xml_structure.replace('"', '\\"')}"""
root = ET.fromstring(xml_data)

# Count directories and files
def count_items(element, depth=0):
    dirs = 0
    files = 0
    
    for child in element:
        if child.tag == 'dir':
            dirs += 1
            d, f = count_items(child, depth + 1)
            dirs += d
            files += f
        elif child.tag == 'file':
            files += 1
    
    return dirs, files

total_dirs, total_files = count_items(root)
print(f"Total directories: {{total_dirs}}")
print(f"Total files: {{total_files}}")
print(f"Total items: {{total_dirs + total_files}}")
""")

print(f"Processing result: {{result['stdout']}}")

# Step 4: Clean up
import shutil
shutil.rmtree(test_dir)
```

## Testing

Run the test suite:
```bash
# Using unittest
python -m unittest test.test -v

# Using pytest (if installed)
pytest test/test.py -v
```

## Troubleshooting

### Common Issues

1. **"No sandbox backend available"**
   - Install Daytona SDK: `pip install daytona-sdk`
   - Or install Docker SDK: `pip install docker`
   - Ensure Docker daemon is running

2. **"FastMCP server won't start"**
   - Check if port 8000 is already in use
   - Verify all dependencies are installed
   - Check FastMCP version compatibility

3. **"Directory analysis fails"**
   - Ensure you have read permissions for the target directory
   - Check that the path exists and is accessible
   - Verify .gitignore file format if present

4. **"Tests fail with import errors"**
   - Ensure PYTHONPATH includes the src directory
   - Check that all dependencies are installed
   - Verify you're running tests from the project root

### Debug Mode

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Run your code - detailed logs will be shown
```

## Project Structure

```
directory-intelligence-tool/
├── src/
│   ├── directory_tool.py      # Directory analysis tool
│   ├── mcp_server.py          # FastMCP server
│   └── execute_code.py        # Sandbox execution engine
├── config/
│   └── config.json            # Server configuration
├── test/
│   └── test.py                # Test suite
├── docs/
│   └── execution_README.md    # Sandbox engine documentation
├── .devcontainer/
│   └── devcontainer.json      # Development environment
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run the test suite
5. Submit a pull request

## License

This project is part of the Directory Intelligence Tool suite.