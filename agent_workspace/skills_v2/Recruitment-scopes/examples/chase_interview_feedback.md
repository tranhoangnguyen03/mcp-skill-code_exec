# Skill: Chase Interview Feedback

## Description
This skill creates a Jira follow-up ticket to chase missing interview feedback and sends reminders in Slack.

## Dependencies
- mcp_tools.jira
- mcp_tools.slack

## Inputs
- Candidate email: `candidate_email` (string, required)
- Role / requisition: `role` (string, required)
- Interviewer Slack IDs: `interviewer_slack_ids` (list of strings, required)
- Slack channel: `channel` (string, optional). Default: `#recruiting`

## Action Steps
1. Create a Jira ticket to track the feedback chase.
2. DM each interviewer a short reminder with the candidate + role.
3. Post a summary in the recruiting channel with the ticket id.
4. Print a short summary (ticket id and number of DMs sent).

## Logic Flow
1. Create a Jira ticket in project `RECR` with a summary “Feedback needed: {candidate_email} ({role})”.
2. For each interviewer Slack ID, call `slack.send_dm(user_id=..., message=...)`.
3. Post a Slack message to the channel noting that reminders were sent and referencing the Jira ticket id.
4. Print a final summary including ticket id and DM count.

## Notes
- If there are zero interviewer Slack IDs, do not create the ticket; print a clear “no-op” message.
- Avoid spamming: only send one DM per interviewer per run.

