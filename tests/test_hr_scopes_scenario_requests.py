from __future__ import annotations

import json
import os
import re

import pytest

from tests.utils.qualitative_judge import HeuristicJudge, OpenRouterJudge, evaluate_with_judge
from tests.utils.scenario_harness import Scenario, run_scenario


class DeterministicScenarioAgentLLM:
    def __init__(self, *, request_to_skill: dict[str, str], code_by_skill: dict[str, str]):
        self.request_to_skill = request_to_skill
        self.code_by_skill = code_by_skill
        self._last_skill: str | None = None

    def chat(self, messages, temperature=0.2):
        content = messages[-1].content

        if "Return ONLY valid JSON" in content:
            user_request = content.split("User request:\n", 1)[1].split("\n\nSupported skills:", 1)[0].strip()
            skill_name = self.request_to_skill[user_request]
            self._last_skill = skill_name
            return json.dumps(
                {
                    "action": "execute_skill",
                    "skill_group": "HR-scopes",
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
}


SCENARIOS: list[Scenario] = [
    Scenario(
        name="Daily new hires digest",
        expected_skill="Daily New Hires Digest",
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
        expected_skill="Onboard New Hires",
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
        expected_skill="Probation Check-in Reminders",
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
        expected_skill="Offboard Employee",
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
        expected_skill="Offboarding Queue Review",
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
        expected_skill="Role Change + Access Review",
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
        expected_skill="Leave & Absence Management",
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
        expected_skill="Performance Review Cycle",
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
]


def _build_request_to_skill() -> dict[str, str]:
    mapping: dict[str, str] = {}
    for scenario in SCENARIOS:
        for r in scenario.user_requests:
            mapping[r] = scenario.expected_skill
    return mapping


@pytest.mark.parametrize(
    "scenario,user_request",
    [
        (scenario, r)
        for scenario in SCENARIOS
        for r in scenario.user_requests
    ],
)
def test_hr_scopes_scenarios_pass_heuristic_qualitative_evaluation(scenario: Scenario, user_request: str):
    llm = DeterministicScenarioAgentLLM(request_to_skill=_build_request_to_skill(), code_by_skill=CODE_BY_SKILL)
    run = run_scenario(llm=llm, scenario=scenario, user_request=user_request)

    assert run.plan.get("action") == "execute_skill"
    assert run.plan.get("skill_group") == "HR-scopes"

    verdict = evaluate_with_judge(judge=HeuristicJudge(), scenario=scenario, run=run)
    assert verdict.passed, "; ".join(verdict.notes)


@pytest.mark.integration
@pytest.mark.parametrize(
    "scenario,user_request",
    [(scenario, r) for scenario in SCENARIOS for r in scenario.user_requests],
)
def test_hr_scopes_scenarios_pass_openrouter_qualitative_evaluation_if_configured(
    scenario: Scenario, user_request: str
):
    if not os.getenv("open_router_api_key") or not os.getenv("open_router_model_name"):
        pytest.skip("OpenRouter judge not configured")

    llm = DeterministicScenarioAgentLLM(request_to_skill=_build_request_to_skill(), code_by_skill=CODE_BY_SKILL)
    run = run_scenario(llm=llm, scenario=scenario, user_request=user_request)
    verdict = evaluate_with_judge(judge=OpenRouterJudge(), scenario=scenario, run=run)
    assert verdict.passed, "; ".join(verdict.notes)
