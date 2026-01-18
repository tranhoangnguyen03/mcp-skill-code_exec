import asyncio

import chainlit as cl

from agent_workspace.workflow_agent.agent import WorkflowAgent
from agent_workspace.workflow_agent.types import ExecutionResult
from agent_workspace.main import build_agent, load_env


@cl.on_chat_start
async def on_chat_start():
    load_env()
    agent = build_agent()
    cl.user_session.set("agent", agent)


@cl.on_message
async def on_message(message: cl.Message):
    agent: WorkflowAgent = cl.user_session.get("agent")
    user_input = message.content

    # 1. Planning phase with HITL gate
    while True:
        async with cl.Step(name="Plan") as step:
            plan, plan_json, skill = await asyncio.to_thread(agent.plan, user_message=user_input)
            step.output = "```json\n" + plan_json.strip() + "\n```"

        if plan.action == "chat":
            async with cl.Step(name="Respond") as step:
                final = await asyncio.to_thread(agent.chat, user_message=user_input)
                step.output = final
            await cl.Message(content=final).send()
            return

        # Human-in-the-loop: Approve Plan
        actions = [
            cl.Action(name="approve", payload={"value": "approve"}, label="✅ Approve Plan"),
            cl.Action(name="replan", payload={"value": "replan"}, label="🔄 Re-plan"),
            cl.Action(name="cancel", payload={"value": "cancel"}, label="❌ Cancel Request"),
        ]

        res = await cl.AskActionMessage(
            content=f"Proposed Plan: **{plan.intent}**\n\nDo you want me to proceed with code generation and execution?",
            actions=actions,
            timeout=3600,
            raise_on_timeout=False,
        ).send()

        choice = None
        if isinstance(res, dict):
            payload = res.get("payload")
            if isinstance(payload, dict):
                choice = payload.get("value")

        if choice == "approve":
            break
        elif choice == "replan":
            feedback = await cl.AskUserMessage(content="What should I change in the plan?").send()
            if feedback:
                user_input += f"\n\n[User feedback on previous plan]: {feedback['output']}"
                continue
            else:
                await cl.Message(content="Re-plan cancelled. Stopping workflow.").send()
                return
        else:
            await cl.Message(content="Workflow cancelled.").send()
            return

    # 2. Execution phase (Codegen + Run)
    skill_md = await asyncio.to_thread(agent.get_skill_md, plan=plan, selected_skill=skill)

    last_code = ""
    last_error = ""
    exec_result = ExecutionResult(stdout="", stderr="", exit_code=1)
    attempts_used = 0

    for attempt in range(1, agent.max_attempts + 1):
        attempts_used = attempt
        async with cl.Step(name=f"Codegen (attempt {attempt})") as step:
            try:
                code = await asyncio.to_thread(
                    agent.codegen,
                    user_message=user_input,
                    plan_json=plan_json,
                    skill_md=skill_md,
                    attempt=attempt,
                    previous_error=last_error,
                    previous_code=last_code,
                )
                last_code = code
                step.output = "```python\n" + code.strip() + "\n```"
            except Exception as e:
                last_error = f"Code generation failed: {e}"
                exec_result = ExecutionResult(stdout="", stderr=last_error, exit_code=1)
                step.output = last_error
                continue

        async with cl.Step(name=f"Execute (attempt {attempt})") as step:
            exec_result = await asyncio.to_thread(agent.execute, code=last_code)
            output = []
            if exec_result.stdout:
                output.append("**Stdout**\n```text\n" + exec_result.stdout.strip() + "\n```")
            if exec_result.stderr:
                output.append("**Stderr**\n```text\n" + exec_result.stderr.strip() + "\n```")
            output.append(f"Exit code: {exec_result.exit_code}")
            step.output = "\n\n".join(output)

        if exec_result.exit_code == 0:
            break

        last_error = exec_result.stderr or f"Execution failed with exit_code={exec_result.exit_code}"

    async with cl.Step(name="Respond") as step:
        final = await asyncio.to_thread(
            agent.respond,
            user_message=user_input,
            plan_json=plan_json,
            executed_code=last_code,
            exec_result=exec_result,
            attempts=attempts_used,
        )
        step.output = final

    await cl.Message(content=final).send()
