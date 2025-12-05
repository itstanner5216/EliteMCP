#!/usr/bin/env python3
"""
Causal flow engine for graph traversal and multi-hop reasoning.
"""

import logging
from typing import List, Dict, Any, Set, Optional
import json

logger = logging.getLogger(__name__)


class CausalFlowEngine:
    """Implements graph traversal for causal flow analysis."""

    def __init__(self, database, max_depth: int = 3):
        """
        Initialize the causal flow engine.
        
        Args:
            database: NSCCNDatabase instance
            max_depth: Maximum traversal depth (default 3)
        """
        self.db = database
        self.max_depth = max_depth
        logger.info(f"CausalFlowEngine initialized with max_depth={max_depth}")

    def traverse_upstream(self, entity_id: str, depth: int = 3) -> Dict[str, Any]:
        """
        Find who calls this entity (callers).
        
        Args:
            entity_id: Starting entity ID
            depth: Maximum hops to traverse
            
        Returns:
            Subgraph as adjacency list JSON
        """
        depth = min(depth, self.max_depth)
        visited = set()
        adjacency_list = {}
        entities_info = {}
        
        def traverse(current_id, current_depth):
            if current_depth > depth or current_id in visited:
                return
            
            visited.add(current_id)
            
            # Get entity info
            entity = self.db.get_entity(current_id)
            if entity:
                entities_info[current_id] = {
                    'id': current_id,
                    'type': entity['type'],
                    'name': entity['name'],
                    'file_path': entity['file_path'],
                    'signature': entity.get('signature', '')
                }
            
            # Find edges where this entity is the target (incoming edges)
            edges = self.db.get_edges_by_target(current_id, relation='CALLS')
            
            if current_id not in adjacency_list:
                adjacency_list[current_id] = []
            
            for edge in edges:
                source_id = edge['source_id']
                adjacency_list[current_id].append({
                    'target': source_id,
                    'relation': edge['relation']
                })
                
                # Recurse to parent
                traverse(source_id, current_depth + 1)
        
        traverse(entity_id, 0)
        
        return {
            'root': entity_id,
            'direction': 'upstream',
            'depth': depth,
            'adjacency_list': adjacency_list,
            'entities': entities_info
        }

    def traverse_downstream(self, entity_id: str, depth: int = 3) -> Dict[str, Any]:
        """
        Find what this entity calls (callees).
        
        Args:
            entity_id: Starting entity ID
            depth: Maximum hops to traverse
            
        Returns:
            Subgraph as adjacency list JSON
        """
        depth = min(depth, self.max_depth)
        visited = set()
        adjacency_list = {}
        entities_info = {}
        
        def traverse(current_id, current_depth):
            if current_depth > depth or current_id in visited:
                return
            
            visited.add(current_id)
            
            # Get entity info
            entity = self.db.get_entity(current_id)
            if entity:
                entities_info[current_id] = {
                    'id': current_id,
                    'type': entity['type'],
                    'name': entity['name'],
                    'file_path': entity['file_path'],
                    'signature': entity.get('signature', '')
                }
            
            # Find edges where this entity is the source (outgoing edges)
            edges = self.db.get_edges_by_source(current_id, relation='CALLS')
            
            if current_id not in adjacency_list:
                adjacency_list[current_id] = []
            
            for edge in edges:
                target_id = edge['target_id']
                adjacency_list[current_id].append({
                    'target': target_id,
                    'relation': edge['relation']
                })
                
                # Recurse to child
                traverse(target_id, current_depth + 1)
        
        traverse(entity_id, 0)
        
        return {
            'root': entity_id,
            'direction': 'downstream',
            'depth': depth,
            'adjacency_list': adjacency_list,
            'entities': entities_info
        }

    def get_inheritance_chain(self, entity_id: str) -> Dict[str, Any]:
        """
        Get class hierarchy (inheritance chain).
        
        Args:
            entity_id: Starting class entity ID
            
        Returns:
            Inheritance chain with parents and children
        """
        visited = set()
        parents = []
        children = []
        entities_info = {}
        
        # Get entity info
        entity = self.db.get_entity(entity_id)
        if entity:
            entities_info[entity_id] = {
                'id': entity_id,
                'type': entity['type'],
                'name': entity['name'],
                'file_path': entity['file_path'],
                'signature': entity.get('signature', '')
            }
        
        # Find parent classes (what this class inherits from)
        def get_parents(current_id, depth=0):
            if depth > self.max_depth or current_id in visited:
                return
            
            visited.add(current_id)
            
            edges = self.db.get_edges_by_source(current_id, relation='INHERITS')
            for edge in edges:
                parent_id = edge['target_id']
                parent_entity = self.db.get_entity(parent_id)
                
                if parent_entity:
                    parent_info = {
                        'id': parent_id,
                        'type': parent_entity['type'],
                        'name': parent_entity['name'],
                        'file_path': parent_entity['file_path'],
                        'depth': depth
                    }
                    parents.append(parent_info)
                    entities_info[parent_id] = parent_info
                    
                    # Recurse
                    get_parents(parent_id, depth + 1)
        
        get_parents(entity_id)
        
        # Find child classes (what inherits from this class)
        visited.clear()
        
        def get_children(current_id, depth=0):
            if depth > self.max_depth or current_id in visited:
                return
            
            visited.add(current_id)
            
            edges = self.db.get_edges_by_target(current_id, relation='INHERITS')
            for edge in edges:
                child_id = edge['source_id']
                child_entity = self.db.get_entity(child_id)
                
                if child_entity:
                    child_info = {
                        'id': child_id,
                        'type': child_entity['type'],
                        'name': child_entity['name'],
                        'file_path': child_entity['file_path'],
                        'depth': depth
                    }
                    children.append(child_info)
                    entities_info[child_id] = child_info
                    
                    # Recurse
                    get_children(child_id, depth + 1)
        
        get_children(entity_id)
        
        return {
            'root': entity_id,
            'parents': parents,
            'children': children,
            'entities': entities_info
        }

    def trace_path(self, source_id: str, target_id: str, max_depth: Optional[int] = None) -> Optional[List[str]]:
        """
        Find a path from source to target entity.
        
        Args:
            source_id: Starting entity ID
            target_id: Target entity ID
            max_depth: Maximum search depth
            
        Returns:
            List of entity IDs representing the path, or None if no path found
        """
        if max_depth is None:
            max_depth = self.max_depth
        
        visited = set()
        
        def dfs(current_id, path, depth):
            if depth > max_depth:
                return None
            
            if current_id == target_id:
                return path + [current_id]
            
            if current_id in visited:
                return None
            
            visited.add(current_id)
            
            # Try CALLS edges
            edges = self.db.get_edges_by_source(current_id, relation='CALLS')
            for edge in edges:
                next_id = edge['target_id']
                result = dfs(next_id, path + [current_id], depth + 1)
                if result:
                    return result
            
            return None
        
        return dfs(source_id, [], 0)
