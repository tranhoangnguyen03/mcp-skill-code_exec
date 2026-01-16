# Skill: Vendor Onboarding Request

## Description
This skill creates a vendor onboarding ticket in Jira and schedules an internal kickoff meeting on the requester’s calendar.

## Dependencies
- mcp_tools.jira
- mcp_tools.google_calendar
- mcp_tools.slack

## Inputs
- Vendor name: `vendor_name` (string, required)
- Requester email: `requester_email` (string, required)
- Business justification: `justification` (string, required)
- Kickoff start time: `start_time` (string, required, ISO like `2026-01-20T15:00:00`)
- Kickoff end time: `end_time` (string, required, ISO like `2026-01-20T15:30:00`)
- Slack channel: `channel` (string, optional). Default: `#procurement`

## Action Steps
1. Create a Jira ticket to track vendor onboarding.
2. Create a kickoff calendar event for the requester.
3. Post a Slack message with the vendor name, ticket id, and event id.
4. Print a short summary (ticket id and event id).

## Logic Flow
1. Create a Jira ticket in project `PROC` with a summary “Vendor onboarding: {vendor_name}” and include justification.
2. Create a calendar event via `google_calendar.create_event(email=requester_email, title=..., start_time=..., end_time=...)`.
3. Post a Slack message to the channel referencing the Jira ticket id and the calendar event id.
4. Print a final summary including ticket id and event id.

## Notes
- Keep justification short in Slack; use the Jira ticket as the source of truth.

