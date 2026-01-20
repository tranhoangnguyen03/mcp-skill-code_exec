# Change Proposal: Working Steps vs Response Steps Distinction

**Date:** 2026-01-20
**Author:** Claude Code
**Status:** Pending Implementation

## Problem Statement

Currently, the codebase lacks a clear distinction between:
1. **Working steps** (plan, codegen, execute) - intermediate artifacts
2. **Response steps** (chat, final response) - conversation turns

This causes two issues:
1. **Duplication**: Assistant responses are written twice to storage - once via `SessionMemory.add_message()` and again via `cl.Message().send()` → same content appears twice in history
2. **No persistent working step history**: Working artifacts (plan JSON, generated code, execution output) are only visible during execution via temporary Chainlit UI steps

## Proposed Solution

### 1. New Memory Schema

Add a separate `steps[]` array for working steps while keeping `messages[]` for conversation turns:

```yaml
session_id: str
created_at: str
updated_at: str
messages: []    # Only conversation turns (user/assistant responses) - NO DUPLICATION
facts: []       # Extracted key facts
steps: []       # Working step artifacts (plan, codegen, execute outputs)
```

### 2. New Dataclasses (session_memory.py)

```python
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

class StepType(Enum):
    PLAN = "plan"
    CODEGEN = "codegen"
    EXECUTE = "execute"
    RESPONSE = "response"

class StepCategory(Enum):
    WORKING = "working"   # Plan, codegen, execute - display as Chainlit steps
    RESPONSE = "response" # Chat/final response - display as Chainlit messages

@dataclass(frozen=True)
class WorkingStep:
    """Immutable record of a working step artifact."""
    step_type: str         # "plan", "codegen", "execute"
    category: StepCategory # WORKING or RESPONSE
    content: str           # JSON, code, output, etc.
    metadata: dict | None  # Extra data (exit_code, attempt_num, etc.)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
```

### 3. Updated SessionMemory API

```python
class SessionMemory:
    def add_working_step(
        self,
        step_type: str,
        content: str,
        category: StepCategory,
        metadata: dict | None = None
    ) -> None:
        """Add a working step artifact (plan, codegen code, execution output)."""
        # Stores to steps[] array - persistent across sessions

    def add_response(self, role: str, content: str) -> None:
        """Add a conversation turn (user input or assistant response).

        This is the ONLY method for storing responses - eliminates duplication
        because cl.Message().send() now only handles UI display, not storage.
        """
        # Stores to messages[] array

    def get_working_steps(self) -> list[WorkingStep]:
        """Return all working step artifacts for this session."""
```

### 4. Chainlit App Updates (chainlit_app_v2.py)

```python
@cl.on_message
async def on_message(message: cl.Message):
    agent = cl.user_session.get("agent")
    memory = cl.user_session.get("memory")
    user_input = message.content

    # Store user message (single write - no duplication)
    memory.add_response("user", user_input)

    # 1. PLAN PHASE
    plan, plan_json, skill = await asyncio.to_thread(agent.plan, user_message=user_input)

    # Persist plan as working step
    memory.add_working_step(
        step_type="plan",
        content=plan_json,
        category=StepCategory.WORKING,
        metadata={"intent": plan.intent, "action": plan.action}
    )

    async with cl.Step(name="Plan") as step:
        step.output = f"```json\n{plan_json.strip()}\n```"

    # HITL gate (unchanged)...

    # 2. CODEGEN PHASE
    skill_md = await asyncio.to_thread(agent.get_skill_md, plan=plan, selected_skill=skill)

    for attempt in range(1, agent.max_attempts + 1):
        code = await asyncio.to_thread(
            agent.codegen,
            user_message=user_input,
            plan_json=plan_json,
            skill_md=skill_md,
            attempt=attempt,
            previous_error=last_error,
            previous_code=last_code,
        )

        # Persist generated code
        memory.add_working_step(
            step_type="codegen",
            content=code,
            category=StepCategory.WORKING,
            metadata={"attempt": attempt}
        )

        async with cl.Step(name=f"Codegen (attempt {attempt})") as step:
            step.output = f"```python\n{code.strip()}\n```"

        # 3. EXECUTE PHASE
        exec_result = await asyncio.to_thread(agent.execute, code=code)

        # Persist execution result
        memory.add_working_step(
            step_type="execute",
            content=f"stdout: {exec_result.stdout}\nstderr: {exec_result.stderr}",
            category=StepCategory.WORKING,
            metadata={"exit_code": exec_result.exit_code, "attempt": attempt}
        )

        async with cl.Step(name=f"Execute (attempt {attempt})") as step:
            # Build output...

    # 4. RESPONSE PHASE
    final = await asyncio.to_thread(
        agent.respond,
        user_message=user_input,
        plan_json=plan_json,
        executed_code=last_code,
        exec_result=exec_result,
        attempts=attempts_used,
    )

    # Store response (single write path)
    memory.add_response("assistant", final)

    # cl.Message for UI display only - no storage duplication
    await cl.Message(content=final).send()
```

### 5. FileDataLayer Updates (chainlit_data_layer.py)

- Update `_get_thread_data()` to initialize `steps[]` array
- Update `_thread_data_to_dict()` to include working steps in ThreadDict
- Simplify `create_step()` to only handle actual Chainlit step events

## Files to Modify

| File | Changes |
|------|---------|
| `agent_workspace/memory/session_memory.py` | Add `StepType`, `StepCategory` enums, `WorkingStep` dataclass, `add_working_step()`, `get_working_steps()` methods |
| `agent_workspace/memory/chainlit_data_layer.py` | Update schema initialization, thread serialization |
| `chainlit_app_v2.py` | Use `add_working_step()` for artifacts, `add_response()` for turns, remove duplicate writes |

## Documentation Updates

| File | Changes |
|------|---------|
| `agent_workspace/memory/Readme.md` | Document new `add_working_step()` API and working step concept |
| `chainlit.md` | Update workflow description to reflect new step categorization |
| `Readme.md` | Update session memory section |

## Benefits

1. **No duplication**: Single `add_response()` path for conversation turns
2. **Persistent working history**: Plan, code, execution output survive session resume
3. **Clear separation of concerns**: Working steps vs conversation turns
4. **Better Chainlit UX**: Working steps as `cl.Step()`, responses as `cl.Message()`
5. **Cleaner YAML structure**: Organized by purpose (`messages[]` vs `steps[]`)
