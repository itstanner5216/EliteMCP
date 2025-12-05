# GitHub Copilot Instructions for NSCCN Implementation

## Critical: Read the Research Specification First

**Before making any NSCCN changes, ALWAYS read `docs/NSCCN_SPEC.md`**. This is the research-backed specification that defines:

- The six-layer architecture
- The "Map vs. Territory" cognitive model
- Why each technology was chosen (Tree-sitter, nomic-embed-text-v1.5, RRF k=60)
- Performance targets validated by research
- Database schema for the Heterogeneous Code Graph

## What is NSCCN?

The Neuro-Symbolic Causal Code Navigator solves the **Context Window Saturation Paradox**: LLMs are handicapped by tools that dump entire files instead of providing intelligent navigation.

**Research-Backed Results**:
- **78-85% localization accuracy** (vs 12-18% for naive tools)
- **80-90% context reduction** (5,000 tokens → 800 tokens)
- **<50ms query latency** (local execution, no API calls)

**The Four-Tool Workflow**: Locate → Orient → Trace → Examine

## Implementation Phases

Check `docs/NSCCN_PHASES.md` for current implementation status:

- ✅ **Phase 0**: Core infrastructure (COMPLETED)
- ⏳ **Phase 1**: MUTATES edge extraction (state tracking)
- ⏳ **Phase 2**: READS_CONFIG edge extraction (config tracking)
- ⏳ **Phase 3**: PROPAGATES_ERROR edge extraction (error flow)
- ⏳ **Phase 4**: RRF k=60 optimization and validation
- ⏳ **Phase 5**: Binary quantization (32x storage, 17x speed)
- ⏳ **Phase 6**: Directory tool deprecation

## Before Submitting Any PR

### 1. Run Phase Tests

**CRITICAL**: Always run tests before submitting:

```bash
# For NSCCN changes
pytest test/test_nsccn*.py -v

# For specific components
pytest test/test_nsccn.py::TestDatabase -v
pytest test/test_nsccn.py::TestParser -v
pytest test/test_nsccn.py::TestGraph -v

# With coverage
pytest test/test_nsccn*.py --cov=src/nsccn --cov-report=term
```

The CI workflow (`.github/workflows/nsccn-ci.yml`) automatically runs these tests on PRs touching `src/nsccn/**` or `test/test_nsccn*.py`.

### 2. Verify Performance Targets

Your changes must meet research-backed performance targets:

| Operation | Target | Why |
|-----------|--------|-----|
| File change update | <100ms | Real-time incremental updates |
| Search query | <50ms | Local execution speed |
| Skeleton generation | <20ms | Cached retrieval |
| Graph traversal (depth 3) | <5ms | 95% of dependencies within 3 hops |
| Surgical window read | <1ms | Minimal I/O |

If you impact performance, include benchmark results in your PR.

### 3. Maintain Research Principles

Every NSCCN decision is research-backed. Don't deviate without justification:

- **Tree-sitter**: Chosen for incremental parsing (GLR algorithm), error tolerance, zero dependencies
- **nomic-embed-text-v1.5**: 8192-token context (vs 512 for MiniLM), MRL for 256-dim, superior code retrieval
- **RRF k=60**: Research-optimal fusion parameter, 10-15% MRR improvement
- **sqlite-vec**: Local execution, binary quantization support (32x storage, 17x speed)
- **Depth 3**: 95% of dependencies within 3 hops

## Key Architecture Concepts

### The Six-Layer Stack

```
Layer 6: FastMCP Interface (4 tools via stdio)
Layer 5: Intent Resolution Engine (Hybrid RRF, k=60)
Layer 4: Skeletonization Engine (TSC: 70-90% reduction)
Layer 3: Heterogeneous Code Graph (entities + edges)
Layer 2: Neural-Lexical Index (sqlite-vec + ripgrep)
Layer 1: Incremental Graph Builder (watchdog + tree-sitter)
```

### The Five Edge Types

1. **CALLS**: Function invocations (Tree-sitter call_expression) - ✅ Implemented
2. **MUTATES**: State changes (assignments to self.X, dict[key]) - ⏳ Phase 1
3. **READS_CONFIG**: Config access (UPPERCASE_VARS, os.environ) - ⏳ Phase 2
4. **PROPAGATES_ERROR**: Exception raises (raise statements) - ⏳ Phase 3
5. **INHERITS**: Class inheritance - ✅ Implemented

### The Four Tools (Locate → Orient → Trace → Examine)

1. **search_and_rank**: Hybrid RRF search (lexical + semantic)
2. **read_skeleton**: TSC view (80-90% token reduction)
3. **trace_causal_path**: Multi-hop graph traversal (upstream/downstream/state)
4. **open_surgical_window**: Precise entity reading (20-80 lines)

## Common Implementation Patterns

### Adding a New Edge Type (Phases 1-3)

Example: Implementing MUTATES edges

```python
# 1. Define Tree-sitter query in parser.py
MUTATES_QUERY = """
(assignment
  left: (attribute) @target
  right: (_)) @mutation
"""

# 2. Extract edges in _extract_mutates_edges()
def _extract_mutates_edges(self, tree, file_path):
    captures = self.query(MUTATES_QUERY, tree.root_node)
    for target, mutation in captures:
        # Create edge: source MUTATES target
        yield {
            'source_id': current_function_id,
            'relation': 'MUTATES',
            'target_id': f"attr:{file_path}:{target_name}",
            'context': f"line {target.start_point[0]}"
        }

# 3. Integrate in parse_file()
edges.extend(self._extract_mutates_edges(tree, file_path))

# 4. Store in database via NSCCNDatabase
self.db.insert_edges(edges)

# 5. Add tests in test_nsccn.py
def test_mutates_edge_extraction():
    code = """
def update_user(user, email):
    user.email = email
"""
    edges = parser.extract_edges(code)
    assert any(e['relation'] == 'MUTATES' for e in edges)
```

### Optimizing Search (Phase 4)

```python
# RRF formula must use k=60 (research-backed)
def reciprocal_rank_fusion(lexical_results, semantic_results, k=60):
    """
    Research: k=60 is optimal for IR tasks.
    Formula: Score(d) = Σ 1/(k + rank(d))
    """
    scores = {}
    
    # Lexical stream
    for rank, (entity_id, _) in enumerate(lexical_results, start=1):
        scores[entity_id] = scores.get(entity_id, 0) + 1 / (k + rank)
    
    # Semantic stream
    for rank, (entity_id, _) in enumerate(semantic_results, start=1):
        scores[entity_id] = scores.get(entity_id, 0) + 1 / (k + rank)
    
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
```

### Implementing Binary Quantization (Phase 5)

```python
# Research: 32x storage reduction, 17x faster, <5% accuracy loss
def quantize_binary(embedding: np.ndarray) -> bytes:
    """Convert 256 float32 → 256 bits (32 bytes)."""
    return np.packbits(embedding > 0).tobytes()

# Two-stage search: fast binary, precise re-rank
def hybrid_search(query_vec, k=10, rerank_k=50):
    # Stage 1: Fast binary search (17x faster)
    binary_results = db.search_binary(query_vec, limit=rerank_k)
    
    # Stage 2: Precise float re-ranking
    float_vecs = db.get_float_embeddings(binary_results)
    reranked = cosine_similarity(query_vec, float_vecs)
    return reranked[:k]
```

## Database Schema (Critical)

All code entities and relationships are stored in SQLite:

```sql
-- Nodes: functions, classes, methods
CREATE TABLE entities (
    id TEXT PRIMARY KEY,          -- "func:src/auth.py:validate_token"
    type TEXT NOT NULL,           -- "function", "class", "method"
    file_path TEXT,
    name TEXT,
    start_line INTEGER,
    end_line INTEGER,
    signature TEXT,               -- "def validate_token(token: str) -> bool"
    docstring TEXT,
    embedding BLOB,               -- 256-dim float32 or binary quantized
    last_updated REAL
);

-- Edges: CALLS, MUTATES, READS_CONFIG, PROPAGATES_ERROR, INHERITS
CREATE TABLE edges (
    source_id TEXT,
    relation TEXT,                -- Edge type
    target_id TEXT,
    context TEXT,                 -- Line numbers, method info
    PRIMARY KEY (source_id, relation, target_id)
);

-- Cached TSC views
CREATE TABLE skeletons (
    file_path TEXT PRIMARY KEY,
    content TEXT,                 -- 70-90% compressed
    last_modified REAL
);
```

## Configuration (Don't Hardcode)

All values come from `config/nsccn_config.json`:

```json
{
  "database_path": "nsccn.db",
  "embedding_model": "nomic-ai/nomic-embed-text-v1.5",
  "embedding_dim": 256,
  "rrf_k": 60,
  "max_traversal_depth": 3,
  "skeleton_cache_enabled": true,
  "watch_debounce_ms": 100,
  "binary_quantization_enabled": false,
  "quantization_threshold_entities": 50000
}
```

**Critical Parameters**:
- `rrf_k: 60` - Research-backed, don't change
- `embedding_dim: 256` - Via MRL from 768
- `max_traversal_depth: 3` - 95% of deps within 3 hops
- `quantization_threshold_entities: 50000` - Auto-enable for large codebases

## Naming Conventions

### Entity IDs
Format: `{type}:{file_path}:{name}`

Examples:
- `func:src/auth.py:validate_token`
- `class:src/models.py:User`
- `method:src/models.py:User.save`
- `config:env:DATABASE_URL`
- `exception:ValidationError`

### Edge Relations
Uppercase enum values: `CALLS`, `MUTATES`, `READS_CONFIG`, `PROPAGATES_ERROR`, `INHERITS`

### Database Tables
Lowercase plural: `entities`, `edges`, `skeletons`

## Code Quality Requirements

### Type Hints (Required)
```python
def extract_entities(self, file_path: str) -> List[Dict[str, Any]]:
    """Extract entities with full type annotations."""
    pass
```

### Docstrings (Required)
```python
def reciprocal_rank_fusion(
    lexical_results: List[Tuple[str, float]],
    semantic_results: List[Tuple[str, float]],
    k: int = 60
) -> List[Tuple[str, float]]:
    """
    Combine two result streams using Reciprocal Rank Fusion.
    
    Research-backed: k=60 is optimal for information retrieval.
    Formula: Score(d) = Σ 1/(k + rank(d))
    
    Args:
        lexical_results: List of (entity_id, score) from ripgrep
        semantic_results: List of (entity_id, score) from embeddings
        k: Fusion parameter (default: 60, research-validated)
    
    Returns:
        List of (entity_id, rrf_score) sorted by score
    """
    pass
```

### Error Handling
```python
# Use specific exceptions, avoid bare except
try:
    tree = parser.parse(code)
except TreeSitterError as e:
    logger.error(f"Parse failed: {e}")
    raise
```

## Troubleshooting

### Tests Failing
1. Check dependencies: `pip install -r requirements.txt`
2. Some tests require model download (~50MB for nomic-embed-text-v1.5)
3. Database locked: Close connections
4. Import errors: Ensure `src/` in PYTHONPATH

### Performance Issues
1. Profile: `pytest --profile` or `cProfile`
2. Check database indexes (critical for <5ms traversals)
3. Use batch operations (avoid N+1 queries)
4. Verify skeleton cache is working

### Parsing Issues
1. Ensure tree-sitter >= 0.20.0
2. Verify Python grammar loaded from tree-sitter-languages
3. Test with minimal example to isolate pattern
4. Print AST: `print(tree.root_node.sexp())`

## Example Workflows

### Implementing Phase 1 (MUTATES)

```bash
# 1. Read the research specification
cat docs/NSCCN_SPEC.md | grep -A 30 "MUTATES"

# 2. Read the phase plan
cat docs/NSCCN_PHASES.md | grep -A 50 "Phase 1"

# 3. Create test fixtures first (TDD)
# Edit test/test_nsccn.py, add TestMutatesEdges class

# 4. Implement Tree-sitter queries
# Edit src/nsccn/parser.py, add MUTATES_QUERY

# 5. Run tests iteratively
pytest test/test_nsccn.py::TestMutatesEdges -v

# 6. Integration test
pytest test/test_nsccn.py -v

# 7. Update documentation
# Edit docs/NSCCN_SPEC.md with implementation details

# 8. Submit PR with benchmark results
```

### Debugging Failed Search

```python
# Enable detailed logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Test each stream separately
lexical_results = ripgrep_search("JWT token")
print(f"Lexical: {lexical_results}")

semantic_results = embedding_search("JWT token")
print(f"Semantic: {semantic_results}")

# Test RRF fusion
rrf_results = reciprocal_rank_fusion(lexical_results, semantic_results, k=60)
print(f"RRF (k=60): {rrf_results}")

# Verify entity embeddings exist
entities = db.query("SELECT id, embedding FROM entities WHERE embedding IS NOT NULL")
print(f"Entities with embeddings: {len(entities)}")
```

## Commit Message Format

Use conventional commits for NSCCN:

```
feat(nsccn): implement MUTATES edge extraction
fix(nsccn): correct RRF k=60 score calculation  
docs(nsccn): add binary quantization research validation
test(nsccn): add mutation detection test cases
perf(nsccn): optimize graph traversal with indexes
refactor(nsccn): simplify embedding generation pipeline
```

## PR Checklist

Before submitting:

- [ ] Read relevant sections of `docs/NSCCN_SPEC.md`
- [ ] Check `docs/NSCCN_PHASES.md` for phase requirements
- [ ] Write tests for your changes (TDD preferred)
- [ ] Run `pytest test/test_nsccn*.py -v` locally - **all tests must pass**
- [ ] Meet performance targets (benchmark if needed)
- [ ] Update documentation (NSCCN_SPEC.md or NSCCN_PHASES.md)
- [ ] Add code examples if adding features
- [ ] Verify backward compatibility
- [ ] Follow naming conventions (Entity IDs, edge relations)
- [ ] Include research justification for design decisions

## Research References

When making architectural decisions, cite research:

```python
# Good: Research-backed decision
# Research: LocAgent study shows 95% of dependencies within 3 hops
max_depth = config.get('max_traversal_depth', 3)

# Bad: Arbitrary decision
max_depth = 5  # Why 5? No research justification
```

```python
# Good: Research-backed parameter
# Research: k=60 is optimal for IR tasks, provides 10-15% MRR improvement
rrf_k = 60

# Bad: Unvalidated parameter
rrf_k = 100  # Not supported by research
```

## Key Research Findings to Remember

1. **Context Window Saturation Paradox**: Brute-force file dumping consumes 80-90% of context with noise
2. **LocAgent Study**: Graph-guided navigation achieves 78% accuracy vs 12-18% for naive retrieval
3. **TSC (Telegraphic Semantic Compression)**: 70-90% token reduction, 100% structure preservation
4. **nomic-embed-text-v1.5**: 8192-token context, MRL for 256-dim, outperforms legacy models
5. **RRF k=60**: Optimal fusion parameter, 10-15% MRR improvement, research-validated
6. **Binary Quantization**: 32x storage reduction, 17x faster queries, <5% accuracy loss
7. **95% Rule**: 95% of dependencies within 3 hops - why default depth is 3
8. **CAST (AST-Based Chunking)**: Syntactically valid blocks, preserves semantic coherence

## Final Reminder

**Quality implementation starts with understanding the research.**

Always read `docs/NSCCN_SPEC.md` before making NSCCN changes. Every design decision in NSCCN is backed by contemporary research. Don't deviate without strong justification and validation.

The goal: Transform AI agents from text-processing chatbots into context-aware software engineers capable of navigating million-line codebases with surgical precision.
