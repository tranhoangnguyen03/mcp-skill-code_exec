import json
from pathlib import Path

from agent_workspace.workflow_agent.agent import HRAgent


class FakeLLM:
    def __init__(self):
        self.calls = 0

    def chat(self, messages, temperature=0.2):
        self.calls += 1
        content = messages[-1].content
        if "Return ONLY valid JSON" in content:
            return json.dumps(
                {
                    "action": "execute_skill",
                    "skill_group": "HR-scopes",
                    "skill_name": "Onboard New Hires",
                    "intent": "Run onboarding digest",
                    "steps": ["fetch hires", "notify managers", "summarize"],
                }
            )
        if "Return ONLY a single Python code block." in content:
            return """```python
import mcp_tools
import mcp_tools.bamboo_hr as bamboo

hires = bamboo.get_todays_hires()
print("mcp_tools_file:", mcp_tools.__file__)
print("hires:", len(hires))
```"""
        if "Write a concise response to the user" in content:
            return "Completed v2 workflow."
        raise AssertionError("Unexpected prompt")


def test_agent_v2_end_to_end_fake_llm():
    agent = HRAgent(llm=FakeLLM())
    result = __import__("asyncio").run(agent.run(user_message="Run onboarding"))
    assert "Completed v2 workflow" in result.final_response
    assert result.exec_stdout is not None
    assert "hires: 3" in result.exec_stdout
    assert "skills_v2/HR-scopes/tools/mcp_tools" in result.exec_stdout.replace("\\", "/")
    assert result.attempts == 1


class ChatLLM:
    def chat(self, messages, temperature=0.2):
        content = messages[-1].content
        if "Return ONLY valid JSON" in content:
            return json.dumps({"action": "chat", "skill_name": None, "intent": "greeting", "steps": []})
        if "does not require running any workflows" in content:
            return "Hello from v2."
        raise AssertionError("Unexpected prompt")


def test_agent_v2_chat_does_not_execute():
    agent = HRAgent(llm=ChatLLM())
    result = __import__("asyncio").run(agent.run(user_message="hello"))
    assert "Hello from v2." in result.final_response
    assert result.generated_code is None
    assert result.exec_stdout is None
    assert result.attempts is None


class UnknownSkillLLM:
    def chat(self, messages, temperature=0.2):
        content = messages[-1].content
        if "Return ONLY valid JSON" in content:
            return json.dumps(
                {
                    "action": "execute_skill",
                    "skill_name": "HR-notify-employee",
                    "intent": "Notify someone",
                    "steps": ["send dm"],
                }
            )
        if "Return ONLY a single Python code block." in content:
            return """```python
print("ok")
```"""
        if "Write a concise response to the user" in content:
            return "Done."
        raise AssertionError("Unexpected prompt")


def test_agent_v2_unknown_skill_name_does_not_crash():
    agent = HRAgent(llm=UnknownSkillLLM())
    plan, plan_json, selected_skill = agent.plan(user_message="Notify Alice")
    assert plan.action in {"execute_skill", "custom_script"}
