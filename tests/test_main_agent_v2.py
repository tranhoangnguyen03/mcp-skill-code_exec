import os

from agent_workspace.main import build_agent
from agent_workspace.workflow_agent.agent import HRAgent


def test_build_agent_v2_builds_agent(monkeypatch):
    monkeypatch.setenv("open_router_api_key", os.getenv("open_router_api_key") or "test-key")
    monkeypatch.setenv("open_router_model_name", os.getenv("open_router_model_name") or "test-model")
    agent = build_agent()
    assert isinstance(agent, HRAgent)
