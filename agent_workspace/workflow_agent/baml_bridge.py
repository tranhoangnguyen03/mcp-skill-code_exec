from __future__ import annotations


def workflow_plan(*, user_message: str, skills_readme: str, skill_names: list[str]) -> dict:
    from baml_client.sync_client import b

    plan = b.WorkflowPlan(user_message=user_message, skills_readme=skills_readme, skill_names=skill_names)

    action = getattr(plan.action, "value", plan.action)
    action_map = {
        "Chat": "chat",
        "ExecuteSkill": "execute_skill",
        "CustomScript": "custom_script",
        "chat": "chat",
        "execute_skill": "execute_skill",
        "custom_script": "custom_script",
    }
    action_normalized = action_map.get(str(action), str(action))

    return {
        "action": action_normalized,
        "skill_group": plan.skill_group,
        "skill_name": plan.skill_name,
        "intent": plan.intent,
        "steps": list(plan.steps or []),
    }


def workflow_plan_review(*, user_message: str, proposed_plan_json: str, selected_skill_md: str) -> dict:
    from baml_client.sync_client import b

    plan = b.WorkflowPlanReview(
        user_message=user_message,
        proposed_plan_json=proposed_plan_json,
        selected_skill_md=selected_skill_md,
    )

    action = getattr(plan.action, "value", plan.action)
    action_map = {
        "Chat": "chat",
        "ExecuteSkill": "execute_skill",
        "CustomScript": "custom_script",
        "chat": "chat",
        "execute_skill": "execute_skill",
        "custom_script": "custom_script",
    }
    action_normalized = action_map.get(str(action), str(action))

    return {
        "action": action_normalized,
        "skill_group": plan.skill_group,
        "skill_name": plan.skill_name,
        "intent": plan.intent,
        "steps": list(plan.steps or []),
    }


def workflow_codegen(
    *,
    user_message: str,
    plan_json: str,
    skill_md: str,
    tool_contracts: str,
    attempt: int,
    previous_error: str,
    previous_code: str,
) -> str:
    from baml_client.sync_client import b

    return b.WorkflowCodegen(
        user_message=user_message,
        plan_json=plan_json,
        skill_md=skill_md,
        tool_contracts=tool_contracts,
        attempt=attempt,
        previous_error=previous_error,
        previous_code=previous_code,
    )


def workflow_chat(*, user_message: str, skills_readme: str, custom_skill_md: str) -> str:
    from baml_client.sync_client import b

    return b.WorkflowChat(user_message=user_message, skills_readme=skills_readme, custom_skill_md=custom_skill_md)


def workflow_respond(
    *,
    user_message: str,
    plan_json: str,
    executed_code: str,
    exec_stdout: str,
    exec_stderr: str,
    exit_code: int,
    attempts: int,
) -> str:
    from baml_client.sync_client import b

    return b.WorkflowRespond(
        user_message=user_message,
        plan_json=plan_json,
        executed_code=executed_code,
        exec_stdout=exec_stdout,
        exec_stderr=exec_stderr,
        exit_code=exit_code,
        attempts=attempts,
    )
