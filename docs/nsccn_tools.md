# NSCCN Tools Reference

## Overview

NSCCN provides four primary tools for context-efficient code navigation. These tools implement a progressive workflow: **Locate → Orient → Trace → Examine**.

## Tool 1: search_and_rank (Locate)

**Purpose**: Find code entities using hybrid search (lexical + semantic).

**When to use**: 
- Finding entry points for a feature or bug
- Locating relevant code for a task
- Discovering what exists in a codebase

**Parameters**:
- `query` (str): Natural language description of what you're looking for
- `limit` (int, default=10): Maximum number of results

**Output Format**:
```json
[
  {
    "id": "func:src/auth.py:validate_token",
    "score": 0.89,
    "sig": "def validate_token(token: str) -> bool",
    "file": "src/auth.py",
    "line": 15
  },
  {
    "id": "func:src/auth.py:check_expiry",
    "score": 0.72,
    "sig": "def check_expiry(exp: int) -> bool",
    "file": "src/auth.py",
    "line": 42
  }
]
```

**Example Usage**:
```python
# Find authentication related functions
results = search_and_rank("validate JWT token", limit=5)

# Find error handling code
results = search_and_rank("handle database connection error", limit=10)

# Find data processing functions
results = search_and_rank("parse CSV file into dataframe", limit=5)
```

**How it works**:
1. **Lexical Search**: Uses ripgrep to find keyword matches
2. **Semantic Search**: Embeds query and finds similar entities
3. **RRF Fusion**: Combines results using Reciprocal Rank Fusion
4. **Returns**: Ranked entities with relevance scores

---

## Tool 2: read_skeleton (Orient)

**Purpose**: Get Telegraphic Semantic Compression (TSC) view of a file.

**When to use**:
- Understanding file structure before reading full code
- Getting a high-level overview
- Checking what functions/classes exist in a file
- Reducing context tokens while maintaining structure

**Parameters**:
- `file_path` (str): Path to the file to skeletonize

**Output Format**:
```python
# src/auth.py

class AuthService:
    """Handles authentication and token validation."""
    
    def __init__(self, secret: str): ...
    
    def validate_token(self, token: str) -> bool:
        """Validate JWT token and check expiry."""
        ...
    
    def check_expiry(self, exp: int) -> bool:
        """Check if token expiration timestamp is valid."""
        ...
    
    def generate_token(self, user_id: str) -> str:
        """Generate new JWT token for user."""
        ...
```

**Example Usage**:
```python
# Get overview of authentication module
skeleton = read_skeleton("src/auth.py")

# Understand API structure
skeleton = read_skeleton("src/api/routes.py")

# Check test file structure
skeleton = read_skeleton("test/test_auth.py")
```

**Token Reduction**:
- Typical reduction: 70-90%
- Preserves: signatures, types, docstrings, structure
- Removes: implementation details (replaced with `...`)
- Cached for performance

---

## Tool 3: trace_causal_path (Trace)

**Purpose**: Trace the causal graph from a specific code entity.

**When to use**:
- Understanding call chains
- Finding who calls a function (impact analysis)
- Discovering what a function calls (dependency analysis)
- Exploring class hierarchies

**Parameters**:
- `entity_id` (str): Entity to start from (e.g., "func:src/auth.py:login")
- `direction` (str, default="downstream"): 
  - `"upstream"`: Who calls this? (callers)
  - `"downstream"`: What does this call? (callees)
  - `"inheritance"`: Class hierarchy
- `depth` (int, default=3): Maximum hops to traverse

**Output Format**:
```json
{
  "root": "func:src/auth.py:validate_token",
  "direction": "downstream",
  "depth": 3,
  "adjacency_list": {
    "func:src/auth.py:validate_token": [
      {"target": "func:src/auth.py:check_expiry", "relation": "CALLS"},
      {"target": "func:src/auth.py:verify_signature", "relation": "CALLS"}
    ],
    "func:src/auth.py:check_expiry": [
      {"target": "func:src/utils.py:parse_timestamp", "relation": "CALLS"}
    ]
  },
  "entities": {
    "func:src/auth.py:validate_token": {
      "id": "func:src/auth.py:validate_token",
      "type": "function",
      "name": "validate_token",
      "file_path": "src/auth.py",
      "signature": "def validate_token(token: str) -> bool"
    }
  }
}
```

**Example Usage**:
```python
# Find what login function calls
trace = trace_causal_path(
    entity_id="func:src/auth.py:login",
    direction="downstream",
    depth=2
)

# Find who calls a utility function (impact analysis)
trace = trace_causal_path(
    entity_id="func:src/utils.py:send_email",
    direction="upstream",
    depth=3
)

# Explore class hierarchy
trace = trace_causal_path(
    entity_id="class:src/models.py:User",
    direction="inheritance",
    depth=2
)
```

**Depth Guidelines**:
- Depth 1: Direct calls only
- Depth 2: Two-hop relationships
- Depth 3 (default): Research shows 95% of dependencies within 3 hops
- Higher depths: Exponentially more results

---

## Tool 4: open_surgical_window (Examine)

**Purpose**: Read specific entity implementation with minimal context.

**When to use**:
- After locating exact entity to edit
- Reading targeted implementation details
- Minimizing context tokens for LLM consumption
- Surgical code edits

**Parameters**:
- `entity_id` (str): Entity to read (e.g., "func:src/auth.py:validate_token")
- `context_lines` (int, default=5): Lines of context above/below entity

**Output Format**:
```json
{
  "entity_id": "func:src/auth.py:validate_token",
  "file": "src/auth.py",
  "start": 15,
  "end": 23,
  "code": "  10 | \n  11 | class AuthService:\n  12 |     \"\"\"Authentication service.\"\"\"\n  13 | \n  14 |     def validate_token(self, token: str) -> bool:\n  15 |         \"\"\"Validate JWT token.\"\"\"\n  16 |         try:\n  17 |             decoded = jwt.decode(token, self.secret)\n  18 |             return self.check_expiry(decoded['exp'])\n  19 |         except jwt.InvalidTokenError:\n  20 |             return False\n  21 | \n  22 |     def check_expiry(self, exp: int) -> bool:\n  23 |         return exp > time.time()\n"
}
```

**Example Usage**:
```python
# Read specific function implementation
code = open_surgical_window(
    entity_id="func:src/auth.py:validate_token",
    context_lines=5
)

# Read method with minimal context
code = open_surgical_window(
    entity_id="method:src/models.py:User.save",
    context_lines=3
)

# Read class definition with more context
code = open_surgical_window(
    entity_id="class:src/api.py:APIRouter",
    context_lines=10
)
```

**Context Guidelines**:
- 3 lines: Minimal context, fastest
- 5 lines (default): Good balance
- 10+ lines: More context for complex code

---

## Complete Workflow Example

### Task: Fix token validation bug

1. **Locate** - Find relevant code:
```python
results = search_and_rank("validate JWT token", limit=5)
# Returns: func:src/auth.py:validate_token (score: 0.89)
```

2. **Orient** - Understand file structure:
```python
skeleton = read_skeleton("src/auth.py")
# Shows: AuthService class with validate_token, check_expiry, etc.
```

3. **Trace** - Understand dependencies:
```python
trace = trace_causal_path(
    entity_id="func:src/auth.py:validate_token",
    direction="downstream",
    depth=2
)
# Shows: calls check_expiry and verify_signature
```

4. **Examine** - Read implementation:
```python
code = open_surgical_window(
    entity_id="func:src/auth.py:validate_token",
    context_lines=5
)
# Returns: Full implementation with context
```

---

## Performance & Best Practices

### Search Tips
- Use descriptive queries: "validate JWT token" vs "token"
- Combine keywords and concepts: "parse CSV into DataFrame"
- Limit results to stay focused (5-10 is usually enough)

### Skeleton Tips
- Use before reading full file to understand structure
- Cached after first generation (very fast)
- Great for large files (>500 LOC)

### Trace Tips
- Start with depth=2 or 3 (most useful)
- Use upstream for impact analysis
- Use downstream for dependency analysis
- Inheritance direction for class hierarchies

### Surgical Window Tips
- Only use after locating exact entity
- Adjust context_lines based on complexity
- Minimize context for token efficiency

---

## Entity ID Format

Entity IDs follow a consistent format: `{type}:{file_path}:{name}`

**Examples**:
- Function: `func:src/auth.py:validate_token`
- Method: `method:src/models.py:User.save`
- Class: `class:src/api.py:APIRouter`
- Module: `module:src/utils.py:__init__`

**Getting Entity IDs**:
1. From `search_and_rank` results (`id` field)
2. From `trace_causal_path` output (`entities` dict)
3. Manual construction if you know the location
