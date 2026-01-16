## Goal
- Add `Recruitment-scopes` and `Procurement-scopes` under `agent_workspace/skills_v2`.
- Ensure the agent can (1) discover skills across multiple scope groups and (2) emit the correct `skill_group` in `plan_json`.
- Validate in 2 tiers: unit tests + scenario (LLM-as-judge) tests.

## Required Agent Changes (To Support Multiple Scopes)
- Generalize skill discovery so `skills_v2/*/examples/*.md` are discoverable (not just HR-scopes).
- Generalize `skill_group` inference so it returns the top-level folder name under `skills_v2/` (e.g., `Recruitment-scopes`, `Procurement-scopes`, `HR-scopes`).
- Keep tool contracts/imports as-is (still sourced from `HR-scopes/tools`) so the new scope examples can reuse existing mocked tools (`jira`, `slack`, `gmail`, `google_calendar`).

## New Content (Scopes + Example Skills)
- Add group descriptors (non-executable):
  - `skills_v2/Recruitment-scopes/SKILL.md`
  - `skills_v2/Procurement-scopes/SKILL.md`
  These will be ignored by the registry as executable skills (same concept as `HR-scopes/SKILL.md`).
- Add example skills (executable):
  - `Recruitment-scopes/examples/`:
    - “Schedule Candidate Interviews” (Calendar + Slack + Jira)
    - “Offer Approval & Send” (Jira + Gmail + Slack)
  - `Procurement-scopes/examples/`:
    - “Create Purchase Request” (Jira + Slack)
    - “Vendor Onboarding Request” (Jira + Gmail + Slack)
  Each example will include `## Logic Flow` with numbered steps so plan alignment is deterministic.
- Update `skills_v2/Readme.md` to list the two new groups and their example skills.

## Testing (2 Tiers)
### Tier 1: Unit Tests (Fast, Deterministic)
- Add/extend unit tests to verify the new scope groups work end-to-end at the code level:
  - `SkillRegistry.list_skills()` returns the new Recruitment/Procurement example skill titles.
  - Each new example has non-empty `_extract_logic_flow_steps()`.
  - `_infer_skill_group()` returns the correct group for a selected skill path.
- Implementation approach:
  - Extend the existing discoverability test currently focused on HR-scopes (`tests/test_hr_scopes_new_tools_and_examples.py`) or add a parallel test file that asserts the new skills are discoverable and have logic flow steps.

### Tier 2: Scenario + LLM-as-Judge Tests (Qualitative)
- Extend the existing scenario suite (`tests/test_hr_scopes_scenario_requests.py`) to include Recruitment + Procurement scenarios.
- Update the scenario harness/types (`tests/utils/scenario_harness.py`) so each scenario declares an `expected_skill_group`, and the assertions validate `plan.skill_group` accordingly.
- Ensure two scenario modes remain:
  - Heuristic judge (always-on, deterministic) remains as the default gate.
  - LLM judge (OpenRouter) remains gated behind env vars (already implemented) and will now also run the new scenarios when configured.

## Files Expected to Change / Add
- Modify:
  - `agent_workspace/hr_agent_v2/skill_registry.py` (discover all `*/examples/*.md`; ignore `*-scopes/SKILL.md` group files)
  - `agent_workspace/hr_agent_v2/agent.py` (`_infer_skill_group` generalized)
  - `agent_workspace/skills_v2/Readme.md`
  - `tests/utils/scenario_harness.py` (Scenario gets `expected_skill_group`)
  - `tests/test_hr_scopes_scenario_requests.py` (add new scenarios + group-aware assertion)
  - Unit test file(s) validating new scope discoverability and logic flow
- Add:
  - `agent_workspace/skills_v2/Recruitment-scopes/SKILL.md`
  - `agent_workspace/skills_v2/Recruitment-scopes/examples/*.md`
  - `agent_workspace/skills_v2/Procurement-scopes/SKILL.md`
  - `agent_workspace/skills_v2/Procurement-scopes/examples/*.md`

## Non-Goals (Optional Follow-up)
- Per-scope tool packages + per-scope MCP docs loading (right now all scopes share the existing mocked tool contracts from HR-scopes).