# Skill: Onboard New Hires

## Description
This skill automates basic onboarding steps for new hires. It creates an IT setup Jira ticket and sends a welcome message via Slack DM.

## Dependencies
- mcp_tools.bamboo_hr
- mcp_tools.jira
- mcp_tools.slack

## Inputs
- Date range (optional): `start_date`, `end_date` in `YYYY-MM-DD`. Default: today.
- Department filter (optional): `dept` (string). If provided, filter by exact match to `employee["dept"]`.
- Notify manager (optional): `notify_manager` (boolean). Default: true.

## Logic Flow
1. Fetch hires:
   - If no date range is provided, call `bamboo_hr.get_todays_hires()`.
   - If a date range is provided, call `bamboo_hr.get_new_hires(start_date, end_date)`.
2. If `dept` is provided, keep only employees where `employee["dept"] == dept`.
3. For each selected employee:
   1. Create a Jira ticket:
      - `project="IT"`
      - `priority="High"`
      - `summary` includes the employee name and basic onboarding tasks.
   2. Send a Slack DM to the employee:
      - `slack.send_dm(user_id=employee["slack_id"], message=...)`
   3. If `notify_manager` is true, DM the manager:
      - `slack.send_dm(user_id=employee["manager_slack_id"], message=...)`
4. Print a final summary including the number of hires processed and created ticket ids.

## Notes
- `bamboo_hr` returns a list of dicts with keys: `id`, `name`, `dept`, `role`, `status`, `hire_date`, `manager`, `slack_id`, `manager_slack_id`.
- `employee["manager"]` is a plain string (manager name). Use `employee["manager_slack_id"]` to DM the manager.
- If there are no hires after filtering, do not create tickets. Print a clear "no-op" message.
