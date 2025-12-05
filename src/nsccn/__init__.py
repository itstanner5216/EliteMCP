"""
NSCCN - Neuro-Symbolic Causal Code Navigator
A context-efficient code navigation system using causal graphs and semantic search.
"""

from .database import NSCCNDatabase
from .parser import CodeParser
from .embeddings import EmbeddingEngine
from .search import HybridSearchEngine
from .graph import CausalFlowEngine
from .watcher import IncrementalGraphBuilder
from .tools import NSCCNTools
from .server import NSCCNServer

__all__ = [
    'NSCCNDatabase',
    'CodeParser',
    'EmbeddingEngine',
    'HybridSearchEngine',
    'CausalFlowEngine',
    'IncrementalGraphBuilder',
    'NSCCNTools',
    'NSCCNServer'
]

__version__ = "1.0.0"
