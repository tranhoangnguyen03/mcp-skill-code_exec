from pathlib import Path

from dotenv import load_dotenv

from agent_workspace.workflow_agent.agent import WorkflowAgent


def load_env():
    # Load .env from project root
    root_dir = Path(__file__).resolve().parent.parent
    env_path = root_dir / ".env"
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
