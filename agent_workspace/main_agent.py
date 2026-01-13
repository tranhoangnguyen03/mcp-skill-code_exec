import os
from pathlib import Path

from dotenv import load_dotenv

from hr_agent.agent import HRAgent
from hr_agent.openrouter_client import OpenRouterClient


def main():
    import asyncio

    workspace_dir = Path(__file__).resolve().parent
    env_path = workspace_dir / ".env"
    if env_path.exists():
        load_dotenv(env_path)

    llm = OpenRouterClient(
        api_key=os.getenv("open_router_api_key"),
        model=os.getenv("open_router_model_name"),
    )
    agent = HRAgent(llm=llm)

    user_message = "Run the Monday morning onboarding for engineers."
    result = asyncio.run(agent.run(user_message=user_message))
    print(result.final_response)


if __name__ == "__main__":
    main()
