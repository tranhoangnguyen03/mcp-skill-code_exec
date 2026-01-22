function WorkflowCodegen(
  user_message: string,
  plan_json: string,
  skill_md: string,
  tool_contracts: string,
  attempt: int,
  previous_error: string,
  previous_code: string,
  conversation_history: string
) -> string {
  client OpenRouterChat
  prompt #"
Write a complete, runnable Python script that fulfills the user request by strictly following the steps in the provided Plan JSON.

### Inputs:
- User request: {{ user_message }}
- Plan JSON: {{ plan_json }}
- Skill manual (SKILL.md): {{ skill_md }}
- Tool contracts: {{ tool_contracts }}

Conversation history (most recent last):
{{ conversation_history }}

### Implementation Rules:
1. STRICT ADHERENCE: Follow the steps in the Plan JSON exactly. Do not add steps or skip steps.
2. PROGRESSIVE LOGGING: Print clear [INFO] or [PROGRESS] lines for each major step so the user can see what the agent is doing in real-time.
3. ERROR HANDLING: Be defensive. Check tool outputs and handle cases where no matches are found (e.g. employee search). Print clear [ERROR] messages and exit with code 1 on fatal issues.
4. DETERMINISM: If multiple items match a search, use a logical tie-breaker (e.g. exact name match) and print which one was chosen.
5. NO PLACEHOLDERS: All code must be complete and runnable.

### Multi-Turn / Continuation Support:
If the Plan JSON has `requires_lookahead: true`:
- For CHECKPOINT steps (steps that discover information for downstream use):
  - After completing the lookup/action, emit a fact using: `print("CONTINUE_FACT: <key>=<value>")`
  - Example: `print("CONTINUE_FACT: expert_domain=DevOps")`
  - Example: `print("CONTINUE_FACT: employee_name=Charlie Davis")`
  - After emitting the fact, print `print("CONTINUE_WORKFLOW: checkpoint_complete")` and exit with code 0
  - This signals the agent to pause, store the fact, and continue in the next turn

- For FINAL steps (steps that use the discovered information):
  - Read facts from the conversation context (they will be provided in the prompt as context)
  - Use the stored facts to complete the workflow
  - Do NOT emit CONTINUE signals - this is the final step

If the Plan JSON has `requires_lookahead: false`:
- Execute all steps normally and print "=== FINAL SUMMARY ===" at the end

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

function WorkflowRespond(
  user_message: string,
  plan_json: string,
  executed_code: string,
  exec_stdout: string,
  exec_stderr: string,
  exit_code: int,
  attempts: int,
  conversation_history: string
) -> string {
  client OpenRouterChat
  prompt #"
You are the assistant voice for a workflow automation agent.

Conversation history (most recent last):
{{ conversation_history }}

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
