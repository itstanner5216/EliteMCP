#!/usr/bin/env python3
"""
Tree-sitter based parser for extracting code structure and generating skeletons.
Supports Python with incremental parsing and Telegraphic Semantic Compression.
"""

import logging
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from tree_sitter import Tree
from tree_sitter_languages import get_parser

logger = logging.getLogger(__name__)


class CodeParser:
    """Tree-sitter based parser for code structure extraction."""

    def __init__(self):
        """Initialize the parser with Python language support."""
        self.parser = get_parser('python')
        self.previous_trees = {}  # Cache for incremental parsing
        logger.debug("CodeParser initialized with Python support")

    def parse_file(self, file_path: str, use_incremental: bool = True) -> Optional[Dict[str, Any]]:
        """
        Parse a Python file and extract entities and edges.
        
        Args:
            file_path: Path to the Python file
            use_incremental: Use incremental parsing with cached tree
            
        Returns:
            Dictionary with entities and edges, or None on error
        """
        try:
            with open(file_path, 'rb') as f:
                source_code = f.read()
            
            # Parse with tree-sitter (incremental parsing not used in tree-sitter 0.20 API)
            tree = self.parser.parse(source_code)
            
            # Cache the tree for future use (note: incremental parsing disabled for now)
            self.previous_trees[file_path] = tree
            
            # Extract entities and edges
            entities = self._extract_entities(tree, file_path, source_code)
            edges = self._extract_edges(tree, file_path, source_code)
            
            return {
                'entities': entities,
                'edges': edges,
                'file_path': file_path
            }
            
        except Exception as e:
            logger.error(f"Failed to parse {file_path}: {e}")
            return None

    def _extract_entities(self, tree: Tree, file_path: str, source_code: bytes) -> List[Dict[str, Any]]:
        """Extract function and class entities from the parse tree."""
        entities = []
        
        # Walk the tree and find function and class definitions
        def walk_tree(node, parent_class=None):
            if node.type == 'function_definition':
                entity = self._extract_function(node, file_path, source_code, parent_class)
                if entity:
                    entities.append(entity)
            
            elif node.type == 'class_definition':
                entity = self._extract_class(node, file_path, source_code)
                if entity:
                    entities.append(entity)
                    # Walk children to find methods
                    class_name = entity['name']
                    for child in node.children:
                        walk_tree(child, class_name)
            
            else:
                # Recursively walk children
                for child in node.children:
                    walk_tree(child, parent_class)
        
        walk_tree(tree.root_node)
        return entities

    def _extract_function(self, node, file_path: str, source_code: bytes, parent_class: Optional[str]) -> Optional[Dict[str, Any]]:
        """Extract function/method entity details."""
        try:
            # Get function name
            name_node = node.child_by_field_name('name')
            if not name_node:
                return None
            
            func_name = source_code[name_node.start_byte:name_node.end_byte].decode('utf-8')
            
            # Generate entity ID
            if parent_class:
                entity_id = f"method:{file_path}:{parent_class}.{func_name}"
                entity_type = "method"
            else:
                entity_id = f"func:{file_path}:{func_name}"
                entity_type = "function"
            
            # Get parameters
            params_node = node.child_by_field_name('parameters')
            params_text = ""
            if params_node:
                params_text = source_code[params_node.start_byte:params_node.end_byte].decode('utf-8')
            
            # Get return type
            return_type_node = node.child_by_field_name('return_type')
            return_type = ""
            if return_type_node:
                return_type = source_code[return_type_node.start_byte:return_type_node.end_byte].decode('utf-8')
            
            # Build signature
            signature = f"def {func_name}{params_text}"
            if return_type:
                signature += f" -> {return_type}"
            
            # Extract docstring
            docstring = self._extract_docstring(node, source_code)
            
            # Get line numbers
            start_line = node.start_point[0] + 1
            end_line = node.end_point[0] + 1
            
            return {
                'id': entity_id,
                'type': entity_type,
                'file_path': file_path,
                'name': func_name,
                'start_line': start_line,
                'end_line': end_line,
                'signature': signature,
                'docstring': docstring,
                'last_updated': time.time()
            }
            
        except Exception as e:
            logger.warning(f"Failed to extract function: {e}")
            return None

    def _extract_class(self, node, file_path: str, source_code: bytes) -> Optional[Dict[str, Any]]:
        """Extract class entity details."""
        try:
            # Get class name
            name_node = node.child_by_field_name('name')
            if not name_node:
                return None
            
            class_name = source_code[name_node.start_byte:name_node.end_byte].decode('utf-8')
            
            # Generate entity ID
            entity_id = f"class:{file_path}:{class_name}"
            
            # Get base classes
            superclasses_node = node.child_by_field_name('superclasses')
            bases = []
            if superclasses_node:
                bases_text = source_code[superclasses_node.start_byte:superclasses_node.end_byte].decode('utf-8')
                signature = f"class {class_name}{bases_text}"
            else:
                signature = f"class {class_name}"
            
            # Extract docstring
            docstring = self._extract_docstring(node, source_code)
            
            # Get line numbers
            start_line = node.start_point[0] + 1
            end_line = node.end_point[0] + 1
            
            return {
                'id': entity_id,
                'type': 'class',
                'file_path': file_path,
                'name': class_name,
                'start_line': start_line,
                'end_line': end_line,
                'signature': signature,
                'docstring': docstring,
                'last_updated': time.time()
            }
            
        except Exception as e:
            logger.warning(f"Failed to extract class: {e}")
            return None

    def _extract_docstring(self, node, source_code: bytes) -> str:
        """Extract docstring from a function or class definition."""
        # Look for the first string in the body
        body_node = node.child_by_field_name('body')
        if not body_node:
            return ""
        
        # Get first statement in body
        for child in body_node.children:
            if child.type == 'expression_statement':
                # Check if it contains a string
                for grandchild in child.children:
                    if grandchild.type == 'string':
                        docstring_raw = source_code[grandchild.start_byte:grandchild.end_byte].decode('utf-8')
                        # Remove quotes
                        docstring = docstring_raw.strip('"""').strip("'''").strip('"').strip("'").strip()
                        return docstring
        
        return ""

    def _extract_edges(self, tree: Tree, file_path: str, source_code: bytes) -> List[Tuple[str, str, str, Optional[str]]]:
        """Extract CALLS and INHERITS edges from the parse tree."""
        edges = []
        
        # Track current entity context
        entity_stack = []
        
        def walk_tree(node):
            # Track entity context (function or class)
            if node.type == 'function_definition':
                name_node = node.child_by_field_name('name')
                if name_node:
                    func_name = source_code[name_node.start_byte:name_node.end_byte].decode('utf-8')
                    # Determine if it's a method or function
                    if entity_stack and entity_stack[-1]['type'] == 'class':
                        entity_id = f"method:{file_path}:{entity_stack[-1]['name']}.{func_name}"
                    else:
                        entity_id = f"func:{file_path}:{func_name}"
                    
                    entity_stack.append({'type': 'function', 'id': entity_id, 'name': func_name})
                    
                    # Walk children to find calls
                    for child in node.children:
                        walk_tree(child)
                    
                    entity_stack.pop()
                    return
            
            elif node.type == 'class_definition':
                name_node = node.child_by_field_name('name')
                if name_node:
                    class_name = source_code[name_node.start_byte:name_node.end_byte].decode('utf-8')
                    entity_id = f"class:{file_path}:{class_name}"
                    
                    entity_stack.append({'type': 'class', 'id': entity_id, 'name': class_name})
                    
                    # Extract INHERITS edges
                    superclasses_node = node.child_by_field_name('superclasses')
                    if superclasses_node:
                        # Extract base class names
                        for child in superclasses_node.children:
                            if child.type == 'identifier':
                                base_name = source_code[child.start_byte:child.end_byte].decode('utf-8')
                                # Create edge (note: target might not be in same file)
                                target_id = f"class:{file_path}:{base_name}"  # Simplified
                                edges.append((entity_id, 'INHERITS', target_id, None))
                    
                    # Walk children
                    for child in node.children:
                        walk_tree(child)
                    
                    entity_stack.pop()
                    return
            
            elif node.type == 'call':
                # Extract CALLS edge
                if entity_stack:
                    caller_id = entity_stack[-1]['id']
                    
                    # Get the function being called
                    func_node = node.child_by_field_name('function')
                    if func_node:
                        if func_node.type == 'identifier':
                            callee_name = source_code[func_node.start_byte:func_node.end_byte].decode('utf-8')
                            # Simplified: assume same file
                            target_id = f"func:{file_path}:{callee_name}"
                            edges.append((caller_id, 'CALLS', target_id, None))
                        
                        elif func_node.type == 'attribute':
                            # Method call like obj.method()
                            attr_node = func_node.child_by_field_name('attribute')
                            if attr_node:
                                method_name = source_code[attr_node.start_byte:attr_node.end_byte].decode('utf-8')
                                # Simplified: don't know the class, use generic format
                                target_id = f"method:{file_path}:*.{method_name}"
                                edges.append((caller_id, 'CALLS', target_id, None))
            
            # Recursively walk children
            for child in node.children:
                walk_tree(child)
        
        walk_tree(tree.root_node)
        return edges

    def generate_skeleton(self, file_path: str) -> Optional[str]:
        """
        Generate Telegraphic Semantic Compression (TSC) view of a file.
        Shows signatures, docstrings, and structure without implementation details.
        """
        try:
            with open(file_path, 'rb') as f:
                source_code = f.read()
            
            tree = self.parser.parse(source_code)
            skeleton_lines = []
            
            # Add file header
            skeleton_lines.append(f"# {file_path}")
            skeleton_lines.append("")
            
            # Walk the tree and extract structure
            def walk_tree(node, indent=0):
                indent_str = "    " * indent
                
                if node.type == 'class_definition':
                    # Extract class signature
                    name_node = node.child_by_field_name('name')
                    if not name_node:
                        return
                    
                    class_name = source_code[name_node.start_byte:name_node.end_byte].decode('utf-8')
                    
                    superclasses_node = node.child_by_field_name('superclasses')
                    if superclasses_node:
                        bases = source_code[superclasses_node.start_byte:superclasses_node.end_byte].decode('utf-8')
                        skeleton_lines.append(f"{indent_str}class {class_name}{bases}:")
                    else:
                        skeleton_lines.append(f"{indent_str}class {class_name}:")
                    
                    # Add docstring if present
                    docstring = self._extract_docstring(node, source_code)
                    if docstring:
                        skeleton_lines.append(f'{indent_str}    """{docstring}"""')
                    
                    # Process class body (methods)
                    body_node = node.child_by_field_name('body')
                    if body_node:
                        for child in body_node.children:
                            walk_tree(child, indent + 1)
                    
                    skeleton_lines.append("")
                
                elif node.type == 'function_definition':
                    # Extract function signature
                    name_node = node.child_by_field_name('name')
                    if not name_node:
                        return
                    
                    func_name = source_code[name_node.start_byte:name_node.end_byte].decode('utf-8')
                    
                    params_node = node.child_by_field_name('parameters')
                    params = ""
                    if params_node:
                        params = source_code[params_node.start_byte:params_node.end_byte].decode('utf-8')
                    
                    return_type_node = node.child_by_field_name('return_type')
                    return_type = ""
                    if return_type_node:
                        return_type = source_code[return_type_node.start_byte:return_type_node.end_byte].decode('utf-8')
                    
                    signature = f"{indent_str}def {func_name}{params}"
                    if return_type:
                        signature += f" -> {return_type}"
                    signature += ":"
                    skeleton_lines.append(signature)
                    
                    # Add docstring if present
                    docstring = self._extract_docstring(node, source_code)
                    if docstring:
                        skeleton_lines.append(f'{indent_str}    """{docstring}"""')
                    
                    # Replace body with ...
                    skeleton_lines.append(f"{indent_str}    ...")
                    skeleton_lines.append("")
                
                elif node.type == 'import_statement' or node.type == 'import_from_statement':
                    # Keep imports
                    import_text = source_code[node.start_byte:node.end_byte].decode('utf-8')
                    skeleton_lines.append(f"{indent_str}{import_text}")
                
                else:
                    # For module level, walk children
                    if indent == 0:
                        for child in node.children:
                            walk_tree(child, indent)
            
            walk_tree(tree.root_node)
            
            return "\n".join(skeleton_lines)
            
        except Exception as e:
            logger.error(f"Failed to generate skeleton for {file_path}: {e}")
            return None

    def invalidate_cache(self, file_path: str) -> None:
        """Remove cached parse tree for a file."""
        if file_path in self.previous_trees:
            del self.previous_trees[file_path]
            logger.debug(f"Invalidated parse cache for {file_path}")
