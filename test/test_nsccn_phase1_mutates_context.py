#!/usr/bin/env python3
"""
Phase 1 Tests: MUTATES Edge Context Verification

This test suite specifically validates the format and content of the 
context string attached to MUTATES edges.

Format spec: "line:<line_number> type:<mutation_type>"
"""

import unittest
import sys
import os
import tempfile
import re
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from nsccn.parser import CodeParser

class TestMutatesContext(unittest.TestCase):
    
    def setUp(self):
        self.parser = CodeParser()
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def _parse_code(self, code: str) -> dict:
        test_file = Path(self.temp_dir) / "test_context.py"
        test_file.write_text(code)
        return self.parser.parse_file(str(test_file))
    
    def test_assignment_context(self):
        """Verify context for simple assignment."""
        code = """
def func(x):
    x = 1  # line 3
"""
        result = self._parse_code(code)
        mutates = [e for e in result['edges'] if e[1] == 'MUTATES']
        
        self.assertTrue(mutates, "Should detect assignment")
        context = mutates[0][3]
        
        # Expect: "line:3 type:assignment"
        self.assertRegex(context, r"line:3 type:assignment")
    
    def test_augmented_assignment_context(self):
        """Verify context for augmented assignment."""
        code = """
def func(x):
    x += 1  # line 3
"""
        result = self._parse_code(code)
        mutates = [e for e in result['edges'] if e[1] == 'MUTATES']
        
        self.assertTrue(mutates)
        context = mutates[0][3]
        
        # Expect: "line:3 type:augmented_assignment"
        self.assertRegex(context, r"line:3 type:augmented_assignment")

    def test_method_call_context(self):
        """Verify context for mutating method call."""
        code = """
def func(lst):
    lst.append(1)  # line 3
"""
        result = self._parse_code(code)
        mutates = [e for e in result['edges'] if e[1] == 'MUTATES']
        
        self.assertTrue(mutates)
        context = mutates[0][3]
        
        # Expect: "line:3 type:method_call"
        self.assertRegex(context, r"line:3 type:method_call")

if __name__ == '__main__':
    unittest.main()
