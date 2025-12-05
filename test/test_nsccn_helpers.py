#!/usr/bin/env python3
"""
Shared helper functions for NSCCN phase tests.

These utilities provide workarounds for features not yet implemented
and common test patterns used across multiple phase test files.
"""


def get_edges_by_relation_helper(db, result, relation):
    """
    Helper to get edges by relation type.
    
    This is a workaround until NSCCNDatabase.get_edges_by_relation() is implemented.
    
    Args:
        db: NSCCNDatabase instance
        result: Parser result containing entities
        relation: Edge relation type to filter by (e.g., 'MUTATES', 'READS_CONFIG')
    
    Returns:
        List of edges with the specified relation type
    """
    all_edges = []
    if result and 'entities' in result:
        for entity in result['entities']:
            edges = db.get_edges_by_source(entity['id'])
            all_edges.extend(edges)
    return [e for e in all_edges if e.get('relation') == relation]
