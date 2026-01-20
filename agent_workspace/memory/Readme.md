# Session Memory

Simple file-based conversation memory using YAML files. Stores conversation turns, working step artifacts, and extracted key facts.

## Concept: Messages vs Working Steps

The memory system distinguishes between two types of content:

| Type | Storage | Purpose | Display |
|------|---------|---------|---------|
| **Messages** | `messages[]` | Conversation turns (user/assistant dialogue) | `cl.Message()` |
| **Working Steps** | `steps[]` | Intermediate artifacts (plan, codegen, execute) | `cl.Step()` |

This separation prevents duplication and provides clear organization:

- **Messages**: Only store actual conversation turns. Use `add_response()` for a single write path.
- **Working Steps**: Store intermediate artifacts useful for debugging and session resumption.

## Usage

```python
from agent_workspace.memory import SessionMemory, StepType, StepCategory, extract_facts_simple

# Create or resume a session
mem = SessionMemory("my_session_id")

# Add conversation turns (single write path - no duplication)
mem.add_response("user", "Submit leave for John Smith for next Monday")
mem.add_response("assistant", "Done! Leave request LR-123 submitted.")

# Add working step artifacts
mem.add_working_step(
    step_type=StepType.PLAN,
    content='{"action": "execute_skill", "intent": "Submit leave request"}',
    category=StepCategory.WORKING,
    metadata={"intent": "Submit leave request", "action": "execute_skill"},
)

mem.add_working_step(
    step_type=StepType.CODEGEN,
    content="def submit_leave(employee_id, date): ...",
    category=StepCategory.WORKING,
    metadata={"attempt": 1},
)

mem.add_working_step(
    step_type=StepType.EXECUTE,
    content="stdout: Leave request submitted\nstderr:",
    category=StepCategory.WORKING,
    metadata={"exit_code": 0, "attempt": 1},
)

# Extract and store facts automatically
facts = extract_facts_simple(user_msg, assistant_msg)
mem.add_facts(facts)

# Get formatted context for prompts
context = mem.get_context_summary(max_messages=10)

# Retrieve data
messages = mem.get_messages()      # list[Message]
working_steps = mem.get_working_steps()  # list[WorkingStep]
facts = mem.get_facts()            # list[KeyFact]

# Clear session (deletes file)
mem.clear()
```

## API

### SessionMemory

| Method | Description |
|--------|-------------|
| `add_response(role, content)` | Add a user or assistant message (conversation turn) |
| `add_message(role, content)` | Alias for `add_response()` (backward compatibility) |
| `add_working_step(step_type, content, category, metadata)` | Add a working step artifact |
| `add_fact(fact)` | Add a single key fact |
| `add_facts(facts)` | Add multiple facts at once |
| `get_messages()` | Return all messages |
| `get_working_steps()` | Return all working step artifacts |
| `get_facts()` | Return all key facts |
| `get_context_summary(max_messages=10)` | Format for prompt injection |
| `clear()` | Delete session and file |

### StepType Enum

```python
class StepType(str, Enum):
    PLAN = "plan"      # Plan proposal
    CODEGEN = "codegen"  # Generated code
    EXECUTE = "execute"  # Execution output
    RESPONSE = "response"  # Final response
```

### StepCategory Enum

```python
class StepCategory(str, Enum):
    WORKING = "working"   # Plan, codegen, execute - display as Chainlit steps
    RESPONSE = "response" # Chat/final response - display as Chainlit messages
```

### Data Classes

```python
@dataclass(frozen=True)
class Message:
    role: str       # "user" or "assistant"
    content: str
    timestamp: str  # ISO format

@dataclass(frozen=True)
class WorkingStep:
    step_type: str         # "plan", "codegen", "execute"
    category: StepCategory # WORKING or RESPONSE
    content: str           # JSON, code, output, etc.
    metadata: dict | None  # Extra data (exit_code, attempt_num, etc.)
    timestamp: str         # ISO format

@dataclass(frozen=True)
class KeyFact:
    fact: str
    source_turn: int  # which turn this came from
    timestamp: str
```

### Fact Extractor

```python
extract_facts_simple(user_message, assistant_response) -> list[str]
```

Extracts facts using regex patterns:
- Names (e.g., "John Smith")
- Dates (e.g., "2024-02-01", "1/20/2024")
- References (e.g., "LR-123", "#456")
- Completed actions (e.g., "submitted", "created")

## Storage Format

Sessions are stored as YAML in `sessions/`:

```yaml
session_id: my_session_id
created_at: '2024-01-20T10:30:00'
updated_at: '2024-01-20T10:31:00'
messages:
  - role: user
    content: Submit leave for John Smith for next Monday
    timestamp: '2024-01-20T10:30:00'
  - role: assistant
    content: Done! Leave request LR-123 submitted.
    timestamp: '2024-01-20T10:30:30'
steps:
  - step_type: plan
    category: working
    content: '{"action": "execute_skill", "intent": "Submit leave request"}'
    metadata:
      intent: Submit leave request
      action: execute_skill
    timestamp: '2024-01-20T10:30:01'
  - step_type: codegen
    category: working
    content: 'def submit_leave(employee_id, date): ...'
    metadata:
      attempt: 1
    timestamp: '2024-01-20T10:30:15'
  - step_type: execute
    category: working
    content: 'stdout: Leave request submitted\nstderr:'
    metadata:
      exit_code: 0
      attempt: 1
    timestamp: '2024-01-20T10:31:00'
facts:
  - fact: 'Person mentioned: John Smith'
    source_turn: 1
    timestamp: '2024-01-20T10:30:05'
```

## File Structure

```
memory/
├── __init__.py          # Public exports
├── session_memory.py    # SessionMemory, Message, WorkingStep, KeyFact, enums
├── fact_extractor.py    # extract_facts_simple()
├── sessions/            # Persisted session files (*.yaml)
└── Readme.md
```

## Chainlit Integration

Each new conversation in Chainlit creates a new session. Use the **New Conversation** button to start fresh with a new session ID.

```python
# In chainlit_app_v2.py
from agent_workspace.memory import SessionMemory, StepType, StepCategory

@cl.on_chat_start
async def on_chat_start():
    memory = SessionMemory(session_id=thread_id)
    cl.user_session.set("memory", memory)

@cl.on_message
async def on_message(message: cl.Message):
    memory = cl.user_session.get("memory")

    # Store user message (single write)
    memory.add_response("user", message.content)

    # ... agent processing ...

    # Store plan as working step
    memory.add_working_step(
        step_type=StepType.PLAN,
        content=plan_json,
        category=StepCategory.WORKING,
        metadata={"intent": plan.intent},
    )

    # Store assistant response (single write - cl.Message for UI only)
    memory.add_response("assistant", final)
    await cl.Message(content=final).send()
```
