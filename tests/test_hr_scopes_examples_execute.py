import json

from agent_workspace.workflow_agent.agent import HRAgent


class ExampleLLM:
    def __init__(self, *, skill_name: str, code: str):
        self.skill_name = skill_name
        self.code = code

    def chat(self, messages, temperature=0.2):
        content = messages[-1].content
        if "Return ONLY valid JSON" in content:
            return json.dumps(
                {
                    "action": "execute_skill",
                    "skill_group": "HR-scopes",
                    "skill_name": self.skill_name,
                    "intent": f"Run {self.skill_name}",
                    "steps": ["run workflow"],
                }
            )
        if "Return ONLY a single Python code block." in content:
            return "```python\n" + self.code.strip() + "\n```"
        if "Write a concise response to the user" in content:
            return f"Ran {self.skill_name}."
        raise AssertionError("Unexpected prompt")


def test_hr_scopes_daily_new_hires_digest_executes():
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
    agent = HRAgent(llm=ExampleLLM(skill_name="Daily New Hires Digest", code=code))
    result = __import__("asyncio").run(agent.run(user_message="Run daily new hires digest"))
    assert result.exec_stdout is not None
    assert "count 3" in result.exec_stdout


def test_hr_scopes_onboard_new_hires_executes():
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
    agent = HRAgent(llm=ExampleLLM(skill_name="Onboard New Hires", code=code))
    result = __import__("asyncio").run(agent.run(user_message="Onboard today's hires"))
    assert result.exec_stdout is not None
    assert "processed 3" in result.exec_stdout
    assert "tickets 3" in result.exec_stdout


def test_hr_scopes_probation_checkin_reminders_executes():
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
    agent = HRAgent(llm=ExampleLLM(skill_name="Probation Check-in Reminders", code=code))
    result = __import__("asyncio").run(agent.run(user_message="Send probation reminders"))
    assert result.exec_stdout is not None
    assert "count 1" in result.exec_stdout
    assert "tickets 1" in result.exec_stdout


def test_hr_scopes_offboard_employee_executes():
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
    agent = HRAgent(llm=ExampleLLM(skill_name="Offboard Employee", code=code))
    result = __import__("asyncio").run(agent.run(user_message="Offboard Maya"))
    assert result.exec_stdout is not None
    assert "status Offboarding (" in result.exec_stdout


def test_hr_scopes_offboarding_queue_review_executes():
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
    agent = HRAgent(llm=ExampleLLM(skill_name="Offboarding Queue Review", code=code))
    result = __import__("asyncio").run(agent.run(user_message="Anyone offboarding we need to process?"))
    assert result.exec_stdout is not None
    assert "offboarding 1" in result.exec_stdout
    assert "tickets 1" in result.exec_stdout


def test_hr_scopes_role_change_access_review_executes():
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
    agent = HRAgent(llm=ExampleLLM(skill_name="Role Change + Access Review", code=code))
    result = __import__("asyncio").run(agent.run(user_message="Update Ben's role"))
    assert result.exec_stdout is not None
    assert "role Senior DevOps Engineer" in result.exec_stdout
