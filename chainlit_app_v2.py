import asyncio
import os
import secrets

import chainlit as cl
import chainlit.data as cl_data
from chainlit.types import ThreadDict

from agent_workspace.memory import SessionMemory, StepType, StepCategory
from agent_workspace.memory.chainlit_data_layer import FileDataLayer
from agent_workspace.workflow_agent.agent import WorkflowAgent
from agent_workspace.workflow_agent.types import ExecutionResult
from agent_workspace.main import build_agent, load_env

# Initialize the custom data layer for chat history
cl_data._data_layer = FileDataLayer()
load_env()
if "CHAINLIT_AUTH_SECRET" not in os.environ:
    os.environ["CHAINLIT_AUTH_SECRET"] = secrets.token_urlsafe(32)


@cl.password_auth_callback
def auth_callback(username: str, password: str):
    expected_username = os.environ.get("CHAINLIT_AUTH_USERNAME")
    expected_password = os.environ.get("CHAINLIT_AUTH_PASSWORD")
    if not expected_username or not expected_password:
        return None
    if username == expected_username and password == expected_password:
        return cl.User(identifier=username, metadata={"provider": "credentials"})
    return None


async def _ensure_thread_user(thread_id: str) -> None:
    user = cl.user_session.get("user")
    user_id = getattr(user, "id", None) if user else None
    if user_id:
        await cl_data._data_layer.update_thread(thread_id, user_id=user_id)


@cl.on_chat_start
async def on_chat_start():
    load_env()
    agent = build_agent()

    # Get thread_id from Chainlit context for session memory
    thread_id = cl.context.session.thread_id
    memory = SessionMemory(session_id=thread_id)

    cl.user_session.set("agent", agent)
    cl.user_session.set("memory", memory)
    await cl_data._data_layer.update_thread(thread_id)
    await _ensure_thread_user(thread_id)


@cl.on_chat_resume
async def on_chat_resume(thread: ThreadDict):
    """Resume a previous conversation from chat history."""
    load_env()
    agent = build_agent()

    # Load memory for the resumed thread
    thread_id = thread["id"]
    memory = SessionMemory(session_id=thread_id)

    cl.user_session.set("agent", agent)
    cl.user_session.set("memory", memory)
    await cl_data._data_layer.update_thread(thread_id)
    await _ensure_thread_user(thread_id)

    # Show how many messages were loaded
    msg_count = len(memory.get_messages())
    if msg_count > 0:
        await cl.Message(
            content=f"Resumed conversation with {msg_count} previous messages.",
        ).send()


@cl.on_message
async def on_message(message: cl.Message):
    agent: WorkflowAgent = cl.user_session.get("agent")
    memory: SessionMemory = cl.user_session.get("memory")
    user_input = message.content

    # Store user message in memory (single write path - no duplication)
    memory.add_response("user", user_input)

    # 1. Planning phase with HITL gate
    while True:
        async with cl.Step(name="Plan") as step:
            plan, plan_json, skill = await asyncio.to_thread(agent.plan, user_message=user_input)
            step.output = "```json\n" + plan_json.strip() + "\n```"

        # Persist plan as working step
        memory.add_working_step(
            step_type=StepType.PLAN.value,
            content=plan_json,
            category=StepCategory.WORKING,
            metadata={"intent": plan.intent, "action": plan.action},
        )

        if plan.action == "chat":
            async with cl.Step(name="Respond") as step:
                final = await asyncio.to_thread(agent.chat, user_message=user_input)
                step.output = final
            # Store assistant response in memory (single write)
            memory.add_response("assistant", final)
            await cl.Message(content=final).send()
            return

        # Human-in-the-loop: Approve Plan
        actions = [
            cl.Action(name="approve", payload={"value": "approve"}, label="Approve Plan"),
            cl.Action(name="replan", payload={"value": "replan"}, label="Re-plan"),
            cl.Action(name="cancel", payload={"value": "cancel"}, label="Cancel Request"),
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

        # Persist generated code as working step
        memory.add_working_step(
            step_type=StepType.CODEGEN.value,
            content=last_code,
            category=StepCategory.WORKING,
            metadata={"attempt": attempt},
        )

        async with cl.Step(name=f"Execute (attempt {attempt})") as step:
            exec_result = await asyncio.to_thread(agent.execute, code=last_code)
            output = []
            if exec_result.stdout:
                output.append("**Stdout**\n```text\n" + exec_result.stdout.strip() + "\n```")
            if exec_result.stderr:
                output.append("**Stderr**\n```text\n" + exec_result.stderr.strip() + "\n```")
            output.append(f"Exit code: {exec_result.exit_code}")
            step.output = "\n\n".join(output)

        # Persist execution result as working step
        memory.add_working_step(
            step_type=StepType.EXECUTE.value,
            content=f"stdout: {exec_result.stdout}\nstderr: {exec_result.stderr}",
            category=StepCategory.WORKING,
            metadata={"exit_code": exec_result.exit_code, "attempt": attempt},
        )

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

    # Store assistant response in memory (single write - cl.Message for UI only)
    memory.add_response("assistant", final)

    await cl.Message(content=final).send()
