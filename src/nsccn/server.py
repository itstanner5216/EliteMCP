#!/usr/bin/env python3
"""
Main NSCCN server - integrates all components and exposes tools via FastMCP.
"""

import sys
import os
import json
import logging
import argparse
import signal
from pathlib import Path
from typing import Optional
from fastmcp import FastMCP

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from nsccn.database import NSCCNDatabase
from nsccn.parser import CodeParser
from nsccn.embeddings import EmbeddingEngine
from nsccn.search import HybridSearchEngine
from nsccn.graph import CausalFlowEngine
from nsccn.watcher import IncrementalGraphBuilder
from nsccn.tools import NSCCNTools

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NSCCNServer:
    """Main NSCCN server coordinating all components."""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the NSCCN server.
        
        Args:
            config_path: Path to configuration file
        """
        self.config = self._load_config(config_path)
        
        # Initialize components
        self.db = None
        self.parser = None
        self.embedder = None
        self.search = None
        self.graph = None
        self.watcher = None
        self.tools = None
        self.mcp = None
        
        logger.info("NSCCN Server initializing...")

    def _load_config(self, config_path: Optional[str]) -> dict:
        """Load configuration from file."""
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "config" / "nsccn_config.json"
        
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            logger.info(f"Configuration loaded from {config_path}")
            return config
        except Exception as e:
            logger.warning(f"Failed to load config: {e}, using defaults")
            return {
                "database_path": "nsccn.db",
                "embedding_model": "nomic-ai/nomic-embed-text-v1.5",
                "embedding_dim": 256,
                "rrf_k": 60,
                "max_traversal_depth": 3,
                "skeleton_cache_enabled": True,
                "watch_debounce_ms": 100,
                "supported_languages": ["python"],
                "ignore_patterns": ["**/test_*", "**/__pycache__/**", "**/.*"]
            }

    def initialize(self, root_path: str = "."):
        """
        Initialize all components.
        
        Args:
            root_path: Root directory for code analysis
        """
        logger.info("Initializing components...")
        
        # Initialize database
        self.db = NSCCNDatabase(self.config.get("database_path", "nsccn.db"))
        
        # Initialize parser
        self.parser = CodeParser()
        
        # Initialize embedding engine
        self.embedder = EmbeddingEngine(
            model_name=self.config.get("embedding_model", "nomic-ai/nomic-embed-text-v1.5"),
            embedding_dim=self.config.get("embedding_dim", 256)
        )
        
        # Initialize search engine
        self.search = HybridSearchEngine(
            self.db,
            self.embedder,
            rrf_k=self.config.get("rrf_k", 60)
        )
        
        # Initialize graph engine
        self.graph = CausalFlowEngine(
            self.db,
            max_depth=self.config.get("max_traversal_depth", 3)
        )
        
        # Initialize watcher
        self.watcher = IncrementalGraphBuilder(
            self.db,
            self.parser,
            self.embedder,
            root_path=root_path,
            debounce_ms=self.config.get("watch_debounce_ms", 100)
        )
        
        # Initialize tools
        self.tools = NSCCNTools(self.db, self.parser, self.search, self.graph)
        
        logger.info("All components initialized")

    def build_initial_index(self, root_path: str = "."):
        """Build initial index for a directory."""
        logger.info(f"Building initial index for {root_path}")
        self.watcher.build_initial_index(root_path)
        logger.info("Initial index built successfully")

    def start_watcher(self):
        """Start the file watcher."""
        logger.info("Starting file watcher...")
        self.watcher.start()

    def stop_watcher(self):
        """Stop the file watcher."""
        logger.info("Stopping file watcher...")
        self.watcher.stop()

    def register_tools_with_mcp(self):
        """Register tools with FastMCP."""
        logger.info("Registering tools with FastMCP...")
        
        self.mcp = FastMCP(name="nsccn-server")
        
        # Register search_and_rank tool
        @self.mcp.tool()
        def search_and_rank(query: str, limit: int = 10) -> str:
            """
            Find code entities using Hybrid RRF (Lexical + Semantic).
            Use this to find initial entry points for a feature or bug.
            
            Args:
                query: Natural language description of what you're looking for
                limit: Maximum number of results to return
            
            Returns:
                JSON list of entity IDs with relevance scores and metadata
            """
            return self.tools.search_and_rank(query, limit)
        
        # Register read_skeleton tool
        @self.mcp.tool()
        def read_skeleton(file_path: str) -> str:
            """
            Get Telegraphic Semantic Compression (TSC) view of a file.
            Shows signatures, docstrings, and structure without implementation details.
            Use this to understand file structure before reading full code.
            
            Args:
                file_path: Path to the file to skeletonize
            
            Returns:
                Compressed view with function/class signatures (bodies replaced with ...)
            """
            return self.tools.read_skeleton(file_path)
        
        # Register trace_causal_path tool
        @self.mcp.tool()
        def trace_causal_path(
            entity_id: str,
            direction: str = "downstream",
            depth: int = 3
        ) -> str:
            """
            Trace the causal graph from a specific code entity.
            
            Args:
                entity_id: The entity to start from (e.g., "func:src/auth.py:login")
                direction: "upstream" (who calls this?), "downstream" (what does this call?), 
                           "inheritance" (class hierarchy)
                depth: Maximum hops to traverse (default 3)
            
            Returns:
                JSON adjacency list representing the dependency subgraph
            """
            return self.tools.trace_causal_path(entity_id, direction, depth)
        
        # Register open_surgical_window tool
        @self.mcp.tool()
        def open_surgical_window(
            entity_id: str,
            context_lines: int = 5
        ) -> str:
            """
            Read the specific implementation of an entity with minimal context.
            Use this ONLY after locating the exact entity to edit via search/trace.
            
            Args:
                entity_id: The entity to read (e.g., "func:src/auth.py:validate_token")
                context_lines: Lines of context above/below the entity
            
            Returns:
                The entity's source code with file path and line numbers
            """
            return self.tools.open_surgical_window(entity_id, context_lines)
        
        logger.info("Tools registered with FastMCP")

    def run(self):
        """Run the FastMCP server."""
        if not self.mcp:
            raise RuntimeError("Tools not registered. Call register_tools_with_mcp() first.")
        
        logger.info("Starting NSCCN FastMCP server...")
        
        # Set up signal handlers for graceful shutdown
        def signal_handler(signum, frame):
            logger.info("Shutdown signal received")
            self.shutdown()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        try:
            self.mcp.run()
        except KeyboardInterrupt:
            logger.info("Server interrupted by user")
        finally:
            self.shutdown()

    def shutdown(self):
        """Gracefully shutdown all components."""
        logger.info("Shutting down NSCCN server...")
        
        if self.watcher:
            self.watcher.stop()
        
        if self.embedder:
            self.embedder.cleanup()
        
        if self.db:
            self.db.close()
        
        logger.info("NSCCN server shut down")

    def print_info(self):
        """Print tool information for discovery."""
        tools_info = {
            "name": "NSCCN - Neuro-Symbolic Causal Code Navigator",
            "version": "1.0.0",
            "description": "Context-efficient code navigation using causal graphs and semantic search",
            "tools": [
                {
                    "name": "search_and_rank",
                    "description": "Find code entities using Hybrid RRF (Lexical + Semantic)",
                    "parameters": ["query: str", "limit: int = 10"]
                },
                {
                    "name": "read_skeleton",
                    "description": "Get Telegraphic Semantic Compression view of a file",
                    "parameters": ["file_path: str"]
                },
                {
                    "name": "trace_causal_path",
                    "description": "Trace the causal graph from a specific code entity",
                    "parameters": ["entity_id: str", "direction: str = 'downstream'", "depth: int = 3"]
                },
                {
                    "name": "open_surgical_window",
                    "description": "Read entity implementation with minimal context",
                    "parameters": ["entity_id: str", "context_lines: int = 5"]
                }
            ]
        }
        print(json.dumps(tools_info, indent=2))


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="NSCCN Server")
    parser.add_argument("--init", metavar="DIR", help="Build initial index for directory")
    parser.add_argument("--info", action="store_true", help="Print tool information and exit")
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument("--root", default=".", help="Root directory to watch (default: current dir)")
    
    args = parser.parse_args()
    
    # Create server
    server = NSCCNServer(config_path=args.config)
    
    # Handle --info flag
    if args.info:
        server.print_info()
        return
    
    # Initialize components
    server.initialize(root_path=args.root)
    
    # Handle --init flag
    if args.init:
        server.build_initial_index(args.init)
        logger.info("Initial indexing complete. Exiting.")
        return
    
    # Start watcher
    server.start_watcher()
    
    # Register tools and run server
    server.register_tools_with_mcp()
    server.run()


if __name__ == "__main__":
    main()
