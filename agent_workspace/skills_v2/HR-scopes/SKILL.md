---
name: hr-scopes
description: A set of scoped examples for common HR lifecycle workflows (onboarding, offboarding, leave management, performance reviews, etc.). Use this skill whenever asked to define, scope, or implement an HR workflow using BambooHR, Jira, Slack, and other enterprise tools.
license: Internal
---

## When to use this skill
Use this skill when the request involves:
- Onboarding new hires
- Offboarding employees
- Role/department changes that require access review
- Probation milestone check-ins and reminders
- Daily or periodic reporting on new hires
- Managing employee leave and absence logistics (OOO, Calendar, Email)
- Initiating and running performance review cycles
- Designing a consistent “scope” and workflow for HR automations

## How to use this skill
1. Identify the closest matching workflow scope from the user request.
2. Load the matching example from the `examples/` directory:
   - `examples/onboarding_new_hires.md`
   - `examples/offboarding_employee.md`
   - `examples/role_change_access_review.md`
   - `examples/probation_checkin_reminders.md`
   - `examples/daily_new_hires_digest.md`
   - `examples/leave_absence_workflow.md`
   - `examples/performance_review_cycle.md`
3. Follow the example’s structure for inputs, dependencies, and logic flow.
4. If the request is a variant, start from the closest example and adapt deterministically (explicit defaults, clear disambiguation, and a final summary).

## Tools
The agent can write custom Python scripts and call individual tools from a local `mcp_tools` package to perform custom HR tasks. Tool contracts are documented under `tools/mcp_docs`.

```
- [lattice.py](file:///Users/nguyen.tran/Documents/My%20Remote%20Vault/mcp-skill-code_exec/agent_workspace/tools/mcp_tools/lattice.py)
- [candidate_tracker.py](file:///Users/nguyen.tran/Documents/My%20Remote%20Vault/mcp-skill-code_exec/agent_workspace/tools/mcp_tools/candidate_tracker.py)

```

## Keywords
HR workflows, onboarding, offboarding, role change, access review, probation check-in, new hire digest, leave management, OOO, performance review, BambooHR, Jira, Slack, Google Calendar, Gmail, Lattice, candidate tracker
