#!/usr/bin/env python3
"""
Test suite for the sandbox execution engine (execute_code.py)
and directory intelligence tool (directory_tool.py)
"""

import unittest
import sys
import os
import tempfile
import time
import stat
import xml.etree.ElementTree as ET
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from execute_code import execute_python, cleanup_sandbox
from directory_tool import DirectoryIntelligenceTool


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

    def test_docker_output_normalization(self):
        """Test that Docker output is normalized correctly."""
        script = """
print("Test output to stdout")
print("Error output", file=sys.stderr)
"""
        result = execute_python(script)

        # Verify output handling
        self.assertIn("Test output to stdout", result['stdout'])
        # For Docker backend, stderr should be empty string
        self.assertEqual(result['stderr'], "")

    def test_daytona_capability_validation(self):
        """Test that missing Daytona capabilities are detected."""
        from unittest.mock import MagicMock

        # Create a mock workspace missing capabilities
        mock_workspace = MagicMock()
        del mock_workspace.fs  # Remove fs attribute
        del mock_workspace.exec  # Remove exec attribute
        del mock_workspace.remove  # Remove remove attribute

        # Import the sandbox engine class
        from execute_code import SandboxExecutionEngine

        engine = SandboxExecutionEngine.__new__(SandboxExecutionEngine)

        # Test capability checking
        with self.assertRaises(RuntimeError) as context:
            engine._check_daytona_capabilities(mock_workspace)

        # Should mention missing capabilities
        self.assertIn("workspace.fs", str(context.exception))
        self.assertIn("workspace.exec", str(context.exception))
        self.assertIn("workspace.remove", str(context.exception))


class TestDirectoryIntelligenceTool(unittest.TestCase):
    """Test suite for directory intelligence tool."""

    def test_unreadable_directory_warning(self):
        """Test that unreadable directories generate warnings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tool = DirectoryIntelligenceTool(tmpdir)

            # Create a subdirectory
            subdir = Path(tmpdir) / "restricted"
            subdir.mkdir()

            # Remove read permissions
            subdir.chmod(0o000)

            try:
                # Generate structure - should generate warning
                xml_output = tool.generate_xml_structure(expand_large=True)

                # Check that warning was generated
                self.assertTrue(len(tool.warnings) > 0)
                # Find unreadable_directory warning
                unreadable_warnings = [w for w in tool.warnings if 'unreadable_directory:' in w]
                self.assertTrue(len(unreadable_warnings) > 0)
            finally:
                # Restore permissions for cleanup
                subdir.chmod(0o755)

    def test_unreadable_file_warning(self):
        """Test that unreadable files generate warnings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tool = DirectoryIntelligenceTool(tmpdir)

            # Create a file
            test_file = Path(tmpdir) / "restricted.txt"
            test_file.write_text("test content")

            # Remove read permissions
            test_file.chmod(0o000)

            try:
                # Generate structure - should generate warning
                xml_output = tool.generate_xml_structure(expand_large=True)

                # Check that warning was generated
                self.assertTrue(len(tool.warnings) > 0)
                # Find unreadable_file warning
                unreadable_warnings = [w for w in tool.warnings if 'unreadable_file:' in w]
                self.assertTrue(len(unreadable_warnings) > 0)
            finally:
                # Restore permissions for cleanup
                test_file.chmod(0o644)

    def test_malformed_gitignore_warning(self):
        """Test that malformed .gitignore generates warnings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tool = DirectoryIntelligenceTool(tmpdir)

            # Create a malformed .gitignore
            gitignore = Path(tmpdir) / ".gitignore"
            gitignore.write_text("*[broken pattern\n")  # Deliberately malformed

            # Generate structure
            xml_output = tool.generate_xml_structure(expand_large=True)

            # Check that warning was generated
            self.assertTrue(len(tool.warnings) > 0)
            # Find malformed_gitignore warning
            malformed_warnings = [w for w in tool.warnings if 'malformed_gitignore:' in w]
            self.assertTrue(len(malformed_warnings) > 0)

    def test_ignore_rule_consolidation(self):
        """Test that ignore rules are properly consolidated."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tool = DirectoryIntelligenceTool(tmpdir)

            # Create test files/directories
            (Path(tmpdir) / "__pycache__").mkdir()  # Should be ignored (default)
            (Path(tmpdir) / ".hidden").mkdir()  # Should be ignored (top-level dotdir)
            (Path(tmpdir) / ".git").mkdir()  # Should be ignored (default)
            (Path(tmpdir) / "normal_file.txt").touch()
            (Path(tmpdir) / "normal_dir").mkdir()

            # Create custom .gitignore
            gitignore = Path(tmpdir) / ".gitignore"
            gitignore.write_text("custom_ignore\n")

            # Create custom_ignore file
            (Path(tmpdir) / "custom_ignore").touch()

            # Generate structure
            xml_output = tool.generate_xml_structure(expand_large=True)

            # Parse XML
            root = ET.fromstring(xml_output)

            # Find all file elements
            files = [elem.text for elem in root.iter() if elem.tag == 'file']
            dirs = [elem.get('name') for elem in root.iter() if elem.tag == 'dir']

            # Verify ignored items are not in output
            self.assertNotIn("custom_ignore", files)
            self.assertNotIn("__pycache__", dirs)
            self.assertNotIn(".hidden", dirs)
            self.assertNotIn(".git", dirs)

            # Verify non-ignored items are present
            self.assertIn("normal_file.txt", files)
            self.assertIn("normal_dir", dirs)

    def test_summary_threshold_logic(self):
        """Test that directories with > max_file_count produce summary."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tool = DirectoryIntelligenceTool(tmpdir)

            # Create a directory with many files
            test_dir = Path(tmpdir) / "large_directory"
            test_dir.mkdir()

            # Create 60 files (threshold is 50 by default)
            for i in range(60):
                (test_dir / f"file_{i}.txt").touch()

            # Generate structure
            xml_output = tool.generate_xml_structure(expand_large=False)

            # Parse XML
            root = ET.fromstring(xml_output)

            # Find the large_directory element
            large_dir_elem = None
            for elem in root.iter():
                if elem.tag == 'dir' and elem.get('name') == 'large_directory':
                    large_dir_elem = elem
                    break

            self.assertIsNotNone(large_dir_elem)

            # Should have summary element
            summary_elems = list(large_dir_elem.iter())
            summary_count = sum(1 for e in summary_elems if e.tag == 'summary')
            self.assertGreater(summary_count, 0)

    def test_symlink_loop_warning(self):
        """Test that symlink loops generate warnings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tool = DirectoryIntelligenceTool(tmpdir)

            # Create a file to link to
            target = Path(tmpdir) / "target.txt"
            target.touch()

            # Create a symlink that points to itself
            symlink = Path(tmpdir) / "self_link.txt"
            symlink.symlink_to(symlink)

            # Generate structure
            xml_output = tool.generate_xml_structure(expand_large=True)

            # Check that warning was generated
            self.assertTrue(len(tool.warnings) > 0)
            # Find symlink_loop warning
            symlink_warnings = [w for w in tool.warnings if 'symlink_loop:' in w]
            self.assertTrue(len(symlink_warnings) > 0)

    def test_warning_overflow(self):
        """Test that >100 warnings are truncated."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tool = DirectoryIntelligenceTool(tmpdir)

            # Create 105 unreadable files to trigger warnings
            for i in range(105):
                f = Path(tmpdir) / f"file_{i}.txt"
                f.touch()
                f.chmod(0o000)

            try:
                # Generate structure
                xml_output = tool.generate_xml_structure(expand_large=True)

                # Check that truncation warning exists
                truncation_warnings = [w for w in tool.warnings if 'too_many_warnings: truncated' in w]
                self.assertTrue(len(truncation_warnings) > 0)

                # Should still have many warnings (just not all 105)
                self.assertGreater(len(tool.warnings), 100)
            finally:
                # Restore permissions
                for i in range(105):
                    f = Path(tmpdir) / f"file_{i}.txt"
                    if f.exists():
                        f.chmod(0o644)


if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)