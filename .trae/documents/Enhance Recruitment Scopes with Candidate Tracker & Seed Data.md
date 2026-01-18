## Goal
- Enhance Recruitment and HR functionality by adding a `candidate_tracker` tool and realistic seed data for candidates.
- This allows the agent to handle "Progressive Disclosure" queries where it first discovers candidates in the pipeline before acting on them.

## Technical Implementation

### 1. Data Layer: `agent_workspace/data/recruiting/candidates.json`
- Create realistic candidate profiles with:
  - `id`, `name`, `email`, `role`, `stage` (e.g., Screening, Technical, On-site, Offer).
  - `status` (e.g., In-progress, Hired, Rejected).
  - `interview_history`: List of events with dates and interviewers.
  - `skills`: List of technical/soft skills.

### 2. Tool Layer: `mcp_tools/candidate_tracker.py`
- Implement CRUD operations using the `_data.py` loader:
  - `list_candidates(stage=None, status=None)`
  - `get_candidate(email_or_id)`
  - `search_candidates(query)`
  - `update_candidate_stage(email, new_stage)`
  - `add_interview_log(email, date, feedback_status)`

### 3. Documentation: `mcp_docs/candidate_tracker`
- Add `server.json` and `examples.md` for the new tool.
- Register it under `Recruitment-scopes` and optionally `HR-scopes`.

### 4. Workflow Example: `candidate_pipeline_review.md`
- Add a new skill example that uses the `candidate_tracker`:
  - Step 1: Fetch candidates in a specific stage.
  - Step 2: For each, check if an interview is scheduled.
  - Step 3: Notify recruiters or schedule follow-ups.

## Testing & Verification (2 Tiers)

### Tier 1: Unit Tests
- Create `tests/test_candidate_tracker.py` to verify:
  - Loading from JSON fixtures.
  - Date token expansion (e.g., `${TODAY}`).
  - Search and stage update logic.

### Tier 2: Scenario Tests (LLM-as-judge)
- Add a new scenario to `tests/test_hr_scopes_scenario_requests.py`:
  - **Scenario**: "Review Technical Pipeline"
  - **User Request**: "Who is in the technical interview stage? Send a summary to #recruiting."
  - **Expected Outcome**: Agent uses `candidate_tracker.list_candidates`, summarizes them, and posts to Slack.

## Backward Compatibility
- The `candidate_tracker` will be a new tool; existing examples that take candidate data as inputs will continue to work as-is.
- The new seed data will be isolated in its own folder.

Confirm if you would like me to proceed with this plan.