import json

from agent_workspace.workflow_agent.agent import HRAgent


class ScopeDocsAssertingLLM:
    def __init__(self):
        self.saw_codegen_prompt = False

    def chat(self, messages, temperature=0.2):
        content = messages[-1].content
        if "Return ONLY valid JSON" in content:
            return json.dumps(
                {
                    "action": "execute_skill",
                    "skill_group": "Recruitment-scopes",
                    "skill_name": "Schedule Candidate Interviews",
                    "intent": "Schedule candidate interviews",
                    "steps": ["placeholder"],
                }
            )
        if "Return ONLY a single Python code block." in content:
            self.saw_codegen_prompt = True
            assert "Ticketing for recruiting coordination and follow-ups." in content
            assert "# bamboo_hr" not in content
            return """```python
print("noop")
```"""
        if "Write a concise response to the user" in content:
            assert self.saw_codegen_prompt is True
            return "Done."
        raise AssertionError("Unexpected prompt")


def test_agent_uses_scope_specific_tool_docs_for_codegen():
    agent = HRAgent(llm=ScopeDocsAssertingLLM())
    result = __import__("asyncio").run(agent.run(user_message="Schedule candidate interviews"))
    assert "Done." in (result.final_response or "")

