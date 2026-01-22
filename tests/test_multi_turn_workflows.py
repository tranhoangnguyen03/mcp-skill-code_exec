"""Tests for multi-turn workflow functionality.

Tests the ability to handle workflows that span multiple execution turns,
such as "Assign Mr.Davis to interview candidates in his domain expertise".
"""
import json
import pytest

from agent_workspace.workflow_agent import agent as agent_module
from agent_workspace.workflow_agent.agent import WorkflowAgent
from agent_workspace.workflow_agent.sub_agents.executor import (
    detect_continuation_signals,
    MultiTurnExecuteResult,
    MultiTurnWorkflowExecutor,
)
from agent_workspace.workflow_agent.types import ExecutionResult


class TestContinuationSignalDetection:
    """Tests for detecting CONTINUE_FACT and CONTINUE_WORKFLOW signals in stdout."""

    def test_detect_single_fact(self):
        stdout = """
[INFO] Looking up employee Davis...
Found: Charlie Davis - DevOps Engineer
CONTINUE_FACT: expert_domain=DevOps
CONTINUE_WORKFLOW: checkpoint_complete
"""
        needs_continuation, facts = detect_continuation_signals(stdout)
        assert needs_continuation is True
        assert facts == {"expert_domain": "DevOps"}

    def test_detect_multiple_facts(self):
        stdout = """
[INFO] Searching for employees...
Found: Charlie Davis (ID: 103) in Engineering
CONTINUE_FACT: employee_name=Charlie Davis
CONTINUE_FACT: employee_id=103
CONTINUE_FACT: employee_dept=Engineering
CONTINUE_WORKFLOW: checkpoint_complete
"""
        needs_continuation, facts = detect_continuation_signals(stdout)
        assert needs_continuation is True
        assert facts["employee_name"] == "Charlie Davis"
        assert facts["employee_id"] == "103"
        assert facts["employee_dept"] == "Engineering"

    def test_no_continuation_signal(self):
        stdout = """
[INFO] Processing request...
[INFO] Completed all tasks
=== FINAL SUMMARY ===
Processed 3 items successfully.
"""
        needs_continuation, facts = detect_continuation_signals(stdout)
        assert needs_continuation is False
        assert facts == {}

    def test_fact_without_workflow_signal(self):
        """Facts should not trigger continuation without workflow signal."""
        stdout = """
[INFO] Found some data
CONTINUE_FACT: some_key=some_value
"""
        needs_continuation, facts = detect_continuation_signals(stdout)
        assert needs_continuation is False


class TestWorkflowState:
    """Tests for workflow state creation and updates."""

    def test_create_workflow_state(self):
        state = WorkflowAgent.create_workflow_state(
            session_id="test_session_123",
            plan_json='{"action": "custom_script", "intent": "test"}',
            collected_facts={"key": "value"},
        )

        assert state["session_id"] == "test_session_123"
        assert state["plan_json"] == '{"action": "custom_script", "intent": "test"}'
        assert state["collected_facts"] == {"key": "value"}
        assert state["is_multi_turn"] is True
        assert state["workflow_id"].startswith("wf_")
        assert "created_at" in state

    def test_update_workflow_state(self):
        original_state = {
            "workflow_id": "wf_abc123",
            "session_id": "session_123",
            "current_step": 0,
            "plan_json": "{}",
            "collected_facts": {"existing": "fact"},
            "checkpoint_results": [],
            "is_multi_turn": True,
            "created_at": "2024-01-01T00:00:00",
        }

        updated = WorkflowAgent.update_workflow_state(
            original_state,
            next_step=1,
            facts={"new_fact": "new_value"},
            checkpoint_result={"step": "lookup", "result": "success"},
        )

        assert updated["current_step"] == 1
        assert updated["collected_facts"]["existing"] == "fact"
        assert updated["collected_facts"]["new_fact"] == "new_value"
        assert len(updated["checkpoint_results"]) == 1


class TestMultiTurnAgentExecution:
    """Tests for multi-turn execution with mocked BAML responses."""

    def test_multi_turn_plan_requires_lookahead(self, monkeypatch):
        """Test that the planner sets requires_lookahead for requests needing data lookup."""

        def fake_workflow_plan(
            *, user_message: str, skills_readme: str, skill_names: list[str], skill_groups: list[str], conversation_history: str
        ) -> dict:
            # Simulate the LLM detecting that this request needs lookahead
            return {
                "action": "custom_script",
                "skill_group": "Recruitment-scopes",
                "skill_name": None,
                "intent": "Assign Mr.Davis as interviewer based on domain expertise",
                "steps": [
                    "Look up Mr.Davis to discover domain expertise",
                    "Find candidates in that domain",
                    "Assign Mr.Davis as interviewer"
                ],
                "requires_lookahead": True,
                "checkpoints": ["lookup_davis", "discover_domain"],
            }

        monkeypatch.setattr(agent_module, "workflow_plan", fake_workflow_plan)

        agent = WorkflowAgent()
        plan, plan_json, selected_skill = agent.plan(
            user_message="Assign Mr.Davis to be the interviewer for the candidate in his domain expertise"
        )

        assert plan.requires_lookahead is True
        assert "lookup_davis" in plan.checkpoints

    def test_plan_json_includes_multi_turn_fields(self, monkeypatch):
        """Test that plan JSON serialization includes multi-turn fields."""

        def fake_workflow_plan(
            *, user_message: str, skills_readme: str, skill_names: list[str], skill_groups: list[str], conversation_history: str
        ) -> dict:
            return {
                "action": "custom_script",
                "skill_group": "HR-scopes",
                "skill_name": None,
                "intent": "Test multi-turn",
                "steps": ["step1", "step2"],
                "requires_lookahead": True,
                "checkpoints": ["checkpoint1"],
            }

        monkeypatch.setattr(agent_module, "workflow_plan", fake_workflow_plan)

        agent = WorkflowAgent()
        plan, plan_json, selected_skill = agent.plan(user_message="test")

        plan_data = json.loads(plan_json)
        assert plan_data["requires_lookahead"] is True
        assert plan_data["checkpoints"] == ["checkpoint1"]

    def test_multi_turn_execute_result(self):
        """Test MultiTurnExecuteResult dataclass."""
        result = MultiTurnExecuteResult(
            code="print('test')",
            exec_result=ExecutionResult(stdout="", stderr="", exit_code=0),
            attempts_used=1,
            needs_continuation=True,
            collected_facts={"domain": "DevOps"},
        )

        assert result.needs_continuation is True
        assert result.collected_facts == {"domain": "DevOps"}


class TestBackwardCompatibility:
    """Tests to ensure backward compatibility with single-turn workflows."""

    def test_plan_without_lookahead_defaults_to_false(self, monkeypatch):
        """Plans without lookahead flag should default to False."""

        def fake_workflow_plan(
            *, user_message: str, skills_readme: str, skill_names: list[str], skill_groups: list[str], conversation_history: str
        ) -> dict:
            # Old-style plan without lookahead
            return {
                "action": "execute_skill",
                "skill_group": "HR-scopes",
                "skill_name": "Onboard New Hires",
                "intent": "Onboard new hires",
                "steps": ["fetch hires", "create tickets"],
            }

        monkeypatch.setattr(agent_module, "workflow_plan", fake_workflow_plan)

        agent = WorkflowAgent()
        plan, plan_json, selected_skill = agent.plan(user_message="Onboard new hires")

        assert plan.requires_lookahead is False
        assert plan.checkpoints == []

    def test_plan_json_without_lookahead(self, monkeypatch):
        """Plan JSON should not include lookahead fields when not set."""

        def fake_workflow_plan(
            *, user_message: str, skills_readme: str, skill_names: list[str], skill_groups: list[str], conversation_history: str
        ) -> dict:
            return {
                "action": "execute_skill",
                "skill_group": "HR-scopes",
                "skill_name": "Onboard New Hires",
                "intent": "Onboard new hires",
                "steps": ["fetch hires"],
            }

        monkeypatch.setattr(agent_module, "workflow_plan", fake_workflow_plan)

        agent = WorkflowAgent()
        plan, plan_json, selected_skill = agent.plan(user_message="Onboard new hires")

        plan_data = json.loads(plan_json)
        # Fields should still be present but default to False/empty
        assert plan_data["requires_lookahead"] is False
        assert plan_data["checkpoints"] == []


class TestExecutorIntegration:
    """Integration tests for the multi-turn executor."""

    def test_execute_with_continuation_injects_facts(self, monkeypatch):
        """Test that collected facts from previous turns are injected into conversation history."""
        seen_histories = []

        def fake_workflow_codegen(
            *,
            user_message: str,
            plan_json: str,
            skill_md: str,
            tool_contracts: str,
            attempt: int,
            previous_error: str,
            previous_code: str,
            conversation_history: str,
        ) -> str:
            seen_histories.append(conversation_history)
            # Return final summary code (no continuation signal)
            return """```python
print("Using collected facts to complete the task")
print("=== FINAL SUMMARY ===")
```"""

        monkeypatch.setattr(agent_module, "workflow_codegen", fake_workflow_codegen)

        agent = WorkflowAgent()
        executor = MultiTurnWorkflowExecutor(agent._workflow_executor)

        # Execute with workflow state containing collected facts
        result = executor.execute_with_continuation(
            user_message="Assign Mr.Davis to interview candidates",
            plan_json='{"action": "custom_script", "requires_lookahead": true}',
            skill_md="",
            conversation_history="",
            workflow_state={
                "workflow_id": "wf_test",
                "session_id": "test",
                "collected_facts": {"expert_domain": "DevOps", "employee_name": "Charlie Davis"},
                "is_multi_turn": True,
            },
        )

        # Verify that the conversation history was enriched with collected facts
        assert len(seen_histories) == 1
        history = seen_histories[0]
        assert "Collected Facts from Previous Steps" in history
        assert "expert_domain: DevOps" in history
        assert "employee_name: Charlie Davis" in history

        # Should not need continuation (no CONTINUE signals in output)
        assert result.needs_continuation is False


class TestOrganicMultiTurnScenario:
    def test_multi_turn_two_steps_with_session_memory(self, monkeypatch, tmp_path):
        from agent_workspace.memory.session_memory import SessionMemory

        def fake_workflow_codegen(
            *,
            user_message: str,
            plan_json: str,
            skill_md: str,
            tool_contracts: str,
            attempt: int,
            previous_error: str,
            previous_code: str,
            conversation_history: str,
        ) -> str:
            if "Collected Facts from Previous Steps" not in conversation_history:
                return """```python
import mcp_tools.bamboo_hr as bamboo_hr

matches = bamboo_hr.search_employees(query="Davis")
if not matches:
    raise SystemExit("expected at least one Davis match")

e = matches[0]
role = str(e.get("role") or "")
domain = "DevOps" if "devops" in role.lower() else (role.split()[0] if role.split() else "Unknown")

print(f"CONTINUE_FACT: employee_name={e.get('name')}")
print(f"CONTINUE_FACT: expert_domain={domain}")
print("CONTINUE_WORKFLOW: checkpoint_complete")
```"""

            return f"""```python
import re
import mcp_tools.candidate_tracker as candidate_tracker

history = {json.dumps(conversation_history)}
m = re.search(r"expert_domain:\\s*(.+)", history)
domain = m.group(1).strip() if m else "Unknown"

candidates = candidate_tracker.search_candidates(domain)
print("domain", domain)
print("candidates", len(candidates))
print("=== FINAL SUMMARY ===")
```"""

        monkeypatch.setattr(agent_module, "workflow_codegen", fake_workflow_codegen)

        agent = WorkflowAgent()
        plan_json = json.dumps(
            {
                "action": "custom_script",
                "intent": "Assign Mr.Davis to interview candidates in his domain",
                "steps": ["lookup_davis", "assign_interviewer"],
                "requires_lookahead": True,
                "checkpoints": ["lookup_davis"],
            }
        )

        turn_1 = agent.execute_multi_turn_workflow(
            user_message="Assign Mr.Davis to be the interviewer for the candidate in his domain expertise",
            plan_json=plan_json,
            skill_md="",
        )
        assert turn_1.exec_result.exit_code == 0
        assert turn_1.needs_continuation is True
        assert turn_1.continuation_facts.get("expert_domain") == "DevOps"
        assert turn_1.continuation_facts.get("employee_name")

        memory = SessionMemory(session_id="test_multi_turn", memory_dir=tmp_path)
        state = WorkflowAgent.create_workflow_state(
            session_id=memory.session_id,
            plan_json=plan_json,
            collected_facts=turn_1.continuation_facts,
        )
        memory.save_workflow_state(state)
        assert memory.has_pending_workflow() is True
        loaded = memory.get_workflow_state()
        assert loaded is not None

        turn_2 = agent.execute_multi_turn_workflow(
            user_message="Continue",
            plan_json=plan_json,
            skill_md="",
            workflow_state=loaded,
        )
        assert turn_2.exec_result.exit_code == 0
        assert turn_2.needs_continuation is False
        assert "domain DevOps" in turn_2.exec_result.stdout
        assert "=== FINAL SUMMARY ===" in turn_2.exec_result.stdout

        memory.clear_workflow_state()
        assert memory.has_pending_workflow() is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
