# EliteMCP - Advanced Code Navigation & Execution

A comprehensive toolkit combining context-efficient code navigation with secure execution and intelligent directory analysis. EliteMCP provides three core capabilities powered by research-backed architectures.

## Project Overview

This project provides three core capabilities:

1. **🧠 NSCCN (Neuro-Symbolic Causal Code Navigator)** - Context-efficient code navigation achieving ~84% token reduction using causal graphs and semantic search
2. **📁 Directory Analysis** - Intelligently analyze directory structures with `.gitignore` awareness, automatic summarization, and robust error handling
3. **🔒 Secure Code Execution** - Execute Python code in isolated sandboxes with Daytona primary backend and Docker fallback

**Architecture:** Four integrated components work together to provide a complete solution for code understanding, navigation, and execution.

- **NSCCN Server** - Causal code graph with hybrid search and incremental indexing
- **Directory Intelligence Tool** - Core directory analysis engine
- **FastMCP Server** - Network-accessible interface to tools
- **Sandbox Execution Engine** - Secure, isolated Python execution environment

[NSCCN Architecture →](docs/nsccn_architecture.md) | [NSCCN Tools →](docs/nsccn_tools.md) | [Execution Architecture →](docs/execution_README.md#architecture)

## Components

### 1. NSCCN (Neuro-Symbolic Causal Code Navigator)

**New!** Context-efficient code navigation system replacing naive file operations with causal graph reasoning.

**Key Features:**
- **~84% Token Reduction** - Telegraphic Semantic Compression (TSC) preserves structure while removing implementation
- **Hybrid Search** - Combines lexical (ripgrep) and semantic (embeddings) with RRF fusion
- **Causal Graph** - Multi-hop reasoning over CALLS and INHERITS edges
- **Incremental Updates** - Real-time file watching with <100ms update latency
- **Four Navigation Tools** - Locate → Orient → Trace → Examine workflow

**Quickstart:**
```bash
# Initialize index for current directory
python src/nsccn/server.py --init .

# Start NSCCN server with file watching
python src/nsccn/server.py --root .

# Get tool information
python src/nsccn/server.py --info
```

**Example Usage:**
```python
from nsccn import NSCCNServer

# Create and initialize server
server = NSCCNServer()
server.initialize(root_path="./src")
server.build_initial_index("./src")

# Use tools
from nsccn.tools import NSCCNTools
tools = NSCCNTools(server.db, server.parser, server.search, server.graph)

# Find entities
results = tools.search_and_rank("validate JWT token", limit=5)

# Get file skeleton
skeleton = tools.read_skeleton("src/auth.py")

# Trace dependencies
trace = tools.trace_causal_path(
    entity_id="func:src/auth.py:login",
    direction="downstream",
    depth=3
)

# Read specific entity
code = tools.open_surgical_window(
    entity_id="func:src/auth.py:validate_token",
    context_lines=5
)
```

[NSCCN Architecture →](docs/nsccn_architecture.md) | [NSCCN Tools Reference →](docs/nsccn_tools.md)

### 2. Directory Intelligence Tool

**File:** `src/directory_tool.py`

Analyzes directory structures with intelligent summarization and `.gitignore` support.

**Key Features:**
- **Warning Taxonomy** - Six warning types for different error conditions (unreadable_file, unreadable_directory, malformed_gitignore, broken_symlink, symlink_loop, too_many_warnings)
- **Smart Summarization** - Automatically summarizes large directories (>50 files by default) to prevent XML bloat
- **Deterministic Ignore Precedence** - Clear evaluation order: gitignore patterns → top-level dotdirs → normal scanning
- **XML Schema** - Structured output with `<dir>`, `<file>`, `<summary>`, and `<warnings>` elements

**Quickstart:**
```python
from directory_tool import get_codebase_structure

# Analyze current directory
xml = get_codebase_structure(".")

# Expand large directories
xml = get_codebase_structure(".", expand_large=True)
```

[Detailed Documentation →](docs/directory_tool.md) | [Warning Taxonomy →](docs/directory_tool.md#warning-system) | [Summarization →](docs/directory_tool.md#summary-element)

### 3. FastMCP Server

**File:** `src/mcp_server.py`

Network-accessible FastMCP service exposing the directory tool.

**Key Features:**
- **Configuration Management** - Loads from `config/config.json` with environment variable overrides
- **Automatic Backend Detection** - Daytona-first with Docker fallback for sandbox execution
- **Validation** - Comprehensive config validation with clear error messages

**Usage:**
```bash
# Run server
python src/mcp_server.py

# Server starts on 127.0.0.1:8000 by default
```

**Note:** Tool-specific config (max_file_count, expand_large) loads but doesn't automatically propagate to DirectoryIntelligenceTool unless explicitly coded.

[Configuration Guide →](docs/configuration.md) | [FastMCP Integration →](docs/directory_tool.md#as-fastmcp-tool)

### 4. Sandbox Execution Engine

**File:** `src/execute_code.py`

Secure Python execution with Daytona primary backend and Docker fallback.

**Key Features:**
- **Backend Fallback** - Daytona-first, automatic Docker fallback
- **Persistent Filesystem** - Files written to workspace persist across executions
- **Daytona/Docker Parity** - Identical pip-install failure semantics across backends
- **Sequential Execution** - Thread-safe with deterministic order

**Quickstart:**
```python
from execute_code import execute_python

# Simple execution
result = execute_python('print("Hello World")')

# With dependencies
result = execute_python(
    'import requests; print(requests.get("https://api.example.com").status_code)',
    requirements=['requests']
)
```

**Workspace Semantics:**
- Filesystem persists: files remain accessible across executions
- Interpreter resets: each execution starts fresh (no variable persistence)
- Best practice: Always re-import modules in each execution

[Sandbox Documentation →](docs/execution_README.md) | [Backend Selection →](docs/execution_README.md#backend-selection-daytona-first-docker-fallback)

### 5. Development Environment (`.devcontainer/devcontainer.json`)

Pre-configured development environment with:
- Python 3.11 with required dependencies
- Docker-in-Docker support
- VS Code extensions for Python development
- Port forwarding for FastMCP server
- Reproducible environment setup

### 6. Test Suite (`test/test.py`)

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