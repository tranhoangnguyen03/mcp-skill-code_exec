import json
from pathlib import Path

from agent_workspace.workflow_agent.agent import HRAgent


class PlannerLLM:
    def __init__(self):
        pass

    def chat(self, messages, temperature=0.2):
        content = messages[-1].content
        if "Return ONLY valid JSON" in content:
            return json.dumps(
                {
                    "action": "execute_skill",
                    "skill_group": "HR-scopes",
                    "skill_name": "Onboard New Hires",
                    "intent": "Onboard new hires",
                    "steps": ["placeholder step"],
                }
            )
        if "Return ONLY a single Python code block." in content:
            return """```python
print("noop")
```"""
        if "Write a concise response to the user" in content:
            return "Done."
        raise AssertionError("Unexpected prompt")


def test_plan_v2_contains_skill_group_and_logic_flow_steps():
    agent = HRAgent(llm=PlannerLLM())
    plan, plan_json, selected_skill = agent.plan(user_message="Onboard new hires")
    assert plan.skill_group == "HR-scopes"
    assert plan.skill_name == "Onboard New Hires"
    assert selected_skill is not None

    # Steps should follow the Logic Flow of onboarding_new_hires.md
    assert any("Fetch hires" in s for s in plan.steps)
    assert any("Create a Jira ticket" in s for s in plan.steps)
    assert any("Send a Slack DM" in s for s in plan.steps)
    assert any("Print a final summary" in s for s in plan.steps)

    data = json.loads(plan_json)
    assert data["skill_group"] == "HR-scopes"
    assert data["skill_name"] == "Onboard New Hires"
    assert isinstance(data["steps"], list) and len(data["steps"]) >= 3
