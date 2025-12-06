#!/usr/bin/env python3
"""
Phase 1 Tests: MUTATES Edge Extraction

Research spec reference: NSCCN_SPEC.md §3.2.2
"MUTATES: Function modifies a class attribute or global variable. 
Extracted by tracking assignments to self.X or module-level variables."

Implementation phase: NSCCN_PHASES.md Phase 1

These tests define acceptance criteria for MUTATES edge extraction.
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


class TestMutatesEdgeExtraction(unittest.TestCase):
    """
    Test MUTATES edge extraction per NSCCN_SPEC.md §3.2.2.
    
    MUTATES edges track state changes and data mutations:
    - Attribute assignments (obj.attr = value)
    - Self mutations (self.count += 1)
    - Dictionary updates (dict[key] = value)
    - List mutations (list.append(item))
    - Set mutations (set.add(item))
    """
    
    def setUp(self):
        """Set up test parser and database."""
        self.parser = CodeParser()
        self.temp_dir = tempfile.mkdtemp()
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()  # Fix for Windows: close handle so SQLite can open it
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
    
    def test_attribute_mutation(self):
        """
        Test case 1: Attribute mutation detection.
        Reference: NSCCN_PHASES.md Phase 1 - "user.email = email"
        
        Expected: MUTATES edge from update_user to user.email
        """
        code = '''
def update_user(user, email):
    """Update user email address."""
    user.email = email
    return user
'''
        result = self._parse_code(code)
        
        self.assertIsNotNone(result, "Parser should return result")
        
        # Find MUTATES edges
        mutates_edges = [e for e in result['edges'] if e[1] == 'MUTATES']
        
        self.assertGreater(
            len(mutates_edges), 0,
            "Should extract at least one MUTATES edge for attribute assignment"
        )
        
        # Verify edge points to the mutated attribute
        edge_targets = [e[2] for e in mutates_edges]
        self.assertTrue(
            any('email' in target for target in edge_targets),
            f"MUTATES edge should reference 'email' attribute, got: {edge_targets}"
        )
    
    def test_self_mutation(self):
        """
        Test case 2: Self mutation in class methods.
        Reference: NSCCN_PHASES.md Phase 1 - "self.count += 1"
        
        Expected: MUTATES edge from increment to self.count
        """
        code = '''
class Counter:
    """Simple counter class."""
    
    def __init__(self):
        self.count = 0
    
    def increment(self):
        """Increment counter by one."""
        self.count += 1
    
    def decrement(self):
        """Decrement counter by one."""
        self.count -= 1
'''
        result = self._parse_code(code)
        
        self.assertIsNotNone(result, "Parser should return result")
        
        # Find MUTATES edges from increment method
        mutates_edges = [e for e in result['edges'] if e[1] == 'MUTATES']
        
        # Should have at least 2 MUTATES edges (increment and decrement)
        self.assertGreaterEqual(
            len(mutates_edges), 2,
            f"Should extract MUTATES edges for self.count mutations, got {len(mutates_edges)} edges"
        )
        
        # Verify edges reference self.count
        edge_targets = [e[2] for e in mutates_edges]
        count_mutations = [t for t in edge_targets if 'count' in t]
        self.assertGreaterEqual(
            len(count_mutations), 2,
            f"Should have MUTATES edges to 'count' attribute, got: {edge_targets}"
        )
    
    def test_dictionary_mutation(self):
        """
        Test case 3: Dictionary mutation detection.
        Reference: NSCCN_PHASES.md Phase 1 - "config[key] = value"
        
        Expected: MUTATES edge for dictionary item assignment
        """
        code = '''
def set_config(config, key, value):
    """Set a configuration value."""
    config[key] = value

def update_config(config, updates):
    """Update multiple config values."""
    config.update(updates)
'''
        result = self._parse_code(code)
        
        self.assertIsNotNone(result, "Parser should return result")
        
        # Find MUTATES edges
        mutates_edges = [e for e in result['edges'] if e[1] == 'MUTATES']
        
        self.assertGreater(
            len(mutates_edges), 0,
            "Should extract MUTATES edges for dictionary mutations"
        )
        
        # Verify edges reference config
        edge_targets = [e[2] for e in mutates_edges]
        self.assertTrue(
            any('config' in target.lower() for target in edge_targets),
            f"MUTATES edge should reference 'config', got: {edge_targets}"
        )
    
    def test_list_mutation(self):
        """
        Test case 4: List mutation detection.
        Reference: NSCCN_PHASES.md Phase 1 - "items.append(item)"
        
        Expected: MUTATES edge for list.append() and other list mutations
        """
        code = '''
def add_item(items, item):
    """Add item to list."""
    items.append(item)

def add_multiple(items, new_items):
    """Add multiple items to list."""
    items.extend(new_items)

def insert_item(items, index, item):
    """Insert item at specific position."""
    items.insert(index, item)
'''
        result = self._parse_code(code)
        
        self.assertIsNotNone(result, "Parser should return result")
        
        # Find MUTATES edges
        mutates_edges = [e for e in result['edges'] if e[1] == 'MUTATES']
        
        # Should detect at least 3 list mutations (append, extend, insert)
        self.assertGreaterEqual(
            len(mutates_edges), 3,
            f"Should extract MUTATES edges for list mutations, got {len(mutates_edges)} edges"
        )
    
    def test_set_mutation(self):
        """
        Test case 5: Set mutation detection.
        Reference: Tree-sitter mutation patterns
        
        Expected: MUTATES edge for set.add() and set.update()
        """
        code = '''
def add_tag(tags, tag):
    """Add a tag to the set."""
    tags.add(tag)

def add_multiple_tags(tags, new_tags):
    """Add multiple tags."""
    tags.update(new_tags)
'''
        result = self._parse_code(code)
        
        self.assertIsNotNone(result, "Parser should return result")
        
        # Find MUTATES edges
        mutates_edges = [e for e in result['edges'] if e[1] == 'MUTATES']
        
        # Should detect at least 2 set mutations (add, update)
        self.assertGreaterEqual(
            len(mutates_edges), 2,
            f"Should extract MUTATES edges for set mutations, got {len(mutates_edges)} edges"
        )
    
    def test_global_variable_mutation(self):
        """
        Test case 6: Global variable mutation detection.
        Reference: NSCCN_SPEC.md §3.2.2 - "module-level variables"
        
        Expected: MUTATES edge for global variable assignments
        """
        code = '''
# Global variable
cache = {}

def update_cache(key, value):
    """Update global cache."""
    global cache
    cache[key] = value

def clear_cache():
    """Clear the global cache."""
    global cache
    cache = {}
'''
        result = self._parse_code(code)
        
        self.assertIsNotNone(result, "Parser should return result")
        
        # Find MUTATES edges
        mutates_edges = [e for e in result['edges'] if e[1] == 'MUTATES']
        
        self.assertGreater(
            len(mutates_edges), 0,
            "Should extract MUTATES edges for global variable mutations"
        )
        
        # Verify edges reference cache
        edge_targets = [e[2] for e in mutates_edges]
        self.assertTrue(
            any('cache' in target.lower() for target in edge_targets),
            f"MUTATES edge should reference 'cache', got: {edge_targets}"
        )
    
    def test_multiple_mutations_in_function(self):
        """
        Test case 7: Multiple mutations in single function.
        
        Expected: Multiple MUTATES edges for each mutation
        """
        code = '''
class User:
    """User model."""
    
    def update_profile(self, name, email, tags):
        """Update user profile with multiple fields."""
        self.name = name
        self.email = email
        self.tags.extend(tags)
        self.updated_at = time.time()
'''
        result = self._parse_code(code)
        
        self.assertIsNotNone(result, "Parser should return result")
        
        # Find MUTATES edges from update_profile
        mutates_edges = [e for e in result['edges'] if e[1] == 'MUTATES']
        
        # Should have at least 4 MUTATES edges (name, email, tags, updated_at)
        self.assertGreaterEqual(
            len(mutates_edges), 4,
            f"Should extract MUTATES edges for all attribute mutations, got {len(mutates_edges)} edges"
        )
    
    def test_mutation_edge_context(self):
        """
        Test case 8: MUTATES edge context information.
        Reference: NSCCN_PHASES.md Phase 1.2 - "Store line numbers and mutation type"
        
        Expected: Edge context contains line number information
        """
        code = '''
def update_user(user, email):
    """Update user email."""
    user.email = email  # Line 4
'''
        result = self._parse_code(code)
        
        self.assertIsNotNone(result, "Parser should return result")
        
        # Find MUTATES edges
        mutates_edges = [e for e in result['edges'] if e[1] == 'MUTATES']
        
        self.assertGreater(len(mutates_edges), 0, "Should have at least one MUTATES edge")
        
        # Verify edge has context (4th element in tuple)
        edge = mutates_edges[0]
        self.assertEqual(len(edge), 4, "Edge should have 4 elements: (source, relation, target, context)")
        
        # Context should contain line information or mutation details
        context = edge[3]
        if context:
            self.assertIsInstance(context, str, "Context should be a string")


class TestMutatesGraphTraversal(unittest.TestCase):
    """
    Test graph traversal with MUTATES edges for state tracking.
    Reference: NSCCN_SPEC.md §4.3 - trace_causal_path with direction='state'
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
    
    def test_state_traversal_direction(self):
        """
        Test traversing MUTATES edges with direction='state'.
        Reference: NSCCN_PHASES.md Phase 1.5 - "Test trace_causal_path with direction='state'"
        
        Expected: Can query "what code modifies this data?"
        """
        code = '''
class Counter:
    def __init__(self):
        self.count = 0
    
    def increment(self):
        self.count += 1
    
    def reset(self):
        self.count = 0
'''
        test_file = Path(self.temp_dir) / "counter.py"
        test_file.write_text(code)
        
        result = self.parser.parse_file(str(test_file))
        self.assertIsNotNone(result, "Parser should return result")
        
        # Store entities and edges in database
        if result['entities']:
            self.db.upsert_entities_batch(result['entities'])
        if result['edges']:
            self.db.upsert_edges_batch(result['edges'])
        
        # Query for MUTATES edges
        # Note: get_edges_by_relation doesn't exist yet, filter manually
        all_edges = []
        for entity in result['entities']:
            edges = self.db.get_edges_by_source(entity['id'])
            all_edges.extend(edges)
        mutates_edges = [e for e in all_edges if e['relation'] == 'MUTATES']
        
        # Verify MUTATES edges exist in database
        self.assertGreater(
            len(mutates_edges), 0,
            "Database should contain MUTATES edges for state tracking"
        )
    
    def test_upstream_state_query(self):
        """
        Test querying "who mutates this attribute?"
        
        Expected: Can trace back to functions that mutate a specific attribute
        """
        code = '''
class User:
    def __init__(self):
        self.email = ""
        self.name = ""
    
    def set_email(self, email):
        self.email = email
    
    def update_from_dict(self, data):
        if 'email' in data:
            self.email = data['email']
'''
        test_file = Path(self.temp_dir) / "user.py"
        test_file.write_text(code)
        
        result = self.parser.parse_file(str(test_file))
        self.assertIsNotNone(result, "Parser should return result")
        
        # Store in database
        if result['entities']:
            self.db.upsert_entities_batch(result['entities'])
        if result['edges']:
            self.db.upsert_edges_batch(result['edges'])
        
        # Query for functions that mutate email attribute
        # This tests the ability to answer: "What code modifies User.email?"
        # Get all edges from stored entities
        all_edges = []
        for entity in result['entities']:
            edges = self.db.get_edges_by_source(entity['id'])
            all_edges.extend(edges)
        mutates_edges = [e for e in all_edges 
                        if e['relation'] == 'MUTATES' and 'email' in e['target_id'].lower()]
        
        # Should find at least 2 functions that mutate email
        self.assertGreaterEqual(
            len(mutates_edges), 2,
            f"Should find multiple functions mutating email, got {len(mutates_edges)}"
        )


if __name__ == '__main__':
    unittest.main()
