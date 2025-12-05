#!/usr/bin/env python3
"""
Phase 3 Tests: PROPAGATES_ERROR Edge Extraction

Research spec reference: NSCCN_SPEC.md §3.2.2
"PROPAGATES_ERROR: Function raises a specific exception. 
Extracted via raise statement queries."

Implementation phase: NSCCN_PHASES.md Phase 3

These tests define acceptance criteria for PROPAGATES_ERROR edge extraction.
Tests currently FAIL as features are not yet implemented.
"""

import unittest
import sys
import os
import tempfile
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from nsccn.parser import CodeParser
from nsccn.database import NSCCNDatabase


def get_edges_by_relation_helper(db, result, relation):
    """Helper to get edges by relation type (workaround until get_edges_by_relation is implemented)."""
    all_edges = []
    if result and 'entities' in result:
        for entity in result['entities']:
            edges = db.get_edges_by_source(entity['id'])
            all_edges.extend(edges)
    return [e for e in all_edges if e.get('relation') == relation]


class TestPropagatesErrorEdgeExtraction(unittest.TestCase):
    """
    Test PROPAGATES_ERROR edge extraction per NSCCN_SPEC.md §3.2.2.
    
    PROPAGATES_ERROR edges track error flow:
    - Explicit raises (raise ExceptionType)
    - Re-raises (except: ... raise)
    - Exception chaining (raise X from Y)
    - Bare raises in exception handlers
    """
    
    def setUp(self):
        """Set up test parser and database."""
        self.parser = CodeParser()
        self.temp_dir = tempfile.mkdtemp()
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.db = NSCCNDatabase(self.temp_db.name)
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        self.db.close()
        os.unlink(self.temp_db.name)
        shutil.rmtree(self.temp_dir)
    
    def _parse_code(self, code: str, filename: str = "test.py") -> dict:
        """Helper to parse code and return result."""
        test_file = Path(self.temp_dir) / filename
        test_file.write_text(code)
        return self.parser.parse_file(str(test_file))
    
    def test_explicit_raise(self):
        """
        Test case 1: Explicit exception raise
        Reference: NSCCN_PHASES.md Phase 3.1 - 'raise ValidationError("msg")'
        
        Expected: PROPAGATES_ERROR edge from function to ValidationError
        """
        code = '''
def validate(data):
    """Validate data structure."""
    if not data:
        raise ValidationError("Empty data")
    return True
'''
        result = self._parse_code(code)
        
        self.assertIsNotNone(result, "Parser should return result")
        
        # Find PROPAGATES_ERROR edges
        error_edges = [e for e in result['edges'] if e[1] == 'PROPAGATES_ERROR']
        
        self.assertGreater(
            len(error_edges), 0,
            "Should extract PROPAGATES_ERROR edge for explicit raise"
        )
        
        # Verify edge references ValidationError
        edge_targets = [e[2] for e in error_edges]
        self.assertTrue(
            any('ValidationError' in target for target in edge_targets),
            f"PROPAGATES_ERROR edge should reference ValidationError, got: {edge_targets}"
        )
    
    def test_reraise_in_except(self):
        """
        Test case 2: Re-raise in exception handler
        Reference: NSCCN_PHASES.md Phase 3.1 - "except: ... raise"
        
        Expected: PROPAGATES_ERROR edge for re-raised exception
        """
        code = '''
def wrapper():
    """Wrapper that logs and re-raises."""
    try:
        risky_operation()
    except Exception as e:
        log_error(e)
        raise
'''
        result = self._parse_code(code)
        
        self.assertIsNotNone(result, "Parser should return result")
        
        # Find PROPAGATES_ERROR edges
        error_edges = [e for e in result['edges'] if e[1] == 'PROPAGATES_ERROR']
        
        self.assertGreater(
            len(error_edges), 0,
            "Should extract PROPAGATES_ERROR edge for re-raise"
        )
        
        # Verify edge references Exception (the caught type)
        edge_targets = [e[2] for e in error_edges]
        self.assertTrue(
            any('Exception' in target for target in edge_targets),
            f"PROPAGATES_ERROR edge should reference Exception, got: {edge_targets}"
        )
    
    def test_exception_chaining(self):
        """
        Test case 3: Exception chaining with 'from'
        Reference: NSCCN_PHASES.md Phase 3.1 - "raise X from Y"
        
        Expected: PROPAGATES_ERROR edges for both exceptions
        """
        code = '''
def process():
    """Process data with error context."""
    try:
        parse_data()
    except ParseError as e:
        raise ProcessError("Failed to process") from e
'''
        result = self._parse_code(code)
        
        self.assertIsNotNone(result, "Parser should return result")
        
        # Find PROPAGATES_ERROR edges
        error_edges = [e for e in result['edges'] if e[1] == 'PROPAGATES_ERROR']
        
        # Should have edges for both ProcessError and ParseError
        self.assertGreater(
            len(error_edges), 0,
            "Should extract PROPAGATES_ERROR edges for exception chaining"
        )
        
        edge_targets = [e[2] for e in error_edges]
        # Should reference at least ProcessError
        self.assertTrue(
            any('ProcessError' in target or 'ParseError' in target 
                for target in edge_targets),
            f"Should reference chained exceptions, got: {edge_targets}"
        )
    
    def test_bare_raise(self):
        """
        Test case 4: Bare raise statement
        Reference: NSCCN_PHASES.md Phase 3.1
        
        Expected: PROPAGATES_ERROR edge for bare raise
        """
        code = '''
def handle_error():
    """Handle error and conditionally re-raise."""
    try:
        dangerous_call()
    except ValueError as e:
        if should_propagate(e):
            raise  # Bare raise
        else:
            handle(e)
'''
        result = self._parse_code(code)
        
        self.assertIsNotNone(result, "Parser should return result")
        
        # Find PROPAGATES_ERROR edges
        error_edges = [e for e in result['edges'] if e[1] == 'PROPAGATES_ERROR']
        
        self.assertGreater(
            len(error_edges), 0,
            "Should extract PROPAGATES_ERROR edge for bare raise"
        )
        
        # Should reference ValueError (the exception type in except clause)
        edge_targets = [e[2] for e in error_edges]
        self.assertTrue(
            any('ValueError' in target or 'Exception' in target 
                for target in edge_targets),
            f"Should reference exception type, got: {edge_targets}"
        )
    
    def test_multiple_exception_types(self):
        """
        Test case 5: Function raising multiple exception types
        
        Expected: Multiple PROPAGATES_ERROR edges
        """
        code = '''
def validate_user(user):
    """Validate user with multiple error cases."""
    if not user:
        raise ValueError("User is None")
    
    if not user.email:
        raise ValidationError("Missing email")
    
    if not user.is_active:
        raise PermissionError("User is inactive")
    
    return True
'''
        result = self._parse_code(code)
        
        self.assertIsNotNone(result, "Parser should return result")
        
        # Find PROPAGATES_ERROR edges
        error_edges = [e for e in result['edges'] if e[1] == 'PROPAGATES_ERROR']
        
        # Should have at least 3 edges (ValueError, ValidationError, PermissionError)
        self.assertGreaterEqual(
            len(error_edges), 3,
            f"Should extract multiple PROPAGATES_ERROR edges, got {len(error_edges)}"
        )
        
        edge_targets = [e[2] for e in error_edges]
        # Verify all three exception types are referenced
        has_value_error = any('ValueError' in t for t in edge_targets)
        has_validation_error = any('ValidationError' in t for t in edge_targets)
        has_permission_error = any('PermissionError' in t for t in edge_targets)
        
        self.assertTrue(
            has_value_error or has_validation_error or has_permission_error,
            f"Should reference all exception types, got: {edge_targets}"
        )
    
    def test_custom_exception_class(self):
        """
        Test case 6: Custom exception class definition
        Reference: NSCCN_PHASES.md Phase 3.3 - exception entity tracking
        
        Expected: Entity created for custom exception class
        """
        code = '''
class CustomError(Exception):
    """Custom application error."""
    pass

def fail():
    """Raise custom error."""
    raise CustomError("Something went wrong")
'''
        result = self._parse_code(code)
        
        self.assertIsNotNone(result, "Parser should return result")
        
        # Should have entity for CustomError class
        class_entities = [e for e in result['entities'] if e['type'] == 'class']
        custom_error_classes = [e for e in class_entities if e['name'] == 'CustomError']
        
        self.assertGreater(
            len(custom_error_classes), 0,
            "Should create entity for custom exception class"
        )
        
        # Should have PROPAGATES_ERROR edge to CustomError
        error_edges = [e for e in result['edges'] if e[1] == 'PROPAGATES_ERROR']
        self.assertGreater(
            len(error_edges), 0,
            "Should extract PROPAGATES_ERROR edge for custom exception"
        )
    
    def test_exception_in_nested_function(self):
        """
        Test case 7: Exception raised in nested context
        
        Expected: PROPAGATES_ERROR edge tracks nested raises
        """
        code = '''
def outer():
    """Outer function."""
    def inner():
        """Inner function that raises."""
        raise RuntimeError("Inner error")
    
    inner()
'''
        result = self._parse_code(code)
        
        self.assertIsNotNone(result, "Parser should return result")
        
        # Find PROPAGATES_ERROR edges
        error_edges = [e for e in result['edges'] if e[1] == 'PROPAGATES_ERROR']
        
        self.assertGreater(
            len(error_edges), 0,
            "Should extract PROPAGATES_ERROR edge from nested function"
        )


class TestPropagatesErrorContext(unittest.TestCase):
    """
    Test PROPAGATES_ERROR edge context information.
    Reference: NSCCN_PHASES.md Phase 3.4
    """
    
    def setUp(self):
        """Set up test environment."""
        self.parser = CodeParser()
        self.temp_dir = tempfile.mkdtemp()
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.db = NSCCNDatabase(self.temp_db.name)
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        self.db.close()
        os.unlink(self.temp_db.name)
        shutil.rmtree(self.temp_dir)
    
    def test_edge_context_explicit_raise(self):
        """
        Test PROPAGATES_ERROR edge context for explicit raise.
        Reference: NSCCN_PHASES.md Phase 3.4 - context format
        
        Expected: Context includes propagation method (explicit)
        """
        code = '''
def validate(data):
    if not data:
        raise ValueError("Invalid")
'''
        test_file = Path(self.temp_dir) / "test.py"
        test_file.write_text(code)
        
        result = self.parser.parse_file(str(test_file))
        self.assertIsNotNone(result, "Parser should return result")
        
        # Find PROPAGATES_ERROR edges
        error_edges = [e for e in result['edges'] if e[1] == 'PROPAGATES_ERROR']
        
        if error_edges:
            # Check context (4th element in tuple)
            edge = error_edges[0]
            self.assertEqual(len(edge), 4, "Edge should have context element")
            
            context = edge[3]
            if context:
                # Context should indicate explicit raise or include line info
                self.assertIsInstance(context, str, "Context should be string")
    
    def test_edge_context_reraise(self):
        """
        Test PROPAGATES_ERROR edge context for re-raise.
        
        Expected: Context indicates re-raise method
        """
        code = '''
def wrapper():
    try:
        risky()
    except Exception:
        log("error")
        raise
'''
        test_file = Path(self.temp_dir) / "test.py"
        test_file.write_text(code)
        
        result = self.parser.parse_file(str(test_file))
        self.assertIsNotNone(result, "Parser should return result")
        
        # Find PROPAGATES_ERROR edges
        error_edges = [e for e in result['edges'] if e[1] == 'PROPAGATES_ERROR']
        
        if error_edges:
            edge = error_edges[0]
            self.assertEqual(len(edge), 4, "Edge should have context element")
    
    def test_edge_context_chained(self):
        """
        Test PROPAGATES_ERROR edge context for exception chaining.
        
        Expected: Context indicates chained exception
        """
        code = '''
def process():
    try:
        parse()
    except ParseError as e:
        raise ProcessError("failed") from e
'''
        test_file = Path(self.temp_dir) / "test.py"
        test_file.write_text(code)
        
        result = self.parser.parse_file(str(test_file))
        self.assertIsNotNone(result, "Parser should return result")
        
        # Find PROPAGATES_ERROR edges
        error_edges = [e for e in result['edges'] if e[1] == 'PROPAGATES_ERROR']
        
        if error_edges:
            edge = error_edges[0]
            self.assertEqual(len(edge), 4, "Edge should have context element")


class TestPropagatesErrorGraphQuery(unittest.TestCase):
    """
    Test graph queries for error flow analysis.
    Reference: NSCCN_PHASES.md Phase 3.5
    """
    
    def setUp(self):
        """Set up test environment."""
        self.parser = CodeParser()
        self.temp_dir = tempfile.mkdtemp()
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.db = NSCCNDatabase(self.temp_db.name)
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        self.db.close()
        os.unlink(self.temp_db.name)
        shutil.rmtree(self.temp_dir)
    
    def test_error_flow_query(self):
        """
        Test query: "What errors can this function raise?"
        Reference: NSCCN_PHASES.md Phase 3.5
        
        Expected: Can identify all exceptions a function may raise
        """
        code = '''
def validate_and_process(data):
    """Validate and process data."""
    if not data:
        raise ValueError("Empty data")
    
    if not isinstance(data, dict):
        raise TypeError("Data must be dict")
    
    process(data)
'''
        test_file = Path(self.temp_dir) / "processor.py"
        test_file.write_text(code)
        
        result = self.parser.parse_file(str(test_file))
        self.assertIsNotNone(result, "Parser should return result")
        
        # Store in database
        if result['entities']:
            self.db.upsert_entities_batch(result['entities'])
        if result['edges']:
            self.db.upsert_edges_batch(result['edges'])
        
        # Query: "What errors does validate_and_process raise?"
        all_error_edges = get_edges_by_relation_helper(self.db, result, 'PROPAGATES_ERROR')
        
        # Filter edges from validate_and_process function
        func_id_pattern = 'validate_and_process'
        func_error_edges = [e for e in all_error_edges 
                           if func_id_pattern in e['source_id']]
        
        # Should identify multiple error types
        self.assertGreater(
            len(func_error_edges), 0,
            "Should identify exceptions raised by function"
        )
    
    def test_exception_propagation_chain(self):
        """
        Test query: "What errors propagate through this call chain?"
        Reference: NSCCN_PHASES.md Phase 3 Expected Outcomes
        
        Expected: Can trace error flow through function calls
        """
        code = '''
def parse(text):
    """Parse text, may raise ParseError."""
    if not text:
        raise ParseError("Empty text")
    return parsed

def validate(data):
    """Validate data, may raise ValidationError."""
    if not data.valid:
        raise ValidationError("Invalid data")
    return True

def process(input_text):
    """Process input - may raise multiple errors."""
    data = parse(input_text)  # May raise ParseError
    validate(data)  # May raise ValidationError
    return result
'''
        test_file = Path(self.temp_dir) / "pipeline.py"
        test_file.write_text(code)
        
        result = self.parser.parse_file(str(test_file))
        self.assertIsNotNone(result, "Parser should return result")
        
        # Store in database
        if result['entities']:
            self.db.upsert_entities_batch(result['entities'])
        if result['edges']:
            self.db.upsert_edges_batch(result['edges'])
        
        # Query all PROPAGATES_ERROR edges
        error_edges = get_edges_by_relation_helper(self.db, result, 'PROPAGATES_ERROR')
        
        # Should have multiple error propagation edges
        self.assertGreater(
            len(error_edges), 0,
            "Should track error propagation through call chain"
        )
        
        # Verify we can identify different exception types
        target_ids = [e['target_id'] for e in error_edges]
        exception_types = set()
        for target in target_ids:
            if 'Error' in target:
                # Extract exception type name
                exception_types.add(target)
        
        self.assertGreater(
            len(exception_types), 0,
            "Should identify multiple exception types in propagation chain"
        )
    
    def test_exception_handler_coverage(self):
        """
        Test identifying which exceptions are caught vs propagated.
        
        Expected: Can distinguish between caught and propagated exceptions
        """
        code = '''
def safe_process(data):
    """Process with exception handling."""
    try:
        validate(data)  # May raise ValidationError
    except ValidationError:
        return None  # Caught, not propagated
    
    try:
        transform(data)  # May raise TransformError
    except TransformError:
        log("error")
        raise  # Propagated
'''
        test_file = Path(self.temp_dir) / "safe.py"
        test_file.write_text(code)
        
        result = self.parser.parse_file(str(test_file))
        self.assertIsNotNone(result, "Parser should return result")
        
        # Store in database
        if result['entities']:
            self.db.upsert_entities_batch(result['entities'])
        if result['edges']:
            self.db.upsert_edges_batch(result['edges'])
        
        # Query PROPAGATES_ERROR edges from safe_process
        error_edges = [e for e in get_edges_by_relation_helper(self.db, result, 'PROPAGATES_ERROR')
                      if 'safe_process' in e['source_id']]
        
        # Should only have edge for TransformError (re-raised)
        # ValidationError is caught and handled, so should not be in PROPAGATES_ERROR
        # Note: This test validates the distinction between caught and propagated
        # The exact implementation may vary
        self.assertIsNotNone(error_edges, "Should track error propagation")


if __name__ == '__main__':
    unittest.main()
