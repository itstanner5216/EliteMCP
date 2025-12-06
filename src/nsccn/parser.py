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
        logger.debug("CodeParser initialized with Python support")

    def parse_file(self, file_path: str, use_incremental: bool = False) -> Optional[Dict[str, Any]]:
        """Parse a Python file and extract entities and edges.

        Args:
            file_path: Path to the Python file
            use_incremental: Use incremental parsing with cached tree

        Returns:
            Dictionary with entities and edges, or None on error
        """
        try:
            with open(file_path, 'rb') as f:
                source_code = f.read()

            # Parse with tree-sitter (incremental disabled for compatibility)
            tree = self.parser.parse(source_code)

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
        entities: List[Dict[str, Any]] = []

        def walk_tree(node, parent_class: Optional[str] = None):
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
                for child in node.children:
                    walk_tree(child, parent_class)

        walk_tree(tree.root_node)
        return entities

    def _extract_function(self, node, file_path: str, source_code: bytes, parent_class: Optional[str]) -> Optional[Dict[str, Any]]:
        """Extract function/method entity details."""
        try:
            name_node = node.child_by_field_name('name')
            if not name_node:
                return None
            func_name = source_code[name_node.start_byte:name_node.end_byte].decode('utf-8')

            if parent_class:
                entity_id = f"method:{file_path}:{parent_class}.{func_name}"
                entity_type = "method"
            else:
                entity_id = f"func:{file_path}:{func_name}"
                entity_type = "function"

            # Parameters
            params_node = node.child_by_field_name('parameters')
            params_text = ''
            if params_node:
                params_text = source_code[params_node.start_byte:params_node.end_byte].decode('utf-8')

            # Return type
            return_type_node = node.child_by_field_name('return_type')
            return_type = ''
            if return_type_node:
                return_type = source_code[return_type_node.start_byte:return_type_node.end_byte].decode('utf-8')

            signature = f"def {func_name}{params_text}"
            if return_type:
                signature += f" -> {return_type}"

            docstring = self._extract_docstring(node, source_code)
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
            name_node = node.child_by_field_name('name')
            if not name_node:
                return None
            class_name = source_code[name_node.start_byte:name_node.end_byte].decode('utf-8')
            entity_id = f"class:{file_path}:{class_name}"

            superclasses_node = node.child_by_field_name('superclasses')
            if superclasses_node:
                bases_text = source_code[superclasses_node.start_byte:superclasses_node.end_byte].decode('utf-8')
                signature = f"class {class_name}{bases_text}"
            else:
                signature = f"class {class_name}"

            docstring = self._extract_docstring(node, source_code)
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
        body_node = node.child_by_field_name('body')
        if not body_node:
            return ""
        for child in body_node.children:
            if child.type == 'expression_statement':
                for grandchild in child.children:
                    if grandchild.type == 'string':
                        raw = source_code[grandchild.start_byte:grandchild.end_byte].decode('utf-8')
                        # Strip surrounding quotes (single, double, triple)
                        doc = raw.strip('"""').strip("''").strip('"').strip("'").strip()
                        return doc
        return ""

    def _extract_edges(self, tree: Tree, file_path: str, source_code: bytes) -> List[Tuple[str, str, str, Optional[str]]]:
        """Extract CALLS, INHERITS, and MUTATES edges from the parse tree."""
        edges: List[Tuple[str, str, str, Optional[str]]] = []
        entity_stack: List[Dict[str, str]] = []

        mutating_methods = {'append', 'extend', 'insert', 'update', 'add', 'remove', 'pop', 'clear', 'discard'}

        def add_mutates(target_id: str, line_no: int, mut_type: str):
            if entity_stack:
                source_id = entity_stack[-1]['id']
                context = f"line:{line_no} type:{mut_type}"
                edges.append((source_id, 'MUTATES', target_id, context))

        def add_reads_config(config_id: str, line_no: int, access_method: str):
            if entity_stack:
                source_id = entity_stack[-1]['id']
                context = f"line:{line_no} via:{access_method}"
                edges.append((source_id, 'READS_CONFIG', config_id, context))

        def walk(node):
            # Function definitions – push context
            if node.type == 'function_definition':
                name_node = node.child_by_field_name('name')
                if name_node:
                    func_name = source_code[name_node.start_byte:name_node.end_byte].decode('utf-8')
                    if entity_stack and entity_stack[-1]['type'] == 'class':
                        entity_id = f"method:{file_path}:{entity_stack[-1]['name']}.{func_name}"
                    else:
                        entity_id = f"func:{file_path}:{func_name}"
                    entity_stack.append({'type': 'function', 'id': entity_id, 'name': func_name})
                    for child in node.children:
                        walk(child)
                    entity_stack.pop()
                    return

            # Class definitions – push context and handle INHERITS
            if node.type == 'class_definition':
                name_node = node.child_by_field_name('name')
                if name_node:
                    class_name = source_code[name_node.start_byte:name_node.end_byte].decode('utf-8')
                    entity_id = f"class:{file_path}:{class_name}"
                    entity_stack.append({'type': 'class', 'id': entity_id, 'name': class_name})
                    # INHERITS edges
                    super_node = node.child_by_field_name('superclasses')
                    if super_node:
                        for child in super_node.children:
                            if child.type == 'identifier':
                                base_name = source_code[child.start_byte:child.end_byte].decode('utf-8')
                                target_id = f"class:{file_path}:{base_name}"  # simplified
                                edges.append((entity_id, 'INHERITS', target_id, None))
                    for child in node.children:
                        walk(child)
                    entity_stack.pop()
                    return

            # CALLS and Mutating Method edges
            if node.type == 'call':
                if entity_stack:
                    caller_id = entity_stack[-1]['id']
                    func_node = node.child_by_field_name('function')
                    if func_node:
                        if func_node.type == 'identifier':
                            callee_name = source_code[func_node.start_byte:func_node.end_byte].decode('utf-8')
                            target_id = f"func:{file_path}:{callee_name}"
                            edges.append((caller_id, 'CALLS', target_id, None))
                        elif func_node.type == 'attribute':
                            attr_node = func_node.child_by_field_name('attribute')
                            if attr_node:
                                method_name = source_code[attr_node.start_byte:attr_node.end_byte].decode('utf-8')
                                target_id = f"method:{file_path}:*.{method_name}"
                                edges.append((caller_id, 'CALLS', target_id, None))

                                # MUTATES edge for specific methods
                                if method_name in mutating_methods:
                                    obj_node = func_node.child_by_field_name('object')
                                    if obj_node:
                                        obj_name = source_code[obj_node.start_byte:obj_node.end_byte].decode('utf-8')
                                        line_no = func_node.start_point[0] + 1
                                        if obj_node.type == 'identifier':
                                            target_id = f"var:{file_path}:{obj_name}"
                                            add_mutates(target_id, line_no, 'method_call')
                                        elif obj_node.type == 'attribute':
                                            sub_attr = obj_node.child_by_field_name('attribute')
                                            if sub_attr:
                                                sub_name = source_code[sub_attr.start_byte:sub_attr.end_byte].decode('utf-8')
                                                target_id = f"attr:{file_path}:{sub_name}"
                                                add_mutates(target_id, line_no, 'method_call')

                                # READS_CONFIG: Check for os.getenv() or os.environ.get()
                                obj_node = func_node.child_by_field_name('object')
                                
                                # os.getenv('VAR')
                                if method_name == 'getenv' and obj_node and obj_node.type == 'identifier':
                                    obj_name = source_code[obj_node.start_byte:obj_node.end_byte].decode('utf-8')
                                    if obj_name == 'os':
                                        args_node = node.child_by_field_name('arguments')
                                        if args_node:
                                            for arg_child in args_node.children:
                                                if arg_child.type == 'string':
                                                    for string_part in arg_child.children:
                                                        if string_part.type == 'string_content':
                                                            env_var = source_code[string_part.start_byte:string_part.end_byte].decode('utf-8')
                                                            config_id = f"config:env:{env_var}"
                                                            line_no = node.start_point[0] + 1
                                                            add_reads_config(config_id, line_no, 'os.getenv')
                                                            break
                                
                                # os.environ.get('VAR')
                                elif method_name == 'get' and obj_node and obj_node.type == 'attribute':
                                    sub_obj = obj_node.child_by_field_name('object')
                                    sub_attr = obj_node.child_by_field_name('attribute')
                                    if sub_obj and sub_attr:
                                        sub_obj_name = source_code[sub_obj.start_byte:sub_obj.end_byte].decode('utf-8')
                                        sub_attr_name = source_code[sub_attr.start_byte:sub_attr.end_byte].decode('utf-8')
                                        if sub_obj_name == 'os' and sub_attr_name == 'environ':
                                            args_node = node.child_by_field_name('arguments')
                                            if args_node:
                                                for arg_child in args_node.children:
                                                    if arg_child.type == 'string':
                                                        for string_part in arg_child.children:
                                                            if string_part.type == 'string_content':
                                                                env_var = source_code[string_part.start_byte:string_part.end_byte].decode('utf-8')
                                                                config_id = f"config:env:{env_var}"
                                                                line_no = node.start_point[0] + 1
                                                                add_reads_config(config_id, line_no, 'os.environ.get')
                                                                break

                for child in node.children:
                    walk(child)
                return

            # Assignment mutations
            if node.type in ('assignment', 'augmented_assignment'):
                left_node = node.child_by_field_name('left')
                if left_node:
                    if left_node.type == 'identifier':
                        var_name = source_code[left_node.start_byte:left_node.end_byte].decode('utf-8')
                        target_id = f"var:{file_path}:{var_name}"
                        line_no = left_node.start_point[0] + 1
                        add_mutates(target_id, line_no, node.type)
                    elif left_node.type == 'attribute':
                        attr_node = left_node.child_by_field_name('attribute')
                        if attr_node:
                            attr_name = source_code[attr_node.start_byte:attr_node.end_byte].decode('utf-8')
                            target_id = f"attr:{file_path}:{attr_name}"
                            line_no = left_node.start_point[0] + 1
                            add_mutates(target_id, line_no, node.type)
                for child in node.children:
                    walk(child)
                return


            # READS_CONFIG: os.environ['VAR'] subscript access
            if node.type == 'subscript':
                value_node = node.child_by_field_name('value')
                if value_node and value_node.type == 'attribute':
                    obj_node = value_node.child_by_field_name('object')
                    attr_node = value_node.child_by_field_name('attribute')
                    if obj_node and attr_node:
                        obj_name = source_code[obj_node.start_byte:obj_node.end_byte].decode('utf-8')
                        attr_name = source_code[attr_node.start_byte:attr_node.end_byte].decode('utf-8')
                        if obj_name == 'os' and attr_name == 'environ':
                            # Extract subscript key (env var name)
                            for child in node.children:
                                if child.type == 'string':
                                    for string_part in child.children:
                                        if string_part.type == 'string_content':
                                            env_var = source_code[string_part.start_byte:string_part.end_byte].decode('utf-8')
                                            config_id = f"config:env:{env_var}"
                                            line_no = node.start_point[0] + 1
                                            add_reads_config(config_id, line_no, 'os.environ[]')
                                            break

            # READS_CONFIG: Uppercase constant references
            if node.type == 'identifier' and entity_stack:
                identifier_name = source_code[node.start_byte:node.end_byte].decode('utf-8')
                # Check if it's an uppercase constant (heuristic: all uppercase, length > 2)
                if identifier_name.isupper() and len(identifier_name) > 2 and '_' in identifier_name:
                    # Avoid false positives: skip if it's a class name or in specific contexts
                    parent = node.parent
                    if parent and parent.type not in ('class_definition', 'function_definition', 'import_from_statement'):
                        config_id = f"config:const:{identifier_name}"
                        line_no = node.start_point[0] + 1
                        add_reads_config(config_id, line_no, 'constant')

            # Recurse for other nodes
            for child in node.children:
                walk(child)

        walk(tree.root_node)
        return edges

    def generate_skeleton(self, file_path: str) -> Optional[str]:
        """Generate Telegraphic Semantic Compression (TSC) view of a file.
        Shows signatures, docstrings, and structure without implementation details.
        """
        try:
            with open(file_path, 'rb') as f:
                source_code = f.read()

            tree = self.parser.parse(source_code)
            skeleton_lines: List[str] = []
            skeleton_lines.append(f"# {file_path}")
            skeleton_lines.append("")

            def walk(node, indent: int = 0):
                indent_str = "    " * indent
                if node.type == 'class_definition':
                    name_node = node.child_by_field_name('name')
                    if not name_node:
                        return
                    class_name = source_code[name_node.start_byte:name_node.end_byte].decode('utf-8')
                    super_node = node.child_by_field_name('superclasses')
                    if super_node:
                        bases = source_code[super_node.start_byte:super_node.end_byte].decode('utf-8')
                        skeleton_lines.append(f"{indent_str}class {class_name}{bases}:")
                    else:
                        skeleton_lines.append(f"{indent_str}class {class_name}:")
                    doc = self._extract_docstring(node, source_code)
                    if doc:
                        skeleton_lines.append(f"{indent_str}    \"\"\"{doc}\"\"\"")
                    body = node.child_by_field_name('body')
                    if body:
                        for child in body.children:
                            walk(child, indent + 1)
                    skeleton_lines.append("")
                elif node.type == 'function_definition':
                    name_node = node.child_by_field_name('name')
                    if not name_node:
                        return
                    func_name = source_code[name_node.start_byte:name_node.end_byte].decode('utf-8')
                    params_node = node.child_by_field_name('parameters')
                    params = ''
                    if params_node:
                        params = source_code[params_node.start_byte:params_node.end_byte].decode('utf-8')
                    ret_node = node.child_by_field_name('return_type')
                    ret = ''
                    if ret_node:
                        ret = source_code[ret_node.start_byte:ret_node.end_byte].decode('utf-8')
                    signature = f"{indent_str}def {func_name}{params}"
                    if ret:
                        signature += f" -> {ret}"
                    signature += ":"
                    skeleton_lines.append(signature)
                    doc = self._extract_docstring(node, source_code)
                    if doc:
                        skeleton_lines.append(f"{indent_str}    \"\"\"{doc}\"\"\"")
                    skeleton_lines.append(f"{indent_str}    ...")
                    skeleton_lines.append("")
                elif node.type in ('import_statement', 'import_from_statement'):
                    import_text = source_code[node.start_byte:node.end_byte].decode('utf-8')
                    skeleton_lines.append(f"{indent_str}{import_text}")
                else:
                    if indent == 0:
                        for child in node.children:
                            walk(child, indent)

            walk(tree.root_node)
            return "\n".join(skeleton_lines)
        except Exception as e:
            logger.error(f"Failed to generate skeleton for {file_path}: {e}")
            return None

    def invalidate_cache(self, file_path: str) -> None:
        """Remove cached parse tree for a file (currently no-op as caching is disabled)."""
        # Incremental parsing cache is currently disabled for tree-sitter 0.20 compatibility
        pass
