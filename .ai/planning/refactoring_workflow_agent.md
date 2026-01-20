# Change Proposal: Refactoring WorkflowAgent for Clarity and SOC

## Overview
The current [agent.py](file:///Users/nguyen.tran/Documents/My%20Remote%20Vault/mcp-skill-code_exec/agent_workspace/workflow_agent/agent.py) implementation follows a "God Class" pattern, where the `WorkflowAgent` class handles planning, skill discovery, code generation orchestration, execution retries, and result summarization. This proposal suggests decomposing this class into specialized components to improve maintainability, testability, and separation of concerns.

## Proposed Architecture

### 1. `Planner` (New Component)
**Responsibility**: Decoupling the intent analysis from the orchestration.
- **Input**: User message, conversation history, available skills.
- **Output**: A structured `Plan` object.
- **Logic**: Encapsulates `workflow_plan`, `workflow_plan_review`, and skill matching/normalization logic currently in `agent.py`.

### 2. `WorkflowExecutor` (New Component)
**Responsibility**: Managing the iterative lifecycle of code generation and execution.
- **Input**: User intent, selected skill/manual, tool contracts.
- **Output**: `ExecutionResult`.
- **Logic**: Handles the `generate_and_execute_with_retries` loop, error feedback for codegen, and environment/PYTHONPATH setup for the `PythonCodeExecutor`.

### 3. Enhanced `SkillRegistry` & `Skill` Class
**Responsibility**: Moving metadata parsing out of the agent.
- **Change**: [skill_registry.py](file:///Users/nguyen.tran/Documents/My%20Remote%20Vault/mcp-skill-code_exec/agent_workspace/workflow_agent/skill_registry.py) should return rich `Skill` objects.
- **New Methods**: `Skill.get_logic_flow_steps()` and `Skill.group` should be properties of the object, removing regex-based parsing from the agent's main loop.

### 4. Slim `WorkflowAgent`
**Responsibility**: Pure orchestration.
- **New Flow**:
    1. Call `Planner.get_plan()`
    2. (If applicable) Call `WorkflowExecutor.execute()`
    3. Call `workflow_respond` via `baml_bridge`.

## Implementation Plan

1.  **Phase 1: Component Extraction**
    - Create `agent_workspace/workflow_agent/sub_agents/planner.py`.
    - Create `agent_workspace/workflow_agent/sub_agents/executor.py`.
2.  **Phase 2: Registry Enhancement**
    - Refactor `SkillRegistry` to use a proper `Skill` dataclass with helper methods for parsing Markdown.
3.  **Phase 3: Orchestration Update**
    - Update `WorkflowAgent` to use these new components.
    - Maintain backward compatibility for `main.py` and `chainlit_app_v2.py`.

## Testing & Validation Plan

To ensure the refactoring maintains existing functionality and preserves backward compatibility, the following testing strategy will be implemented:

### 1. Regression Testing
- **Existing Tests**: Run all tests in `tests/test_agent_flow_v2.py` before and after refactoring. These tests verify the end-to-end flow from planning to execution.
- **Baseline Verification**: Capture the `AgentResult` (plan, code, response) for a set of standard queries (e.g., "Onboard today's new hires") before refactoring to use as a "gold standard" for comparison.

### 2. Unit Testing New Components
- **Planner Tests**: Create `tests/test_planner.py` to verify:
    - Intent classification (chat vs skill vs custom).
    - Skill matching and name normalization.
    - Logic flow step extraction.
- **WorkflowExecutor Tests**: Create `tests/test_workflow_executor.py` using mocks for the LLM `codegen` call to verify:
    - Retry logic works on execution failure.
    - Error messages are correctly passed back to the next codegen attempt.
    - Correct `PYTHONPATH` is constructed for different skill groups.

### 3. Backward Compatibility Verification
- **main.py**: Ensure the CLI entry point `python agent_workspace/main.py` continues to function without any changes to its import or calling logic.
- **Chainlit UI**: 
    - Verify `chainlit_app_v2.py` correctly handles the refactored `WorkflowAgent`.
    - Validate that session memory persistence (YAML files) remains consistent and that previous sessions can still be resumed.
- **BAML Integration**: Ensure the structured output from BAML remains correctly mapped to the new `Plan` and `ExecutionResult` types.

## Benefits
- **Testability**: The `Planner` can be unit-tested with various prompts without running code. The `WorkflowExecutor` can be tested with mock codegen results.
- **Clarity**: The "Logic Flow" extraction and "Skill Group" inference are no longer hidden as private helper functions in a 400-line file.
- **SOC**: `agent.py` becomes a high-level description of the workflow rather than an implementation of every step.
