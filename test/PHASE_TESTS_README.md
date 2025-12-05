# NSCCN Phase Test Files

This directory contains test files for each NSCCN implementation phase as defined in `docs/NSCCN_PHASES.md`.

## Overview

**Total Tests**: 71 tests across 6 phases

All tests currently **FAIL** as expected - they define acceptance criteria for features that are not yet implemented. Each test references the relevant section in `docs/NSCCN_SPEC.md` or `docs/NSCCN_PHASES.md`.

## Test Files

### Phase 1: MUTATES Edge Extraction (10 tests)
**File**: `test_nsccn_phase1_mutates.py`  
**Reference**: NSCCN_SPEC.md §3.2.2, NSCCN_PHASES.md Phase 1

Tests MUTATES edge extraction for state tracking:
- Attribute mutations (`user.email = value`)
- Self mutations (`self.count += 1`)
- Dictionary mutations (`dict[key] = value`)
- List mutations (`list.append()`)
- Set mutations (`set.add()`)
- Global variable mutations
- State traversal with `direction='state'`

**Run independently**:
```bash
pytest test/test_nsccn_phase1_mutates.py -v
```

### Phase 2: READS_CONFIG Edge Extraction (14 tests)
**File**: `test_nsccn_phase2_reads_config.py`  
**Reference**: NSCCN_SPEC.md §3.2.2, NSCCN_PHASES.md Phase 2

Tests READS_CONFIG edge extraction for configuration tracking:
- Environment variables (`os.environ.get()`)
- Config file reads (`json.load()`, `yaml.load()`)
- Settings imports (`from config import X`)
- Uppercase constant references
- Pseudo-entity creation (`config:env:*`, `config:file:*`, `config:const:*`)
- Configuration dependency queries

**Run independently**:
```bash
pytest test/test_nsccn_phase2_reads_config.py -v
```

### Phase 3: PROPAGATES_ERROR Edge Extraction (13 tests)
**File**: `test_nsccn_phase3_propagates_error.py`  
**Reference**: NSCCN_SPEC.md §3.2.2, NSCCN_PHASES.md Phase 3

Tests PROPAGATES_ERROR edge extraction for error flow tracking:
- Explicit raises (`raise ValidationError()`)
- Re-raises (`except: ... raise`)
- Exception chaining (`raise X from Y`)
- Bare raises
- Multiple exception types per function
- Custom exception classes
- Error flow queries

**Run independently**:
```bash
pytest test/test_nsccn_phase3_propagates_error.py -v
```

### Phase 4: Intent Resolution Engine (9 tests)
**File**: `test_nsccn_phase4_intent_resolution.py`  
**Reference**: NSCCN_SPEC.md §3.3.2, NSCCN_PHASES.md Phase 4

Tests RRF k=60 implementation and search quality:
- Verify RRF constant is 60 (research-validated)
- RRF formula implementation (`Score(d) = Σ 1/(k + rank(d))`)
- Consensus boosting (items in both streams rank higher)
- Ranked results with scores
- Search latency targets (<50ms for 10K entities)
- Configuration validation

**Run independently**:
```bash
pytest test/test_nsccn_phase4_intent_resolution.py -v
```

**Note**: Phase 4 tests may take longer due to model downloads.

### Phase 5: Binary Quantization (13 tests)
**File**: `test_nsccn_phase5_binary_quantization.py`  
**Reference**: NSCCN_SPEC.md §5.2, NSCCN_PHASES.md Phase 5

Tests binary quantization for scalability:
- Binary conversion (256 float32 → 256 bits)
- 32x storage reduction validation
- Two-stage search (fast binary + precise float re-rank)
- <5% accuracy loss verification
- 17x query speedup target
- Performance at 100K+ entities
- Configuration (auto-enable at 50K entities)

**Run independently**:
```bash
pytest test/test_nsccn_phase5_binary_quantization.py -v
```

### Phase 6: Directory Tool Deprecation (12 tests)
**File**: `test_nsccn_phase6_deprecate_directory.py`  
**Reference**: NSCCN_SPEC.md §1.1, NSCCN_PHASES.md Phase 6

Tests NSCCN feature parity and token efficiency:
- All 4 NSCCN tools available (Locate → Orient → Trace → Examine)
- File overview capability (vs directory tool)
- Structure navigation
- >70% token reduction (TSC compression)
- Surgical windows (20-80 lines vs full files)
- 80-90% context efficiency improvement
- 78-85% localization accuracy target

**Run independently**:
```bash
pytest test/test_nsccn_phase6_deprecate_directory.py -v
```

## Running All Phase Tests

```bash
# Run all phase tests
pytest test/test_nsccn_phase*.py -v

# Run with summary
pytest test/test_nsccn_phase*.py -v --tb=short

# Collect only (no execution)
pytest test/test_nsccn_phase*.py --collect-only
```

## Test Structure

Each test file follows this structure:

1. **Imports**: Standard test setup with path configuration
2. **Helper Functions**: Workarounds for features not yet implemented
3. **Test Classes**: Organized by feature area
4. **Test Methods**: Individual test cases with:
   - Docstring with spec reference
   - Clear expected behavior
   - Descriptive assertion messages

### Example Test

```python
def test_attribute_mutation(self):
    """
    Test case 1: Attribute mutation detection.
    Reference: NSCCN_PHASES.md Phase 1 - "user.email = email"
    
    Expected: MUTATES edge from update_user to user.email
    """
    code = '''
def update_user(user, email):
    user.email = email
'''
    result = self._parse_code(code)
    
    mutates_edges = [e for e in result['edges'] if e[1] == 'MUTATES']
    
    self.assertGreater(
        len(mutates_edges), 0,
        "Should extract at least one MUTATES edge"
    )
```

## Test Results

### Current Status (All Phases)

```
Phase 1: 10 tests - 10 FAILED (features not implemented)
Phase 2: 14 tests - 11 FAILED, 3 PASSED (partial pseudo-entity support)
Phase 3: 13 tests - 9 FAILED, 4 PASSED (basic exception detection)
Phase 4: 9 tests - TBD (requires model download)
Phase 5: 13 tests - TBD (features not implemented)
Phase 6: 12 tests - TBD (depends on other phases)
```

### Expected Behavior

**Before Implementation**: Tests FAIL with clear error messages indicating missing features.

**After Implementation**: Tests PASS, validating that:
- Edge extraction works correctly
- Performance targets are met
- Research-backed parameters are used
- Feature parity is achieved

## Implementation Workflow

For each phase:

1. **Read the specification**: `docs/NSCCN_SPEC.md` and `docs/NSCCN_PHASES.md`
2. **Review the tests**: Understand acceptance criteria
3. **Implement features**: Make tests pass
4. **Run tests iteratively**: `pytest test/test_nsccn_phase{N}_*.py -v`
5. **Verify all pass**: Before merging PR
6. **Update documentation**: Reflect implementation status

## Quality Gates

Before completing each phase, verify:

- [ ] All phase-specific tests pass (100%)
- [ ] No regressions in other phase tests
- [ ] Performance benchmarks met
- [ ] Documentation updated
- [ ] Code review completed

## Research Validation

All tests are grounded in research findings from:

- **LocAgent Study (2025)**: 78-85% localization accuracy with graph navigation
- **TSC Research**: 70-90% token reduction with structure preservation
- **RRF k=60**: Optimal fusion parameter for IR tasks (10-15% MRR improvement)
- **Binary Quantization**: 32x storage, 17x speed, <5% accuracy loss
- **Meta's Glean**: Incremental graph updates at scale

See `docs/NSCCN_SPEC.md` Appendix B for full citations.

## Troubleshooting

### Tests fail to import

```bash
# Ensure dependencies are installed
pip install -r requirements.txt

# Check Python path
python -c "import sys; print(sys.path)"
```

### Model download takes too long

Phase 4 tests download `nomic-embed-text-v1.5` (~50MB) on first run. Subsequent runs use cached model.

```bash
# Skip Phase 4 if needed
pytest test/test_nsccn_phase[1-356]*.py -v
```

### Database errors

Some tests use temporary databases. If errors persist:

```bash
# Clean up any stale databases
rm -f *.db
```

## Contributing

When adding new tests:

1. Reference the spec section in docstring
2. Use descriptive assertion messages
3. Include code examples in test cases
4. Follow existing naming conventions
5. Test independently before committing

## Resources

- **Specification**: `docs/NSCCN_SPEC.md`
- **Phase Plan**: `docs/NSCCN_PHASES.md`
- **Existing Tests**: `test/test_nsccn.py`
- **Configuration**: `config/nsccn_config.json`

---

**Last Updated**: December 2024  
**Status**: All phase tests created, features pending implementation  
**Next Step**: Begin Phase 1 implementation (MUTATES edge extraction)
