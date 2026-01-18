from __future__ import annotations

from pathlib import Path


def test_mock_data_fixtures_exist_and_are_valid_json():
    repo_root = Path(__file__).resolve().parents[1]
    data_dir = repo_root / "agent_workspace" / "data"

    employees = data_dir / "bamboo_hr" / "employees.json"
    users = data_dir / "lattice" / "users.json"

    assert employees.exists()
    assert users.exists()

    import json

    json.loads(employees.read_text(encoding="utf-8"))
    json.loads(users.read_text(encoding="utf-8"))

