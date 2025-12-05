# Development Guide

This guide covers development workflows, testing strategies, and guidelines for contributing to the Directory Intelligence Tool project.

## Project Structure

```
directory-intelligence-tool/
├── src/
│   ├── directory_tool.py      # Directory intelligence tool
│   ├── mcp_server.py          # FastMCP server
│   └── execute_code.py        # Sandbox execution engine
├── config/
│   └── config.json            # Server configuration
├── test/
│   └── test.py                # Test suite
├── docs/                      # Documentation
│   ├── execution_README.md    # Sandbox execution docs
│   ├── directory_tool.md      # Directory tool docs
│   ├── configuration.md       # Configuration guide
│   ├── development.md         # This file
│   └── examples/              # Example XML files
├── .devcontainer/
│   └── devcontainer.json      # Development environment
├── requirements.txt           # Python dependencies
└── README.md                  # Project overview
```

## Development Environment

### Using DevContainer (Recommended)

1. Open project in VS Code
2. Install DevContainer extension
3. Click "Reopen in Container" when prompted
4. Wait for environment setup to complete
5. Start developing!

The devcontainer provides:
- Python 3.11
- All dependencies pre-installed
- Docker-in-Docker support
- VS Code extensions
- Configured PYTHONPATH

### Manual Setup

```bash
# Clone repository
git clone <repository-url>
cd directory-intelligence-tool

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install project in editable mode
pip install -e .

# Set environment variables
export DAYTONA_API_KEY="your-api-key"
export DOCKER_HOST="unix:///var/run/docker.sock"
```

## Running Tests

### Using Unittest

```bash
# Run all tests
python -m unittest test.test -v

# Run specific test class
python -m unittest test.test.TestSandboxExecutionEngine -v

# Run specific test
python -m unittest test.test.TestSandboxExecutionEngine.test_basic_script_execution -v
```

### Using Pytest

```bash
# Install pytest
pip install pytest

# Run all tests
pytest test/test.py -v

# Run with coverage
pytest test/test.py --cov=src -v
```

## Running the MCP Server

### Direct Execution

```bash
# Set environment variables (optional)
export DIRECTORY_TOOL_MAX_FILES=100
export DIRECTORY_TOOL_EXPAND_LARGE=true

# Run the server
python src/mcp_server.py
```

**Server startup logs:**
```
Server:starting: name=directory-intelligence-server
Server:listening: host=127.0.0.1 port=8000
Tools:enabled: get_codebase_structure
Environment: python=3.11.0 os=posix
```

### With Docker Backend

```bash
# Ensure Docker daemon is running
docker ps

# Run server
python src/mcp_server.py

# In another terminal, test the tool
python -c "
from directory_tool import get_codebase_structure
xml = get_codebase_structure('.', expand_large=False)
print(xml[:500])  # Print first 500 chars
"
```

### Verify Server is Running

```python
import requests
import json

# Check server health (if health endpoint added)
try:
    response = requests.get('http://127.0.0.1:8000')
    print(f"Server response: {response.status_code}")
except Exception as e:
    print(f"Cannot connect: {e}")
```

## Running Directory Tool Manually

### As Python Module

```python
from directory_tool import get_codebase_structure

# Analyze current directory
xml_output = get_codebase_structure(".")
print(xml_output)

# Analyze specific path
xml_output = get_codebase_structure("/path/to/project", expand_large=True)
print(xml_output)

# Save to file
with open('structure.xml', 'w') as f:
    f.write(xml_output)
```

### Command Line

```bash
# Analyze current directory
python src/directory_tool.py

# Analyze specific path
python src/directory_tool.py /path/to/project

# Expand large directories
python src/directory_tool.py /path/to/project --expand-large

# Save output to file
python src/directory_tool.py --output structure.xml

# Analyze with custom threshold (via env var)
DIRECTORY_TOOL_MAX_FILES=100 python src/directory_tool.py
```

**Command line help:**
```bash
python src/directory_tool.py --help
```

## Using the Sandbox Engine

### Basic Execution

```python
from execute_code import execute_python

# Simple script execution
result = execute_python("""
print("Hello, World!")
for i in range(3):
    print(f"Count: {i}")
""")

print(f"Exit code: {result['exit_code']}")
print(f"Output: {result['stdout']}")
```

### With Dependencies

```python
# Install packages and execute
result = execute_python("""
import requests
import json

response = requests.get('https://jsonplaceholder.typicode.com/posts/1')
data = response.json()

print(f"Title: {data['title']}")
print(f"User ID: {data['userId']}")
""", requirements=["requests"])

print(f"Exit code: {result['exit_code']}")
print(f"Output: {result['stdout']}")
```

### Multi-step Workflow (Persistent Filesystem)

```python
# Step 1: Write data
result1 = execute_python("""
import json

data = {"users": ["alice", "bob"], "count": 2}
with open('/workspace/users.json', 'w') as f:
    json.dump(data, f)
print("Data saved")
""")

# Step 2: Read and process data
result2 = execute_python("""
import json

with open('/workspace/users.json', 'r') as f:
    data = json.load(f)

print(f"Found {data['count']} users")
for user in data['users']:
    print(f"- {user}")
""")

# Important: Clean up when done
from execute_code import cleanup_sandbox
cleanup_sandbox()
```

### Test Categories

#### Sandbox Execution Tests
- `TestSandboxExecutionEngine`: Tests for execute_code.py
  - Basic script execution
  - Output capture (stdout/stderr)
  - Error handling
  - Persistent workspace (filesystem)
  - Dependency installation
  - Sequential execution
  - Docker output normalization
  - Daytona capability validation

#### Directory Tool Tests
- `TestDirectoryIntelligenceTool`: Tests for directory_tool.py
  - Unreadable directory warnings
  - Unreadable file warnings
  - Malformed .gitignore warnings
  - Ignore rule consolidation
  - Summary threshold logic
  - Symlink loop detection
  - Warning overflow handling

## Writing New Tests

### Test Structure

```python
class TestYourFeature(unittest.TestCase):
    """Test suite for your feature."""

    def setUp(self):
        """Set up before each test."""
        pass

    def tearDown(self):
        """Clean up after each test."""
        pass

    def test_something(self):
        """Test description."""
        # Arrange
        expected = "value"

        # Act
        result = your_function()

        # Assert
        self.assertEqual(result, expected)
```

### Best Practices

1. **Use Descriptive Test Names**
   - `test_should_handle_unreadable_files()` not `test1()`

2. **Follow AAA Pattern**
   - Arrange: Set up test data
   - Act: Call the function being tested
   - Assert: Verify the results

3. **Use Temporary Directories**
   ```python
   import tempfile
   from pathlib import Path

   with tempfile.TemporaryDirectory() as tmpdir:
       # Your test code here
   ```

4. **Test Edge Cases**
   - Empty inputs
   - Missing files
   - Permission errors
   - Large datasets

5. **Clean Up Resources**
   ```python
   try:
       # Test code
   finally:
       # Restore permissions, cleanup files
       pass
   ```

6. **Mock External Dependencies**
   ```python
   from unittest.mock import MagicMock, patch

   # Mock external calls
   with patch('module.external_function') as mock:
       mock.return_value = "expected"
       result = your_function()
   ```

### Testing Checklist

When adding new features, ensure tests cover:

- [ ] Happy path (normal operation)
- [ ] Edge cases
- [ ] Error conditions
- [ ] Boundary conditions
- [ ] Invalid inputs
- [ ] Resource cleanup
- [ ] Warning generation
- [ ] Logging

## Extending the Directory Tool

### Adding New Ignore Patterns

Edit `src/directory_tool.py`, default_patterns list:

```python
default_patterns = [
    ".git",
    ".vscode",
    ".idea",
    # Add your patterns here
    "your_pattern",
    "*.your_extension",
]
```

### Adding New Warning Types

1. Add warning in appropriate location:
   ```python
   self.warnings.append(f"warning_type: {path} - {message}")
   ```

2. Add test for the warning

3. Document in docs/directory_tool.md

### Adding Configuration Options

1. Add to config defaults:
   ```python
   defaults = {
       'max_file_count': 50,
       'your_option': 'default_value',
   }
   ```

2. Add environment variable support:
   ```python
   your_option_str = os.environ.get('DIRECTORY_TOOL_YOUR_OPTION')
   if your_option_str:
       config['your_option'] = your_option_str
   ```

3. Add to validation if needed

4. Add tests

5. Document in docs/configuration.md

## Extending the Sandbox Engine

### Adding New Execution Backend

1. Create backend class:
   ```python
   class YourBackend:
       def __init__(self):
           # Initialize backend
           pass

       def create_workspace(self):
           # Create workspace
           pass

       def execute(self, script):
           # Execute script
           pass
   ```

2. Update `SandboxExecutionEngine`:
   ```python
   def _init_your_backend(self) -> bool:
       # Initialize your backend
       pass

   def _get_or_create_workspace(self):
       if self._backend_type == "your_backend":
           return self._create_your_backend_workspace()
   ```

3. Add tests

### Modifying Error Handling

When adding new error conditions:

1. Use descriptive error messages
2. Follow pattern: `"<type>: <details>"`
3. Log errors at appropriate level
4. Test error paths

## Code Style

### Formatting

- Use Black for Python formatting
- Run: `black src/ test/`

### Linting

- Use flake8 for linting
- Run: `flake8 src/ test/`

### Type Hints

- Add type hints to all functions
- Use `from typing import` for complex types

### Docstrings

Use Google-style docstrings:

```python
def your_function(param1: str, param2: int) -> bool:
    """Brief description of function.

    Longer description if needed.

    Args:
        param1: Description of param1.
        param2: Description of param2.

    Returns:
        Description of return value.

    Raises:
        ValueError: Description of when this is raised.
    """
    pass
```

## Documentation

### When to Update Documentation

- Add new features
- Change configuration options
- Modify APIs
- Fix bugs that affect usage
- Add new error conditions

### Documentation Files

- **README.md**: Project overview and quick start
- **docs/**: Detailed documentation
  - `directory_tool.md`: Directory tool reference
  - `execution_README.md`: Sandbox execution reference
  - `configuration.md`: Configuration guide
  - `development.md`: This file
  - `examples/`: Example XML files

### Building Documentation

Currently, documentation is in Markdown format. To update:

1. Edit relevant .md file
2. Verify links work
3. Check examples are valid
4. Update README.md if needed

## Debugging

### Enable Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Common Issues

#### Import Errors
- Check PYTHONPATH includes src/
- Verify __init__.py files exist
- Check module names match filenames

#### Test Failures
- Run single test to isolate: `python -m unittest test.test.TestClass.test_method -v`
- Check setup/teardown logic
- Verify mocks are configured correctly

#### Docker Issues
- Check Docker daemon is running
- Verify docker.sock permissions
- Check Docker SDK is installed

#### Daytona Issues
- Verify API key is set
- Check Daytona SDK installation
- Review Daytona logs

### Debugging Tools

```python
# Print variable with type
print(f"{var=} {type(var)=}")

# Debug logging
logger.debug(f"Variable value: {var}")

# Trace execution
import traceback
try:
    # code
except Exception as e:
    traceback.print_exc()
```

## Version Control

### Commit Messages

Follow conventional commits:

```
type(scope): description

[optional body]

[optional footer]
```

Types:
- feat: New feature
- fix: Bug fix
- docs: Documentation
- test: Adding tests
- refactor: Code refactoring
- style: Formatting changes

Examples:
```
feat(directory_tool): add support for .svn ignore patterns
fix(execute_code): handle None result from Docker exec
docs: update configuration guide
test: add test for symlink loop detection
```

### Pull Request Process

1. Create feature branch
2. Make changes
3. Write/update tests
4. Update documentation
5. Run test suite
6. Submit PR
7. Address review feedback
8. Merge after approval

## Performance

### Profiling

```python
import cProfile
cProfile.run('your_function()')
```

### Benchmarking

```python
import time

start = time.time()
your_function()
end = time.time()
print(f"Duration: {end - start:.2f}s")
```

### Optimization Tips

1. Profile before optimizing
2. Focus on hot paths
3. Consider data structures
4. Avoid premature optimization

## Security

### Best Practices

1. **No Secrets in Code**
   - Use environment variables
   - Don't commit .env files
   - Don't hardcode API keys

2. **Input Validation**
   - Validate all inputs
   - Sanitize filenames
   - Check path boundaries

3. **Error Handling**
   - Don't expose sensitive info in errors
   - Log errors, don't print to user

4. **Dependencies**
   - Keep dependencies updated
   - Review security advisories

## Release Process

1. Update version numbers if applicable
2. Run full test suite
3. Update changelog
4. Update documentation
5. Create release tag
6. Build and publish if applicable

## Support

### Getting Help

- Check documentation in docs/
- Review example code
- Run tests to verify environment

### Reporting Issues

Include:
- Python version
- OS version
- Error message
- Steps to reproduce
- Expected behavior

## Requirements

- Python 3.11+
- All dependencies from requirements.txt
- Docker (for sandbox testing)
- Daytona SDK (optional, for Daytona backend)

## License

This development guide is part of the Directory Intelligence Tool project.
