# Skill: Offboarding Queue Review

## Description
This skill finds employees already marked as offboarding and helps HR process the queue. It creates IT offboarding tickets for any pending offboarding employees and notifies the manager.

## Dependencies
- mcp_tools.bamboo_hr
- mcp_tools.jira
- mcp_tools.slack

## Inputs
- Offboarding status filter (optional): `status_prefix` (string). Default: `Offboarding (` which matches BambooHR `mark_offboarding`.
- Jira project (optional): `project` (string, default: `IT`)

## Action Steps
1. Fetch all employees from BambooHR.
2. Filter employees whose status indicates offboarding.
3. For each offboarding employee, create an IT offboarding Jira ticket.
4. DM the employee’s manager with the ticket reference.
5. Print a short summary with counts and ticket ids.

## Logic Flow
1. List employees:
   - Call `bamboo_hr.list_employees()`.
2. Filter offboarding employees:
   - Keep employees where `employee["status"]` starts with `status_prefix`.
3. For each offboarding employee:
   - Create a Jira ticket: `jira.create_ticket(project=project, summary=..., priority="High")`.
   - DM the manager: `slack.send_dm(user_id=employee["manager_slack_id"], message=...)`.
4. Print a final summary including employee count and created ticket ids.
