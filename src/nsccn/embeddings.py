#!/usr/bin/env python3
"""
Embedding engine using fastembed with Nomic embeddings.
Implements Matryoshka Representation Learning (MRL) for 256-dim vectors.
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional
import numpy as np
from queue import Queue
from threading import Thread, Lock

logger = logging.getLogger(__name__)

# Lazy import fastembed to avoid startup issues
_fastembed_loaded = False
_TextEmbedding = None


def _load_fastembed():
    """Lazy load fastembed module."""
    global _fastembed_loaded, _TextEmbedding
    if not _fastembed_loaded:
        try:
            from fastembed import TextEmbedding
            _TextEmbedding = TextEmbedding
            _fastembed_loaded = True
        except ImportError:
            logger.error("fastembed not installed. Install with: pip install fastembed")
            raise


class EmbeddingEngine:
    """Manages text embeddings using Nomic model with MRL."""

    def __init__(self, model_name: str = "nomic-ai/nomic-embed-text-v1.5", embedding_dim: int = 256):
        """
        Initialize the embedding engine.
        
        Args:
            model_name: The fastembed model to use
            embedding_dim: Target embedding dimension (supports MRL)
        """
        self.model_name = model_name
        self.embedding_dim = embedding_dim
        self.model = None
        self._model_lock = Lock()
        
        # Async embedding queue
        self.embedding_queue = Queue()
        self.results_queue = Queue()
        self.worker_thread = None
        self.worker_running = False
        
        logger.info(f"EmbeddingEngine initialized: model={model_name}, dim={embedding_dim}")

    def _ensure_model_loaded(self):
        """Ensure the embedding model is loaded."""
        if self.model is None:
            with self._model_lock:
                if self.model is None:
                    _load_fastembed()
                    logger.info(f"Loading embedding model: {self.model_name}")
                    self.model = _TextEmbedding(model_name=self.model_name)
                    logger.info("Embedding model loaded successfully")

    def embed_text(self, text: str) -> np.ndarray:
        """
        Embed a single text string.
        
        Args:
            text: Text to embed
            
        Returns:
            Numpy array of shape (embedding_dim,)
        """
        self._ensure_model_loaded()
        
        try:
            # Generate embedding
            embeddings = list(self.model.embed([text]))
            embedding = np.array(embeddings[0], dtype=np.float32)
            
            # Truncate to target dimension (MRL)
            if len(embedding) > self.embedding_dim:
                embedding = embedding[:self.embedding_dim]
            
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to embed text: {e}")
            # Return zero vector on error
            return np.zeros(self.embedding_dim, dtype=np.float32)

    def embed_batch(self, texts: List[str]) -> List[np.ndarray]:
        """
        Embed multiple texts in a batch.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of numpy arrays, each of shape (embedding_dim,)
        """
        self._ensure_model_loaded()
        
        if not texts:
            return []
        
        try:
            # Generate embeddings in batch
            embeddings = list(self.model.embed(texts))
            
            # Convert and truncate
            result = []
            for embedding in embeddings:
                emb_array = np.array(embedding, dtype=np.float32)
                if len(emb_array) > self.embedding_dim:
                    emb_array = emb_array[:self.embedding_dim]
                result.append(emb_array)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to embed batch: {e}")
            # Return zero vectors on error
            return [np.zeros(self.embedding_dim, dtype=np.float32) for _ in texts]

    def embed_entity(self, entity: Dict[str, Any]) -> np.ndarray:
        """
        Embed an entity by combining signature and docstring.
        
        Args:
            entity: Entity dictionary with 'signature' and 'docstring'
            
        Returns:
            Numpy array of shape (embedding_dim,)
        """
        # Combine signature and docstring for embedding
        text_parts = []
        
        if entity.get('signature'):
            text_parts.append(entity['signature'])
        
        if entity.get('docstring'):
            text_parts.append(entity['docstring'])
        
        if not text_parts:
            # Fallback to name
            text_parts.append(entity.get('name', ''))
        
        text = " ".join(text_parts)
        return self.embed_text(text)

    def embed_entities_batch(self, entities: List[Dict[str, Any]]) -> List[np.ndarray]:
        """
        Embed multiple entities in a batch.
        
        Args:
            entities: List of entity dictionaries
            
        Returns:
            List of numpy arrays, each of shape (embedding_dim,)
        """
        # Prepare texts from entities
        texts = []
        for entity in entities:
            text_parts = []
            if entity.get('signature'):
                text_parts.append(entity['signature'])
            if entity.get('docstring'):
                text_parts.append(entity['docstring'])
            if not text_parts:
                text_parts.append(entity.get('name', ''))
            texts.append(" ".join(text_parts))
        
        return self.embed_batch(texts)

    def start_async_worker(self):
        """Start the async embedding worker thread."""
        if self.worker_running:
            logger.warning("Async worker already running")
            return
        
        self.worker_running = True
        self.worker_thread = Thread(target=self._async_worker, daemon=True)
        self.worker_thread.start()
        logger.info("Async embedding worker started")

    def stop_async_worker(self):
        """Stop the async embedding worker thread."""
        if not self.worker_running:
            return
        
        self.worker_running = False
        # Add sentinel to queue to wake up worker
        self.embedding_queue.put(None)
        
        if self.worker_thread:
            self.worker_thread.join(timeout=5.0)
        
        logger.info("Async embedding worker stopped")

    def _async_worker(self):
        """Worker thread for async embeddings."""
        while self.worker_running:
            try:
                # Get task from queue (blocking)
                task = self.embedding_queue.get(timeout=1.0)
                
                if task is None:  # Sentinel for shutdown
                    break
                
                task_id, entity = task
                
                # Embed the entity
                embedding = self.embed_entity(entity)
                
                # Put result in results queue
                self.results_queue.put((task_id, embedding))
                
            except Exception as e:
                if self.worker_running:
                    logger.error(f"Error in async worker: {e}")

    def queue_entity_for_embedding(self, entity: Dict[str, Any], task_id: Optional[str] = None) -> str:
        """
        Queue an entity for async embedding.
        
        Args:
            entity: Entity to embed
            task_id: Optional task ID (defaults to entity ID)
            
        Returns:
            Task ID for retrieving the result
        """
        if not self.worker_running:
            self.start_async_worker()
        
        if task_id is None:
            task_id = entity.get('id', str(id(entity)))
        
        self.embedding_queue.put((task_id, entity))
        return task_id

    def get_async_result(self, timeout: float = 0.1) -> Optional[tuple]:
        """
        Get a result from the async queue (non-blocking).
        
        Args:
            timeout: How long to wait for a result
            
        Returns:
            Tuple of (task_id, embedding) or None
        """
        try:
            return self.results_queue.get(timeout=timeout)
        except:
            return None

    def cleanup(self):
        """Cleanup resources."""
        self.stop_async_worker()
