#!/usr/bin/env python3
"""
Incremental graph builder using watchdog for real-time file monitoring.
"""

import logging
import time
import os
from pathlib import Path
from typing import Optional, Callable, Set
from threading import Thread, Event, Lock
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent, FileDeletedEvent

logger = logging.getLogger(__name__)


class CodeFileHandler(FileSystemEventHandler):
    """Handles file system events for code files."""

    def __init__(self, callback: Callable[[str, str], None], debounce_ms: int = 100):
        """
        Initialize the file handler.
        
        Args:
            callback: Function to call on file changes (path, event_type)
            debounce_ms: Debounce delay in milliseconds
        """
        self.callback = callback
        self.debounce_delay = debounce_ms / 1000.0
        self.pending_events = {}  # path -> (event_type, timestamp)
        self.lock = Lock()

    def on_modified(self, event):
        """Handle file modification events."""
        if not event.is_directory and self._is_python_file(event.src_path):
            self._queue_event(event.src_path, 'modified')

    def on_created(self, event):
        """Handle file creation events."""
        if not event.is_directory and self._is_python_file(event.src_path):
            self._queue_event(event.src_path, 'created')

    def on_deleted(self, event):
        """Handle file deletion events."""
        if not event.is_directory and self._is_python_file(event.src_path):
            self._queue_event(event.src_path, 'deleted')

    def _is_python_file(self, path: str) -> bool:
        """Check if file is a Python file."""
        return path.endswith('.py')

    def _queue_event(self, path: str, event_type: str):
        """Queue an event with debouncing."""
        with self.lock:
            self.pending_events[path] = (event_type, time.time())

    def process_pending_events(self):
        """Process pending events that have exceeded debounce delay."""
        with self.lock:
            current_time = time.time()
            to_process = []
            
            for path, (event_type, timestamp) in list(self.pending_events.items()):
                if current_time - timestamp >= self.debounce_delay:
                    to_process.append((path, event_type))
                    del self.pending_events[path]
        
        # Process events outside the lock
        for path, event_type in to_process:
            try:
                self.callback(path, event_type)
            except Exception as e:
                logger.error(f"Error processing event for {path}: {e}")


class IncrementalGraphBuilder:
    """Monitors files and incrementally updates the code graph."""

    def __init__(
        self,
        database,
        parser,
        embedding_engine,
        root_path: str = ".",
        debounce_ms: int = 100
    ):
        """
        Initialize the incremental graph builder.
        
        Args:
            database: NSCCNDatabase instance
            parser: CodeParser instance
            embedding_engine: EmbeddingEngine instance
            root_path: Root directory to watch
            debounce_ms: Debounce delay in milliseconds
        """
        self.db = database
        self.parser = parser
        self.embedder = embedding_engine
        self.root_path = Path(root_path).resolve()
        self.debounce_ms = debounce_ms
        
        self.observer = None
        self.event_handler = None
        self.running = False
        self.stop_event = Event()
        self.processor_thread = None
        
        logger.info(f"IncrementalGraphBuilder initialized for {self.root_path}")

    def start(self):
        """Start watching for file changes."""
        if self.running:
            logger.warning("Watcher already running")
            return
        
        self.running = True
        self.stop_event.clear()
        
        # Create event handler
        self.event_handler = CodeFileHandler(
            callback=self._handle_file_change,
            debounce_ms=self.debounce_ms
        )
        
        # Create and start observer
        self.observer = Observer()
        self.observer.schedule(self.event_handler, str(self.root_path), recursive=True)
        self.observer.start()
        
        # Start processor thread for debouncing
        self.processor_thread = Thread(target=self._processor_loop, daemon=True)
        self.processor_thread.start()
        
        logger.info("File watcher started")

    def stop(self):
        """Stop watching for file changes."""
        if not self.running:
            return
        
        self.running = False
        self.stop_event.set()
        
        # Stop observer
        if self.observer:
            self.observer.stop()
            self.observer.join(timeout=5.0)
        
        # Wait for processor thread
        if self.processor_thread:
            self.processor_thread.join(timeout=5.0)
        
        logger.info("File watcher stopped")

    def _processor_loop(self):
        """Background loop to process pending events."""
        while self.running and not self.stop_event.is_set():
            if self.event_handler:
                self.event_handler.process_pending_events()
            
            # Sleep for a short interval
            time.sleep(self.debounce_ms / 1000.0)

    def _handle_file_change(self, file_path: str, event_type: str):
        """
        Handle a file change event.
        
        Args:
            file_path: Path to the changed file
            event_type: Type of event (modified, created, deleted)
        """
        logger.info(f"Processing file change: {file_path} ({event_type})")
        
        try:
            if event_type == 'deleted':
                self._handle_file_deleted(file_path)
            else:
                self._handle_file_updated(file_path)
        except Exception as e:
            logger.error(f"Error handling file change for {file_path}: {e}")

    def _handle_file_updated(self, file_path: str):
        """Handle file creation or modification."""
        # Check if file exists and is readable
        if not os.path.exists(file_path):
            return
        
        # Parse the file
        parse_result = self.parser.parse_file(file_path, use_incremental=True)
        
        if not parse_result:
            logger.warning(f"Failed to parse {file_path}")
            return
        
        # Get existing entities for this file
        existing_entities = self.db.get_entities_by_file(file_path)
        existing_ids = {e['id'] for e in existing_entities}
        
        # Get new entities
        new_entities = parse_result['entities']
        new_ids = {e['id'] for e in new_entities}
        
        # Determine changes
        added_ids = new_ids - existing_ids
        removed_ids = existing_ids - new_ids
        updated_ids = new_ids & existing_ids
        
        logger.debug(f"File {file_path}: added={len(added_ids)}, removed={len(removed_ids)}, updated={len(updated_ids)}")
        
        # Remove deleted entities
        for entity_id in removed_ids:
            # Delete edges
            self.db.delete_edges_by_source(entity_id)
            # Note: Entity will be removed when we delete all entities for file
        
        # Delete all entities for this file (will be re-added)
        self.db.delete_entities_by_file(file_path)
        
        # Embed new entities
        if new_entities:
            embeddings = self.embedder.embed_entities_batch(new_entities)
            for entity, embedding in zip(new_entities, embeddings):
                entity['embedding'] = embedding
            
            # Insert entities
            self.db.upsert_entities_batch(new_entities)
        
        # Insert edges
        if parse_result['edges']:
            self.db.upsert_edges_batch(parse_result['edges'])
        
        # Invalidate skeleton cache
        self.db.delete_skeleton(file_path)
        
        logger.info(f"Updated graph for {file_path}: {len(new_entities)} entities, {len(parse_result['edges'])} edges")

    def _handle_file_deleted(self, file_path: str):
        """Handle file deletion."""
        # Get entities for this file
        entities = self.db.get_entities_by_file(file_path)
        
        # Delete edges for all entities
        for entity in entities:
            self.db.delete_edges_by_source(entity['id'])
        
        # Delete all entities
        self.db.delete_entities_by_file(file_path)
        
        # Delete skeleton
        self.db.delete_skeleton(file_path)
        
        # Invalidate parser cache
        self.parser.invalidate_cache(file_path)
        
        logger.info(f"Removed {len(entities)} entities for deleted file {file_path}")

    def build_initial_index(self, root_path: Optional[str] = None):
        """
        Build initial index for a directory.
        
        Args:
            root_path: Root directory to index (uses self.root_path if None)
        """
        if root_path is None:
            root_path = self.root_path
        else:
            root_path = Path(root_path).resolve()
        
        logger.info(f"Building initial index for {root_path}")
        start_time = time.time()
        
        # Find all Python files
        python_files = list(root_path.rglob("*.py"))
        
        # Filter out ignored patterns
        python_files = [
            f for f in python_files
            if not any(part.startswith('.') or part == '__pycache__' for part in f.parts)
        ]
        
        logger.info(f"Found {len(python_files)} Python files to index")
        
        # Process each file
        total_entities = 0
        total_edges = 0
        
        for i, file_path in enumerate(python_files):
            try:
                # Parse file
                parse_result = self.parser.parse_file(str(file_path), use_incremental=False)
                
                if not parse_result:
                    continue
                
                entities = parse_result['entities']
                edges = parse_result['edges']
                
                if entities:
                    # Embed entities
                    embeddings = self.embedder.embed_entities_batch(entities)
                    for entity, embedding in zip(entities, embeddings):
                        entity['embedding'] = embedding
                    
                    # Insert entities
                    self.db.upsert_entities_batch(entities)
                    total_entities += len(entities)
                
                if edges:
                    # Insert edges
                    self.db.upsert_edges_batch(edges)
                    total_edges += len(edges)
                
                if (i + 1) % 10 == 0:
                    logger.info(f"Indexed {i + 1}/{len(python_files)} files")
                
            except Exception as e:
                logger.error(f"Error indexing {file_path}: {e}")
        
        elapsed = time.time() - start_time
        logger.info(f"Initial indexing complete: {total_entities} entities, {total_edges} edges in {elapsed:.2f}s")

    def is_running(self) -> bool:
        """Check if watcher is running."""
        return self.running
