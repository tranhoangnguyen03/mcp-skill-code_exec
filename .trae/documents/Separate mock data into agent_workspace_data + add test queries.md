## What I See Today
- `bamboo_hr.py` embeds seed employee records directly in the module (`_EMPLOYEES = [...]`).
- Other tools keep mutable in-memory state in-module:
  - `jira`: `_SEQ`, `_TICKETS`
  - `slack`: `_MESSAGES`
  - `gmail`: `_SETTINGS`
  - `google_calendar`: `_EVENTS`
  - `lattice`: `_USERS`, `_CYCLES`

## Recommendation (Yes, Separate Data)
- Seed/mock data (fixtures) should live in `agent_workspace/data/`.
- Tool modules should contain behavior (CRUD logic), but load initial records from data files.
- For tools with purely runtime state (tickets/messages/events), keep in-memory state but optionally allow initializing from a seed file and/or resetting deterministically for tests.

## Implementation Plan
### 1) Create `agent_workspace/data/` structure
- Add `agent_workspace/data/README.md` describing:
  - seed fixtures vs runtime state
  - how to reset
- Add seed JSON (or YAML) fixtures:
  - `agent_workspace/data/bamboo_hr/employees.json`
  - `agent_workspace/data/lattice/users.json`
  - (optional) `agent_workspace/data/slack/messages.json` (seed empty)
  - (optional) `agent_workspace/data/jira/tickets.json` (seed empty)
  - (optional) `agent_workspace/data/google_calendar/events.json` (seed empty)
  - (optional) `agent_workspace/data/gmail/auto_responders.json` (seed empty)

### 2) Add a small shared loader utility
- Add `agent_workspace/skills_v2/HR-scopes/tools/mcp_tools/_data.py` that:
  - resolves the repo root reliably from `__file__`
  - reads JSON fixtures from `agent_workspace/data/...`
  - provides `load_json(path, default)` helpers

### 3) Refactor tools to use external seed fixtures
- `bamboo_hr.py`:
  - move `_EMPLOYEES` seed to `employees.json`
  - parse into dicts or dataclasses at import time
  - keep update operations in-memory (update_employee/mark_offboarding) but based on loaded seed
- `lattice.py`:
  - move `_USERS` seed to `users.json`
  - keep `_CYCLES` runtime in-memory
- For `jira/slack/gmail/google_calendar`:
  - keep existing runtime in-memory behavior (it’s useful for multi-step workflows)
  - optionally support loading an initial empty list/dict from `agent_workspace/data/...` (or leave hardcoded empty but documented)

### 4) Tests
- Unit tests:
  - add tests that fixtures load and tool behavior remains identical (same employee counts, same probation window results, etc.)
  - ensure updates (e.g., `mark_offboarding`) still work against the loaded dataset
- Scenario tests:
  - keep existing scenario suite as-is, ensuring behavior unchanged

### 5) Verification
- Run `pytest -q` and ensure all tests pass.

## Deliverable: Viable User Queries To Test The Agent
### HR-scopes (skill matches)
- “Onboard today’s new hires.”
- “Onboard today’s new hires in Engineering only.”
- “Onboard new hires from 2026-01-10 to 2026-01-17 and DM their managers.”
- “Offboard Maya Lopez effective today.”
- “Start offboarding for employee id 105 for 2026-02-01.”
- “Review offboarding queue and create IT tickets.”
- “Anyone currently offboarding that needs processing? Create tickets.”
- “Role change: update Charlie Davis to Senior DevOps Engineer and create an access review ticket.”
- “Change employee 103 dept to Platform and create an access review ticket.”
- “Send probation check-in reminders for the 90-day window.”
- “Send probation check-in reminders using a 60-day milestone.”
- “Set OOO calendar and auto-reply for alice@company.com next week and notify #engineering.”
- “Approved leave: block calendar for bob@company.com from 2026-02-10 to 2026-02-14 and notify #sales.”
- “Kick off a Q4 performance review cycle and notify eligible employees.”

### Recruitment-scopes (skill matches)
- “Schedule candidate interviews for candidate@example.com (Backend Engineer) with interviewer1@company.com and interviewer2@company.com, 2026-01-20 10:00–11:00. Notify #recruiting.”
- “Schedule interviews for candidate@example.com tomorrow 2–3pm with 3 interviewers and post to #recruiting.”
- “Chase interview feedback for candidate@example.com (Backend Engineer); remind U_ALICE and U_CHARLIE and post a summary in #recruiting.”

### Procurement-scopes (skill matches)
- “Create a purchase request: requester=Alice Chen, dept=Engineering, item=MacBook Pro, estimated cost=$2500. Notify #procurement.”
- “Open a procurement ticket for ‘Figma licenses (10 seats)’ for Design, $1200, notify #procurement.”
- “Vendor onboarding request: vendor=Acme Security, requester_email=alice@company.com, kickoff 2026-01-20 15:00–15:30, justification=security audit tool. Notify #procurement.”

### Tool-level / custom-script style queries (exercise CRUD + retrieval)
- “List all employees in BambooHR.”
- “Search employees for ‘Engineering Manager’ and show matches.”
- “Who are today’s hires? Summarize names and managers.”
- “Who has a work anniversary today?”
- “Show probation check-ins due this week.”
- “List Slack messages in #hr.”
- “Create a Jira ticket in IT and then fetch it back by id.”
- “Create two Jira tickets and then search open tickets in project IT.”
- “Transition a Jira ticket to Done and verify status.”
- “Create a calendar event for alice@company.com tomorrow and then list events for that date.”
- “Set a Gmail auto responder for bob@company.com and then read it back.”

### Edge / robustness queries
- “Offboard ‘Lee’ (ambiguous last name) effective today.”
- “Role change for a non-existent employee name; explain and do not create tickets.”
- “Set OOO but omit end date (should fail fast with clear error).”
- “Schedule interviews but omit interviewer list (should fail fast with clear error).”

If you approve, I’ll implement the data separation refactor (fixtures in `agent_workspace/data/`) and keep all existing behaviors/tests passing.