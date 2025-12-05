#!/usr/bin/env python3
"""
Database layer for NSCCN - manages SQLite database with entities, edges, and skeletons.
"""

import sqlite3
import json
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
import numpy as np

logger = logging.getLogger(__name__)


class NSCCNDatabase:
    """Database manager for NSCCN code graph and cache."""

    def __init__(self, db_path: str = "nsccn.db"):
        """Initialize database connection and create tables if needed."""
        self.db_path = Path(db_path)
        self.conn: Optional[sqlite3.Connection] = None
        self._initialize()

    def _initialize(self):
        """Initialize database connection and create schema."""
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_schema()
        logger.info(f"Database initialized: {self.db_path}")

    def _create_schema(self):
        """Create database schema with entities, edges, and skeletons tables."""
        cursor = self.conn.cursor()
        
        # Entities table (graph nodes)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entities (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                file_path TEXT NOT NULL,
                name TEXT NOT NULL,
                start_line INTEGER,
                end_line INTEGER,
                signature TEXT,
                docstring TEXT,
                embedding BLOB,
                last_updated REAL
            )
        """)
        
        # Edges table (causal relationships)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS edges (
                source_id TEXT NOT NULL,
                relation TEXT NOT NULL,
                target_id TEXT NOT NULL,
                context TEXT,
                PRIMARY KEY (source_id, relation, target_id),
                FOREIGN KEY(source_id) REFERENCES entities(id),
                FOREIGN KEY(target_id) REFERENCES entities(id)
            )
        """)
        
        # Create indexes for efficient querying
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_entities_file ON entities(file_path)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(type)
        """)
        
        # Skeletons cache table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS skeletons (
                file_path TEXT PRIMARY KEY,
                content TEXT,
                last_modified REAL
            )
        """)
        
        self.conn.commit()
        logger.debug("Database schema created")

    def upsert_entity(self, entity: Dict[str, Any]) -> None:
        """Insert or update an entity in the database."""
        cursor = self.conn.cursor()
        
        # Convert embedding to bytes if present
        embedding_blob = None
        if entity.get('embedding') is not None:
            embedding_blob = entity['embedding'].tobytes()
        
        cursor.execute("""
            INSERT OR REPLACE INTO entities 
            (id, type, file_path, name, start_line, end_line, signature, docstring, embedding, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entity['id'],
            entity['type'],
            entity['file_path'],
            entity['name'],
            entity.get('start_line'),
            entity.get('end_line'),
            entity.get('signature'),
            entity.get('docstring'),
            embedding_blob,
            entity.get('last_updated')
        ))
        self.conn.commit()

    def upsert_entities_batch(self, entities: List[Dict[str, Any]]) -> None:
        """Batch insert or update entities."""
        cursor = self.conn.cursor()
        
        data = []
        for entity in entities:
            embedding_blob = None
            if entity.get('embedding') is not None:
                embedding_blob = entity['embedding'].tobytes()
            
            data.append((
                entity['id'],
                entity['type'],
                entity['file_path'],
                entity['name'],
                entity.get('start_line'),
                entity.get('end_line'),
                entity.get('signature'),
                entity.get('docstring'),
                embedding_blob,
                entity.get('last_updated')
            ))
        
        cursor.executemany("""
            INSERT OR REPLACE INTO entities 
            (id, type, file_path, name, start_line, end_line, signature, docstring, embedding, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, data)
        self.conn.commit()

    def get_entity(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve an entity by ID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM entities WHERE id = ?", (entity_id,))
        row = cursor.fetchone()
        
        if row is None:
            return None
        
        entity = dict(row)
        
        # Convert embedding from bytes to numpy array
        if entity['embedding']:
            entity['embedding'] = np.frombuffer(entity['embedding'], dtype=np.float32)
        
        return entity

    def get_entities_by_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Get all entities for a specific file."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM entities WHERE file_path = ?", (file_path,))
        rows = cursor.fetchall()
        
        entities = []
        for row in rows:
            entity = dict(row)
            if entity['embedding']:
                entity['embedding'] = np.frombuffer(entity['embedding'], dtype=np.float32)
            entities.append(entity)
        
        return entities

    def delete_entities_by_file(self, file_path: str) -> None:
        """Delete all entities for a specific file."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM entities WHERE file_path = ?", (file_path,))
        self.conn.commit()

    def upsert_edge(self, source_id: str, relation: str, target_id: str, context: Optional[str] = None) -> None:
        """Insert or update an edge in the database."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO edges (source_id, relation, target_id, context)
            VALUES (?, ?, ?, ?)
        """, (source_id, relation, target_id, context))
        self.conn.commit()

    def upsert_edges_batch(self, edges: List[Tuple[str, str, str, Optional[str]]]) -> None:
        """Batch insert or update edges."""
        cursor = self.conn.cursor()
        cursor.executemany("""
            INSERT OR REPLACE INTO edges (source_id, relation, target_id, context)
            VALUES (?, ?, ?, ?)
        """, edges)
        self.conn.commit()

    def get_edges_by_source(self, source_id: str, relation: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all edges originating from a source entity."""
        cursor = self.conn.cursor()
        
        if relation:
            cursor.execute(
                "SELECT * FROM edges WHERE source_id = ? AND relation = ?",
                (source_id, relation)
            )
        else:
            cursor.execute("SELECT * FROM edges WHERE source_id = ?", (source_id,))
        
        return [dict(row) for row in cursor.fetchall()]

    def get_edges_by_target(self, target_id: str, relation: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all edges pointing to a target entity."""
        cursor = self.conn.cursor()
        
        if relation:
            cursor.execute(
                "SELECT * FROM edges WHERE target_id = ? AND relation = ?",
                (target_id, relation)
            )
        else:
            cursor.execute("SELECT * FROM edges WHERE target_id = ?", (target_id,))
        
        return [dict(row) for row in cursor.fetchall()]

    def delete_edges_by_source(self, source_id: str) -> None:
        """Delete all edges originating from a source entity."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM edges WHERE source_id = ?", (source_id,))
        self.conn.commit()

    def upsert_skeleton(self, file_path: str, content: str, last_modified: float) -> None:
        """Insert or update a skeleton in the cache."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO skeletons (file_path, content, last_modified)
            VALUES (?, ?, ?)
        """, (file_path, content, last_modified))
        self.conn.commit()

    def get_skeleton(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Retrieve a skeleton from the cache."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM skeletons WHERE file_path = ?", (file_path,))
        row = cursor.fetchone()
        
        if row is None:
            return None
        
        return dict(row)

    def delete_skeleton(self, file_path: str) -> None:
        """Delete a skeleton from the cache."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM skeletons WHERE file_path = ?", (file_path,))
        self.conn.commit()

    def search_entities_by_embedding(self, query_embedding: np.ndarray, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search entities by embedding similarity (cosine similarity).
        Returns entities sorted by similarity score.
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, embedding FROM entities WHERE embedding IS NOT NULL")
        rows = cursor.fetchall()
        
        results = []
        query_norm = np.linalg.norm(query_embedding)
        
        for row in rows:
            entity_id = row['id']
            embedding_bytes = row['embedding']
            entity_embedding = np.frombuffer(embedding_bytes, dtype=np.float32)
            
            # Cosine similarity
            entity_norm = np.linalg.norm(entity_embedding)
            if entity_norm > 0 and query_norm > 0:
                similarity = np.dot(query_embedding, entity_embedding) / (query_norm * entity_norm)
                results.append({'id': entity_id, 'score': float(similarity)})
        
        # Sort by similarity (descending) and limit
        results.sort(key=lambda x: x['score'], reverse=True)
        
        # Get full entity details for top results
        top_results = []
        for result in results[:limit]:
            entity = self.get_entity(result['id'])
            if entity:
                entity['score'] = result['score']
                top_results.append(entity)
        
        return top_results

    def get_all_entities(self) -> List[Dict[str, Any]]:
        """Get all entities from the database."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM entities")
        rows = cursor.fetchall()
        
        entities = []
        for row in rows:
            entity = dict(row)
            if entity['embedding']:
                entity['embedding'] = np.frombuffer(entity['embedding'], dtype=np.float32)
            entities.append(entity)
        
        return entities

    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")
