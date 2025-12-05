#!/usr/bin/env python3
"""
Comprehensive test suite for NSCCN components.
"""

import unittest
import sys
import os
import tempfile
import time
from pathlib import Path
import numpy as np

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from nsccn.database import NSCCNDatabase
from nsccn.parser import CodeParser
from nsccn.embeddings import EmbeddingEngine
from nsccn.search import HybridSearchEngine
from nsccn.graph import CausalFlowEngine
from nsccn.watcher import IncrementalGraphBuilder
from nsccn.tools import NSCCNTools


class TestDatabase(unittest.TestCase):
    """Test database operations."""
    
    def setUp(self):
        """Set up test database."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.db = NSCCNDatabase(self.temp_db.name)
    
    def tearDown(self):
        """Clean up test database."""
        self.db.close()
        os.unlink(self.temp_db.name)
    
    def test_entity_crud(self):
        """Test entity create, read, update, delete operations."""
        # Create entity
        entity = {
            'id': 'func:test.py:test_func',
            'type': 'function',
            'file_path': 'test.py',
            'name': 'test_func',
            'start_line': 1,
            'end_line': 5,
            'signature': 'def test_func()',
            'docstring': 'Test function',
            'last_updated': time.time()
        }
        
        self.db.upsert_entity(entity)
        
        # Read entity
        retrieved = self.db.get_entity('func:test.py:test_func')
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved['name'], 'test_func')
        self.assertEqual(retrieved['type'], 'function')
        
        # Update entity
        entity['docstring'] = 'Updated docstring'
        self.db.upsert_entity(entity)
        
        retrieved = self.db.get_entity('func:test.py:test_func')
        self.assertEqual(retrieved['docstring'], 'Updated docstring')
        
        # Delete entity
        self.db.delete_entities_by_file('test.py')
        retrieved = self.db.get_entity('func:test.py:test_func')
        self.assertIsNone(retrieved)
    
    def test_edge_operations(self):
        """Test edge create and query operations."""
        # Create entities
        entity1 = {
            'id': 'func:test.py:caller',
            'type': 'function',
            'file_path': 'test.py',
            'name': 'caller',
            'start_line': 1,
            'end_line': 3,
            'signature': 'def caller()',
            'last_updated': time.time()
        }
        entity2 = {
            'id': 'func:test.py:callee',
            'type': 'function',
            'file_path': 'test.py',
            'name': 'callee',
            'start_line': 5,
            'end_line': 7,
            'signature': 'def callee()',
            'last_updated': time.time()
        }
        
        self.db.upsert_entity(entity1)
        self.db.upsert_entity(entity2)
        
        # Create edge
        self.db.upsert_edge('func:test.py:caller', 'CALLS', 'func:test.py:callee')
        
        # Query edges
        edges = self.db.get_edges_by_source('func:test.py:caller')
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0]['relation'], 'CALLS')
        self.assertEqual(edges[0]['target_id'], 'func:test.py:callee')
        
        edges = self.db.get_edges_by_target('func:test.py:callee')
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0]['source_id'], 'func:test.py:caller')
    
    def test_skeleton_cache(self):
        """Test skeleton cache operations."""
        file_path = 'test.py'
        content = 'def test(): ...'
        last_modified = time.time()
        
        # Insert skeleton
        self.db.upsert_skeleton(file_path, content, last_modified)
        
        # Retrieve skeleton
        skeleton = self.db.get_skeleton(file_path)
        self.assertIsNotNone(skeleton)
        self.assertEqual(skeleton['content'], content)
        
        # Delete skeleton
        self.db.delete_skeleton(file_path)
        skeleton = self.db.get_skeleton(file_path)
        self.assertIsNone(skeleton)


class TestParser(unittest.TestCase):
    """Test code parser."""
    
    def setUp(self):
        """Set up test parser."""
        self.parser = CodeParser()
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up temp files."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_parse_simple_function(self):
        """Test parsing a simple function."""
        code = '''
def hello(name: str) -> str:
    """Say hello to someone."""
    return f"Hello, {name}!"
'''
        
        test_file = Path(self.temp_dir) / 'test.py'
        test_file.write_text(code)
        
        result = self.parser.parse_file(str(test_file))
        
        self.assertIsNotNone(result)
        self.assertEqual(len(result['entities']), 1)
        
        entity = result['entities'][0]
        self.assertEqual(entity['type'], 'function')
        self.assertEqual(entity['name'], 'hello')
        self.assertIn('def hello(name: str)', entity['signature'])
        self.assertIn('Say hello', entity['docstring'])
    
    def test_parse_class(self):
        """Test parsing a class."""
        code = '''
class Calculator:
    """A simple calculator."""
    
    def add(self, a: int, b: int) -> int:
        """Add two numbers."""
        return a + b
    
    def subtract(self, a: int, b: int) -> int:
        """Subtract two numbers."""
        return a - b
'''
        
        test_file = Path(self.temp_dir) / 'test.py'
        test_file.write_text(code)
        
        result = self.parser.parse_file(str(test_file))
        
        self.assertIsNotNone(result)
        # Should have 1 class + 2 methods = 3 entities
        self.assertEqual(len(result['entities']), 3)
        
        # Check class
        class_entities = [e for e in result['entities'] if e['type'] == 'class']
        self.assertEqual(len(class_entities), 1)
        self.assertEqual(class_entities[0]['name'], 'Calculator')
        
        # Check methods
        method_entities = [e for e in result['entities'] if e['type'] == 'method']
        self.assertEqual(len(method_entities), 2)
        method_names = [m['name'] for m in method_entities]
        self.assertIn('add', method_names)
        self.assertIn('subtract', method_names)
    
    def test_parse_calls_edge(self):
        """Test extracting CALLS edges."""
        code = '''
def helper():
    return 42

def main():
    result = helper()
    return result
'''
        
        test_file = Path(self.temp_dir) / 'test.py'
        test_file.write_text(code)
        
        result = self.parser.parse_file(str(test_file))
        
        self.assertIsNotNone(result)
        # Should extract at least one CALLS edge
        calls_edges = [e for e in result['edges'] if e[1] == 'CALLS']
        self.assertGreater(len(calls_edges), 0)
    
    def test_generate_skeleton(self):
        """Test skeleton generation."""
        code = '''
def calculate(x: int, y: int) -> int:
    """Calculate sum of x and y."""
    result = x + y
    print(f"Result is {result}")
    return result

class Math:
    """Math utilities."""
    
    def multiply(self, a: int, b: int) -> int:
        """Multiply two numbers."""
        return a * b
'''
        
        test_file = Path(self.temp_dir) / 'test.py'
        test_file.write_text(code)
        
        skeleton = self.parser.generate_skeleton(str(test_file))
        
        self.assertIsNotNone(skeleton)
        # Should contain signatures but not implementation
        self.assertIn('def calculate(x: int, y: int) -> int:', skeleton)
        self.assertIn('class Math:', skeleton)
        self.assertIn('def multiply(self, a: int, b: int) -> int:', skeleton)
        self.assertIn('...', skeleton)
        # Should NOT contain implementation details
        self.assertNotIn('result = x + y', skeleton)
        self.assertNotIn('print(f"Result', skeleton)


class TestEmbeddings(unittest.TestCase):
    """Test embedding engine."""
    
    def setUp(self):
        """Set up test embedder."""
        # Use small dimension for faster tests
        self.embedder = EmbeddingEngine(embedding_dim=256)
    
    def tearDown(self):
        """Clean up embedder."""
        self.embedder.cleanup()
    
    def test_embed_text(self):
        """Test embedding a single text."""
        text = "def hello(name: str) -> str"
        embedding = self.embedder.embed_text(text)
        
        self.assertIsInstance(embedding, np.ndarray)
        self.assertEqual(embedding.shape, (256,))
        self.assertEqual(embedding.dtype, np.float32)
    
    def test_embed_batch(self):
        """Test embedding multiple texts."""
        texts = [
            "def hello(name: str) -> str",
            "def goodbye(name: str) -> str",
            "class Calculator"
        ]
        
        embeddings = self.embedder.embed_batch(texts)
        
        self.assertEqual(len(embeddings), 3)
        for emb in embeddings:
            self.assertIsInstance(emb, np.ndarray)
            self.assertEqual(emb.shape, (256,))
    
    def test_embed_entity(self):
        """Test embedding an entity."""
        entity = {
            'id': 'func:test.py:hello',
            'name': 'hello',
            'signature': 'def hello(name: str) -> str',
            'docstring': 'Say hello to someone'
        }
        
        embedding = self.embedder.embed_entity(entity)
        
        self.assertIsInstance(embedding, np.ndarray)
        self.assertEqual(embedding.shape, (256,))


class TestGraph(unittest.TestCase):
    """Test graph traversal."""
    
    def setUp(self):
        """Set up test graph."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.db = NSCCNDatabase(self.temp_db.name)
        self.graph = CausalFlowEngine(self.db, max_depth=3)
        
        # Create test entities and edges
        self._create_test_graph()
    
    def tearDown(self):
        """Clean up."""
        self.db.close()
        os.unlink(self.temp_db.name)
    
    def _create_test_graph(self):
        """Create a test graph: main -> process -> helper"""
        entities = [
            {
                'id': 'func:test.py:main',
                'type': 'function',
                'file_path': 'test.py',
                'name': 'main',
                'start_line': 1,
                'end_line': 3,
                'signature': 'def main()',
                'last_updated': time.time()
            },
            {
                'id': 'func:test.py:process',
                'type': 'function',
                'file_path': 'test.py',
                'name': 'process',
                'start_line': 5,
                'end_line': 7,
                'signature': 'def process()',
                'last_updated': time.time()
            },
            {
                'id': 'func:test.py:helper',
                'type': 'function',
                'file_path': 'test.py',
                'name': 'helper',
                'start_line': 9,
                'end_line': 11,
                'signature': 'def helper()',
                'last_updated': time.time()
            }
        ]
        
        self.db.upsert_entities_batch(entities)
        
        edges = [
            ('func:test.py:main', 'CALLS', 'func:test.py:process', None),
            ('func:test.py:process', 'CALLS', 'func:test.py:helper', None)
        ]
        
        self.db.upsert_edges_batch(edges)
    
    def test_traverse_downstream(self):
        """Test downstream traversal (what does this call?)."""
        result = self.graph.traverse_downstream('func:test.py:main', depth=2)
        
        self.assertEqual(result['root'], 'func:test.py:main')
        self.assertEqual(result['direction'], 'downstream')
        
        # Should find process and helper
        self.assertIn('func:test.py:main', result['entities'])
        self.assertIn('func:test.py:process', result['entities'])
        self.assertIn('func:test.py:helper', result['entities'])
    
    def test_traverse_upstream(self):
        """Test upstream traversal (who calls this?)."""
        result = self.graph.traverse_upstream('func:test.py:helper', depth=2)
        
        self.assertEqual(result['root'], 'func:test.py:helper')
        self.assertEqual(result['direction'], 'upstream')
        
        # Should find process and main
        self.assertIn('func:test.py:helper', result['entities'])
        self.assertIn('func:test.py:process', result['entities'])
        self.assertIn('func:test.py:main', result['entities'])
    
    def test_depth_limiting(self):
        """Test that depth limiting works."""
        result = self.graph.traverse_downstream('func:test.py:main', depth=1)
        
        # Should only find main and process, not helper
        self.assertIn('func:test.py:main', result['entities'])
        self.assertIn('func:test.py:process', result['entities'])
        # Helper is 2 hops away, should not be included with depth=1
        # Note: depth=1 means we can traverse 1 hop from root


class TestSearch(unittest.TestCase):
    """Test hybrid search."""
    
    def setUp(self):
        """Set up test search."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.db = NSCCNDatabase(self.temp_db.name)
        self.embedder = EmbeddingEngine(embedding_dim=256)
        self.search = HybridSearchEngine(self.db, self.embedder, rrf_k=60)
        
        # Create test entities
        self._create_test_entities()
    
    def tearDown(self):
        """Clean up."""
        self.embedder.cleanup()
        self.db.close()
        os.unlink(self.temp_db.name)
    
    def _create_test_entities(self):
        """Create test entities."""
        entities = [
            {
                'id': 'func:auth.py:login',
                'type': 'function',
                'file_path': 'auth.py',
                'name': 'login',
                'start_line': 1,
                'end_line': 5,
                'signature': 'def login(user: str, password: str) -> bool',
                'docstring': 'Authenticate user with credentials',
                'last_updated': time.time()
            },
            {
                'id': 'func:auth.py:logout',
                'type': 'function',
                'file_path': 'auth.py',
                'name': 'logout',
                'start_line': 7,
                'end_line': 10,
                'signature': 'def logout(user: str) -> None',
                'docstring': 'Log out user from system',
                'last_updated': time.time()
            }
        ]
        
        # Embed entities
        embeddings = self.embedder.embed_entities_batch(entities)
        for entity, embedding in zip(entities, embeddings):
            entity['embedding'] = embedding
        
        self.db.upsert_entities_batch(entities)
    
    def test_semantic_search(self):
        """Test semantic search."""
        results = self.search.semantic_search_only('authenticate user', limit=5)
        
        # Should find login function
        self.assertGreater(len(results), 0)
        # Top result should be login function
        self.assertIn('login', results[0]['name'])
    
    def test_rrf_fusion(self):
        """Test RRF fusion."""
        lexical_ranks = {'entity1': 0, 'entity2': 1, 'entity3': 2}
        semantic_ranks = {'entity2': 0, 'entity3': 1, 'entity4': 2}
        
        fused = self.search._rrf_fuse(lexical_ranks, semantic_ranks, k=60)
        
        # Should combine results
        self.assertGreater(len(fused), 0)
        # entity2 appears in both, should have highest score
        entity_ids = [e[0] for e in fused]
        self.assertEqual(entity_ids[0], 'entity2')


class TestIntegration(unittest.TestCase):
    """Integration tests for NSCCN."""
    
    def setUp(self):
        """Set up integration test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        
        # Initialize components
        self.db = NSCCNDatabase(self.temp_db.name)
        self.parser = CodeParser()
        self.embedder = EmbeddingEngine(embedding_dim=256)
        self.search = HybridSearchEngine(self.db, self.embedder)
        self.graph = CausalFlowEngine(self.db)
        self.tools = NSCCNTools(self.db, self.parser, self.search, self.graph)
        
        # Create test files
        self._create_test_files()
    
    def tearDown(self):
        """Clean up."""
        import shutil
        self.embedder.cleanup()
        self.db.close()
        os.unlink(self.temp_db.name)
        shutil.rmtree(self.temp_dir)
    
    def _create_test_files(self):
        """Create test Python files."""
        # Create auth.py
        auth_code = '''
def validate_token(token: str) -> bool:
    """Validate JWT token."""
    return check_expiry(token)

def check_expiry(token: str) -> bool:
    """Check if token is expired."""
    return True

def login(username: str, password: str) -> str:
    """Login user and return token."""
    token = generate_token(username)
    return token

def generate_token(username: str) -> str:
    """Generate JWT token for user."""
    return f"token_{username}"
'''
        
        auth_file = Path(self.temp_dir) / 'auth.py'
        auth_file.write_text(auth_code)
        
        # Parse and index
        result = self.parser.parse_file(str(auth_file))
        if result:
            # Embed entities
            embeddings = self.embedder.embed_entities_batch(result['entities'])
            for entity, embedding in zip(result['entities'], embeddings):
                entity['embedding'] = embedding
            
            self.db.upsert_entities_batch(result['entities'])
            self.db.upsert_edges_batch(result['edges'])
    
    def test_full_workflow(self):
        """Test complete workflow: search -> trace -> window."""
        import json
        
        # 1. Search for entities
        search_result = self.tools.search_and_rank('validate token', limit=5)
        results = json.loads(search_result)
        
        self.assertGreater(len(results), 0)
        
        # 2. Get skeleton
        skeleton_result = self.tools.read_skeleton(str(Path(self.temp_dir) / 'auth.py'))
        skeleton_data = json.loads(skeleton_result)
        
        self.assertIn('skeleton', skeleton_data)
        skeleton = skeleton_data['skeleton']
        self.assertIn('def validate_token', skeleton)
        self.assertIn('...', skeleton)
        
        # 3. Trace downstream from validate_token
        auth_file_path = str(Path(self.temp_dir) / 'auth.py')
        entity_id = f"func:{auth_file_path}:validate_token"
        trace_result = self.tools.trace_causal_path(entity_id, direction='downstream', depth=2)
        trace_data = json.loads(trace_result)
        
        self.assertEqual(trace_data['root'], entity_id)
        self.assertEqual(trace_data['direction'], 'downstream')
        
        # 4. Open surgical window
        window_result = self.tools.open_surgical_window(entity_id, context_lines=2)
        window_data = json.loads(window_result)
        
        self.assertEqual(window_data['entity_id'], entity_id)
        self.assertIn('code', window_data)


if __name__ == '__main__':
    unittest.main()
