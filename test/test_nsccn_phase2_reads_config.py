#!/usr/bin/env python3
"""
Phase 2 Tests: READS_CONFIG Edge Extraction

Research spec reference: NSCCN_SPEC.md §3.2.2
"READS_CONFIG: Function accesses a configuration constant. 
Extracted by tracking references to UPPERCASE_VARS."

Implementation phase: NSCCN_PHASES.md Phase 2

These tests define acceptance criteria for READS_CONFIG edge extraction.
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
from test_nsccn_helpers import get_edges_by_relation_helper


class TestReadsConfigEdgeExtraction(unittest.TestCase):
    """
    Test READS_CONFIG edge extraction per NSCCN_SPEC.md §3.2.2.
    
    READS_CONFIG edges track configuration dependencies:
    - Environment variables (os.environ.get)
    - Config file reads (json.load, yaml.load)
    - Settings imports (from config import X)
    - Uppercase constant references
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
    
    def test_environ_get_detection(self):
        """
        Test case 1: Environment variable access via os.environ.get()
        Reference: NSCCN_PHASES.md Phase 2.1 - "os.environ.get('DATABASE_URL')"
        
        Expected: READS_CONFIG edge to config:env:DATABASE_URL
        """
        code = '''
import os

def connect_database():
    """Connect to database using environment variable."""
    url = os.environ.get('DATABASE_URL')
    return create_connection(url)
'''
        result = self._parse_code(code)
        
        self.assertIsNotNone(result, "Parser should return result")
        
        # Find READS_CONFIG edges
        config_edges = [e for e in result['edges'] if e[1] == 'READS_CONFIG']
        
        self.assertGreater(
            len(config_edges), 0,
            "Should extract READS_CONFIG edge for os.environ.get()"
        )
        
        # Verify edge references DATABASE_URL
        edge_targets = [e[2] for e in config_edges]
        self.assertTrue(
            any('DATABASE_URL' in target for target in edge_targets),
            f"READS_CONFIG edge should reference DATABASE_URL, got: {edge_targets}"
        )
    
    def test_environ_subscript_detection(self):
        """
        Test case 2: Environment variable access via os.environ[]
        Reference: NSCCN_PHASES.md Phase 2.1
        
        Expected: READS_CONFIG edge for direct environment access
        """
        code = '''
import os

def get_secret_key():
    """Get secret key from environment."""
    return os.environ['SECRET_KEY']
'''
        result = self._parse_code(code)
        
        self.assertIsNotNone(result, "Parser should return result")
        
        # Find READS_CONFIG edges
        config_edges = [e for e in result['edges'] if e[1] == 'READS_CONFIG']
        
        self.assertGreater(
            len(config_edges), 0,
            "Should extract READS_CONFIG edge for os.environ[]"
        )
        
        # Verify edge references SECRET_KEY
        edge_targets = [e[2] for e in config_edges]
        self.assertTrue(
            any('SECRET_KEY' in target for target in edge_targets),
            f"READS_CONFIG edge should reference SECRET_KEY, got: {edge_targets}"
        )
    
    def test_getenv_detection(self):
        """
        Test case 3: Environment variable access via os.getenv()
        Reference: NSCCN_PHASES.md Phase 2.1
        
        Expected: READS_CONFIG edge for os.getenv()
        """
        code = '''
import os

def get_debug_mode():
    """Get debug mode from environment."""
    return os.getenv('DEBUG', 'false')
'''
        result = self._parse_code(code)
        
        self.assertIsNotNone(result, "Parser should return result")
        
        # Find READS_CONFIG edges
        config_edges = [e for e in result['edges'] if e[1] == 'READS_CONFIG']
        
        self.assertGreater(
            len(config_edges), 0,
            "Should extract READS_CONFIG edge for os.getenv()"
        )
        
        # Verify edge references DEBUG
        edge_targets = [e[2] for e in config_edges]
        self.assertTrue(
            any('DEBUG' in target for target in edge_targets),
            f"READS_CONFIG edge should reference DEBUG, got: {edge_targets}"
        )
    
    def test_json_config_load(self):
        """
        Test case 4: Config file read via json.load()
        Reference: NSCCN_PHASES.md Phase 2.1 - "json.load(f)"
        
        Expected: READS_CONFIG edge to config:file:config.json
        """
        code = '''
import json

def load_settings():
    """Load settings from JSON file."""
    with open('config.json') as f:
        config = json.load(f)
    return config
'''
        result = self._parse_code(code)
        
        self.assertIsNotNone(result, "Parser should return result")
        
        # Find READS_CONFIG edges
        config_edges = [e for e in result['edges'] if e[1] == 'READS_CONFIG']
        
        self.assertGreater(
            len(config_edges), 0,
            "Should extract READS_CONFIG edge for json.load()"
        )
        
        # Verify edge references config file
        edge_targets = [e[2] for e in config_edges]
        self.assertTrue(
            any('config.json' in target.lower() or 'json' in target.lower() 
                for target in edge_targets),
            f"READS_CONFIG edge should reference config file, got: {edge_targets}"
        )
    
    def test_yaml_config_load(self):
        """
        Test case 5: Config file read via yaml.load()
        Reference: NSCCN_PHASES.md Phase 2.1
        
        Expected: READS_CONFIG edge for YAML config access
        """
        code = '''
import yaml

def load_config():
    """Load configuration from YAML file."""
    with open('config.yaml') as f:
        return yaml.safe_load(f)
'''
        result = self._parse_code(code)
        
        self.assertIsNotNone(result, "Parser should return result")
        
        # Find READS_CONFIG edges
        config_edges = [e for e in result['edges'] if e[1] == 'READS_CONFIG']
        
        self.assertGreater(
            len(config_edges), 0,
            "Should extract READS_CONFIG edge for yaml.load()"
        )
    
    def test_settings_import(self):
        """
        Test case 6: Settings import detection
        Reference: NSCCN_PHASES.md Phase 2.1 - "from config import SECRET_KEY"
        
        Expected: READS_CONFIG edge for imported settings
        """
        code = '''
from config import SECRET_KEY, DATABASE_URL

def authenticate(token):
    """Authenticate using secret key."""
    return verify(token, SECRET_KEY)
'''
        result = self._parse_code(code)
        
        self.assertIsNotNone(result, "Parser should return result")
        
        # Find READS_CONFIG edges
        config_edges = [e for e in result['edges'] if e[1] == 'READS_CONFIG']
        
        # Should detect at least one config import
        self.assertGreater(
            len(config_edges), 0,
            "Should extract READS_CONFIG edge for settings imports"
        )
        
        # Verify edges reference imported constants
        edge_targets = [e[2] for e in config_edges]
        config_refs = [t for t in edge_targets 
                      if 'SECRET_KEY' in t or 'DATABASE_URL' in t]
        self.assertGreater(
            len(config_refs), 0,
            f"Should reference imported constants, got: {edge_targets}"
        )
    
    def test_uppercase_constant_reference(self):
        """
        Test case 7: Uppercase constant reference
        Reference: NSCCN_SPEC.md §3.2.2 - "UPPERCASE_VARS"
        
        Expected: READS_CONFIG edge for uppercase constant usage
        """
        code = '''
# Configuration constants
MAX_CONNECTIONS = 100
TIMEOUT_SECONDS = 30

def create_pool():
    """Create connection pool with config values."""
    return Pool(
        max_connections=MAX_CONNECTIONS,
        timeout=TIMEOUT_SECONDS
    )
'''
        result = self._parse_code(code)
        
        self.assertIsNotNone(result, "Parser should return result")
        
        # Find READS_CONFIG edges
        config_edges = [e for e in result['edges'] if e[1] == 'READS_CONFIG']
        
        self.assertGreater(
            len(config_edges), 0,
            "Should extract READS_CONFIG edge for uppercase constant references"
        )
        
        # Verify edges reference constants
        edge_targets = [e[2] for e in config_edges]
        constant_refs = [t for t in edge_targets 
                        if 'MAX_CONNECTIONS' in t or 'TIMEOUT_SECONDS' in t]
        self.assertGreater(
            len(constant_refs), 0,
            f"Should reference uppercase constants, got: {edge_targets}"
        )
    
    def test_configparser_usage(self):
        """
        Test case 8: ConfigParser usage detection
        Reference: NSCCN_PHASES.md Phase 2.1 - "config.get(section, key)"
        
        Expected: READS_CONFIG edge for ConfigParser access
        """
        code = '''
import configparser

def load_database_config():
    """Load database configuration."""
    config = configparser.ConfigParser()
    config.read('settings.ini')
    return config.get('database', 'host')
'''
        result = self._parse_code(code)
        
        self.assertIsNotNone(result, "Parser should return result")
        
        # Find READS_CONFIG edges
        config_edges = [e for e in result['edges'] if e[1] == 'READS_CONFIG']
        
        self.assertGreater(
            len(config_edges), 0,
            "Should extract READS_CONFIG edge for ConfigParser usage"
        )
    
    def test_dotenv_access(self):
        """
        Test case 9: dotenv/load_dotenv detection
        Reference: NSCCN_PHASES.md Phase 2.1
        
        Expected: READS_CONFIG edge for .env file loading
        """
        code = '''
from dotenv import load_dotenv
import os

def initialize():
    """Initialize with environment from .env file."""
    load_dotenv()
    return os.getenv('API_KEY')
'''
        result = self._parse_code(code)
        
        self.assertIsNotNone(result, "Parser should return result")
        
        # Find READS_CONFIG edges
        config_edges = [e for e in result['edges'] if e[1] == 'READS_CONFIG']
        
        # Should detect both load_dotenv and os.getenv
        self.assertGreater(
            len(config_edges), 0,
            "Should extract READS_CONFIG edges for dotenv usage"
        )


class TestReadsConfigPseudoEntities(unittest.TestCase):
    """
    Test creation of pseudo-entities for configuration items.
    Reference: NSCCN_PHASES.md Phase 2.3
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
    
    def test_env_variable_entity_format(self):
        """
        Test pseudo-entity format for environment variables.
        Reference: NSCCN_PHASES.md Phase 2.3 - "config:env:DATABASE_URL"
        
        Expected: Entity ID follows config:env:{VAR_NAME} format
        """
        code = '''
import os

def connect():
    url = os.environ.get('DATABASE_URL')
    return url
'''
        test_file = Path(self.temp_dir) / "test.py"
        test_file.write_text(code)
        
        result = self.parser.parse_file(str(test_file))
        self.assertIsNotNone(result, "Parser should return result")
        
        # Store in database
        if result['entities']:
            self.db.upsert_entities_batch(result['entities'])
        if result['edges']:
            self.db.upsert_edges_batch(result['edges'])
        
        # Query for config entities
        # Pseudo-entities should be created with format config:env:*
        config_edges = [e for e in get_edges_by_relation_helper(self.db, result, 'READS_CONFIG')]
        
        if config_edges:
            # Check target ID format
            target_ids = [e['target_id'] for e in config_edges]
            env_entities = [t for t in target_ids if t.startswith('config:env:')]
            
            self.assertGreater(
                len(env_entities), 0,
                f"Should create pseudo-entities with config:env: prefix, got: {target_ids}"
            )
    
    def test_config_file_entity_format(self):
        """
        Test pseudo-entity format for config files.
        Reference: NSCCN_PHASES.md Phase 2.3 - "config:file:config/settings.json"
        
        Expected: Entity ID follows config:file:{PATH} format
        """
        code = '''
import json

def load_config():
    with open('config/settings.json') as f:
        return json.load(f)
'''
        test_file = Path(self.temp_dir) / "test.py"
        test_file.write_text(code)
        
        result = self.parser.parse_file(str(test_file))
        self.assertIsNotNone(result, "Parser should return result")
        
        # Store in database
        if result['entities']:
            self.db.upsert_entities_batch(result['entities'])
        if result['edges']:
            self.db.upsert_edges_batch(result['edges'])
        
        # Query for config file entities
        config_edges = [e for e in get_edges_by_relation_helper(self.db, result, 'READS_CONFIG')]
        
        if config_edges:
            target_ids = [e['target_id'] for e in config_edges]
            file_entities = [t for t in target_ids if 'config:file:' in t or 'json' in t.lower()]
            
            self.assertGreater(
                len(file_entities), 0,
                f"Should create pseudo-entities for config files, got: {target_ids}"
            )
    
    def test_constant_entity_format(self):
        """
        Test pseudo-entity format for settings constants.
        Reference: NSCCN_PHASES.md Phase 2.3 - "config:const:SECRET_KEY"
        
        Expected: Entity ID follows config:const:{NAME} format
        """
        code = '''
MAX_RETRIES = 3

def retry_operation():
    for i in range(MAX_RETRIES):
        try_operation()
'''
        test_file = Path(self.temp_dir) / "test.py"
        test_file.write_text(code)
        
        result = self.parser.parse_file(str(test_file))
        self.assertIsNotNone(result, "Parser should return result")
        
        # Store in database
        if result['entities']:
            self.db.upsert_entities_batch(result['entities'])
        if result['edges']:
            self.db.upsert_edges_batch(result['edges'])
        
        # Query for constant entities
        config_edges = [e for e in get_edges_by_relation_helper(self.db, result, 'READS_CONFIG')]
        
        if config_edges:
            target_ids = [e['target_id'] for e in config_edges]
            const_entities = [t for t in target_ids 
                             if 'config:const:' in t or 'MAX_RETRIES' in t]
            
            self.assertGreater(
                len(const_entities), 0,
                f"Should create pseudo-entities for constants, got: {target_ids}"
            )


class TestReadsConfigGraphQuery(unittest.TestCase):
    """
    Test graph queries for configuration dependencies.
    Reference: NSCCN_PHASES.md Phase 2.5
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
    
    def test_config_dependency_query(self):
        """
        Test query: "What code reads CONFIG_X?"
        Reference: NSCCN_PHASES.md Phase 2.5
        
        Expected: Can find all functions that read a specific config value
        """
        code = '''
import os

DATABASE_URL = os.environ.get('DATABASE_URL')

def connect():
    """Connect using DATABASE_URL."""
    return create_connection(DATABASE_URL)

def validate_config():
    """Validate DATABASE_URL is set."""
    return DATABASE_URL is not None
'''
        test_file = Path(self.temp_dir) / "db.py"
        test_file.write_text(code)
        
        result = self.parser.parse_file(str(test_file))
        self.assertIsNotNone(result, "Parser should return result")
        
        # Store in database
        if result['entities']:
            self.db.upsert_entities_batch(result['entities'])
        if result['edges']:
            self.db.upsert_edges_batch(result['edges'])
        
        # Query: "What code reads DATABASE_URL?"
        config_edges = [e for e in get_edges_by_relation_helper(self.db, result, 'READS_CONFIG') 
                       if 'DATABASE_URL' in e['target_id']]
        
        # Should find multiple functions reading DATABASE_URL
        self.assertGreater(
            len(config_edges), 0,
            "Should find functions reading DATABASE_URL config"
        )
    
    def test_impact_analysis_query(self):
        """
        Test query: "What breaks if I change this config?"
        Reference: NSCCN_PHASES.md Phase 2 Expected Outcomes
        
        Expected: Can trace config dependencies for impact analysis
        """
        code = '''
import os

API_KEY = os.getenv('API_KEY')

def authenticate():
    """Authenticate with API."""
    return verify_key(API_KEY)

def make_request(endpoint):
    """Make authenticated API request."""
    return request(endpoint, headers={'key': API_KEY})
'''
        test_file = Path(self.temp_dir) / "api.py"
        test_file.write_text(code)
        
        result = self.parser.parse_file(str(test_file))
        self.assertIsNotNone(result, "Parser should return result")
        
        # Store in database
        if result['entities']:
            self.db.upsert_entities_batch(result['entities'])
        if result['edges']:
            self.db.upsert_edges_batch(result['edges'])
        
        # Query all functions reading API_KEY
        api_key_readers = [e for e in get_edges_by_relation_helper(self.db, result, 'READS_CONFIG') 
                          if 'API_KEY' in e['target_id']]
        
        # Should identify all functions affected by API_KEY changes
        self.assertGreater(
            len(api_key_readers), 0,
            "Should identify functions dependent on API_KEY for impact analysis"
        )


if __name__ == '__main__':
    unittest.main()
