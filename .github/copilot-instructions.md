# GitHub Copilot Repository Instructions

## Project Overview

**EliteMCP** is a comprehensive Python toolkit that combines intelligent directory analysis with secure code execution capabilities. The project consists of three integrated components working together to provide filesystem analysis and sandboxed Python execution.

### Project Type
- **Language**: Python 3.11+
- **Architecture**: Modular toolkit with FastMCP server integration
- **Primary Use Cases**: Directory structure analysis, secure code execution, MCP service hosting

## Core Components

1. **Directory Intelligence Tool** (`src/directory_tool.py`)
   - Analyzes directory structures with .gitignore awareness
   - Generates XML hierarchies with intelligent summarization
   - Handles large directories (>50 files) with automatic summarization
   - Implements robust warning taxonomy for error conditions

2. **FastMCP Server** (`src/mcp_server.py`)
   - Network-accessible interface to directory tool
   - Configuration-driven with JSON config files
   - Supports CORS and request timeouts
   - Exposes tools via FastMCP protocol

3. **Sandbox Execution Engine** (`src/execute_code.py`)
   - Secure Python code execution in isolated sandboxes
   - Daytona SDK as primary backend, Docker as fallback
   - Persistent filesystem across executions
   - Thread-safe sequential execution model

## Coding Standards

### Python Style
- **Follow PEP 8**: Use standard Python style conventions
- **Type Hints**: Always include type hints for function parameters and return values
- **Docstrings**: Use detailed docstrings for all modules, classes, and public functions
  - Module-level docstrings should explain purpose and key features
  - Function docstrings should include Args, Returns, and Raises sections
- **Error Handling**: Use specific exception types with clear error messages
- **Logging**: Use Python's logging module (never print() in production code)

### Code Organization
- Keep functions focused and single-purpose
- Use dataclasses for structured data representation
- Implement proper resource cleanup (context managers where appropriate)
- Maintain separation of concerns between modules

### Naming Conventions
- Classes: `PascalCase` (e.g., `DirectoryIntelligenceTool`)
- Functions/Methods: `snake_case` (e.g., `get_codebase_structure`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `MAX_FILE_COUNT`)
- Private members: Prefix with underscore (e.g., `_load_config`)

## Testing Requirements

### Test Framework
- Use Python's built-in `unittest` framework (primary)
- `pytest` compatibility is supported but not required
- All tests should be in the `test/` directory

### Test Standards
- **Coverage**: Write tests for all new features and bug fixes
- **Test Structure**: Follow existing test patterns in `test/test.py`
- **Test Organization**: Group related tests in test classes
- **Assertions**: Use descriptive assertion messages
- **Setup/Teardown**: Use `setUpClass`/`tearDownClass` for expensive setup
- **Isolation**: Tests should not depend on each other or external state

### Running Tests
```bash
# Run all tests with unittest
python -m unittest test.test -v

# Run with pytest (if installed)
pytest test/test.py -v
```

## Technology Stack

### Core Dependencies
- **pathspec** (≥0.11.0): .gitignore pattern matching
- **fastmcp** (≥0.4.0): FastMCP server framework
- **docker** (≥6.0.0): Docker SDK for Python (sandbox fallback)
- **daytona_sdk**: Daytona SDK for primary sandbox backend

### Development Tools
- **pytest** (≥7.0.0): Testing framework (optional)
- **black**: Code formatting (configured in devcontainer)
- **flake8**: Linting (configured in devcontainer)

### Environment
- **Python Version**: 3.11 (minimum)
- **Container**: VS Code DevContainer with Docker-in-Docker support
- **Privileged Operations**: Required for Docker sandbox backend

## Architecture Guidelines

### Module Structure
```
src/
├── directory_tool.py      # Core directory analysis
├── mcp_server.py          # FastMCP server
└── execute_code.py        # Sandbox execution
```

### Design Patterns
- **Configuration Management**: Load from JSON with environment variable overrides
- **Backend Selection**: Try Daytona first, fallback to Docker automatically
- **Error Handling**: Collect warnings rather than failing immediately
- **Lazy Initialization**: Initialize expensive resources only when needed

### XML Output Format
The directory tool generates structured XML with these elements:
- `<dir name="...">`: Directory elements
- `<file name="...">`: File elements
- `<summary count="N">`: Summarized large directories
- `<warnings>`: Collected error/warning information

## Development Workflow

### Setting Up Development Environment
1. Open project in VS Code
2. Use "Reopen in Container" for DevContainer setup
3. Dependencies auto-install via `postCreateCommand`
4. PYTHONPATH automatically set to include `src/`

### Making Changes
1. **Understand**: Read existing code and documentation first
2. **Test**: Run existing tests to ensure baseline works
3. **Implement**: Make minimal, focused changes
4. **Validate**: Run tests and manual verification
5. **Document**: Update docstrings and README if needed

### Configuration Files
- `config/config.json`: FastMCP server configuration
- `.devcontainer/devcontainer.json`: Development environment setup
- `requirements.txt`: Python package dependencies

### Environment Variables
- `DAYTONA_API_KEY`: Required for Daytona backend
- `DOCKER_HOST`: Docker socket location (set in devcontainer)
- `PYTHONPATH`: Should include `src/` directory

## File Organization Guidelines

### When to Edit Each File
- **`src/directory_tool.py`**: Directory analysis logic, .gitignore handling, XML generation
- **`src/mcp_server.py`**: Server configuration, tool registration, FastMCP setup
- **`src/execute_code.py`**: Sandbox backends, execution logic, workspace management
- **`test/test.py`**: All test cases for the project
- **`config/config.json`**: Server and tool configuration values
- **`README.md`**: User-facing documentation, installation, usage examples

### Files to Never Modify Directly
- `.git/`: Git metadata
- `__pycache__/`: Python bytecode cache
- `.pytest_cache/`: Pytest cache
- Any generated or temporary files

## Common Tasks

### Adding a New Feature
1. Determine which component it belongs to
2. Write tests first (TDD approach encouraged)
3. Implement the minimal code needed
4. Update relevant docstrings
5. Run full test suite
6. Update README if user-visible

### Fixing a Bug
1. Write a test that reproduces the bug
2. Fix the bug with minimal changes
3. Verify the test passes
4. Check for similar issues in related code
5. Update documentation if behavior changes

### Refactoring
1. Ensure comprehensive tests exist first
2. Make incremental changes
3. Run tests after each change
4. Preserve external APIs unless explicitly changing them
5. Update comments and docstrings

## Best Practices

### Code Quality
- Avoid code duplication (DRY principle)
- Keep functions under 50 lines when possible
- Use early returns to reduce nesting
- Prefer composition over inheritance
- Make implicit dependencies explicit

### Error Handling
- Use specific exception types
- Provide actionable error messages
- Log errors appropriately (use logging module)
- Clean up resources in finally blocks or context managers
- Don't catch exceptions unless you can handle them meaningfully

### Performance
- Large directories are automatically summarized (>50 files)
- Sandboxes reuse persistent workspaces
- Thread locks ensure safe concurrent access
- Avoid premature optimization

### Security
- Sandbox execution isolates untrusted code
- No secrets should be committed to the repository
- Environment variables for sensitive data (e.g., API keys)
- Validate all external inputs

## Documentation Standards

### Code Comments
- Explain "why" not "what" (code should be self-explanatory)
- Use comments for complex algorithms or non-obvious behavior
- Keep comments up-to-date with code changes
- Avoid redundant comments

### README Updates
- Keep installation instructions current
- Provide working examples
- Document configuration options
- Include troubleshooting section

### Docstring Format
```python
def function_name(param1: Type1, param2: Type2) -> ReturnType:
    """Brief one-line description.
    
    Detailed description if needed, explaining the function's purpose,
    behavior, and any important implementation details.
    
    Args:
        param1: Description of first parameter
        param2: Description of second parameter
        
    Returns:
        Description of return value
        
    Raises:
        ExceptionType: When and why this exception is raised
    """
```

## Issue Resolution Guidelines

### Understanding Issues
- Read the full issue description and comments
- Check for related issues or PRs
- Reproduce the issue locally if it's a bug
- Ask for clarification if requirements are unclear

### Implementation Approach
- Make minimal changes to fix the issue
- Don't refactor unrelated code
- Follow existing patterns in the codebase
- Consider backward compatibility

### Testing Changes
- Add tests for new functionality
- Verify bug fixes with specific tests
- Run full test suite before submitting
- Test both happy path and error cases

## Additional Notes

- The project uses XML output extensively - maintain schema consistency
- Warning taxonomy is important for error reporting - don't break existing types
- Backend fallback (Daytona → Docker) is a key feature - preserve this behavior
- Thread safety matters for the sandbox engine - use locks appropriately
- Configuration loading has specific precedence - respect the existing order
