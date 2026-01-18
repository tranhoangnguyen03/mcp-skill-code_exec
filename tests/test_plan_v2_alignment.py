import json
from agent_workspace.workflow_agent import agent as agent_module

from agent_workspace.workflow_agent.agent import WorkflowAgent


def test_plan_v2_contains_skill_group_and_logic_flow_steps(monkeypatch):
    def fake_workflow_plan(*, user_message: str, skills_readme: str, skill_names: list[str]) -> dict:
        return {
            "action": "execute_skill",
            "skill_group": "HR-scopes",
            "skill_name": "Onboard New Hires",
            "intent": "Onboard new hires",
            "steps": ["placeholder step"],
        }

    def fake_workflow_plan_review(*, user_message: str, proposed_plan_json: str, selected_skill_md: str) -> dict:
        return json.loads(proposed_plan_json)

    monkeypatch.setattr(agent_module, "workflow_plan", fake_workflow_plan)
    monkeypatch.setattr(agent_module, "workflow_plan_review", fake_workflow_plan_review)

    agent = WorkflowAgent()
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
