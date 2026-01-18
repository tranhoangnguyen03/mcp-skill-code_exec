# Skill-Based Workflow Agent (Chainlit UI)

This UI runs a skill-based automation agent with a human-in-the-loop approval gate.

## What happens on each message

1. The agent proposes a plan (`chat`, `execute_skill`, or `custom_script`) and shows it in the UI.
2. The UI pauses and asks you to choose:
   - Approve Plan: proceed to code generation and execution
   - Re-plan: provide feedback and regenerate the plan
   - Cancel Request: stop the workflow
3. If approved, the UI shows code generation, execution logs, and a final response.

## Run

```bash
chainlit run chainlit_app_v2.py
```
