# Skill: Daily New Hires Digest

## Description
This skill posts a digest of new hires to a Slack channel (e.g. `#hr` or `#people-ops`).

## Dependencies
- mcp_tools.bamboo_hr
- mcp_tools.slack

## Inputs
- Date range (optional): `start_date`, `end_date` in `YYYY-MM-DD`. Default: today.
- Slack channel (optional): `channel` (string). Default: `#hr`.
- Department filter (optional): `dept` (string). If provided, filter by exact match to `employee["dept"]`.

## Logic Flow
1. Fetch hires:
   - If no date range is provided, call `bamboo_hr.get_todays_hires()`.
   - If a date range is provided, call `bamboo_hr.get_new_hires(start_date, end_date)`.
2. If `dept` is provided, filter hires by `employee["dept"]`.
3. Build a digest message:
   - If no hires, the message should say there are no new hires in that range.
   - Otherwise list each hire on its own line: name, dept, role, manager.
4. Post to Slack:
   - `slack.post_message(channel=channel, message=digest)`
5. Print a final summary including the channel and the number of hires included.

## Notes
- Use `slack.post_message(channel, message)`. The channel is a string (e.g. `#hr`).
