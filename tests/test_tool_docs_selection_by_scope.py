import json

from agent_workspace.workflow_agent import agent as agent_module
from agent_workspace.workflow_agent.agent import WorkflowAgent


def test_agent_uses_scope_specific_tool_docs_for_codegen(monkeypatch):
    def fake_workflow_plan(
        *, user_message: str, skills_readme: str, skill_names: list[str], skill_groups: list[str], conversation_history: str
    ) -> dict:
        return {
            "action": "execute_skill",
            "skill_group": "Recruitment-scopes",
            "skill_name": "Schedule Candidate Interviews",
            "intent": "Schedule candidate interviews",
            "steps": ["placeholder"],
        }

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
        assert "Ticketing for recruiting coordination and follow-ups." in tool_contracts
        assert "# bamboo_hr" not in tool_contracts
        return """```python
print("noop")
```"""

    def fake_workflow_respond(
        *,
        user_message: str,
        plan_json: str,
        executed_code: str,
        exec_stdout: str,
        exec_stderr: str,
        exit_code: int,
        attempts: int,
        conversation_history: str,
    ) -> str:
        return "Done."

    def fake_workflow_plan_review(
        *, user_message: str, proposed_plan_json: str, selected_skill_md: str, conversation_history: str
    ) -> dict:
        return json.loads(proposed_plan_json)

    monkeypatch.setattr(agent_module, "workflow_plan", fake_workflow_plan)
    monkeypatch.setattr(agent_module, "workflow_plan_review", fake_workflow_plan_review)
    monkeypatch.setattr(agent_module, "workflow_codegen", fake_workflow_codegen)
    monkeypatch.setattr(agent_module, "workflow_respond", fake_workflow_respond)

    agent = WorkflowAgent()
    result = __import__("asyncio").run(agent.run(user_message="Schedule candidate interviews"))
    assert "Done." in (result.final_response or "")


def test_agent_scopes_tool_docs_for_custom_script(monkeypatch):
    def fake_workflow_plan(
        *, user_message: str, skills_readme: str, skill_names: list[str], skill_groups: list[str], conversation_history: str
    ) -> dict:
        assert "Recruitment-scopes" in set(skill_groups)
        return {
            "action": "custom_script",
            "skill_group": "Recruitment-scopes",
            "skill_name": "Candidate lookup",
            "intent": "Look up candidate and report status",
            "steps": ["Search for a candidate by email", "Print their stage"],
        }

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
        assert "Ticketing for recruiting coordination and follow-ups." in tool_contracts
        assert "# bamboo_hr" not in tool_contracts
        return """```python
print("noop")
```"""

    def fake_workflow_respond(
        *,
        user_message: str,
        plan_json: str,
        executed_code: str,
        exec_stdout: str,
        exec_stderr: str,
        exit_code: int,
        attempts: int,
        conversation_history: str,
    ) -> str:
        return "Done."

    monkeypatch.setattr(agent_module, "workflow_plan", fake_workflow_plan)
    monkeypatch.setattr(agent_module, "workflow_codegen", fake_workflow_codegen)
    monkeypatch.setattr(agent_module, "workflow_respond", fake_workflow_respond)

    agent = WorkflowAgent()
    result = __import__("asyncio").run(agent.run(user_message="Find candidate status for alice@example.com"))
    assert "Done." in (result.final_response or "")
