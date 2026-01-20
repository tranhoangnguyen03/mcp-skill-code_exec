# Skill & Scope Reference

> **Purpose**: This document is the authoritative index for the planner. Use it to determine whether a user request maps to a pre-written skill or requires a custom script.

---

## Decision Criteria: Skill vs Custom Script

**Choose `execute_skill` when:**
- The request matches a skill's core purpose
- The user wants the skill's full workflow (e.g., tickets + notifications + calendar)
- The skill name or description closely aligns with the user's intent

**Choose `custom_script` when:**
- The request is a one-off query or ad-hoc task
- The user wants only a subset of what a skill does
- No skill covers the requested action
- The request is exploratory (e.g., "list all...", "search for...", "who is...")

**Key principle**: Do not select a skill if it would perform significant actions the user didn't request. Prefer `custom_script` for minimal, targeted operations.

For custom script implementation guidelines, see [custom_skill.md](./custom_skill.md).

---

## Supported Scopes

### HR-scopes

**Domain**: Employee lifecycle management—onboarding, offboarding, leave, role changes, performance reviews.

**Available Tools**:
- **BambooHR** — Employee records, hire dates, departments
- **Gmail** — Email and auto-responders
- **Google Calendar** — Meeting scheduling, OOO events
- **Jira** — IT/HR ticket creation and tracking
- **Lattice** — Performance review workflows
- **Slack** — Notifications, DMs, channel posts
- **Candidate Tracker** — New hire pipeline data

**Skills** (use when request matches the full workflow):

- **Onboard New Hires** — Full onboarding: fetch hires → create tickets → schedule meetings → notify channels
- **Offboard Employee** — Full offboarding: revoke access → create IT ticket → notify manager
- **Offboarding Queue Review** — Review pending offboards and create necessary tickets
- **Leave & Absence Management** — Set OOO calendar + auto-reply + notify team
- **Role Change + Access Review** — Update role in system → trigger access review → notify stakeholders
- **Performance Review Cycle** — Kick off review cycle → notify eligible employees
- **Probation Check-in Reminders** — Send reminders for employees approaching probation milestones
- **Daily New Hires Digest** — Summarize today's new hires for a channel

---

### Recruitment-scopes

**Domain**: Candidate pipeline coordination—interview scheduling, feedback collection, stage updates.

**Available Tools**:
- **Candidate Tracker** — Candidate records, interview stages
- **Google Calendar** — Interview scheduling
- **Jira** — Recruitment task tracking
- **Slack** — Recruiter notifications, reminders

**Skills**:

- **Schedule Candidate Interviews** — Book interview slots with multiple interviewers + notify channel
- **Chase Interview Feedback** — Remind interviewers who haven't submitted feedback
- **Candidate Pipeline Review** — Summarize candidates by stage, flag stale pipelines

---

### Procurement-scopes

**Domain**: Purchase requests and vendor onboarding workflows.

**Available Tools**:
- **Google Calendar** — Kickoff meeting scheduling
- **Jira** — Purchase/vendor ticket tracking
- **Slack** — Procurement team notifications

**Skills**:

- **Create Purchase Request** — Submit purchase request → create Jira ticket → notify #procurement
- **Vendor Onboarding Request** — New vendor setup → schedule kickoff → notify stakeholders

---

## Quick Reference: All Skills by Scope

**HR-scopes:**
- Onboard New Hires
- Offboard Employee
- Offboarding Queue Review
- Leave & Absence Management
- Role Change + Access Review
- Performance Review Cycle
- Probation Check-in Reminders
- Daily New Hires Digest

**Recruitment-scopes:**
- Schedule Candidate Interviews
- Chase Interview Feedback
- Candidate Pipeline Review

**Procurement-scopes:**
- Create Purchase Request
- Vendor Onboarding Request

---

## When No Skill Matches

If the user request doesn't align with any skill above, select `action: custom_script`. The code generator will use [custom_skill.md](./custom_skill.md) guidelines to produce a minimal, targeted Python script using the scope's available tools.

**Examples of `custom_script` scenarios:**
- "List all employees in Engineering" → custom (just a query, no workflow)
- "DM the new hires a link" → custom (subset of onboarding)
- "Search for employees named Chen" → custom (exploratory)
- "Create two Jira tickets" → custom (direct tool usage)
