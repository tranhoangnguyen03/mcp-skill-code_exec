import json
from pathlib import Path

from agent_workspace.hr_agent.agent import HRAgent


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
                    "skill_name": "onboarding_new_hires",
                    "intent": "Onboard engineering hires today",
                    "steps": ["fetch hires", "filter engineering", "create tickets and DMs"],
                }
            )
        if "Return ONLY a single Python code block." in content:
            return """```python
import mcp_tools.bamboo_hr as bamboo
import mcp_tools.jira as jira
import mcp_tools.slack as slack

hires = bamboo.get_todays_hires()
for e in hires:
    if e["dept"] == "Engineering":
        tid = jira.create_ticket("IT", f"Laptop setup for {e['name']}", "High")
        slack.send_dm(e["slack_id"], f"Welcome! Ticket: {tid}")
print("done")
```"""
        if "Write a concise response to the user" in content:
            return "Completed onboarding workflow."
        raise AssertionError("Unexpected prompt")


def test_agent_end_to_end_fake_llm():
    agent = HRAgent(llm=FakeLLM())
    result = __import__("asyncio").run(agent.run(user_message="Onboard engineering hires"))
    assert "Completed onboarding workflow" in result.final_response
    assert result.exec_stdout is not None
    assert "done" in result.exec_stdout
    assert result.attempts == 1


class ChatLLM:
    def chat(self, messages, temperature=0.2):
        content = messages[-1].content
        if "Return ONLY valid JSON" in content:
            return json.dumps({"action": "chat", "skill_name": None, "intent": "greeting", "steps": []})
        if "does not require running any workflows" in content:
            return "Hello! Tell me what HR workflow you want to run."
        raise AssertionError("Unexpected prompt")


def test_agent_greeting_does_not_execute():
    agent = HRAgent(llm=ChatLLM())
    result = __import__("asyncio").run(agent.run(user_message="hello"))
    assert "Hello!" in result.final_response
    assert result.generated_code is None
    assert result.exec_stdout is None
    assert result.attempts is None


class RetryCodegenLLM:
    def __init__(self):
        self.codegen_calls = 0

    def chat(self, messages, temperature=0.2):
        content = messages[-1].content
        if "Return ONLY valid JSON" in content:
            return json.dumps(
                {
                    "action": "execute_skill",
                    "skill_name": "onboarding_new_hires",
                    "intent": "Onboard engineering hires today",
                    "steps": ["fetch hires", "filter engineering", "create tickets and DMs"],
                }
            )
        if "Return ONLY a single Python code block." in content:
            self.codegen_calls += 1
            if self.codegen_calls == 1:
                return "```python\nprint(\n```"
            return """```python
print("done")
```"""
        if "Write a concise response to the user" in content:
            return "Completed after retry."
        raise AssertionError("Unexpected prompt")


def test_agent_retries_codegen_then_succeeds():
    agent = HRAgent(llm=RetryCodegenLLM(), max_attempts=3)
    result = __import__("asyncio").run(agent.run(user_message="Onboard engineering hires"))
    assert result.exec_stdout is not None
    assert "done" in result.exec_stdout
    assert result.attempts == 2


class RetryExecutionLLM:
    def __init__(self):
        self.codegen_calls = 0

    def chat(self, messages, temperature=0.2):
        content = messages[-1].content
        if "Return ONLY valid JSON" in content:
            return json.dumps(
                {
                    "action": "execute_skill",
                    "skill_name": "onboarding_new_hires",
                    "intent": "Onboard engineering hires today",
                    "steps": ["fetch hires", "filter engineering", "create tickets and DMs"],
                }
            )
        if "Return ONLY a single Python code block." in content:
            self.codegen_calls += 1
            if self.codegen_calls == 1:
                return """```python
raise RuntimeError("boom")
```"""
            return """```python
print("done")
```"""
        if "Write a concise response to the user" in content:
            return "Completed after execution retry."
        raise AssertionError("Unexpected prompt")


def test_agent_retries_execution_then_succeeds():
    agent = HRAgent(llm=RetryExecutionLLM(), max_attempts=3)
    result = __import__("asyncio").run(agent.run(user_message="Onboard engineering hires"))
    assert result.exec_stdout is not None
    assert "done" in result.exec_stdout
    assert result.attempts == 2


class CustomScriptLLM:
    def chat(self, messages, temperature=0.2):
        content = messages[-1].content
        if "Return ONLY valid JSON" in content:
            return json.dumps(
                {
                    "action": "custom_script",
                    "skill_name": None,
                    "intent": "Custom HR automation request",
                    "steps": ["use tools", "execute script", "summarize"],
                }
            )
        if "Return ONLY a single Python code block." in content:
            return """```python
print("custom done")
```"""
        if "Write a concise response to the user" in content:
            return "Completed custom script."
        raise AssertionError("Unexpected prompt")


def test_agent_custom_script_path_executes():
    agent = HRAgent(llm=CustomScriptLLM())
    result = __import__("asyncio").run(agent.run(user_message="Do something unusual"))
    assert result.exec_stdout is not None
    assert "custom done" in result.exec_stdout
    assert result.attempts == 1
