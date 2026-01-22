function WorkflowPlan(user_message: string, skills_readme: string, skill_names: string[], skill_groups: string[], conversation_history: string) -> Plan {
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

### Multi-Turn Detection (requires_lookahead)

CRITICAL: Set `requires_lookahead` to `true` when:
- The request requires looking up external data (e.g., employee info, candidate records, domain expertise) before deciding on subsequent actions.
- The request mentions an entity (person, team, department) that needs discovery of its properties (domain, manager, lead, etc.) to proceed.
- The workflow involves multiple logical stages where the output of stage N is required to define the parameters of stage N+1.

Examples where `requires_lookahead` MUST be TRUE:
- "Assign Mr.Davis to interview candidates in his domain" -> TRUE (Need Mr. Davis's domain first)
- "Find the manager of the employee in dept X and send them a message" -> TRUE (Need to find the employee and then their manager)
- "Schedule a meeting with the lead of the DevOps team" -> TRUE (Need to find the lead's identity first)
- "Send a follow-up to all candidates who interviewed yesterday" -> TRUE (Need to find candidates who interviewed yesterday first)

Examples where `requires_lookahead` should be FALSE:
- "List all employees in Engineering" -> FALSE (Direct query)
- "Send a DM to Alice Chen" -> FALSE (Direct action with known target)
- "Create a ticket for onboarding" -> FALSE (Direct action)

When `requires_lookahead` is true:
- Set `checkpoints` to list the specific discovery steps (e.g., ["lookup_davis_expertise", "search_domain_candidates"]).
- Ensure `steps` reflects the full high-level sequence of the workflow.
- The first step or checkpoint MUST be the information gathering task.

Conversation history (most recent last):
{{ conversation_history }}

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

function WorkflowPlanReview(user_message: string, proposed_plan_json: string, selected_skill_md: string, conversation_history: string) -> Plan {
  client OpenRouterChat
  prompt #"
You are a careful plan reviewer for a workflow automation agent.

You are given:
- The user request
- The proposed plan JSON (possibly selecting a known skill)
- The selected skill manual content (if any)
- Conversation history

Your job is to decide whether the proposed plan is appropriate, minimal, and correctly identifies if multi-turn lookahead is required.

CRITICAL RULES:
1. If the request requires discovering information (like a person's domain, a manager, or a list of specific candidates) before performing the main action, `requires_lookahead` MUST be `true`.
2. If `requires_lookahead` is `true`, `checkpoints` must contain the discovery steps.

Example Review:
User: "Assign Mr. Davis to his domain's candidates"
Proposed Plan: { "requires_lookahead": false, ... }
Review: This is INCORRECT. It needs `requires_lookahead: true` because Mr. Davis's domain must be looked up first.

{{ conversation_history }}

User message:
{{ user_message }}

Proposed Plan JSON:
{{ proposed_plan_json }}

Skill Manual:
{{ selected_skill_md }}

{{ ctx.output_format }}
"#
}
