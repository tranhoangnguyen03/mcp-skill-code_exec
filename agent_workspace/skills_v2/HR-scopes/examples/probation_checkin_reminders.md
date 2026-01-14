# Skill: Probation Check-in Reminders

## Description
This skill finds employees who are approaching a probation milestone and reminds managers to complete a check-in.

## Dependencies
- mcp_tools.bamboo_hr
- mcp_tools.jira
- mcp_tools.slack

## Inputs
- `days_since_hire` (integer, default: 90)
- `window_days` (integer, default: 7)
- Jira project (optional): `project` (string, default: `PEOPLE`)

## Logic Flow
1. Fetch employees in the check-in window:
   - `employees = bamboo_hr.get_probation_checkins(days_since_hire=days_since_hire, window_days=window_days)`
2. For each employee:
   1. Create a Jira ticket:
      - `ticket_id = jira.create_ticket(project=project, summary="Probation check-in: <name>", priority="Low")`
      - Optionally add a comment specifying the target day and window.
   2. Slack DM the manager:
      - `slack.send_dm(user_id=employee["manager_slack_id"], message=...)`
3. If there are no employees in the window, print a clear no-op summary.
