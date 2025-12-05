#!/usr/bin/env python3
"""
FastMCP tools for NSCCN - implements the four primary navigation tools.
"""

import logging
import json
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class NSCCNTools:
    """NSCCN tool implementations for FastMCP."""

    def __init__(self, database, parser, search_engine, graph_engine):
        """
        Initialize NSCCN tools.
        
        Args:
            database: NSCCNDatabase instance
            parser: CodeParser instance
            search_engine: HybridSearchEngine instance
            graph_engine: CausalFlowEngine instance
        """
        self.db = database
        self.parser = parser
        self.search = search_engine
        self.graph = graph_engine
        logger.info("NSCCN tools initialized")

    def search_and_rank(self, query: str, limit: int = 10) -> str:
        """
        Find code entities using Hybrid RRF (Lexical + Semantic).
        Use this to find initial entry points for a feature or bug.
        
        Args:
            query: Natural language description of what you're looking for
            limit: Maximum number of results to return
        
        Returns:
            JSON list of entity IDs with relevance scores and metadata
        """
        try:
            results = self.search.search(query, limit)
            
            # Format output compactly
            output = []
            for entity in results:
                output.append({
                    'id': entity['id'],
                    'score': round(entity.get('score', 0.0), 2),
                    'sig': entity.get('signature', ''),
                    'file': entity['file_path'],
                    'line': entity.get('start_line', 0)
                })
            
            return json.dumps(output, separators=(',', ':'))
            
        except Exception as e:
            logger.error(f"search_and_rank failed: {e}")
            return json.dumps({'error': str(e)})

    def read_skeleton(self, file_path: str) -> str:
        """
        Get Telegraphic Semantic Compression (TSC) view of a file.
        Shows signatures, docstrings, and structure without implementation details.
        Use this to understand file structure before reading full code.
        
        Args:
            file_path: Path to the file to skeletonize
        
        Returns:
            Compressed view with function/class signatures (bodies replaced with ...)
        """
        try:
            # Check cache first
            cached = self.db.get_skeleton(file_path)
            
            if cached:
                # Check if file has been modified since cache
                try:
                    file_mtime = Path(file_path).stat().st_mtime
                    if file_mtime <= cached['last_modified']:
                        return cached['content']
                except:
                    pass
            
            # Generate skeleton
            skeleton = self.parser.generate_skeleton(file_path)
            
            if skeleton is None:
                return json.dumps({'error': 'Failed to generate skeleton'})
            
            # Cache the skeleton
            try:
                file_mtime = Path(file_path).stat().st_mtime
                self.db.upsert_skeleton(file_path, skeleton, file_mtime)
            except:
                pass
            
            return skeleton
            
        except Exception as e:
            logger.error(f"read_skeleton failed: {e}")
            return json.dumps({'error': str(e)})

    def trace_causal_path(
        self,
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
        try:
            if direction == "upstream":
                result = self.graph.traverse_upstream(entity_id, depth)
            elif direction == "downstream":
                result = self.graph.traverse_downstream(entity_id, depth)
            elif direction == "inheritance":
                result = self.graph.get_inheritance_chain(entity_id)
            else:
                return json.dumps({'error': f'Invalid direction: {direction}'})
            
            # Compact JSON output
            return json.dumps(result, separators=(',', ':'))
            
        except Exception as e:
            logger.error(f"trace_causal_path failed: {e}")
            return json.dumps({'error': str(e)})

    def open_surgical_window(
        self,
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
        try:
            # Get entity from database
            entity = self.db.get_entity(entity_id)
            
            if not entity:
                return json.dumps({'error': f'Entity not found: {entity_id}'})
            
            file_path = entity['file_path']
            start_line = entity['start_line']
            end_line = entity['end_line']
            
            # Read file
            with open(file_path, 'r') as f:
                lines = f.readlines()
            
            # Calculate context window
            context_start = max(0, start_line - 1 - context_lines)
            context_end = min(len(lines), end_line + context_lines)
            
            # Extract lines
            result_lines = []
            for i in range(context_start, context_end):
                line_num = i + 1
                line_content = lines[i].rstrip('\n')
                result_lines.append(f"{line_num:4d} | {line_content}")
            
            # Format output
            output = {
                'entity_id': entity_id,
                'file': file_path,
                'start': start_line,
                'end': end_line,
                'code': '\n'.join(result_lines)
            }
            
            return json.dumps(output, separators=(',', ':'))
            
        except Exception as e:
            logger.error(f"open_surgical_window failed: {e}")
            return json.dumps({'error': str(e)})
