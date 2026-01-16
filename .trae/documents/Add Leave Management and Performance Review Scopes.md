Based on your request to brainstorm additions to `HR-scopes`, I have identified two high-impact workflows that complement the existing onboarding/offboarding scopes. These additions introduce common HR automation patterns involving calendar management, communication, and performance tracking.

### 1. Leave & Absence Management
**Scope:** `leave_absence_workflow`
**Description:** Automates the logistics when an employee's leave request is approved. It ensures business continuity by updating calendars and setting auto-responders.
**Workflow:**
1.  Detect approved leave request (simulated input).
2.  Create an "Out of Office" event in the employee's calendar.
3.  Set a Gmail auto-responder for the duration.
4.  Post a notification in the team's Slack channel.
**New Tools to Mock:**
*   `google_calendar`: `create_event(email, start, end, title)`, `get_events(email, date)`.
*   `gmail`: `set_auto_responder(email, start, end, message)`.

### 2. Performance Review Cycle
**Scope:** `performance_review_cycle`
**Description:** Initiates the quarterly performance review process for eligible employees.
**Workflow:**
1.  Identify employees eligible for review (e.g., tenure > 3 months).
2.  Create a review cycle in the performance platform.
3.  Notify employees and managers via Slack to begin their self/peer assessments.
**New Tools to Mock:**
*   `lattice` (Performance Platform): `create_cycle(name, due_date)`, `get_eligible_employees(min_tenure_days)`.

### Implementation Plan
If you approve, I will:
1.  **Create Tool Mocks**:
    *   Implement `google_calendar.py`, `gmail.py`, and `lattice.py` in `tools/mcp_tools/`.
    *   Create corresponding documentation in `tools/mcp_docs/`.
    *   Update `tools/mcp_tools/__init__.py` to export these new tools.
2.  **Create Scope Examples**:
    *   Create `examples/leave_absence_workflow.md`.
    *   Create `examples/performance_review_cycle.md`.
3.  **Update Registry**:
    *   Add the new scopes to `HR-scopes/SKILL.md`.
