from __future__ import annotations

import json
import re

import pytest

from agent_workspace.workflow_agent import agent as agent_module
from tests.utils.qualitative_judge import HeuristicJudge, evaluate_with_judge
from tests.utils.scenario_harness import Scenario, run_scenario


HR_SKILLS = {
    "Daily New Hires Digest",
    "Onboard New Hires",
    "Probation Check-in Reminders",
    "Offboard Employee",
    "Offboarding Queue Review",
    "Role Change + Access Review",
    "Leave & Absence Management",
    "Performance Review Cycle",
}

RECRUITMENT_SKILLS = {
    "Schedule Candidate Interviews",
    "Chase Interview Feedback",
    "Candidate Pipeline Review",
}


class DeterministicScenarioAgentLLM:
    def __init__(self, *, request_to_skill: dict[str, str], code_by_skill: dict[str, str]):
        self.request_to_skill = request_to_skill
        self.code_by_skill = code_by_skill
        self._last_skill: str | None = None

    def chat(self, messages, temperature=0.2):
        content = messages[-1].content

        if "Return ONLY valid JSON" in content:
            m = re.search(r"User request:\n(.*?)\n\nReturn ONLY valid JSON\.", content, re.DOTALL)
            if not m:
                raise AssertionError("Failed to extract user request from planning prompt")
            user_request = m.group(1).strip()
            skill_name = self.request_to_skill[user_request]
            self._last_skill = skill_name
            return json.dumps(
                {
                    "action": "execute_skill",
                    "skill_group": "HR-scopes" if skill_name in HR_SKILLS else "Recruitment-scopes" if skill_name in RECRUITMENT_SKILLS else "Procurement-scopes",
                    "skill_name": skill_name,
                    "intent": f"Resolve request using {skill_name}",
                    "steps": ["follow skill logic flow"],
                }
            )

        if "Return ONLY a single Python code block." in content:
            assert self._last_skill is not None
            code = self.code_by_skill[self._last_skill]
            return "```python\n" + code.strip() + "\n```"

        if "Write a concise response to the user" in content:
            if self._last_skill:
                stdout = ""
                if "Execution stdout:" in content:
                    stdout = content.split("Execution stdout:\n", 1)[1].split("\nExecution stderr:", 1)[0].strip()
                ticket_ids = re.findall(r"\b[A-Z]+-\d+\b", stdout)
                uniq_tickets = sorted(set(ticket_ids))
                headline = stdout.splitlines()[-1].strip() if stdout.strip() else ""
                ticket_part = f" Tickets: {', '.join(uniq_tickets)}." if uniq_tickets else ""
                if headline:
                    return f"Completed: {self._last_skill}.{ticket_part} Result: {headline}"
                return f"Completed: {self._last_skill}.{ticket_part}"
            return "Completed."

        raise AssertionError("Unexpected prompt")


CODE_BY_SKILL: dict[str, str] = {
    "Daily New Hires Digest": """
import mcp_tools.bamboo_hr as bamboo
import mcp_tools.slack as slack

hires = bamboo.get_todays_hires()
lines = []
for e in hires:
    lines.append(f"- {e['name']} ({e['dept']}) - {e['role']} (Mgr: {e['manager']})")
digest = "New hires today:\\n" + "\\n".join(lines) if lines else "No new hires today."
slack.post_message(channel="#hr", message=digest)
print("count", len(hires))
""",
    "Onboard New Hires": """
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
""",
    "Probation Check-in Reminders": """
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
""",
    "Offboard Employee": """
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
""",
    "Offboarding Queue Review": """
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
""",
    "Role Change + Access Review": """
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
""",
    "Leave & Absence Management": """
import mcp_tools.google_calendar as gcal
import mcp_tools.gmail as gmail
import mcp_tools.slack as slack

email = "alice@company.com"
start_date = "2023-12-25"
end_date = "2023-12-29"

event = gcal.create_event(
    email=email,
    title="Out of Office",
    start_time=start_date + "T09:00:00",
    end_time=end_date + "T17:00:00",
)
responder = gmail.set_auto_responder(
    email=email,
    start_date=start_date,
    end_date=end_date,
    message=f"I am out of the office from {start_date} to {end_date}.",
)
slack.post_message(channel="#engineering", message=f"FYI: {email} will be OOO from {start_date} to {end_date}.")
print("event", event["id"])
print("auto", responder["enabled"])
""",
    "Performance Review Cycle": """
import mcp_tools.lattice as lattice
import mcp_tools.slack as slack

cycle = lattice.create_cycle(name="Q4 Review", due_date="2024-01-31")
eligible = lattice.get_eligible_employees(min_tenure_days=90)
for u in eligible:
    slack.send_dm(user_id=u["id"], message=f"Performance review started ({cycle['name']}). Due {cycle['due_date']}.")
print("cycle", cycle["id"])
print("eligible", len(eligible))
""",
    "Schedule Candidate Interviews": """
import mcp_tools.google_calendar as gcal
import mcp_tools.jira as jira
import mcp_tools.slack as slack

ticket = jira.create_ticket(
    project="RECR",
    summary="Schedule interviews: candidate@example.com (Backend Engineer)",
    priority="High",
)
event_ids = []
for email in ["interviewer1@company.com", "interviewer2@company.com"]:
    event = gcal.create_event(
        email=email,
        title="Interview: candidate@example.com",
        start_time="2026-01-20T10:00:00",
        end_time="2026-01-20T11:00:00",
    )
    event_ids.append(event["id"])
slack.post_message(
    channel="#recruiting",
    message=f"Scheduled interviews ({len(event_ids)}) for candidate@example.com. Ticket {ticket}.",
)
print("ticket", ticket)
print("events", len(event_ids))
""",
    "Create Purchase Request": """
import mcp_tools.jira as jira
import mcp_tools.slack as slack

ticket = jira.create_ticket(
    project="PROC",
    summary="Purchase request: Laptop for Engineering ($2500)",
    priority="High",
)
slack.post_message(channel="#procurement", message=f"New purchase request: {ticket}. Please review.")
print("ticket", ticket)
""",
    "Candidate Pipeline Review": """
import mcp_tools.candidate_tracker as tracker
import mcp_tools.slack as slack

candidates = tracker.list_candidates(stage="Technical", status="In-progress")
lines = []
for c in candidates:
    lines.append(f"- {c['name']} ({c['role']}) - Source: {c['source']}")

report = "Technical Interview Pipeline:\\n" + "\\n".join(lines) if lines else "No candidates in Technical stage."
slack.post_message(channel="#recruiting", message=report)
print("count", len(candidates))
""",
}


SCENARIOS: list[Scenario] = [
    Scenario(
        name="Daily new hires digest",
        expected_action="execute_skill",
        expected_skill="Daily New Hires Digest",
        expected_skill_group="HR-scopes",
        user_requests=[
            "Run the daily new hires digest for today",
            "Post a new hires summary in #hr",
        ],
        required_code_patterns=[
            r"import mcp_tools\.bamboo_hr",
            r"import mcp_tools\.slack",
            r"get_todays_hires\(",
            r"slack\.post_message\(",
        ],
        required_log_patterns=[
            r"\[Slack\] Posted in #hr:",
            r"count 3",
        ],
        required_response_keywords=["completed", "daily new hires digest"],
    ),
    Scenario(
        name="Onboard new hires",
        expected_action="execute_skill",
        expected_skill="Onboard New Hires",
        expected_skill_group="HR-scopes",
        user_requests=[
            "Onboard today's new hires",
            "Create IT onboarding tickets and DM new hires",
        ],
        required_code_patterns=[
            r"import mcp_tools\.bamboo_hr",
            r"import mcp_tools\.jira",
            r"import mcp_tools\.slack",
            r"jira\.create_ticket\(",
            r"slack\.send_dm\(",
        ],
        required_log_patterns=[
            r"\[Jira\] Created ticket IT-",
            r"\[Slack\] Sent DM to",
            r"tickets 3",
        ],
        required_response_keywords=["completed", "onboard new hires"],
    ),
    Scenario(
        name="Probation check-in reminders",
        expected_action="execute_skill",
        expected_skill="Probation Check-in Reminders",
        expected_skill_group="HR-scopes",
        user_requests=[
            "Send probation check-in reminders",
            "Who needs a 90-day check-in this week? Notify managers",
        ],
        required_code_patterns=[
            r"get_probation_checkins\(",
            r"jira\.create_ticket\(",
            r"slack\.send_dm\(",
        ],
        required_log_patterns=[
            r"\[Jira\] Created ticket PEOPLE-",
            r"tickets 1",
        ],
        required_response_keywords=["completed", "probation check-in reminders"],
    ),
    Scenario(
        name="Offboard employee",
        expected_action="execute_skill",
        expected_skill="Offboard Employee",
        expected_skill_group="HR-scopes",
        user_requests=[
            "Offboard Maya Lopez effective today",
            "Start offboarding for Maya and notify her manager",
        ],
        required_code_patterns=[
            r"search_employees\(",
            r"mark_offboarding\(",
            r"jira\.create_ticket\(",
            r"slack\.send_dm\(",
        ],
        required_log_patterns=[
            r"status Offboarding \(",
            r"\[Jira\] Created ticket IT-",
        ],
        required_response_keywords=["completed", "offboard employee"],
    ),
    Scenario(
        name="Offboarding queue review",
        expected_action="execute_skill",
        expected_skill="Offboarding Queue Review",
        expected_skill_group="HR-scopes",
        user_requests=[
            "Review offboarding queue and create IT tickets",
            "Anyone currently offboarding that needs processing?",
        ],
        required_code_patterns=[
            r"list_employees\(",
            r'startswith\("Offboarding \("',
            r"jira\.create_ticket\(",
        ],
        required_log_patterns=[
            r"offboarding 1",
            r"tickets 1",
        ],
        required_response_keywords=["completed", "offboarding queue review"],
    ),
    Scenario(
        name="Role change access review",
        expected_action="execute_skill",
        expected_skill="Role Change + Access Review",
        expected_skill_group="HR-scopes",
        user_requests=[
            "Role change: update Charlie Davis role and start access review",
            "Create an access review ticket for Charlie after role update",
        ],
        required_code_patterns=[
            r"update_employee\(",
            r"jira\.create_ticket\(",
            r"Access review",
        ],
        required_log_patterns=[
            r"role Senior DevOps Engineer",
            r"\[Jira\] Created ticket IT-",
        ],
        required_response_keywords=["completed", "role change + access review"],
    ),
    Scenario(
        name="Leave and absence logistics",
        expected_action="execute_skill",
        expected_skill="Leave & Absence Management",
        expected_skill_group="HR-scopes",
        user_requests=[
            "Set OOO calendar and email auto-reply for Alice next week",
            "Approved leave: block calendar and notify team for Alice",
        ],
        required_code_patterns=[
            r"import mcp_tools\.google_calendar",
            r"import mcp_tools\.gmail",
            r"gcal\.create_event\(",
            r"gmail\.set_auto_responder\(",
            r"slack\.post_message\(",
        ],
        required_log_patterns=[
            r"event evt_",
            r"auto True",
            r"\[Slack\] Posted in #engineering:",
        ],
        required_response_keywords=["completed", "leave & absence management"],
    ),
    Scenario(
        name="Performance review cycle kickoff",
        expected_action="execute_skill",
        expected_skill="Performance Review Cycle",
        expected_skill_group="HR-scopes",
        user_requests=[
            "Kick off a Q4 performance review cycle and notify eligible employees",
            "Start quarterly reviews; find eligible employees and DM them",
        ],
        required_code_patterns=[
            r"import mcp_tools\.lattice",
            r"lattice\.create_cycle\(",
            r"get_eligible_employees\(",
            r"slack\.send_dm\(",
        ],
        required_log_patterns=[
            r"cycle cycle_",
            r"eligible 2",
        ],
        required_response_keywords=["completed", "performance review cycle"],
    ),
    Scenario(
        name="Schedule candidate interviews",
        expected_action="execute_skill",
        expected_skill="Schedule Candidate Interviews",
        expected_skill_group="Recruitment-scopes",
        user_requests=[
            "Schedule interviews for candidate@example.com next Tuesday at 10am",
            "Coordinate interviews for a Backend Engineer candidate and notify #recruiting",
        ],
        required_code_patterns=[
            r"import mcp_tools\.google_calendar",
            r"import mcp_tools\.jira",
            r"import mcp_tools\.slack",
            r"jira\.create_ticket\(",
            r"gcal\.create_event\(",
            r"slack\.post_message\(",
        ],
        required_log_patterns=[
            r"\[Jira\] Created ticket RECR-",
            r"\[Slack\] Posted in #recruiting:",
            r"events 2",
        ],
        required_response_keywords=["completed", "schedule candidate interviews"],
    ),
    Scenario(
        name="Create purchase request",
        expected_action="execute_skill",
        expected_skill="Create Purchase Request",
        expected_skill_group="Procurement-scopes",
        user_requests=[
            "Create a purchase request for a laptop for Engineering",
            "Open a procurement ticket for a $2500 laptop and notify #procurement",
        ],
        required_code_patterns=[
            r"import mcp_tools\.jira",
            r"import mcp_tools\.slack",
            r"jira\.create_ticket\(",
            r"slack\.post_message\(",
        ],
        required_log_patterns=[
            r"\[Jira\] Created ticket PROC-",
            r"\[Slack\] Posted in #procurement:",
        ],
        required_response_keywords=["completed", "create purchase request"],
    ),
    Scenario(
        name="Candidate Pipeline Review",
        expected_action="execute_skill",
        expected_skill="Candidate Pipeline Review",
        expected_skill_group="Recruitment-scopes",
        user_requests=[
            "Who is in the technical interview stage? Send a summary to #recruiting.",
            "Review the technical interview pipeline and notify #recruiting.",
        ],
        required_code_patterns=[
            r"import mcp_tools\.candidate_tracker",
            r"import mcp_tools\.slack",
            r"tracker\.list_candidates\(stage=\"Technical\"",
            r"slack\.post_message\(",
        ],
        required_log_patterns=[
            r"count [1-9]",
        ],
        required_response_keywords=["completed", "candidate pipeline review"],
    ),
    Scenario(
        name="Profile update reminder for new hires",
        expected_action="custom_script",
        expected_skill=None,
        expected_skill_group=None,
        user_requests=[
            "ask the new hires to visit the internal site internal.example.com/profile/<employee_id> to update their employee profile",
        ],
        required_code_patterns=[
            r"import mcp_tools\.bamboo_hr",
            r"import mcp_tools\.slack",
            r"get_todays_hires\(",
            r"internal\.example\.com/profile/",
            r"slack\.send_dm\(",
        ],
        required_log_patterns=[
            r"\[Slack\] Sent DM to",
            r"count 3",
        ],
        required_response_keywords=["completed", "profile"],
    ),
]


def _build_request_to_scenario() -> dict[str, Scenario]:
    mapping: dict[str, Scenario] = {}
    for s in SCENARIOS:
        for r in s.user_requests:
            mapping[r] = s
    return mapping


@pytest.mark.parametrize(
    "scenario,user_request",
    [
        (scenario, r)
        for scenario in SCENARIOS
        for r in scenario.user_requests
    ],
)
def test_hr_scopes_scenarios_pass_heuristic_qualitative_evaluation(monkeypatch, scenario: Scenario, user_request: str):
    request_to_scenario = _build_request_to_scenario()

    def fake_workflow_plan(*, user_message: str, skills_readme: str, skill_names: list[str], skill_groups: list[str]) -> dict:
        s = request_to_scenario[user_message]
        if s.expected_action == "custom_script":
            return {
                "action": "custom_script",
                "skill_group": None,
                "skill_name": "Profile update reminder",
                "intent": "Prompt new hires to update their employee profile",
                "steps": [
                    "Fetch today's new hires via BambooHR.",
                    "For each hire, compose the internal profile URL and send a Slack DM.",
                    "Print a final summary including the number of hires messaged.",
                ],
            }

        skill_name = s.expected_skill
        group = s.expected_skill_group
        return {
            "action": "execute_skill",
            "skill_group": group,
            "skill_name": skill_name,
            "intent": f"Resolve request using {skill_name}",
            "steps": ["follow skill logic flow"],
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
        plan = json.loads(plan_json)
        action = plan.get("action")
        if action == "custom_script":
            code = """
import mcp_tools.bamboo_hr as bamboo
import mcp_tools.slack as slack

hires = bamboo.get_todays_hires()
for e in hires:
    url = f"internal.example.com/profile/{e['id']}"
    slack.send_dm(user_id=e["slack_id"], message=f\"Please update your employee profile: {url}\")
print("count", len(hires))
"""
            return "```python\n" + code.strip() + "\n```"

        skill_name = plan.get("skill_name")
        code = CODE_BY_SKILL[skill_name]
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
        plan = json.loads(plan_json)
        if plan.get("action") == "custom_script":
            return "Completed: Profile update reminder."
        skill_name = plan.get("skill_name")
        return f"Completed: {skill_name}."

    def fake_workflow_plan_review(*, user_message: str, proposed_plan_json: str, selected_skill_md: str) -> dict:
        return json.loads(proposed_plan_json)

    monkeypatch.setattr(agent_module, "workflow_plan", fake_workflow_plan)
    monkeypatch.setattr(agent_module, "workflow_plan_review", fake_workflow_plan_review)
    monkeypatch.setattr(agent_module, "workflow_codegen", fake_workflow_codegen)
    monkeypatch.setattr(agent_module, "workflow_respond", fake_workflow_respond)

    run = run_scenario(scenario=scenario, user_request=user_request)

    assert run.plan.get("action") == scenario.expected_action
    if scenario.expected_action == "execute_skill":
        assert run.plan.get("skill_group") == scenario.expected_skill_group

    verdict = evaluate_with_judge(judge=HeuristicJudge(), scenario=scenario, run=run)
    assert verdict.passed, "; ".join(verdict.notes)
