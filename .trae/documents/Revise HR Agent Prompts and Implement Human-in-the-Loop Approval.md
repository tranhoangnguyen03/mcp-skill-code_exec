# Proposed Implementation Plan

## Problem 1: Revise Agent Prompts
I will revise the prompt files in [prompts/](file:///Users/nguyen.tran/Documents/My%20Remote%20Vault/mcp-skill-code_exec/agent_workspace/prompts) to ensure they are more conservative, follow the "intent-first" principle, and avoid over-engineering.

### 1. Revise [plan.txt](file:///Users/nguyen.tran/Documents/My%20Remote%20Vault/mcp-skill-code_exec/agent_workspace/prompts/plan.txt)
- **Strict Intent Matching**: Add explicit instructions to only use `execute_skill` if the user's intent fully aligns with the skill's purpose.
- **Anti-Over-engineering**: Warn the model against adding unnecessary steps (like role changes or Jira tickets) when the user only asks for a simple notification.
- **Progressive Disclosure Awareness**: Mention that the plan will be reviewed by a human, encouraging clear and concise step descriptions.
- **Action Priority**: Prefer `custom_script` for simple tasks that don't fit a complex pre-defined workflow.

### 2. Refine [codegen.txt](file:///Users/nguyen.tran/Documents/My%20Remote%20Vault/mcp-skill-code_exec/agent_workspace/prompts/codegen.txt) and [custom_skill.txt](file:///Users/nguyen.tran/Documents/My%20Remote%20Vault/mcp-skill-code_exec/agent_workspace/prompts/custom_skill.txt)
- Ensure generated code strictly follows the approved plan steps.
- Improve logging and progress reporting in the generated scripts to align with the "progressive disclosure" of execution status.

## Problem 2: Human-in-the-Loop (HITL) Integration
I will modify [chainlit_app_v2.py](file:///Users/nguyen.tran/Documents/My%20Remote%20Vault/mcp-skill-code_exec/chainlit_app_v2.py) to introduce a manual gatekeeping step after the planning phase.

### 1. Implement Approval Gate
- After the `agent.plan` step, the agent will send an `AskActionMessage` to the user.
- **Buttons**:
  - **Approve Plan**: Proceeds to code generation and execution.
  - **Re-plan**: Allows the user to provide feedback. The agent will then generate a new plan based on the original request plus the feedback.
  - **Cancel Request**: Terminate the current workflow.

### 2. Logic Flow Update
- Wrap the planning phase in a loop to handle the "Re-plan" scenario.
- Ensure the UI clearly shows the plan before asking for approval.

## Verification
- I will run the specific scenario mentioned by the user ("Tell Mr.Davis to update his profile") to verify that the planner now chooses a simple notification plan instead of a complex role change.
- I will manually test the Chainlit UI to ensure the buttons work as expected and gatekeep the process.

Does this plan look correct to you?