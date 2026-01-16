# Skill: Leave & Absence Management

## Description
This skill automates the logistics when an employee's leave request is approved. It ensures business continuity by updating calendars and setting auto-responders.

## Dependencies
- mcp_tools.google_calendar
- mcp_tools.gmail
- mcp_tools.slack

## Inputs
- Employee Email: `email` (string).
- Start Date: `start_date` (YYYY-MM-DD).
- End Date: `end_date` (YYYY-MM-DD).
- Reason/Title (optional): `reason` (string). Default: "Out of Office".
- Team Channel (optional): `team_channel` (string). Default: "#general".

## Action Steps
1. Create an "Out of Office" event in the employee's calendar.
2. Set a Gmail auto-responder for the duration.
3. Post a notification in the team's Slack channel.
4. Print a summary of actions taken.

## Logic Flow
1. **Calendar Event**:
   - Call `google_calendar.create_event`:
     - `email`: `email`
     - `title`: `reason`
     - `start_time`: `start_date` + "T09:00:00"
     - `end_time`: `end_date` + "T17:00:00"

2. **Email Auto-Responder**:
   - Call `gmail.set_auto_responder`:
     - `email`: `email`
     - `start_date`: `start_date`
     - `end_date`: `end_date`
     - `message`: f"I am out of the office from {start_date} to {end_date}."

3. **Slack Notification**:
   - Call `slack.post_message`:
     - `channel`: `team_channel`
     - `message`: f"FYI: {email} will be OOO from {start_date} to {end_date}."

4. **Summary**:
   - Print "Processed leave for {email}: Calendar blocked, Auto-reply set, Team notified."

## Notes
- Ensure dates are valid strings.
- The workflow assumes the leave is already approved; this automation handles the *logistics* of the leave.
