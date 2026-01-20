import json

from agent_workspace.workflow_agent import agent as agent_module
from agent_workspace.workflow_agent.agent import WorkflowAgent
from agent_workspace.workflow_agent.types import ExecutionResult


def test_agent_v2_end_to_end_fake_baml(monkeypatch):
    def fake_workflow_plan(
        *, user_message: str, skills_readme: str, skill_names: list[str], skill_groups: list[str], conversation_history: str
    ) -> dict:
        return {
            "action": "execute_skill",
            "skill_group": "HR-scopes",
            "skill_name": "Onboard New Hires",
            "intent": "Run onboarding digest",
            "steps": ["fetch hires", "notify managers", "summarize"],
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
        return """```python
import mcp_tools
import mcp_tools.bamboo_hr as bamboo

hires = bamboo.get_todays_hires()
print("mcp_tools_file:", mcp_tools.__file__)
print("hires:", len(hires))
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
        return "Completed v2 workflow."

    def fake_workflow_plan_review(
        *, user_message: str, proposed_plan_json: str, selected_skill_md: str, conversation_history: str
    ) -> dict:
        return json.loads(proposed_plan_json)

    monkeypatch.setattr(agent_module, "workflow_plan", fake_workflow_plan)
    monkeypatch.setattr(agent_module, "workflow_plan_review", fake_workflow_plan_review)
    monkeypatch.setattr(agent_module, "workflow_codegen", fake_workflow_codegen)
    monkeypatch.setattr(agent_module, "workflow_respond", fake_workflow_respond)

    agent = WorkflowAgent()
    result = __import__("asyncio").run(agent.run(user_message="Run onboarding"))
    assert "Completed v2 workflow" in (result.final_response or "")
    assert result.exec_stdout is not None
    assert "hires: 3" in result.exec_stdout
    assert "agent_workspace/tools/mcp_tools" in result.exec_stdout.replace("\\", "/")
    assert result.attempts == 1


def test_agent_v2_chat_does_not_execute(monkeypatch):
    def fake_workflow_plan(
        *, user_message: str, skills_readme: str, skill_names: list[str], skill_groups: list[str], conversation_history: str
    ) -> dict:
        return {"action": "chat", "skill_group": None, "skill_name": None, "intent": "greeting", "steps": []}

    def fake_workflow_chat(*, user_message: str, skills_readme: str, custom_skill_md: str, conversation_history: str) -> str:
        return "Hello from v2."

    monkeypatch.setattr(agent_module, "workflow_plan", fake_workflow_plan)
    monkeypatch.setattr(agent_module, "workflow_chat", fake_workflow_chat)

    agent = WorkflowAgent()
    result = __import__("asyncio").run(agent.run(user_message="hello"))
    assert "Hello from v2." in (result.final_response or "")
    assert result.generated_code is None
    assert result.exec_stdout is None
    assert result.attempts is None


def test_agent_v2_unknown_skill_name_does_not_crash(monkeypatch):
    def fake_workflow_plan(
        *, user_message: str, skills_readme: str, skill_names: list[str], skill_groups: list[str], conversation_history: str
    ) -> dict:
        return {
            "action": "execute_skill",
            "skill_group": "HR-scopes",
            "skill_name": "HR-notify-employee",
            "intent": "Notify someone",
            "steps": ["send dm"],
        }

    monkeypatch.setattr(agent_module, "workflow_plan", fake_workflow_plan)

    agent = WorkflowAgent()
    plan, plan_json, selected_skill = agent.plan(user_message="Notify Alice")
    assert plan.action in {"execute_skill", "custom_script"}


def test_agent_v2_passes_conversation_history(monkeypatch):
    seen: dict[str, str] = {}

    def fake_workflow_plan(
        *, user_message: str, skills_readme: str, skill_names: list[str], skill_groups: list[str], conversation_history: str
    ) -> dict:
        seen["plan"] = conversation_history
        return {"action": "custom_script", "skill_group": "HR-scopes", "skill_name": None, "intent": "do", "steps": ["x"]}

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
        seen["codegen"] = conversation_history
        return "```python\nprint('ok')\n```"

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
        seen["respond"] = conversation_history
        return "ok"

    def fake_workflow_chat(*, user_message: str, skills_readme: str, custom_skill_md: str, conversation_history: str) -> str:
        seen["chat"] = conversation_history
        return "chat"

    monkeypatch.setattr(agent_module, "workflow_plan", fake_workflow_plan)
    monkeypatch.setattr(agent_module, "workflow_codegen", fake_workflow_codegen)
    monkeypatch.setattr(agent_module, "workflow_respond", fake_workflow_respond)
    monkeypatch.setattr(agent_module, "workflow_chat", fake_workflow_chat)

    agent = WorkflowAgent()
    history = "User: is there a mr.Davis among us?\nAssistant: Yes, Charlie Davis."

    agent.plan(user_message="tell him ...", conversation_history=history)
    agent.codegen(user_message="tell him ...", plan_json="{}", skill_md="", conversation_history=history)
    agent.respond(
        user_message="tell him ...",
        plan_json="{}",
        executed_code="print('ok')",
        exec_result=ExecutionResult(stdout="", stderr="", exit_code=0),
        attempts=1,
        conversation_history=history,
    )
    agent.chat(user_message="hi", conversation_history=history)

    assert seen["plan"] == history
    assert seen["codegen"] == history
    assert seen["respond"] == history
    assert seen["chat"] == history
