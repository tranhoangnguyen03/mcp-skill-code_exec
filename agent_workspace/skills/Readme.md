# Supported Skills

Each skill folder contains a `SKILL.md` (or `SKILLS.md`) manual. The agent selects one skill, generates Python code using `mcp_tools`, executes it, then summarizes the result.

## Skills

1. `onboarding_new_hires`
   - Finds new hires in a date range (default: today)
   - Creates IT setup Jira tickets and welcomes hires via Slack DM

2. `daily_new_hires_digest`
   - Posts a daily digest of new hires to a Slack channel

3. `role_change_access_review`
   - Updates an employee’s department/role in BambooHR
   - Creates an access review Jira ticket and notifies the manager

4. `offboarding_employee`
   - Marks an employee as offboarding in BambooHR
   - Creates an IT deprovision Jira ticket and notifies the manager

5. `probation_checkin_reminders`
   - Finds employees near a probation milestone and creates check-in tickets
   - Notifies managers via Slack DM

## Tool Contracts (What the code can call)

The skill manuals assume these tool functions exist and behave as documented:

- `mcp_tools.bamboo_hr`
  - `get_todays_hires() -> list[dict]`
  - `get_new_hires(start_date: str | None, end_date: str | None) -> list[dict]`
  - `search_employees(query: str) -> list[dict]`
  - `get_employee(employee_id: int) -> dict | None`
  - `update_employee(employee_id: int, updates: dict) -> dict`
  - `mark_offboarding(employee_id: int, effective_date: str | None) -> dict`
  - `get_probation_checkins(days_since_hire: int = 90, window_days: int = 7) -> list[dict]`
  - Employee dict shape:
    - `id` (int), `name` (str), `dept` (str), `role` (str), `status` (str), `hire_date` (str, `YYYY-MM-DD`)
    - `manager` (str, manager name), `slack_id` (str), `manager_slack_id` (str)

- `mcp_tools.jira`
  - `create_ticket(project: str, summary: str, priority: str) -> str`
  - `add_comment(ticket_id: str, comment: str) -> None`

- `mcp_tools.slack`
  - `send_dm(user_id: str, message: str) -> None`
  - `post_message(channel: str, message: str) -> None`
