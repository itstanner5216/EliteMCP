#!/usr/bin/env python3
"""
Hybrid search engine implementing Reciprocal Rank Fusion (RRF).
Combines lexical (ripgrep) and semantic (embedding) search.
"""

import logging
import subprocess
import re
from typing import List, Dict, Any, Optional, Set
from pathlib import Path
import numpy as np

logger = logging.getLogger(__name__)


class HybridSearchEngine:
    """Implements hybrid search with lexical and semantic streams."""

    def __init__(self, database, embedding_engine, rrf_k: int = 60):
        """
        Initialize the hybrid search engine.
        
        Args:
            database: NSCCNDatabase instance
            embedding_engine: EmbeddingEngine instance
            rrf_k: RRF parameter (default 60)
        """
        self.db = database
        self.embedder = embedding_engine
        self.rrf_k = rrf_k
        logger.info(f"HybridSearchEngine initialized with k={rrf_k}")

    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining lexical and semantic results.
        
        Args:
            query: Search query string
            limit: Maximum number of results
            
        Returns:
            List of entity dictionaries with scores
        """
        # Get lexical and semantic results
        lexical_results = self._lexical_search(query, limit * 2)
        semantic_results = self._semantic_search(query, limit * 2)
        
        # Create rank dictionaries
        lexical_ranks = {result['id']: rank for rank, result in enumerate(lexical_results)}
        semantic_ranks = {result['id']: rank for rank, result in enumerate(semantic_results)}
        
        # Fuse with RRF
        fused_results = self._rrf_fuse(lexical_ranks, semantic_ranks, self.rrf_k)
        
        # Get full entity details for top results
        final_results = []
        for entity_id, score in fused_results[:limit]:
            entity = self.db.get_entity(entity_id)
            if entity:
                entity['score'] = score
                final_results.append(entity)
        
        logger.debug(f"Hybrid search returned {len(final_results)} results for query: {query}")
        return final_results

    def _lexical_search(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """
        Perform lexical search using ripgrep.
        
        Args:
            query: Search query
            limit: Maximum results
            
        Returns:
            List of entity dictionaries with match info
        """
        try:
            # Use ripgrep to search for the query
            # Search in all Python files
            result = subprocess.run(
                ['rg', '--json', '-i', query, '--type', 'py'],
                capture_output=True,
                text=True,
                timeout=5.0
            )
            
            if result.returncode not in [0, 1]:  # 0 = found, 1 = not found
                logger.warning(f"ripgrep failed with code {result.returncode}")
                return []
            
            # Parse ripgrep JSON output
            file_matches = {}  # file_path -> [(line_num, match_count)]
            
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                
                try:
                    import json
                    data = json.loads(line)
                    
                    if data.get('type') == 'match':
                        file_path = data['data']['path']['text']
                        line_num = data['data']['line_number']
                        
                        if file_path not in file_matches:
                            file_matches[file_path] = []
                        file_matches[file_path].append(line_num)
                
                except json.JSONDecodeError:
                    continue
            
            # Map file matches to entities
            entity_scores = {}  # entity_id -> score
            
            for file_path, line_nums in file_matches.items():
                # Get entities for this file
                entities = self.db.get_entities_by_file(file_path)
                
                for entity in entities:
                    # Check if any match is within entity range
                    for line_num in line_nums:
                        if entity['start_line'] <= line_num <= entity['end_line']:
                            entity_id = entity['id']
                            if entity_id not in entity_scores:
                                entity_scores[entity_id] = 0
                            entity_scores[entity_id] += 1
            
            # Sort by score and return
            sorted_entities = sorted(
                entity_scores.items(),
                key=lambda x: x[1],
                reverse=True
            )
            
            results = []
            for entity_id, score in sorted_entities[:limit]:
                entity = self.db.get_entity(entity_id)
                if entity:
                    entity['lexical_score'] = score
                    results.append(entity)
            
            return results
            
        except FileNotFoundError:
            logger.warning("ripgrep not found, lexical search disabled")
            return []
        except Exception as e:
            logger.error(f"Lexical search failed: {e}")
            return []

    def _semantic_search(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """
        Perform semantic search using embeddings.
        
        Args:
            query: Search query
            limit: Maximum results
            
        Returns:
            List of entity dictionaries with similarity scores
        """
        try:
            # Embed the query
            query_embedding = self.embedder.embed_text(query)
            
            # Search database
            results = self.db.search_entities_by_embedding(query_embedding, limit)
            
            return results
            
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []

    def _rrf_fuse(self, lexical_ranks: Dict[str, int], semantic_ranks: Dict[str, int], k: int = 60) -> List[tuple]:
        """
        Reciprocal Rank Fusion combining lexical and semantic results.
        
        Score(d) = Σ 1/(k + rank(d))
        
        Args:
            lexical_ranks: Entity ID to rank mapping from lexical search
            semantic_ranks: Entity ID to rank mapping from semantic search
            k: RRF parameter (default 60)
            
        Returns:
            List of (entity_id, score) tuples sorted by score
        """
        scores = {}
        all_entities = set(lexical_ranks.keys()) | set(semantic_ranks.keys())
        
        for entity in all_entities:
            lex_rank = lexical_ranks.get(entity, 1000)  # Default high rank if missing
            sem_rank = semantic_ranks.get(entity, 1000)
            scores[entity] = 1/(k + lex_rank) + 1/(k + sem_rank)
        
        return sorted(scores.items(), key=lambda x: x[1], reverse=True)

    def lexical_search_only(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Perform only lexical search (for testing/fallback)."""
        return self._lexical_search(query, limit)

    def semantic_search_only(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Perform only semantic search (for testing/fallback)."""
        return self._semantic_search(query, limit)
