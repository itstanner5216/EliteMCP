# Sandbox Execution Engine

A secure, isolated execution environment for Programmatic Tool Calling (PTC) that supports Daytona as the primary backend with automatic Docker fallback.

## Overview

The sandbox execution engine provides a way to execute Python code in a completely isolated environment. It abstracts the underlying sandbox technology (Daytona or Docker) behind a consistent interface, ensuring that code execution is secure, reproducible, and isolated from the host system.

### Key Features

- **Dual Backend Support**: Uses Daytona as primary backend with automatic Docker fallback
- **Sequential Execution**: All executions run sequentially to prevent race conditions
- **Persistent Workspace**: Maintains state between executions for multi-step workflows
- **Dependency Management**: Installs Python packages in the sandbox environment
- **Comprehensive Error Handling**: Captures and reports all types of execution errors
- **No Host Access**: Complete isolation from the host filesystem and environment

## Architecture

### Backend Selection (Daytona-First, Docker-Fallback)

The execution engine implements a transparent fallback mechanism that prioritizes Daytona but automatically falls back to Docker:

**Backend Selection Algorithm:**

```python
# Pseudo-code representation
if Daytona SDK is available:
    try:
        Initialize Daytona client
        Create Daytona workspace
        return Daytona_backend
    except Exception:
        Log Daytona error
        Try Docker fallback

# Only reach here if Daytona failed or unavailable
if Docker SDK is available:
    try:
        Test Docker connection (docker.ping())
        Create Docker container
        return Docker_backend
    except Exception:
        Log Docker error
        raise RuntimeError("No backend available")
```

**Daytona Backend (Primary):**
- Used when `daytona-sdk` is installed and accessible
- Provides persistent state across executions
- Better performance and resource management
- Native workspace filesystem operations
- Supports workspace.remove() for cleanup

**Docker Backend (Fallback):**
- Used when Daytona is unavailable or fails to initialize
- Creates temporary containers with volume mounts
- Provides process isolation through containerization
- Uses `docker.from_env()` for connection
- Container stops automatically when done

### Execution Flow

**Step 1: Backend Initialization **
- Automatic detection of available backends
- Configuration validation for selected backend
- Connection testing before proceeding

** Step 2: Workspace Creation (Lazy) **
- Workspace is created on first `execute_python()` call
- Reused for subsequent executions (persistent filesystem)
- Daytona: Uses `DaytonaClient.create_workspace()`
- Docker: Creates container with volume mount to temp directory

** Step 3: Dependency Installation **
- Only runs if `requirements` parameter is provided
- Creates `requirements.txt` in workspace
- Executes `pip install -r requirements.txt`
- ** Daytona and Docker have identical failure semantics **
  - Both check `result.exit_code != 0`
  - Both decode stdout/stderr with UTF-8, errors="replace"
  - Both raise `RuntimeError` with decoded output

** Step 4: Script Execution **
- Script is written to `/workspace/task.py`
- Executed with `python /workspace/task.py`
- Fresh interpreter process for each execution (stateless)

** Step 5: Result Capture** (backend-specific)

**Daytona:**
- Returns object with `exit_code`, `stdout`, `stderr` attributes
- stdout and stderr are already decoded strings
- Separate streams preserved

**Docker:**
- Returns object with `exit_code` and `output` (bytes)
- `output` contains merged stdout+stderr
- Must be decoded: `output.decode("utf-8", errors="replace")`
- `stderr` is always empty string (guaranteed by engine)

**Step 6: Resource Management**
- Workspace persists until `cleanup_sandbox()` is called
- Supports graceful shutdown with error handling
- Backend-specific cleanup (Daytona: remove workspace, Docker: stop container)

## Interface

### `execute_python(script: str, requirements: List[str] = None) -> Dict[str, Any]`

Execute Python code in the sandboxed environment.

**Parameters:**
- `script` (str): Python code to execute
- `requirements` (List[str], optional): List of Python packages to install before execution

**Returns:**
```python
{
    "exit_code": int,    # 0 for success, non-zero for failure
    "stdout": str,       # Standard output from the script
    "stderr": str        # Standard error from the script
}
```

### `cleanup_sandbox()`

Clean up sandbox resources. Should be called when done with all executions.

## Sequential Execution Model

All `execute_python` calls are executed sequentially using a `threading.Lock()`. This ensures:

- **Thread Safety**: Multiple threads can safely call execute_python
- **Resource Protection**: Prevents race conditions for workspace access
- **Deterministic Behavior**: Execution order is guaranteed to match call order
- **Error Isolation**: Failures in one execution don't affect others

**Why Sequential Execution?**

1. **Workspace Consistency**: Prevents concurrent modifications to the persistent workspace
2. **Resource Management**: Avoids resource conflicts and deadlocks
3. **Debugging**: Makes it easier to trace execution flow and diagnose issues
4. **Simplicity**: Reduces complexity of the execution engine

## Workspace Semantics

### Persistent Filesystem Behavior

The workspace provides **filesystem persistence** but **interpreter state reset** between executions:

**What PERSISTS (filesystem):**
- Files written to `/workspace/` remain accessible across executions
- Directory structure is maintained
- File contents persist
- This applies to both Daytona and Docker backends

**What RESETS (interpreter state):**
- Python interpreter process starts fresh each time
- Global variables are cleared
- Imported modules must be re-imported
- In-memory state is lost

### Key Implications

1. **File Persistence Example:**
```python
# Execution 1: Write a file
execute_python("""
with open('/workspace/data.txt', 'w') as f:
    f.write('Important data')
print('File written')
""")
# Result: File exists in workspace

# Execution 2: Read the file
execute_python("""
with open('/workspace/data.txt', 'r') as f:
    data = f.read()
print(f'Read: {data}')  # Works!
""")
```

2. **Variable Non-Persistence Example:**
```python
# Execution 1: Set a variable
execute_python("x = 42")
# Result: Variable x exists only during this execution

# Execution 2: Try to access variable
execute_python("print(x)")
# Result: NameError - x is not defined
```

3. **Import Persistence Example:**
```python
# Execution 1: Import a module
execute_python("import json", [])
# Result: json module imported for this execution only

# Execution 2: Use the module without explicit import
execute_python("print(json.dumps({'key': 'value'}'))")
# Result: NameError - json is not defined (must import again)
```

**Best Practice:** Always re-import modules and re-initialize variables in each execution.

## Dependency Installation

Dependencies can be installed in the sandbox environment:

```python
# Install requests and use it
result = execute_python("""
import requests
response = requests.get('https://api.example.com/data')
print(f'Status: {response.status_code}')
""", requirements=["requests"])
```

**Installation Process:**

1. Creates `requirements.txt` with specified packages
2. Writes file to workspace (`/workspace/requirements.txt`)
3. Runs `pip install -r requirements.txt` in sandbox
4. Installs packages in the sandbox environment
5. Packages remain available for subsequent executions

### Daytona/Docker Parity in Requirement Installation

The execution engine ensures **identical failure semantics** between Daytona and Docker backends:

**Common behavior:**
- Both check `result.exit_code != 0` after pip install
- Both decode output with UTF-8, errors="replace"
- Both raise `RuntimeError` with decoded error message
- Both use fallback decoding: `(stderr or stdout or "").encode().decode(...)`

**Daytona-specific:**
- Calls `workspace.exec("pip install ...")`
- Returns object with `exit_code`, `stdout`, `stderr`
- All three attributes are already decoded strings

**Docker-specific:**
- Calls `container.exec_run("pip install ...")`
- Returns object with `exit_code`, `output` (bytes)
- `output` must be decoded before error handling
- `stderr` stream is merged into `output` (Docker limitation)

**Why This Matters:**
- Scripts behave identically regardless of backend
- Error messages have consistent format
- No backend-specific error handling needed in calling code
- Fallback behavior is transparent to users

**Installation Error Examples:**

```python
# Example 1: Package not found (same error format on both backends)
{
    "exit_code": 1,
    "stdout": "",
    "stderr": "Failed to install requirements: ERROR: Could not find a version that satisfies the requirement nonexistent-package"
}

# Example 2: Permission error
{
    "exit_code": 1,
    "stdout": "",
    "stderr": "Failed to install requirements: ERROR: Could not install packages due to an OSError: [Errno 13] Permission denied"
}
```

**Packages are installed per-workspace, not per-execution:**
- Once installed, packages remain available for subsequent executions
- No need to reinstall dependencies for each execution
- Workspace cleanup removes installed packages

## Example Usage

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

### Multi-Step Workflow

```python
# Step 1: Data processing
result1 = execute_python("""
import json

data = {"users": ["alice", "bob", "charlie"], "count": 3}
with open('/workspace/users.json', 'w') as f:
    json.dump(data, f)
print("Data saved successfully")
""")

# Step 2: Data analysis
result2 = execute_python("""
import json

with open('/workspace/users.json', 'r') as f:
    data = json.load(f)

print(f"Found {data['count']} users")
for user in data['users']:
    print(f"- {user}")
""")

# Step 3: Generate report
result3 = execute_python("""
with open('/workspace/users.json', 'r') as f:
    data = json.load(f)

report = f"User Report\\n{'='*50}\\n"
report += f"Total users: {data['count']}\\n"
report += "Users:\\n"
for user in data['users']:
    report += f"  - {user}\\n"

print(report)
""")
```

### With External Dependencies

```python
# Install and use external packages
result = execute_python("""
import requests
import json

# Fetch data from API
response = requests.get('https://jsonplaceholder.typicode.com/posts/1')
data = response.json()

print(f"Title: {data['title']}")
print(f"User ID: {data['userId']}")
""", requirements=["requests"])
```

## Error Handling

The execution engine provides comprehensive error handling:

### Sandbox Initialization Errors

```python
# If Daytona/Docker unavailable
{
    "exit_code": 1,
    "stdout": "",
    "stderr": "Failed to initialize sandbox engine: Failed to initialize any sandbox backend (Daytona or Docker)"
}
```

### Dependency Installation Errors

```python
# If package installation fails
{
    "exit_code": 1,
    "stdout": "",
    "stderr": "Failed to install requirements: ERROR: Could not find a version that satisfies the requirement nonexistent-package"
}
```

### Runtime Errors

```python
# If script has runtime error
{
    "exit_code": 1,
    "stdout": "Before error\n",
    "stderr": "Traceback (most recent call last):\n  File \"task.py\", line 2, in <module>\n    raise ValueError(\"Test error\")\nValueError: Test error\n"
}
```

## Troubleshooting

### Common Issues

1. **"Docker SDK not available"**
   - Install Docker: `pip install docker`
   - Ensure Docker daemon is running

2. **"Daytona SDK not available"**
   - Install Daytona SDK: `pip install daytona-sdk`
   - Configure Daytona API key

3. **"Address already in use"**
   - Another service is using the port
   - Change port in configuration or stop conflicting service

4. **Permission errors**
   - Ensure proper Docker permissions
   - Run with appropriate privileges

### Debug Mode

Enable debug logging to troubleshoot issues:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Now execute your code - detailed logs will be shown
result = execute_python("print('Debug test')")
```

### Checking Backend Status

```python
from execute_code import _execution_engine

if _execution_engine and _execution_engine._backend_type:
    print(f"Using backend: {_execution_engine._backend_type}")
else:
    print("No backend available")
```

## Performance Considerations

- **Workspace Creation**: First execution is slower due to workspace setup
- **Dependency Installation**: Installing packages adds overhead
- **Sequential Execution**: May be slower for parallelizable tasks but ensures correctness
- **Resource Usage**: Each backend has different resource requirements

## Security Considerations

- **Complete Isolation**: No access to host filesystem
- **Network Access**: Sandboxed network access (backend-dependent)
- **Resource Limits**: Backend-specific resource constraints
- **No Privilege Escalation**: Runs with minimal privileges

## Best Practices

1. **Clean Up Resources**: Always call `cleanup_sandbox()` when done
2. **Error Handling**: Check exit codes and handle errors appropriately
3. **Dependency Management**: Install only required packages to reduce overhead
4. **State Management**: Be aware of persistent state when designing workflows
5. **Testing**: Test scripts locally before running in sandbox

## Requirements

- Python 3.11+
- Either Daytona SDK or Docker SDK
- Sufficient system resources for sandbox creation
- Network access (for dependency installation)

## License

This sandbox execution engine is part of the Directory Intelligence Tool project.