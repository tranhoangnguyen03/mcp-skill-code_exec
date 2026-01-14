# Skill: Role Change + Access Review

## Description
This skill supports role/department changes. It updates the employee record and creates an access review Jira ticket.

## Dependencies
- mcp_tools.bamboo_hr
- mcp_tools.jira
- mcp_tools.slack

## Inputs
- Employee identifier:
  - Prefer `employee_id` if provided.
  - Otherwise use `bamboo_hr.search_employees(query)` with a name string.
- Updates:
  - `dept` (optional)
  - `role` (optional)

## Logic Flow
1. Identify the employee:
   - If `employee_id` is provided, call `bamboo_hr.get_employee(employee_id)`.
   - Else call `bamboo_hr.search_employees(query)`.
   - If multiple matches, prefer an exact (case-insensitive) name match; otherwise pick the first match and print the candidate list.
2. Update the employee:
   - Call `bamboo_hr.update_employee(employee_id, updates)`
   - Only send keys that exist in the tool: `dept`, `role`.
3. Create an access review ticket:
   - `ticket_id = jira.create_ticket(project="IT", summary="Access review for <name> (<old role> → <new role>)", priority="Medium")`
   - Optionally `jira.add_comment(ticket_id, "...")` with details (dept/role change).
4. Notify the manager:
   - `slack.send_dm(user_id=employee["manager_slack_id"], message=...)`
5. Print a final summary with the updated employee fields and ticket id.
