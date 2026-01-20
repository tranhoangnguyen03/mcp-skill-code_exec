enum PlanAction {
  Chat
  ExecuteSkill
  CustomScript
}

class Plan {
  action PlanAction
  skill_group string?
  skill_name string?
  intent string
  steps string[]
}

function WorkflowPlan(user_message: string, skills_readme: string, skill_names: string[], skill_groups: string[]) -> Plan {
  client OpenRouterChat
  prompt #"
You are a workflow planner for a skill-based automation agent.

You must choose exactly one action:
- chat: respond conversationally; no workflows; no tools; no code.
- execute_skill: use a known skill from the provided skill names.
- custom_script: write a custom workflow using tools when no skill matches.

Choose the action using this rubric:
- Prefer chat only for purely conversational requests with no desired tool actions.
- Prefer execute_skill ONLY when the user request requires the skill's core side-effects as described in the skill manual. Do not pick a skill just because the topic is related.
- Prefer custom_script when:
  - the user request is a strict subset of a known skill (e.g., only messaging, no ticketing/calendar/email), or
  - using a known skill would add major actions the user did not ask for, or
  - the user explicitly asks for minimal behavior (e.g., "just send them a message", "only do X").

When in doubt between execute_skill and custom_script, choose custom_script to minimize unintended side effects.

When action is execute_skill:
- skill_name must be one of the provided skill names
- set skill_group to the scope that contains the chosen skill, when possible
- steps should be concise, high-level, and executable

When action is chat:
- skill_name and skill_group must be null
- steps should be empty

When action is custom_script:
- skill_name may be null or a short label
- skill_group should be one of the provided skill groups when the scope is clear (prefer setting it)
- steps should be concise, high-level, and executable

User message:
{{ user_message }}

Supported skills:
{{ skills_readme }}

Skill names:
{% for s in skill_names %}
- {{ s }}
{% endfor %}

Skill groups:
{% for g in skill_groups %}
- {{ g }}
{% endfor %}

{{ ctx.output_format }}
"#
}

function WorkflowPlanReview(user_message: string, proposed_plan_json: string, selected_skill_md: string) -> Plan {
  client OpenRouterChat
  prompt #"
You are a careful plan reviewer for a workflow automation agent.

You are given:
- The user request
- The proposed plan JSON (possibly selecting a known skill)
- The selected skill manual content (if any)

Your job is to decide whether the proposed plan is appropriate and minimal.

Rules:
- Never add major side effects the user did not ask for.
- If the proposed plan selects a skill whose core actions (per the skill manual) are not explicitly required by the user request, change the action to custom_script.
- If you change to custom_script, keep the steps minimal and aligned to the user request.
- Keep chat only for purely conversational requests with no tool actions.

User request:
{{ user_message }}

Proposed plan JSON:
{{ proposed_plan_json }}

Selected skill manual:
{{ selected_skill_md }}

{{ ctx.output_format }}
"#
}

function WorkflowCodegen(
  user_message: string,
  plan_json: string,
  skill_md: string,
  tool_contracts: string,
  attempt: int,
  previous_error: string,
  previous_code: string
) -> string {
  client OpenRouterChat
  prompt #"
Write a complete, runnable Python script that fulfills the user request by strictly following the steps in the provided Plan JSON.

### Inputs:
- User request: {{ user_message }}
- Plan JSON: {{ plan_json }}
- Skill manual (SKILL.md): {{ skill_md }}
- Tool contracts: {{ tool_contracts }}

### Implementation Rules:
1. STRICT ADHERENCE: Follow the steps in the Plan JSON exactly. Do not add steps or skip steps.
2. PROGRESSIVE LOGGING: Print clear [INFO] or [PROGRESS] lines for each major step so the user can see what the agent is doing in real-time.
3. ERROR HANDLING: Be defensive. Check tool outputs and handle cases where no matches are found (e.g. employee search). Print clear [ERROR] messages and exit with code 1 on fatal issues.
4. DETERMINISM: If multiple items match a search, use a logical tie-breaker (e.g. exact name match) and print which one was chosen.
5. NO PLACEHOLDERS: All code must be complete and runnable.

### Constraints:
- Use only Python standard library plus the local package \"mcp_tools\".
- Import tool modules from \"mcp_tools\" (e.g. `import mcp_tools.bamboo_hr as bamboo_hr`).
- Do not use input(), sys.argv, or any interactive prompts.
- Print a clear \"=== FINAL SUMMARY ===\" at the end with key results.

Retry context (if any):
Attempt: {{ attempt }}
Previous error: {{ previous_error }}
Previous code: {{ previous_code }}

Return ONLY a single Python code block.
"#
}

function WorkflowChat(user_message: string, skills_readme: string, custom_skill_md: string) -> string {
  client OpenRouterChat
  prompt #"
You are a helpful chat assistant for a workflow automation agent.

When users ask about your capabilities (e.g., \"what can you do?\"), you must describe what THIS agent can do based on the provided repo documentation.

Supported skill groups and skills:
{{ skills_readme }}

Custom script manual:
{{ custom_skill_md }}

User message:
{{ user_message }}

Response requirements:
- Keep it brief and concrete (scopes, example tasks, and how custom scripts work).\n+- Do not claim capabilities outside the tools/scopes described above.\n+- If the user is not asking about capabilities, respond normally and briefly.
"#
}

function WorkflowRespond(
  user_message: string,
  plan_json: string,
  executed_code: string,
  exec_stdout: string,
  exec_stderr: string,
  exit_code: int,
  attempts: int
) -> string {
  client OpenRouterChat
  prompt #"
You are the assistant voice for a workflow automation agent.

User request:
{{ user_message }}

Plan JSON:
{{ plan_json }}

Executed code:
{{ executed_code }}

Execution stdout:
{{ exec_stdout }}

Execution stderr:
{{ exec_stderr }}

Exit code: {{ exit_code }}

Attempts: {{ attempts }}

Write a concise response to the user describing what was done and key outputs.
If there were errors, explain them and propose a fix.
"#
}
