# NSCCN Architecture Documentation

## Overview

NSCCN (Neuro-Symbolic Causal Code Navigator) is a context-efficient code navigation system that replaces naive file operations with a research-backed architecture achieving ~84% token reduction on input context.

## Architecture Layers

NSCCN implements a "Map vs. Territory" cognitive model with six layers:

```
Layer 6: FastMCP Interface (expose tools via stdio)
Layer 5: Intent Resolution Engine (NL → graph traversals + Hybrid RRF)
Layer 4: Skeletonization Engine (Telegraphic Semantic Compression)
Layer 3: Heterogeneous Code Graph (structural nodes + causal edges)
Layer 2: Neural-Lexical Index (sqlite-vec + ripgrep)
Layer 1: Incremental Graph Builder (watchdog + tree-sitter)
```

## Components

### 1. Database Layer (`database.py`)

**Purpose**: Persistent storage for code graph, embeddings, and cached skeletons.

**Key Features**:
- SQLite database with three tables: entities, edges, skeletons
- Efficient indexing for graph queries
- Vector storage for embeddings (numpy arrays as BLOBs)
- CRUD operations for entities, edges, and skeletons

**Schema**:
```sql
-- Entities: code elements (functions, classes, modules)
entities (id, type, file_path, name, start_line, end_line, signature, docstring, embedding, last_updated)

-- Edges: causal relationships (CALLS, INHERITS)
edges (source_id, relation, target_id, context)

-- Skeletons: cached compressed views
skeletons (file_path, content, last_modified)
```

### 2. Parser (`parser.py`)

**Purpose**: Extract code structure and generate compressed views using Tree-sitter.

**Key Features**:
- Tree-sitter based Python parsing
- Extract functions, classes, methods with metadata
- Generate entity IDs: `{type}:{file_path}:{name}`
- Extract CALLS and INHERITS edges
- Telegraphic Semantic Compression (skeleton generation)
- Incremental parsing support (cached parse trees)

**Skeleton Format**:
- Keep: signatures, type hints, docstrings, structure
- Remove: implementation details (replaced with `...`)
- Target: 70-90% token reduction

### 3. Embedding Engine (`embeddings.py`)

**Purpose**: Generate semantic embeddings for code entities.

**Key Features**:
- Uses fastembed with nomic-ai/nomic-embed-text-v1.5
- Matryoshka Representation Learning (MRL) for 256-dim vectors
- Batch embedding for efficiency
- Async embedding queue for incremental updates
- Embeds signature + docstring (not full code)

### 4. Search Engine (`search.py`)

**Purpose**: Hybrid search combining lexical and semantic approaches.

**Key Features**:
- **Lexical Stream**: ripgrep for fast keyword search
- **Semantic Stream**: embedding similarity search
- **RRF Fusion**: Reciprocal Rank Fusion (k=60)

**RRF Formula**:
```
Score(d) = Σ 1/(k + rank(d))
```

### 5. Graph Engine (`graph.py`)

**Purpose**: Causal flow analysis and multi-hop reasoning.

**Key Features**:
- Upstream traversal: find callers (who calls this?)
- Downstream traversal: find callees (what does this call?)
- Inheritance chain: class hierarchy
- Depth limiting (default 3 hops)
- Returns subgraphs as adjacency lists

### 6. File Watcher (`watcher.py`)

**Purpose**: Real-time incremental graph updates.

**Key Features**:
- Monitors `.py` files using watchdog
- Debounces events (100ms default)
- On file change:
  1. Re-parse with Tree-sitter
  2. Compare with database, update delta
  3. Re-extract edges
  4. Queue for re-embedding
  5. Invalidate skeleton cache
- Background thread execution
- Graceful shutdown

### 7. Tools Interface (`tools.py`)

**Purpose**: Expose NSCCN capabilities as FastMCP tools.

**Four Primary Tools**:

1. **`search_and_rank`** (Locate)
   - Find code entities using Hybrid RRF
   - Input: natural language query
   - Output: compact JSON with entity IDs, scores, signatures

2. **`read_skeleton`** (Orient)
   - Get Telegraphic Semantic Compression view
   - Input: file path
   - Output: compressed file view (signatures + structure)

3. **`trace_causal_path`** (Trace)
   - Trace causal graph from entity
   - Input: entity ID, direction (upstream/downstream/inheritance), depth
   - Output: JSON adjacency list of subgraph

4. **`open_surgical_window`** (Examine)
   - Read specific entity implementation
   - Input: entity ID, context lines
   - Output: entity source code with line numbers

### 8. Main Server (`server.py`)

**Purpose**: Orchestrate all components and expose via FastMCP.

**Key Features**:
- Initialize all components
- Load configuration
- Build initial index (`--init` flag)
- Start file watcher
- Register tools with FastMCP
- Graceful shutdown
- Tool discovery (`--info` flag)

## Data Flow

### Initial Indexing

```
1. Scan directory for Python files
2. Parse each file with Tree-sitter
3. Extract entities and edges
4. Embed entities (batch)
5. Store in database
6. Generate and cache skeletons
```

### Incremental Updates

```
1. File change detected by watchdog
2. Debounce (100ms)
3. Re-parse file
4. Compare entities (added/removed/updated)
5. Update database (entities + edges)
6. Queue changed entities for re-embedding
7. Invalidate skeleton cache
```

### Query Flow

```
1. User query → search_and_rank
2. Lexical search (ripgrep) + Semantic search (embeddings)
3. RRF fusion
4. Return ranked entity IDs
5. User selects entity → trace_causal_path
6. Graph traversal (upstream/downstream)
7. Return subgraph
8. User identifies target → open_surgical_window
9. Return entity source with context
```

## Performance Characteristics

**Initial Indexing**:
- ~1 minute for 10k LOC codebase
- Memory: ~500MB for 100k entity index

**Incremental Updates**:
- <100ms per file change
- Background processing

**Search**:
- <50ms for hybrid RRF query
- Combines lexical and semantic results

**Skeleton Generation**:
- <20ms per file
- 70-90% token reduction
- Cached for performance

## Configuration

Configuration file: `config/nsccn_config.json`

```json
{
    "database_path": "nsccn.db",
    "embedding_model": "nomic-ai/nomic-embed-text-v1.5",
    "embedding_dim": 256,
    "rrf_k": 60,
    "max_traversal_depth": 3,
    "skeleton_cache_enabled": true,
    "watch_debounce_ms": 100,
    "supported_languages": ["python"],
    "ignore_patterns": ["**/test_*", "**/__pycache__/**", "**/.*"]
}
```

## Design Principles

1. **Zero-cost**: No external APIs, all local execution
2. **Context-efficient**: 84% token reduction via skeletons
3. **Incremental**: Real-time updates with minimal overhead
4. **Causal**: Graph-based reasoning over naive search
5. **Hybrid**: Combine lexical and semantic approaches
6. **Surgical**: Navigate to exact code location efficiently

## Future Enhancements

- Multi-language support (JavaScript, TypeScript, Go)
- Additional edge types (PROPAGATES_ERROR)
- Cross-file call resolution
- IDE integration
- Performance optimizations (parallel indexing)
