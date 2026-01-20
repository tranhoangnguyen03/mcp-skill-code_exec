# Memory Module Tasks (2026-01-20)

## Phase 1: Quick Fixes (Current Sprint)

### 1.1 Add missing abstract methods to FileDataLayer
**Status**: TODO
**Priority**: High
**Description**: Implement `close()` and `get_favorite_steps()` methods required by Chainlit's `BaseDataLayer`.

**Acceptance Criteria**:
- [ ] `FileDataLayer` can be instantiated without errors
- [ ] `close()` method exists and is a no-op (YAML files don't need connection cleanup)
- [ ] `get_favorite_steps()` returns empty list (not implementing favorites feature yet)

**File**: `agent_workspace/memory/chainlit_data_layer.py`

---

## Phase 2: Unified Storage Layer

### 2.1 Remove _threads_index.yaml dependency
**Status**: TODO
**Priority**: High
**Description**: Refactor `FileDataLayer` to store thread metadata directly in each thread's YAML file instead of a separate index.

**Changes**:
- Remove `_threads_index_path` and `_load_threads_index()` / `_save_threads_index()`
- `update_thread()` writes to the thread's own YAML file
- `list_threads()` scans `sessions/` directory for thread files

### 2.2 Unify thread YAML schema
**Status**: TODO
**Priority**: High
**Description**: Define a single YAML structure that contains both thread metadata and messages.

**Schema**:
```yaml
session_id: str
created_at: str (ISO timestamp)
updated_at: str (ISO timestamp)
user_id: str | None
user_identifier: str | None
name: str | None
metadata: dict
tags: list[str]
messages: list[dict]
facts: list[dict]
```

### 2.3 Update FileDataLayer.get_thread() for unified reads
**Status**: TODO
**Priority**: High
**Description**: Modify `get_thread()` to read messages from the thread's YAML file.

**Changes**:
- Load thread data from `{thread_id}.yaml`
- Build `steps` list from `messages` array in the YAML
- Return `ThreadDict` with populated `steps`

### 2.4 Update FileDataLayer.create_step() for unified writes
**Status**: TODO
**Priority**: High
**Description**: Modify `create_step()` to append to the thread's YAML messages array.

**Changes**:
- Load the thread's YAML file
- Append new message to `messages` array
- Save the updated YAML

---

## Phase 3: SessionMemory Refactoring

### 3.1 Make SessionMemory delegate to FileDataLayer
**Status**: TODO
**Priority**: Medium
**Description**: Refactor `SessionMemory` to use `FileDataLayer` internally instead of managing YAML directly.

**Changes**:
- `SessionMemory.__init__` creates/gets `FileDataLayer` instance
- `add_message()` calls `FileDataLayer.create_step()`
- `get_messages()` calls `FileDataLayer.get_thread()` or reads YAML directly
- Remove duplicate `_save()` / `_load_if_exists()` logic

**Trade-off**: We keep `SessionMemory` as a convenient app-level API, but it delegates to the storage layer.

### 3.2 Keep SessionMemory public API stable
**Status**: TODO
**Priority**: Medium
**Description**: Ensure the `SessionMemory` API doesn't change for existing consumers.

**Methods to preserve**:
- `add_message(role, content)`
- `add_fact(fact)` / `add_facts(facts)`
- `get_messages()`
- `get_facts()`
- `get_context_summary()`
- `clear()`
- `session_id` property

---

## Phase 4: Integration Cleanup

### 4.1 Update chainlit_app_v2.py
**Status**: TODO
**Priority**: Medium
**Description**: Simplify the Chainlit integration to use the unified APIs.

**Changes**:
- Remove redundant `memory.add_message()` calls (let `FileDataLayer.create_step()` handle it)
- Or keep explicit `memory.add_message()` and disable `create_step()` callback
- Ensure `on_chat_resume` properly loads session from unified storage

### 4.2 Clean up unused imports/files
**Status**: TODO
**Priority**: Low
**Description**: Remove temporary files and unused code after refactoring.

- Delete old `_threads_index.yaml` files after migration
- Remove duplicate YAML handling code
- Clean up any dead code paths

---

## Phase 5: Testing

### 5.1 Fix test_chainlit_app_v2_imports
**Status**: TODO
**Priority**: High
**Description**: Ensure the import test passes after adding abstract methods.

### 5.2 Add memory module tests
**Status**: TODO
**Priority**: Medium
**Description**: Create comprehensive tests for the memory module.

**Test scenarios**:
- [ ] SessionMemory round-trip (add/get messages)
- [ ] SessionMemory round-trip (add/get facts)
- [ ] FileDataLayer thread CRUD operations
- [ ] FileDataLayer step creation
- [ ] Thread listing and retrieval
- [ ] Chat resume flow
- [ ] Multiple threads per user

### 5.3 Migration test
**Status**: TODO
**Priority**: Low
**Description**: Verify old `_threads_index.yaml` can be migrated to new format.

---

## Deferred (Backlog)

- [ ] LLM-based fact extraction
- [ ] Fact deduplication and updates
- [ ] User tier (multiple threads per user)
- [ ] Alternative UI backbes (e.g., custom web UI)
- [ ] Search across sessions
- [ ] Session archiving/compression
