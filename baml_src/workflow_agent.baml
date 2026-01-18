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

function WorkflowPlan(user_message: string, skills_readme: string, skill_names: string[]) -> Plan {
  client OpenRouterChat
  prompt #"
You are a workflow planner for a skill-based automation agent.

You must choose exactly one action:
- chat: respond conversationally; no workflows; no tools; no code.
- execute_skill: use a known skill from the provided skill names.
- custom_script: write a custom workflow using tools when no skill matches.

Prefer execute_skill when the user request clearly matches a known skill. Otherwise prefer chat for purely conversational requests.

When action is execute_skill:
- skill_name must be one of the provided skill names
- set skill_group if the scope is clear, otherwise leave it null
- steps should be concise, high-level, and executable

When action is chat:
- skill_name and skill_group must be null
- steps should be empty

When action is custom_script:
- skill_name may be null or a short label
- skill_group may be null
- steps should be concise, high-level, and executable

User message:
{{ user_message }}

Supported skills:
{{ skills_readme }}

Skill names:
{% for s in skill_names %}
- {{ s }}
{% endfor %}

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
