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

### Backend Selection

1. **Daytona (Primary)**: Uses Daytona SDK to create managed workspaces
   - Provides persistent state across executions
   - Better performance and resource management
   - Native workspace filesystem operations

2. **Docker (Fallback)**: Uses Docker containers for isolation
   - Creates temporary containers with volume mounts
   - Provides process isolation
   - Available when Daytona is not installed or configured

### Execution Flow

1. **Backend Initialization**: Automatically detects and initializes available backend
2. **Workspace Creation**: Creates persistent workspace on first use
3. **Dependency Installation**: Installs required Python packages (if specified)
4. **Script Execution**: Writes script to `task.py` and executes in sandbox
5. **Result Capture**: Captures exit code, stdout, and stderr
6. **Cleanup**: Provides method to clean up resources when done

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

## Persistent Workspace Behavior

The sandbox maintains a persistent workspace that survives between executions. This enables:

### State Persistence

```python
# First execution sets a variable
result1 = execute_python("x = 42")

# Second execution can access the variable
result2 = execute_python("print(f'x = {x}')")
```

### File System Persistence

```python
# First execution writes a file
execute_python("""
with open('/workspace/data.txt', 'w') as f:
    f.write('Important data')
""")

# Second execution reads the file
execute_python("""
with open('/workspace/data.txt', 'r') as f:
    data = f.read()
print(f'Read: {data}')
""")
```

### Import Persistence

```python
# First execution installs and imports a module
execute_python("import json", [])

# Second execution can use the module without re-importing
execute_python("print(json.dumps({'key': 'value'}))")
```

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
2. Runs `pip install -r requirements.txt` in sandbox
3. Installs packages in the sandbox environment
4. Packages remain available for subsequent executions

**Error Handling:**
- Installation failures are caught and reported
- Script execution is aborted if dependencies cannot be installed
- Clear error messages indicate which packages failed to install

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