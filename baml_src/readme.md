# BAML Source Files

This directory contains the BAML prompt definitions that generate the LLM code and response functions for the workflow agent.

## What is BAML?

[BAML](https://github.com/BinderAI/baml) (Binder AI Language) is a prompt engineering tool that:
- Lets you write prompts in a dedicated DSL (Domain Specific Language)
- Generates type-safe Python client code via `baml generate`
- Separates prompt logic from application code

## Project Structure

```
baml_src/
├── readme.md          # This file
├── clients.baml       # LLM client configurations (OpenRouter, etc.)
├── generators.baml    # Generator settings (temperature, model, etc.)
├── types.baml         # Shared data structures (Plan, ChatResponse)
├── planner.baml       # Planning and review functions
├── executor.baml      # Code generation and result summary functions
└── chat.baml          # Conversational chat functions
```

### Key Files

| File | Purpose |
|------|---------|
| `types.baml` | Defines shared classes used across all BAML functions |
| `planner.baml` | Contains `WorkflowPlan` and `WorkflowPlanReview` |
| `executor.baml` | Contains `WorkflowCodegen` and `WorkflowRespond` |
| `chat.baml` | Contains `WorkflowChat` |
| `clients.baml` | Defines LLM clients (e.g., `OpenRouterChat`) |
| `generators.baml` | Sets generation parameters like temperature, max tokens |

## Workflow Functions

The agent uses several main BAML functions distributed across files:

| Function | Input | Output | File | When Used |
|----------|-------|--------|------|-----------|
| `WorkflowPlan` | user_message, skills_readme, ..., conversation_history | `Plan` | `planner.baml` | First step: classify request as chat/skill/custom |
| `WorkflowPlanReview` | user_message, proposed_plan, ..., conversation_history | `Plan` | `planner.baml` | Review/Refine plan based on context or multi-turn rules |
| `WorkflowCodegen` | user_message, plan_json, skill_md, ..., conversation_history | string | `executor.baml` | Execute: generate Python script to run |
| `WorkflowChat` | user_message, skills_readme, ..., conversation_history | `ChatResponse` | `chat.baml` | When action="chat": conversational response |
| `WorkflowRespond` | user_message, plan_json, ..., conversation_history | string | `executor.baml` | After execution: summarize results |

`conversation_history` is a compact plain-text transcript of the last N past messages (most recent last).

## The Plan Schema

All planning functions return a `Plan` object (defined in `types.baml`):

```baml
class Plan {
  action string           // "chat" | "execute_skill" | "custom_script"
  skill_group string?     // HR-scopes, Recruitment-scopes, etc.
  skill_name string?      // Specific skill (e.g., "onboard_new_hire")
  intent string           // Human-readable description
  steps string[]          // High-level steps (for execution)
  
  // Multi-turn support fields
  requires_lookahead bool // Set to true when the request needs external data lookup
  checkpoints string[]   // Steps that produce facts for downstream use
}
```

## Making Changes

### 1. Edit the BAML source

Modify prompts in the relevant `.baml` file. Key sections:
- `prompt #"..."#` - The actual prompt text
- `client OpenRouterChat` - Which LLM to use
- Input variables like `{{ user_message }}` - Dynamic content

### 2. Regenerate the client

```bash
cd /path/to/repo
baml generate
```

This updates `baml_client/` with new Python functions.

### 3. Verify

```bash
pytest tests/test_multi_turn_workflows.py -v
```

### Example: Adding a New Prompt

1. Add to a new or existing `.baml` file:
```baml
function MyNewFunction(input: string) -> string {
  client OpenRouterChat
  prompt #"
  Your prompt here: {{ input }}
  "#
}
```

2. Run `baml generate`

3. Call from Python (via bridge):
```python
# In baml_bridge.py
async def workflow_my_new_function(input: str) -> str:
    return await b.MyNewFunction(input=input)
```

## Prompt Engineering Tips

### Accessing Variables
- `{{ variable }}` - Inserts variable value
- `{% for item in list %}` ... `{% endfor %}` - Loops
- `{% if condition %}` ... `{% endif %}` - Conditionals

### Output Format
Use `{{ ctx.output_format }}` at the end of prompts to inject the required JSON schema.

### Best Practices
1. Keep prompts concise - LLMs obey explicit constraints
2. Use "CRITICAL:" or "IMPORTANT:" prefixes for critical rules
3. After changes, run `baml generate` before testing

## Related Files

- [agent.py](../agent_workspace/workflow_agent/agent.py) - Agent that calls BAML functions
- [baml_bridge.py](../agent_workspace/workflow_agent/baml_bridge.py) - Wrapper functions
- [baml_client/](../baml_client/) - Generated Python client (DO NOT EDIT)
