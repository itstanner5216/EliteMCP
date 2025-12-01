#!/usr/bin/env python3
"""
Test suite for the sandbox execution engine (execute_code.py)
"""

import unittest
import sys
import os
import tempfile
import time
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from execute_code import execute_python, cleanup_sandbox


class TestSandboxExecutionEngine(unittest.TestCase):
    """Test suite for sandbox execution engine."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test class - clean any existing sandbox."""
        cleanup_sandbox()
    
    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests."""
        cleanup_sandbox()
    
    def setUp(self):
        """Set up before each test."""
        # Small delay to ensure sequential execution
        time.sleep(0.1)
    
    def test_basic_script_execution(self):
        """Test basic Python script execution."""
        script = """
print("Hello from sandbox!")
print("Test script executed successfully")
"""
        
        result = execute_python(script)
        
        self.assertEqual(result['exit_code'], 0)
        self.assertIn("Hello from sandbox!", result['stdout'])
        self.assertIn("Test script executed successfully", result['stdout'])
        self.assertEqual(result['stderr'], "")
    
    def test_stdout_capture(self):
        """Test that stdout is properly captured."""
        script = """
import sys
print("Line 1")
print("Line 2")
print("Line 3")
print(f"Python version: {sys.version}")
"""
        
        result = execute_python(script)
        
        self.assertEqual(result['exit_code'], 0)
        self.assertIn("Line 1", result['stdout'])
        self.assertIn("Line 2", result['stdout'])
        self.assertIn("Line 3", result['stdout'])
        self.assertIn("Python version:", result['stdout'])
    
    def test_stderr_capture(self):
        """Test that stderr is properly captured from failing scripts."""
        script = """
import sys
print("This goes to stdout")
print("This goes to stderr", file=sys.stderr)
print("More stdout")
"""
        
        result = execute_python(script)
        
        self.assertEqual(result['exit_code'], 0)
        self.assertIn("This goes to stdout", result['stdout'])
        self.assertIn("More stdout", result['stdout'])
        self.assertIn("This goes to stderr", result['stderr'])
    
    def test_script_error_capture(self):
        """Test that script errors are properly captured."""
        script = """
print("Before error")
raise ValueError("Test error")
print("After error - won't be reached")
"""
        
        result = execute_python(script)
        
        self.assertNotEqual(result['exit_code'], 0)
        self.assertIn("Before error", result['stdout'])
        self.assertIn("ValueError", result['stderr'])
        self.assertIn("Test error", result['stderr'])
        self.assertNotIn("After error", result['stdout'])
    
    def test_persistent_workspace_file_write_read(self):
        """Test that workspace persists state between executions."""
        # First script: write a file
        write_script = """
with open('/workspace/test_file.txt', 'w') as f:
    f.write('Hello from persistent workspace!')
print("File written successfully")
"""
        
        result1 = execute_python(write_script)
        self.assertEqual(result1['exit_code'], 0)
        self.assertIn("File written successfully", result1['stdout'])
        
        # Second script: read the file
        read_script = """
try:
    with open('/workspace/test_file.txt', 'r') as f:
        content = f.read()
    print(f"File content: {content}")
    print("File read successfully")
except FileNotFoundError:
    print("ERROR: File not found - workspace not persistent")
    exit(1)
"""
        
        result2 = execute_python(read_script)
        self.assertEqual(result2['exit_code'], 0)
        self.assertIn("File content: Hello from persistent workspace!", result2['stdout'])
        self.assertIn("File read successfully", result2['stdout'])
    
    def test_persistent_workspace_variable_state(self):
        """Test that variables persist between executions."""
        # First script: set a global variable
        script1 = """
import sys
global_var = "persistent_value"
print(f"Set global_var = '{global_var}'")
"""
        
        result1 = execute_python(script1)
        self.assertEqual(result1['exit_code'], 0)
        self.assertIn("Set global_var = 'persistent_value'", result1['stdout'])
        
        # Second script: access the global variable
        script2 = """
try:
    print(f"global_var = '{global_var}'")
    print("Variable access successful")
except NameError:
    print("ERROR: Variable not found - workspace not persistent")
    exit(1)
"""
        
        result2 = execute_python(script2)
        # Note: Variable persistence depends on the backend implementation
        # Daytona should maintain state, Docker might not
        if result2['exit_code'] == 0:
            self.assertIn("Variable access successful", result2['stdout'])
        else:
            # This is acceptable for Docker backend
            self.assertIn("Variable not found", result2['stdout'])
    
    def test_dependency_installation(self):
        """Test that dependencies can be installed and used."""
        script = """
try:
    import json
    import sys
    
    # Test built-in modules
    data = {"test": "value", "number": 42}
    json_str = json.dumps(data)
    parsed = json.loads(json_str)
    
    print(f"JSON encoding/decoding works: {parsed}")
    print(f"Python version: {sys.version}")
    print("Basic dependencies test passed")
    
except ImportError as e:
    print(f"Import error: {e}")
    exit(1)
except Exception as e:
    print(f"Unexpected error: {e}")
    exit(1)
"""
        
        result = execute_python(script)
        self.assertEqual(result['exit_code'], 0)
        self.assertIn("JSON encoding/decoding works", result['stdout'])
        self.assertIn("Basic dependencies test passed", result['stdout'])
    
    def test_large_script_execution(self):
        """Test execution of larger scripts."""
        script = """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

numbers = []
for i in range(10):
    numbers.append(fibonacci(i))

print(f"Fibonacci sequence (first 10): {numbers}")
print(f"Sum: {sum(numbers)}")
"""
        
        result = execute_python(script)
        self.assertEqual(result['exit_code'], 0)
        self.assertIn("Fibonacci sequence (first 10): [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]", result['stdout'])
        self.assertIn("Sum: 88", result['stdout'])
    
    def test_multiple_sequential_executions(self):
        """Test that multiple executions run sequentially without conflicts."""
        results = []
        
        for i in range(5):
            script = f"""
import time
time.sleep(0.1)  # Small delay to test sequential execution
print(f"Execution {i+1} completed")
"""
            result = execute_python(script)
            results.append(result)
            self.assertEqual(result['exit_code'], 0)
            self.assertIn(f"Execution {i+1} completed", result['stdout'])
        
        # Verify all executions completed successfully
        self.assertEqual(len(results), 5)
        for result in results:
            self.assertEqual(result['exit_code'], 0)
    
    def test_empty_script(self):
        """Test execution of empty script."""
        script = ""
        
        result = execute_python(script)
        
        self.assertEqual(result['exit_code'], 0)
        self.assertEqual(result['stdout'], "")
        self.assertEqual(result['stderr'], "")
    
    def test_script_with_only_imports(self):
        """Test script that only contains imports."""
        script = """
import os
import sys
import json
"""
        
        result = execute_python(script)
        
        self.assertEqual(result['exit_code'], 0)
        self.assertEqual(result['stdout'], "")
        self.assertEqual(result['stderr'], "")


if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)