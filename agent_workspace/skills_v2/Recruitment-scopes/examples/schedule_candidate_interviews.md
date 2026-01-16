# Skill: Schedule Candidate Interviews

## Description
This skill schedules candidate interviews by creating calendar events for interviewers and posting coordination updates in Slack. It also creates a tracking ticket in Jira.

## Dependencies
- mcp_tools.jira
- mcp_tools.google_calendar
- mcp_tools.slack

## Inputs
- Candidate email: `candidate_email` (string, required)
- Role / requisition: `role` (string, required)
- Interviewer emails: `interviewer_emails` (list of strings, required)
- Start time: `start_time` (string, required, ISO like `2026-01-20T10:00:00`)
- End time: `end_time` (string, required, ISO like `2026-01-20T11:00:00`)
- Slack channel: `channel` (string, optional). Default: `#recruiting`

## Action Steps
1. Create a Jira ticket to track the interview scheduling.
2. Create calendar events for each interviewer.
3. Post a Slack message summarizing the schedule and ticket id.
4. Print a short summary (ticket id and number of events created).

## Logic Flow
1. Create a Jira ticket in project `RECR` with a summary containing the candidate email and role.
2. For each interviewer email, call `google_calendar.create_event(email=..., title=..., start_time=..., end_time=...)`.
3. Post a coordination message in Slack via `slack.post_message(channel=..., message=...)` including the ticket id and time window.
4. Print a final summary including the created ticket id and event count.

## Notes
- If any required field is missing, fail fast with a clear error message and do not create partial artifacts.
- Keep messages concise and include the candidate email and role for traceability.

