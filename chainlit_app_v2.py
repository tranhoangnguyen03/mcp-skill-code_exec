import asyncio
import json
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


def _enrich_history_with_facts(conversation_history: str, workflow_state: dict | None) -> str:
    if not workflow_state:
        return conversation_history
    collected_facts = workflow_state.get("collected_facts") or {}
    if not collected_facts:
        return conversation_history
    lines = ["## Collected Facts from Previous Steps"]
    for key, value in collected_facts.items():
        lines.append(f"- {key}: {value}")
    lines.append("")
    if conversation_history:
        lines.append(conversation_history)
    return "\n".join(lines).strip()


@cl.on_message
async def on_message(message: cl.Message):
    agent: WorkflowAgent = cl.user_session.get("agent")
    memory: SessionMemory = cl.user_session.get("memory")
    user_input = message.content

    try:
        max_history_messages = int(os.getenv("agent_memory_max_messages", "10") or "10")
    except Exception:
        max_history_messages = 10
    conversation_history = memory.get_conversation_history(max_messages=max_history_messages)

    # Store user message in memory (single write path - no duplication)
    memory.add_response("user", user_input)

    # Check for pending multi-turn workflow
    pending_workflow = memory.get_workflow_state()
    if pending_workflow and pending_workflow.get("is_multi_turn"):
        await _handle_continuation(
            agent=agent,
            memory=memory,
            user_input=user_input,
            conversation_history=conversation_history,
            workflow_state=pending_workflow,
        )
        return

    # 1. Planning phase with HITL gate
    while True:
        async with cl.Step(name="Plan") as step:
            plan, plan_json, skill = await asyncio.to_thread(
                agent.plan, user_message=user_input, conversation_history=conversation_history
            )
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
                final = await asyncio.to_thread(agent.chat, user_message=user_input, conversation_history=conversation_history)
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

    # 2. Execution phase (Codegen + Run) with multi-turn support
    skill_md = await asyncio.to_thread(agent.get_skill_md, plan=plan, selected_skill=skill)

    last_code = ""
    last_error = ""
    exec_result = ExecutionResult(stdout="", stderr="", exit_code=1)
    attempts_used = 0
    needs_continuation = False
    collected_facts = {}

    for attempt in range(1, agent.max_attempts + 1):
        attempts_used = attempt
        async with cl.Step(name=f"Codegen (attempt {attempt})") as step:
            try:
                code = await asyncio.to_thread(
                    agent.codegen,
                    user_message=user_input,
                    plan_json=plan_json,
                    skill_md=skill_md,
                    conversation_history=conversation_history,
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

    # Check for continuation signals in multi-turn workflows
    if exec_result.exit_code == 0:
        from agent_workspace.workflow_agent.sub_agents.executor import detect_continuation_signals
        needs_continuation, collected_facts = detect_continuation_signals(exec_result.stdout)

        if needs_continuation:
            # Save workflow state for continuation
            workflow_state = agent.create_workflow_state(
                session_id=memory.session_id,
                plan_json=plan_json,
                collected_facts=collected_facts,
            )
            memory.save_workflow_state(workflow_state)

            # Show collected facts to user
            facts_msg = "**Checkpoint Complete!** I discovered the following:\n\n"
            for key, value in collected_facts.items():
                facts_msg += f"- **{key}**: {value}\n"
            facts_msg += "\nI'll now continue with the next step..."

            async with cl.Step(name="Continue") as step:
                step.output = facts_msg

            await cl.Message(content=facts_msg).send()

            # Auto-continue with next turn
            await _handle_continuation(
                agent=agent,
                memory=memory,
                user_input=user_input,  # Original request continues
                conversation_history=conversation_history,
                workflow_state=workflow_state,
            )
            return

    async with cl.Step(name="Respond") as step:
        final = await asyncio.to_thread(
            agent.respond,
            user_message=user_input,
            plan_json=plan_json,
            executed_code=last_code,
            exec_result=exec_result,
            attempts=attempts_used,
            conversation_history=conversation_history,
        )
        step.output = final

    # Store assistant response in memory (single write - cl.Message for UI only)
    memory.add_response("assistant", final)

    await cl.Message(content=final).send()


async def _handle_continuation(
    agent: WorkflowAgent,
    memory: SessionMemory,
    user_input: str,
    conversation_history: str,
    workflow_state: dict,
):
    """Handle continuation of a multi-turn workflow.

    Args:
        agent: The WorkflowAgent instance
        memory: The SessionMemory for this session
        user_input: The original user request
        conversation_history: Previous conversation context
        workflow_state: The pending workflow state
    """
    from agent_workspace.workflow_agent.types import ExecutionResult

    # Get the original plan and skill
    plan_json = workflow_state.get("plan_json", "")
    plan_data = json.loads(plan_json)
    skill_group = plan_data.get("skill_group")
    skill_name = plan_data.get("skill_name")
    action = plan_data.get("action") or "custom_script"

    # Get skill content
    selected_skill = None
    if action == "execute_skill" and skill_name:
        skills = agent.skills.list_skills()
        for s in skills:
            if s.name == skill_name:
                selected_skill = s
                break
    if action == "execute_skill" and selected_skill is None:
        action = "custom_script"

    skill_md = agent.get_skill_md(
        plan=type("Plan", (), {"action": action, "skill_group": skill_group, "skill_name": skill_name})(),
        selected_skill=selected_skill,
    )

    enriched_history = _enrich_history_with_facts(conversation_history, workflow_state)

    # Execute the workflow with continuation support
    last_code = ""
    exec_result = ExecutionResult(stdout="", stderr="", exit_code=1)
    attempts_used = 0

    for attempt in range(1, agent.max_attempts + 1):
        attempts_used = attempt
        async with cl.Step(name=f"Continue (attempt {attempt})") as step:
            try:
                code = await asyncio.to_thread(
                    agent.codegen,
                    user_message=user_input,
                    plan_json=plan_json,
                    skill_md=skill_md,
                    conversation_history=enriched_history,
                    attempt=attempt,
                    previous_error="",
                    previous_code=last_code,
                )
                last_code = code
                step.output = "```python\n" + code.strip() + "\n```"
            except Exception as e:
                exec_result = ExecutionResult(stdout="", stderr=f"Code generation failed: {e}", exit_code=1)
                step.output = str(e)
                continue

        # Persist generated code
        memory.add_working_step(
            step_type=StepType.CODEGEN.value,
            content=last_code,
            category=StepCategory.WORKING,
            metadata={"attempt": attempt, "continuation": True},
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

        # Persist execution result
        memory.add_working_step(
            step_type=StepType.EXECUTE.value,
            content=f"stdout: {exec_result.stdout}\nstderr: {exec_result.stderr}",
            category=StepCategory.WORKING,
            metadata={"exit_code": exec_result.exit_code, "attempt": attempt, "continuation": True},
        )

        if exec_result.exit_code == 0:
            break

    # Check if we need another continuation
    from agent_workspace.workflow_agent.sub_agents.executor import detect_continuation_signals
    needs_continuation, collected_facts = detect_continuation_signals(exec_result.stdout)

    if needs_continuation and collected_facts:
        # Update workflow state with new facts
        updated_state = agent.update_workflow_state(
            workflow_state,
            next_step=workflow_state.get("current_step", 0) + 1,
            facts=collected_facts,
        )
        memory.save_workflow_state(updated_state)

        # Show continuation message
        facts_msg = "**Checkpoint Complete!** I discovered the following:\n\n"
        for key, value in collected_facts.items():
            facts_msg += f"- **{key}**: {value}\n"
        facts_msg += "\nContinuing to next step..."

        await cl.Message(content=facts_msg).send()

        # Recursively continue
        await _handle_continuation(
            agent=agent,
            memory=memory,
            user_input=user_input,
            conversation_history=conversation_history,
            workflow_state=updated_state,
        )
        return

    # Final response - clear workflow state
    memory.clear_workflow_state()

    async with cl.Step(name="Respond") as step:
        final = await asyncio.to_thread(
            agent.respond,
            user_message=user_input,
            plan_json=plan_json,
            executed_code=last_code,
            exec_result=exec_result,
            attempts=attempts_used,
            conversation_history=enriched_history,
        )
        step.output = final

    memory.add_response("assistant", final)
    await cl.Message(content=final).send()
