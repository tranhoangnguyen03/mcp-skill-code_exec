# Memory Module Redesign (2026-01-20)

## Context

The memory module was originally designed as a standalone session persistence layer for a CLI/agent workflow system. It provided:

- `SessionMemory`: YAML-based storage for conversation messages and extracted key facts
- `fact_extractor.py`: Simple heuristic-based fact extraction from conversation turns

When integrating with Chainlit, a new layer was added:

- `FileDataLayer`: Implements Chainlit's `BaseDataLayer` protocol for chat history UI

### Current Problems

1. **Missing abstract methods**: `FileDataLayer` doesn't implement `close()` and `get_favorite_steps()`, causing import failures

2. **Dual storage / duplication**: Messages are stored in two places:
   - `{session_id}.yaml` via `SessionMemory.add_message()`
   - `_threads_index.yaml` via `FileDataLayer.update_thread()`
   - Plus individual session files for thread metadata

3. **No unified source of truth**: The two systems can diverge since they write independently

4. **Tight coupling to session concept**: `SessionMemory` assumes a single session per thread, but Chainlit's model allows multiple threads per user

5. **Flexibility concern**: The original design was UI-agnostic, but the current integration makes it harder to swap UIs later

## Design Goals

1. **Thread = Session**: Unify the concept. A thread in Chainlit IS a session in our memory model.

2. **Persistence layer abstraction**: Keep the storage format (YAML) but decouple it from the UI layer.

3. **Single write path**: Messages should be written once, to one location.

4. **Preserve flexibility**: Allow UI-agnostic access via `SessionMemory` while supporting Chainlit's data layer.

## Proposed Architecture

```
                    ┌─────────────────────────────────────┐
                    │     Application Layer               │
                    │  (chainlit_app_v2.py, CLI, etc.)    │
                    └─────────────────────────────────────┘
                                    │
                                    ▼
┌───────────────────────────────────────────────────────────────────────┐
│                         Public APIs                                   │
│  ┌──────────────────────┐  ┌────────────────────────────────────────┐ │
│  │   SessionMemory      │  │        FileDataLayer                   │ │
│  │  (convenience wrapper│  │   (Chainlit BaseDataLayer impl)        │ │
│  │   for app code)      │  │                                        │ │
│  └──────────────────────┘  └────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌───────────────────────────────────────────────────────────────────────┐
│                      Unified Storage Layer                            │
│                                                                       │
│   /memory/                                                            │
│   ├── sessions/              # All thread/session data                │
│   │   ├── {thread_id}.yaml   # Contains:                             │
│   │   │                      #   - session_id                        │
│   │   │                      #   - created_at, updated_at            │
│   │   │                      #   - user_id, userIdentifier           │
│   │   │                      #   - name, metadata, tags              │
│   │   │                      #   - messages[] (role, content, ts)    │
│   │   │                      #   - facts[] (fact, source_turn, ts)   │
│   │   │                                                         │
│   │   └── _users.yaml         # User registry (shared, not per-thread)
│   │                                                             │
│   └── (no separate threads index needed)                          │
└───────────────────────────────────────────────────────────────────────┘
```

## Key Changes

### 1. Unified YAML Schema

Each thread/session file will contain everything:

```yaml
session_id: abc123
created_at: "2026-01-20T10:00:00Z"
updated_at: "2026-01-20T10:30:00Z"
user_id: "user_123"
user_identifier: "alice@company.com"
name: "Onboarding new hires"
metadata: {}
tags: []
messages:
  - role: user
    content: "Onboard today's new hires"
    timestamp: "2026-01-20T10:00:00Z"
  - role: assistant
    content: "Done! Created accounts for John, Sarah, and Mike."
    timestamp: "2026-01-20T10:05:00Z"
facts:
  - fact: "Person mentioned: John Smith"
    source_turn: 0
    timestamp: "2026-01-20T10:00:00Z"
  - fact: "Action: Created accounts for John, Sarah, and Mike"
    source_turn: 1
    timestamp: "2026-01-20T10:05:00Z"
```

### 2. Refactored SessionMemory

- Reads/writes to `{thread_id}.yaml` using the unified schema
- Acts as a convenience wrapper for application code
- Internally uses `FileDataLayer` for persistence

### 3. Refactored FileDataLayer

- Implements all abstract methods (`close`, `get_favorite_steps`)
- Manages the single YAML file per thread
- Handles user storage in `_users.yaml`
- `get_thread()` reads from the thread's YAML file, including steps/messages

### 4. No More `_threads_index.yaml`

Since each thread is self-contained in its own YAML file, we don't need a separate index. Thread listing can be done by scanning the sessions directory.

## Migration Path

1. Add missing abstract methods to `FileDataLayer` (quick fix)
2. Refactor `FileDataLayer` to use unified thread YAML files
3. Update `SessionMemory` to delegate to `FileDataLayer`
4. Update `chainlit_app_v2.py` to use the new APIs
5. Remove old `_threads_index.yaml` after migration

## Future Considerations (Deferred)

- **User tier**: Group multiple threads under a user
- **Different UI backends**: The unified storage layer should work with any UI
- **Fact extraction improvements**: LLM-based extraction, fact updates/deduplication
