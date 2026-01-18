# Skill: Candidate Pipeline Review

## Description
This skill provides a summary of candidates currently in the recruiting pipeline. It can filter by stage and status, and posts a summary report to Slack.

## Dependencies
- mcp_tools.candidate_tracker
- mcp_tools.slack

## Inputs
- `stage` (optional): The interview stage to filter by (e.g., "Screening", "Technical", "On-site", "Offer").
- `status` (optional): The candidate status to filter by (default: "In-progress").
- `channel` (optional): The Slack channel to post the summary to (default: "#recruiting").

## Action Steps
1. Fetch candidates from the tracker based on filters.
2. Format a summary message listing names, roles, and current stages.
3. Post the summary message to the specified Slack channel.
4. Print a short summary of how many candidates were processed.

## Logic Flow
1. Fetch candidates:
   - Call `candidate_tracker.list_candidates(stage=stage, status=status)`.
2. Format report:
   - If no candidates found, the report should say "No candidates found matching the filters."
   - Otherwise, list each candidate with their name, role, and source.
3. Post to Slack:
   - Call `slack.post_message(channel=channel, message=...)`.
4. Print summary:
   - Print "Reported {count} candidates to {channel}."

## Notes
- This skill is useful for weekly recruiting syncs or daily pipeline health checks.
- If multiple stages are requested, the agent may need to call `list_candidates` multiple times or fetch all and filter in Python.
