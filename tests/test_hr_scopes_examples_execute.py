import json

from agent_workspace.workflow_agent import agent as agent_module
from agent_workspace.workflow_agent.agent import WorkflowAgent


def _run_skill(*, monkeypatch, skill_name: str, user_message: str, code: str):
    def fake_workflow_plan(*, user_message: str, skills_readme: str, skill_names: list[str]) -> dict:
        return {
            "action": "execute_skill",
            "skill_group": "HR-scopes",
            "skill_name": skill_name,
            "intent": f"Run {skill_name}",
            "steps": ["run workflow"],
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
    ) -> str:
        return "```python\n" + code.strip() + "\n```"

    def fake_workflow_respond(
        *,
        user_message: str,
        plan_json: str,
        executed_code: str,
        exec_stdout: str,
        exec_stderr: str,
        exit_code: int,
        attempts: int,
    ) -> str:
        return f"Ran {skill_name}."

    def fake_workflow_plan_review(*, user_message: str, proposed_plan_json: str, selected_skill_md: str) -> dict:
        return json.loads(proposed_plan_json)

    monkeypatch.setattr(agent_module, "workflow_plan", fake_workflow_plan)
    monkeypatch.setattr(agent_module, "workflow_plan_review", fake_workflow_plan_review)
    monkeypatch.setattr(agent_module, "workflow_codegen", fake_workflow_codegen)
    monkeypatch.setattr(agent_module, "workflow_respond", fake_workflow_respond)

    agent = WorkflowAgent()
    return __import__("asyncio").run(agent.run(user_message=user_message))


def test_hr_scopes_daily_new_hires_digest_executes(monkeypatch):
    code = """
import mcp_tools.bamboo_hr as bamboo
import mcp_tools.slack as slack

hires = bamboo.get_todays_hires()
lines = []
for e in hires:
    lines.append(f"- {e['name']} ({e['dept']}) - {e['role']} (Mgr: {e['manager']})")
digest = "New hires today:\\n" + "\\n".join(lines) if lines else "No new hires today."
slack.post_message(channel="#hr", message=digest)
print("count", len(hires))
"""
    result = _run_skill(
        monkeypatch=monkeypatch,
        skill_name="Daily New Hires Digest",
        user_message="Run daily new hires digest",
        code=code,
    )
    assert result.exec_stdout is not None
    assert "count 3" in result.exec_stdout


def test_hr_scopes_onboard_new_hires_executes(monkeypatch):
    code = """
import mcp_tools.bamboo_hr as bamboo
import mcp_tools.jira as jira
import mcp_tools.slack as slack

hires = bamboo.get_todays_hires()
ticket_ids = []
for e in hires:
    tid = jira.create_ticket(project="IT", summary=f"Onboarding: {e['name']}", priority="High")
    ticket_ids.append(tid)
    slack.send_dm(user_id=e["slack_id"], message=f"Welcome {e['name']}! IT ticket: {tid}")
    slack.send_dm(user_id=e["manager_slack_id"], message=f"{e['name']} started today. Ticket: {tid}")
print("processed", len(hires))
print("tickets", len(ticket_ids))
"""
    result = _run_skill(
        monkeypatch=monkeypatch,
        skill_name="Onboard New Hires",
        user_message="Onboard today's hires",
        code=code,
    )
    assert result.exec_stdout is not None
    assert "processed 3" in result.exec_stdout
    assert "tickets 3" in result.exec_stdout


def test_hr_scopes_probation_checkin_reminders_executes(monkeypatch):
    code = """
import mcp_tools.bamboo_hr as bamboo
import mcp_tools.jira as jira
import mcp_tools.slack as slack

employees = bamboo.get_probation_checkins(days_since_hire=90, window_days=7)
ticket_ids = []
for e in employees:
    tid = jira.create_ticket(project="PEOPLE", summary=f"Probation check-in: {e['name']}", priority="Low")
    ticket_ids.append(tid)
    slack.send_dm(user_id=e["manager_slack_id"], message=f"Check-in due soon for {e['name']}. Ticket: {tid}")
print("count", len(employees))
print("tickets", len(ticket_ids))
"""
    result = _run_skill(
        monkeypatch=monkeypatch,
        skill_name="Probation Check-in Reminders",
        user_message="Send probation reminders",
        code=code,
    )
    assert result.exec_stdout is not None
    assert "count 1" in result.exec_stdout
    assert "tickets 1" in result.exec_stdout


def test_hr_scopes_offboard_employee_executes(monkeypatch):
    code = """
import mcp_tools.bamboo_hr as bamboo
import mcp_tools.jira as jira
import mcp_tools.slack as slack

matches = bamboo.search_employees(query="Maya Lopez")
assert matches, "expected at least one match"
employee_id = matches[0]["id"]
updated = bamboo.mark_offboarding(employee_id=employee_id)
tid = jira.create_ticket(project="IT", summary=f"Offboarding: {updated['name']} ({updated['status']})", priority="High")
slack.send_dm(user_id=updated["manager_slack_id"], message=f"Offboarding started for {updated['name']}. Ticket: {tid}")
print("status", updated["status"])
"""
    result = _run_skill(
        monkeypatch=monkeypatch,
        skill_name="Offboard Employee",
        user_message="Offboard Maya",
        code=code,
    )
    assert result.exec_stdout is not None
    assert "status Offboarding (" in result.exec_stdout


def test_hr_scopes_offboarding_queue_review_executes(monkeypatch):
    code = """
import mcp_tools.bamboo_hr as bamboo
import mcp_tools.jira as jira
import mcp_tools.slack as slack

employees = bamboo.list_employees()
offboarding = [e for e in employees if str(e.get("status", "")).startswith("Offboarding (")]
ticket_ids = []
for e in offboarding:
    tid = jira.create_ticket(project="IT", summary=f"Offboarding queue: {e['name']} ({e['status']})", priority="High")
    ticket_ids.append(tid)
    slack.send_dm(user_id=e["manager_slack_id"], message=f"Offboarding queued for {e['name']}. Ticket: {tid}")
print("offboarding", len(offboarding))
print("tickets", len(ticket_ids))
"""
    result = _run_skill(
        monkeypatch=monkeypatch,
        skill_name="Offboarding Queue Review",
        user_message="Anyone offboarding we need to process?",
        code=code,
    )
    assert result.exec_stdout is not None
    assert "offboarding 1" in result.exec_stdout
    assert "tickets 1" in result.exec_stdout


def test_hr_scopes_role_change_access_review_executes(monkeypatch):
    code = """
import mcp_tools.bamboo_hr as bamboo
import mcp_tools.jira as jira
import mcp_tools.slack as slack

matches = bamboo.search_employees(query="Charlie Davis")
assert matches, "expected a match"
e = matches[0]
updated = bamboo.update_employee(employee_id=e["id"], updates={"role": "Senior DevOps Engineer"})
tid = jira.create_ticket(project="IT", summary=f"Access review for {updated['name']} ({e['role']} -> {updated['role']})", priority="Medium")
slack.send_dm(user_id=updated["manager_slack_id"], message=f"Role updated for {updated['name']}. Review: {tid}")
print("role", updated["role"])
"""
    result = _run_skill(
        monkeypatch=monkeypatch,
        skill_name="Role Change + Access Review",
        user_message="Update Ben's role",
        code=code,
    )
    assert result.exec_stdout is not None
    assert "role Senior DevOps Engineer" in result.exec_stdout
