from pathlib import Path

from dotenv import load_dotenv

from agent_workspace.workflow_agent.agent import WorkflowAgent


def load_env():
    workspace_dir = Path(__file__).resolve().parent
    env_path = workspace_dir / ".env"
    if env_path.exists():
        load_dotenv(env_path)


def build_agent() -> WorkflowAgent:
    load_env()
    return WorkflowAgent()


def main():
    import asyncio

    agent = build_agent()
    user_message = "Run the Monday morning onboarding for engineers."
    result = asyncio.run(agent.run(user_message=user_message))
    print(result.final_response)


if __name__ == "__main__":
    main()
