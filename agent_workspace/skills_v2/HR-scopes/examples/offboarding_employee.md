# Skill: Offboard Employee

## Description
This skill starts an offboarding workflow for an employee. It marks them as offboarding in BambooHR, creates a deprovision ticket, and notifies the manager.

## Dependencies
- mcp_tools.bamboo_hr
- mcp_tools.jira
- mcp_tools.slack

## Inputs
- Employee identifier:
  - Prefer `employee_id` if provided.
  - Otherwise use `bamboo_hr.search_employees(query)` with a name string.
- Offboarding effective date (optional): `effective_date` in `YYYY-MM-DD`. Default: today.

## Logic Flow
1. Identify the employee:
   - If `employee_id` is provided, call `bamboo_hr.get_employee(employee_id)`.
   - Else call `bamboo_hr.search_employees(query)` and disambiguate as in the role-change skill.
2. Mark offboarding in BambooHR:
   - `updated = bamboo_hr.mark_offboarding(employee_id, effective_date=effective_date)`
   - This sets `updated["status"]` to `Offboarding (<date>)`.
3. Create a Jira ticket in project `IT`:
   - `priority="High"`
   - `summary` includes the employee name and effective date.
   - Optionally add a comment checklist using `jira.add_comment(ticket_id, ...)`.
4. Notify the manager via Slack:
   - `slack.send_dm(user_id=updated["manager_slack_id"], message=...)`
5. Print a final summary with employee status and ticket id.
