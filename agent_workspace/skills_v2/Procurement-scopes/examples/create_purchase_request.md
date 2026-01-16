# Skill: Create Purchase Request

## Description
This skill creates a purchase request ticket in Jira and posts a notification in Slack to kick off approvals.

## Dependencies
- mcp_tools.jira
- mcp_tools.slack

## Inputs
- Requester name: `requester` (string, required)
- Department: `dept` (string, required)
- Item description: `item` (string, required)
- Estimated cost: `estimated_cost` (string, required)
- Slack channel: `channel` (string, optional). Default: `#procurement`

## Action Steps
1. Create a Jira ticket to track the purchase request.
2. Post a Slack message with the request summary and ticket id.
3. Print a short summary (ticket id).

## Logic Flow
1. Create a Jira ticket in project `PROC` with a summary that includes requester, dept, item, and estimated_cost.
2. Post a Slack message to the channel with the created ticket id and the purchase details.
3. Print a final summary including the ticket id.

## Notes
- If any required field is missing, fail fast and do not create a ticket.

