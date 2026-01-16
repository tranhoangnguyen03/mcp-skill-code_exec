import os
from pathlib import Path

from dotenv import load_dotenv

try:
    from workflow_agent.agent import HRAgent
    from workflow_agent.openrouter_client import OpenRouterClient
except ModuleNotFoundError:
    from agent_workspace.workflow_agent.agent import HRAgent
    from agent_workspace.workflow_agent.openrouter_client import OpenRouterClient


def load_env():
    workspace_dir = Path(__file__).resolve().parent
    env_path = workspace_dir / ".env"
    if env_path.exists():
        load_dotenv(env_path)


def build_agent() -> HRAgent:
    load_env()
    llm = OpenRouterClient(
        api_key=os.getenv("open_router_api_key"),
        model=os.getenv("open_router_model_name"),
    )
    return HRAgent(llm=llm)


def main():
    import asyncio

    agent = build_agent()
    user_message = "Run the Monday morning onboarding for engineers."
    result = asyncio.run(agent.run(user_message=user_message))
    print(result.final_response)


if __name__ == "__main__":
    main()
