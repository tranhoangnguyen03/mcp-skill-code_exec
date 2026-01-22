"""WorkflowAgent - Main orchestration class.

This module provides the WorkflowAgent class that orchestrates the complete
workflow from planning to code execution and response generation.

For a more modular architecture, consider using the Planner and WorkflowExecutor
components directly from the sub_agents package.
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from .baml_bridge import workflow_chat
from .code_executor import PythonCodeExecutor
from .skill_registry import SkillRegistry
from .sub_agents.executor import ExecutionResult, WorkflowExecutor, MultiTurnWorkflowExecutor
from .sub_agents.planner import Plan, Planner
from .types import AgentResult, WorkflowExecuteResult, WorkflowState


def _env_bool(name: str, *, default: bool = False) -> bool:
    """Parse environment variable as boolean."""
    value = os.getenv(name)
    if value is None:
        return default
    cleaned = value.strip().lower()
    if not cleaned:
        return default
    if cleaned in {"1", "true", "yes", "y", "on"}:
        return True
    if cleaned in {"0", "false", "no", "n", "off"}:
        return False
    return default


class WorkflowAgent:
    """Main orchestration class for workflow execution.

    The WorkflowAgent coordinates the complete workflow:
    1. Planning - Analyze user intent and create a plan
    2. Code Generation - Generate Python code based on the plan
    3. Execution - Execute the generated code
    4. Response - Generate a final response based on execution results

    This class maintains backward compatibility with the existing API.
    For more granular control, use the Planner and WorkflowExecutor
    components directly from the sub_agents package.
    """

    def __init__(self, max_attempts: int = 3, *, enable_workflow_plan_review: bool | None = None):
        self.max_attempts = max(1, int(max_attempts))
        self.workspace_dir = Path(__file__).resolve().parents[1]
        self.skills_v2_dir = self.workspace_dir / "skills_v2"
        self.skills = SkillRegistry(self.skills_v2_dir)

        self.default_tools_root = self.workspace_dir / "tools"
        self.default_docs_dir = self.skills_v2_dir / "HR-scopes" / "tools" / "mcp_docs"
        self.executor = PythonCodeExecutor(self.workspace_dir, extra_pythonpaths=[self.default_tools_root])
        self.custom_skill_md_path = self.skills_v2_dir / "custom_skill.md"

        # Initialize sub-agents
        self._planner = Planner(self.skills)
        self._workflow_executor = WorkflowExecutor(
            executor=self.executor,
            skills_v2_dir=self.skills_v2_dir,
            default_tools_root=self.default_tools_root,
            default_docs_dir=self.default_docs_dir,
            max_attempts=self.max_attempts,
        )
        # Initialize multi-turn executor wrapper
        self._multi_turn_executor = MultiTurnWorkflowExecutor(self._workflow_executor)

        if enable_workflow_plan_review is None:
            enable_workflow_plan_review = _env_bool("enable_workflow_plan_review", default=False)
        self.enable_workflow_plan_review = bool(enable_workflow_plan_review)

    async def run(self, user_message: str, *, conversation_history: str = "") -> AgentResult:
        """Run the complete workflow.

        This is the main entry point that orchestrates the full workflow
        from planning to response generation.

        Args:
            user_message: The user's request
            conversation_history: Previous conversation context

        Returns:
            AgentResult containing the final response and execution details
        """
        # Phase 1: Planning
        planning_result = self._planner.plan(
            user_message=user_message,
            conversation_history=conversation_history,
            enable_review=self.enable_workflow_plan_review,
        )
        plan = planning_result.plan
        plan_json = planning_result.plan_json
        selected_skill = planning_result.selected_skill

        # Phase 2: Chat or Execute
        if plan.action == "chat":
            final_response = self.chat(user_message=user_message, conversation_history=conversation_history)
            return AgentResult(final_response=final_response.strip(), plan_json=plan_json)

        skill_md = self.get_skill_md(plan=plan, selected_skill=selected_skill)

        # Phase 3: Execute with retries (Multi-turn aware)
        execute_result = self.execute_multi_turn_workflow(
            user_message=user_message,
            plan_json=plan_json,
            skill_md=skill_md,
            conversation_history=conversation_history,
        )

        workflow_state = None
        if execute_result.needs_continuation:
            workflow_state = self.create_workflow_state(
                session_id=str(uuid.uuid4()),
                plan_json=plan_json,
                collected_facts=execute_result.continuation_facts,
            )
            max_turns = 2
            try:
                plan_data = json.loads(plan_json)
                checkpoints = plan_data.get("checkpoints") or []
                if isinstance(checkpoints, list):
                    max_turns = max(2, len(checkpoints) + 1)
            except Exception:
                max_turns = 2

            turns = 1
            while execute_result.needs_continuation and turns < max_turns:
                workflow_state = self.update_workflow_state(
                    workflow_state,
                    next_step=workflow_state.get("current_step", 0) + 1,
                    facts=execute_result.continuation_facts,
                )
                execute_result = self.execute_multi_turn_workflow(
                    user_message=user_message,
                    plan_json=plan_json,
                    skill_md=skill_md,
                    conversation_history=conversation_history,
                    workflow_state=workflow_state,
                )
                turns += 1

            if not execute_result.needs_continuation:
                workflow_state = None

        # Phase 4: Generate response
        final_response = self._workflow_executor.respond(
            user_message=user_message,
            plan_json=plan_json,
            executed_code=execute_result.code,
            exec_result=execute_result.exec_result,
            attempts=execute_result.attempts_used,
            conversation_history=conversation_history,
        )

        return AgentResult(
            final_response=final_response.strip(),
            plan_json=plan_json,
            generated_code=execute_result.code,
            exec_stdout=execute_result.exec_result.stdout,
            exec_stderr=execute_result.exec_result.stderr,
            attempts=execute_result.attempts_used,
            workflow_state=workflow_state,
        )

    def plan(self, user_message: str, *, conversation_history: str = ""):
        """Create a plan from user message.

        This method delegates to the Planner component and returns
        a tuple of (Plan, plan_json, selected_skill).

        Args:
            user_message: The user's request
            conversation_history: Previous conversation context

        Returns:
            Tuple of (Plan, plan_json, selected_skill)
        """
        planning_result = self._planner.plan(
            user_message=user_message,
            conversation_history=conversation_history,
            enable_review=self.enable_workflow_plan_review,
        )
        return planning_result.plan, planning_result.plan_json, planning_result.selected_skill

    def codegen(
        self,
        user_message: str,
        plan_json: str,
        skill_md: str,
        *,
        conversation_history: str = "",
        attempt: int = 1,
        previous_error: str = "",
        previous_code: str = "",
    ) -> str:
        """Generate Python code for the given plan.

        Args:
            user_message: The user's request
            plan_json: JSON string representation of the plan
            skill_md: The skill Markdown content
            conversation_history: Previous conversation context
            attempt: Current attempt number (for retry context)
            previous_error: Error from previous attempt (for retry context)
            previous_code: Code from previous attempt (for retry context)

        Returns:
            Generated Python code as string
        """
        from .sub_agents.executor import _extract_code_block

        docs_registry = self._docs_registry_for_plan(plan_json=plan_json)
        tool_contracts = docs_registry.render_tool_contracts()

        code = workflow_codegen(
            user_message=user_message,
            plan_json=plan_json,
            skill_md=skill_md,
            tool_contracts=tool_contracts,
            attempt=attempt,
            previous_error=previous_error,
            previous_code=previous_code,
            conversation_history=conversation_history,
        )
        extracted = _extract_code_block(code)
        compile(extracted, "<generated>", "exec")
        return extracted

    def execute(self, code: str, *, plan_json: str | None = None) -> ExecutionResult:
        """Execute generated Python code.

        Args:
            code: Python code to execute
            plan_json: Optional JSON string representation of the plan

        Returns:
            ExecutionResult with stdout, stderr, and exit code
        """
        from .sub_agents.executor import ExecutionResult as ExecResult

        tools_root = self._tools_root_for_plan(plan_json=plan_json)
        extra = [tools_root] if tools_root and tools_root != self.default_tools_root else None
        raw_result = self.executor.run(code, extra_pythonpaths=extra)
        return ExecResult(stdout=raw_result.stdout, stderr=raw_result.stderr, exit_code=raw_result.exit_code)

    def respond(
        self,
        user_message: str,
        plan_json: str,
        executed_code: str,
        exec_result: ExecutionResult,
        *,
        conversation_history: str = "",
        attempts: int,
    ) -> str:
        """Generate a final response based on execution results.

        Args:
            user_message: The user's request
            plan_json: JSON string representation of the plan
            executed_code: The code that was executed
            exec_result: The execution result
            conversation_history: Previous conversation context
            attempts: Number of attempts used

        Returns:
            Final response string
        """
        return workflow_respond(
            user_message=user_message,
            plan_json=plan_json,
            executed_code=executed_code,
            exec_stdout=exec_result.stdout,
            exec_stderr=exec_result.stderr,
            exit_code=exec_result.exit_code,
            attempts=attempts,
            conversation_history=conversation_history,
        )

    def chat(self, user_message: str, *, conversation_history: str = "") -> str:
        """Generate a conversational response.

        Args:
            user_message: The user's request
            conversation_history: Previous conversation context

        Returns:
            Response string
        """
        skills_readme = self.skills.read_skills_readme()
        custom_skill_md = self.custom_skill_md_path.read_text(encoding="utf-8")
        return workflow_chat(
            user_message=user_message,
            skills_readme=skills_readme,
            custom_skill_md=custom_skill_md,
            conversation_history=conversation_history,
        )

    def get_skill_md(self, plan: Plan, selected_skill) -> str:
        """Get the skill Markdown content.

        Args:
            plan: The plan object
            selected_skill: The selected skill object

        Returns:
            Skill Markdown content as string
        """
        if plan.action == "execute_skill":
            return selected_skill.content
        return self.custom_skill_md_path.read_text(encoding="utf-8")

    def generate_and_execute_with_retries(
        self, user_message: str, plan_json: str, skill_md: str, *, conversation_history: str = ""
    ):
        """Generate and execute code with retry logic.

        This is a convenience method that wraps the execute phase.
        For more control, use the WorkflowExecutor directly.

        Args:
            user_message: The user's request
            plan_json: JSON string representation of the plan
            skill_md: The skill Markdown content
            conversation_history: Previous conversation context

        Returns:
            Tuple of (code, exec_result, attempts_used)
        """
        execute_result = self._workflow_executor.execute(
            user_message=user_message,
            plan_json=plan_json,
            skill_md=skill_md,
            conversation_history=conversation_history,
        )
        return execute_result.code, execute_result.exec_result, execute_result.attempts_used

    def execute_multi_turn_workflow(
        self,
        user_message: str,
        plan_json: str,
        skill_md: str,
        *,
        conversation_history: str = "",
        workflow_state: dict | None = None,
    ) -> WorkflowExecuteResult:
        """Execute a workflow that may span multiple turns.

        For multi-turn workflows (requires_lookahead=true), this method:
        1. Executes the code with continuation signal detection
        2. If a checkpoint emits CONTINUE signals, returns a WorkflowExecuteResult
           with needs_continuation=True and the collected facts
        3. If no continuation is needed, returns the normal execution result

        Args:
            user_message: The user's request
            plan_json: JSON string representation of the plan
            skill_md: The skill Markdown content
            conversation_history: Previous conversation context
            workflow_state: Optional existing workflow state to resume

        Returns:
            WorkflowExecuteResult with continuation info if applicable
        """
        result = self._multi_turn_executor.execute_with_continuation(
            user_message=user_message,
            plan_json=plan_json,
            skill_md=skill_md,
            conversation_history=conversation_history,
            workflow_state=workflow_state,
        )

        # Convert to WorkflowExecuteResult
        return WorkflowExecuteResult(
            code=result.code,
            exec_result=result.exec_result,
            attempts_used=result.attempts_used,
            needs_continuation=result.needs_continuation,
            workflow_state=None,
            continuation_facts=result.collected_facts,
        )

    @staticmethod
    def create_workflow_state(
        session_id: str,
        plan_json: str,
        collected_facts: dict[str, Any] | None = None,
    ) -> dict:
        """Create a new workflow state dictionary for multi-turn workflows.

        Args:
            session_id: The session/thread ID
            plan_json: The plan JSON for this workflow
            collected_facts: Optional initial facts from first turn

        Returns:
            Dictionary representing the workflow state
        """
        return {
            "workflow_id": f"wf_{uuid.uuid4().hex[:8]}",
            "session_id": session_id,
            "current_step": 0,
            "plan_json": plan_json,
            "collected_facts": collected_facts or {},
            "checkpoint_results": [],
            "is_multi_turn": True,
            "created_at": datetime.now().isoformat(),
        }

    @staticmethod
    def update_workflow_state(
        state: dict,
        next_step: int,
        facts: dict[str, Any] | None = None,
        checkpoint_result: dict | None = None,
    ) -> dict:
        """Update a workflow state for the next turn.

        Args:
            state: The existing workflow state
            next_step: The step index to advance to
            facts: Additional facts to merge
            checkpoint_result: Raw result from the checkpoint

        Returns:
            Updated workflow state dictionary
        """
        updated = dict(state)
        updated["current_step"] = next_step

        # Merge new facts
        if facts:
            existing_facts = updated.get("collected_facts", {})
            updated["collected_facts"] = {**existing_facts, **facts}

        # Add checkpoint result
        if checkpoint_result:
            results = updated.get("checkpoint_results", [])
            results.append(checkpoint_result)
            updated["checkpoint_results"] = results

        updated["updated_at"] = datetime.now().isoformat()
        return updated

    def _docs_registry_for_plan(self, *, plan_json: str):
        """Get the MCP docs registry for the given plan.

        Args:
            plan_json: JSON string representation of the plan

        Returns:
            MCPDocsRegistry instance
        """
        from .mcp_docs_registry import MCPDocsRegistry

        docs_dir = self.default_docs_dir
        try:
            data = json.loads(plan_json)
        except Exception:
            data = {}
        group = data.get("skill_group") if isinstance(data, dict) else None
        if isinstance(group, str) and group.strip():
            group_tools_root = self.skills_v2_dir / group.strip() / "tools"
            group_docs_dir = group_tools_root / "mcp_docs"
            if group_docs_dir.exists():
                docs_dir = group_docs_dir
        return MCPDocsRegistry(docs_dir, tools_pythonpath=self.default_tools_root)

    def _tools_root_for_plan(self, *, plan_json: str | None) -> Path | None:
        """Get the tools root for the given plan.

        Args:
            plan_json: Optional JSON string representation of the plan

        Returns:
            Path to tools root or None
        """
        return self.default_tools_root


# Backward-compatible re-exports for helper functions
# These were previously defined in this module but have been moved/refactored
from .skill_registry import Skill


def _extract_logic_flow_steps(skill_md: str) -> list[str]:
    """Extract logic flow steps from skill Markdown content.

    This is a backward-compatible wrapper around Skill.logic_flow_steps.
    Accepts either a Skill object (uses its content) or a raw string.
    """
    if isinstance(skill_md, Skill):
        return skill_md.logic_flow_steps
    skill = Skill(name="temp", path=Path("temp"), content=skill_md)
    return skill.logic_flow_steps


def _infer_skill_group(skill_path: Path) -> str | None:
    """Infer the skill group from a skill path.

    This is a backward-compatible wrapper around Skill.group.
    Accepts either a Skill object (uses its path) or a Path object.
    """
    if isinstance(skill_path, Skill):
        return skill_path.group
    skill = Skill(name="temp", path=skill_path, content="")
    return skill.group


# Re-export BAML bridge functions for backward compatibility
# Tests may monkeypatch these at the agent module level
from .baml_bridge import (
    workflow_chat,
    workflow_codegen,
    workflow_plan,
    workflow_plan_review,
    workflow_respond,
)

__all__ = [
    "WorkflowAgent",
    "workflow_plan",
    "workflow_plan_review",
    "workflow_codegen",
    "workflow_chat",
    "workflow_respond",
    "_extract_logic_flow_steps",
    "_infer_skill_group",
    # Multi-turn types
    "WorkflowExecuteResult",
    "WorkflowState",
]
