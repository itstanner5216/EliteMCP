#!/usr/bin/env python3
"""
Phase 2 Tests: READS_CONFIG Edge Extraction

Research spec reference: NSCCN_SPEC.md §3.2.3
"READS_CONFIG: Function accesses a configuration constant. 
Extracted by tracking references to UPPERCASE_VARS, os.environ.get(), config file reads."

Implementation phase: NSCCN_PHASES.md Phase 2

These tests define acceptance criteria for READS_CONFIG edge extraction.
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


class TestReadsConfigEdgeExtraction(unittest.TestCase):
    """
    Test READS_CONFIG edge extraction per NSCCN_SPEC.md §3.2.3.
    
    READS_CONFIG edges track configuration dependencies:
    - Environment variables (os.environ.get(), os.environ[], os.getenv())
    - Config file reads (json.load(), yaml.load())
    - Settings imports (from config import X)
    - Uppercase constant references
    """
    
    def setUp(self):
        """Set up test parser and database."""
        self.parser = CodeParser()
        self.temp_dir = tempfile.mkdtemp()
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()  # Fix for Windows
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
    
    def test_os_environ_get(self):
        """
        Test case 1: os.environ.get() detection.
        Reference: NSCCN_PHASES.md Phase 2 - "os.environ.get()"
        
        Expected: READS_CONFIG edge to config:env:DATABASE_URL
        """
        code = '''
import os
def connect():
    """Connect to database using environment variable."""
    url = os.environ.get('DATABASE_URL')
    return url
'''
        result = self._parse_code(code)
        
        self.assertIsNotNone(result, "Parser should return result")
        
        # Find READS_CONFIG edges
        config_edges = [e for e in result['edges'] if e[1] == 'READS_CONFIG']
        
        self.assertGreater(
            len(config_edges), 0,
            "Should extract at least one READS_CONFIG edge for os.environ.get()"
        )
        
        # Verify edge points to the config entity
        edge_targets = [e[2] for e in config_edges]
        self.assertTrue(
            any('DATABASE_URL' in target for target in edge_targets),
            f"READS_CONFIG edge should reference 'DATABASE_URL', got: {edge_targets}"
        )
        
        # Verify it's an environment variable config
        self.assertTrue(
            any('config:env:' in target for target in edge_targets),
            f"Should use config:env: prefix, got: {edge_targets}"
        )
    
    def test_os_environ_subscript(self):
        """
        Test case 2: os.environ['VAR'] subscript access.
        Reference: NSCCN_PHASES.md Phase 2 - "os.environ[]"
        
        Expected: READS_CONFIG edge to config:env:API_KEY
        """
        code = '''
import os
def get_api_key():
    """Get API key from environment."""
    return os.environ['API_KEY']
'''
        result = self._parse_code(code)
        
        self.assertIsNotNone(result, "Parser should return result")
        
        config_edges = [e for e in result['edges'] if e[1] == 'READS_CONFIG']
        
        self.assertGreater(
            len(config_edges), 0,
            "Should extract READS_CONFIG edge for os.environ[] subscript"
        )
        
        edge_targets = [e[2] for e in config_edges]
        self.assertTrue(
            any('API_KEY' in target for target in edge_targets),
            f"READS_CONFIG edge should reference 'API_KEY', got: {edge_targets}"
        )
    
    def test_os_getenv(self):
        """
        Test case 3: os.getenv() detection.
        Reference: NSCCN_PHASES.md Phase 2 - "os.getenv()"
        
        Expected: READS_CONFIG edge to config:env:SECRET_KEY
        """
        code = '''
import os
def authenticate():
    """Authenticate using secret key."""
    key = os.getenv('SECRET_KEY')
    return validate(key)
'''
        result = self._parse_code(code)
        
        self.assertIsNotNone(result, "Parser should return result")
        
        config_edges = [e for e in result['edges'] if e[1] == 'READS_CONFIG']
        
        self.assertGreater(
            len(config_edges), 0,
            "Should extract READS_CONFIG edge for os.getenv()"
        )
        
        edge_targets = [e[2] for e in config_edges]
        self.assertTrue(
            any('SECRET_KEY' in target for target in edge_targets),
            f"READS_CONFIG edge should reference 'SECRET_KEY', got: {edge_targets}"
        )
    
    def test_uppercase_constant(self):
        """
        Test case 4: Uppercase constant reference detection.
        Reference: NSCCN_PHASES.md Phase 2 - "UPPERCASE variables"
        
        Expected: READS_CONFIG edge to config:const:DATABASE_URL
        """
        code = '''
DATABASE_URL = "postgres://localhost/db"

def connect():
    """Connect using constant."""
    return create_connection(DATABASE_URL)
'''
        result = self._parse_code(code)
        
        self.assertIsNotNone(result, "Parser should return result")
        
        config_edges = [e for e in result['edges'] if e[1] == 'READS_CONFIG']
        
        self.assertGreater(
            len(config_edges), 0,
            "Should extract READS_CONFIG edge for uppercase constant"
        )
        
        edge_targets = [e[2] for e in config_edges]
        self.assertTrue(
            any('DATABASE_URL' in target for target in edge_targets),
            f"READS_CONFIG edge should reference 'DATABASE_URL', got: {edge_targets}"
        )
        
        # Verify it's a constant config
        self.assertTrue(
            any('config:const:' in target for target in edge_targets),
            f"Should use config:const: prefix, got: {edge_targets}"
        )
    
    def test_multiple_config_reads(self):
        """
        Test case 5: Multiple configuration reads in one function.
        
        Expected: Multiple READS_CONFIG edges
        """
        code = '''
import os

DATABASE_URL = "default"

def setup():
    """Setup with multiple config sources."""
    db = os.environ.get('DATABASE_URL')
    api = os.getenv('API_KEY')
    fallback = DATABASE_URL
    return db, api, fallback
'''
        result = self._parse_code(code)
        
        self.assertIsNotNone(result, "Parser should return result")
        
        config_edges = [e for e in result['edges'] if e[1] == 'READS_CONFIG']
        
        # Should have at least 3 config reads
        self.assertGreaterEqual(
            len(config_edges), 3,
            f"Should extract READS_CONFIG edges for all config accesses, got {len(config_edges)} edges"
        )
    
    def test_config_edge_context(self):
        """
        Test case 6: READS_CONFIG edge context information.
        Reference: NSCCN_PHASES.md Phase 2.4 - "Context: Include access method"
        
        Expected: Edge context contains access method (e.g., "via os.environ.get()")
        """
        code = '''
import os
def connect():
    """Connect to database."""
    url = os.environ.get('DATABASE_URL')  # Line 5
'''
        result = self._parse_code(code)
        
        self.assertIsNotNone(result, "Parser should return result")
        
        config_edges = [e for e in result['edges'] if e[1] == 'READS_CONFIG']
        
        self.assertGreater(len(config_edges), 0, "Should have at least one READS_CONFIG edge")
        
        # Verify edge has context (4th element in tuple)
        edge = config_edges[0]
        self.assertEqual(len(edge), 4, "Edge should have 4 elements: (source, relation, target, context)")
        
        # Context should contain access method
        context = edge[3]
        if context:
            self.assertIsInstance(context, str, "Context should be a string")
            self.assertTrue(
                'via:' in context or 'line:' in context,
                f"Context should contain 'via:' or 'line:', got: {context}"
            )


class TestReadsConfigGraphTraversal(unittest.TestCase):
    """
    Test graph traversal with READS_CONFIG edges for dependency tracking.
    Reference: NSCCN_SPEC.md §4.3 - trace_causal_path with direction='config'
    """
    
    def setUp(self):
        """Set up test environment."""
        self.parser = CodeParser()
        self.temp_dir = tempfile.mkdtemp()
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()  # Fix for Windows
        self.db = NSCCNDatabase(self.temp_db.name)
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        self.db.close()
        os.unlink(self.temp_db.name)
        shutil.rmtree(self.temp_dir)
    
    def test_config_dependency_tracking(self):
        """
        Test tracking configuration dependencies in database.
        Reference: NSCCN_PHASES.md Phase 2.5 - "Config dependency graph"
        
        Expected: Can query "What code reads DATABASE_URL?"
        """
        code = '''
import os

def connect():
    """Connect to database."""
    url = os.environ.get('DATABASE_URL')
    return create_connection(url)

def reconnect():
    """Reconnect to database."""
    url = os.getenv('DATABASE_URL')
    return create_connection(url)
'''
        test_file = Path(self.temp_dir) / "db.py"
        test_file.write_text(code)
        
        result = self.parser.parse_file(str(test_file))
        self.assertIsNotNone(result, "Parser should return result")
        
        # Store entities and edges in database
        if result['entities']:
            self.db.upsert_entities_batch(result['entities'])
        if result['edges']:
            self.db.upsert_edges_batch(result['edges'])
        
        # Query for READS_CONFIG edges
        all_edges = []
        for entity in result['entities']:
            edges = self.db.get_edges_by_source(entity['id'])
            all_edges.extend(edges)
        config_edges = [e for e in all_edges if e['relation'] == 'READS_CONFIG']
        
        # Verify READS_CONFIG edges exist in database
        self.assertGreater(
            len(config_edges), 0,
            "Database should contain READS_CONFIG edges for config tracking"
        )
        
        # Verify we can find functions that read DATABASE_URL
        database_url_edges = [
            e for e in config_edges 
            if 'DATABASE_URL' in e['target_id']
        ]
        
        self.assertGreaterEqual(
            len(database_url_edges), 2,
            f"Should find multiple functions reading DATABASE_URL, got {len(database_url_edges)}"
        )


if __name__ == '__main__':
    unittest.main()
