import importlib
import importlib.util
import os
import re
import sys
from pathlib import Path
from types import SimpleNamespace


def test_chainlit_app_v2_imports():
    mod = importlib.import_module("chainlit_app_v2")
    assert hasattr(mod, "on_chat_start")
    assert hasattr(mod, "on_message")


def test_chainlit_app_v2_loads_from_file_path_without_repo_sys_path_and_still_imports_baml_client():
    repo_root = Path(__file__).resolve().parents[1]
    app_path = repo_root / "chainlit_app_v2.py"
    old_cwd = os.getcwd()
    old_sys_path = list(sys.path)
    old_modules = dict(sys.modules)

    try:
        os.chdir(str(repo_root.parent))
        sys.path[:] = [p for p in sys.path if p not in {"", str(repo_root)}]
        importlib.invalidate_caches()

        for name in list(sys.modules.keys()):
            if name == "chainlit_app_v2" or name.startswith("agent_workspace") or name.startswith("baml_client"):
                sys.modules.pop(name, None)

        try:
            importlib.import_module("agent_workspace")
        except ModuleNotFoundError:
            return

        spec = importlib.util.spec_from_file_location("chainlit_app_v2", app_path)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        sys.modules["chainlit_app_v2"] = module
        spec.loader.exec_module(module)

        imported = importlib.import_module("baml_client")
        assert hasattr(imported, "__version__")
    finally:
        os.chdir(old_cwd)
        sys.path[:] = old_sys_path
        sys.modules.clear()
        sys.modules.update(old_modules)


def test_file_data_layer_lists_threads_by_user_id_and_user_identifier(tmp_path: Path):
    from agent_workspace.memory.chainlit_data_layer import FileDataLayer

    dl = FileDataLayer(storage_dir=tmp_path)
    dl._save_users(
        {
            "testuser": {
                "id": "user-1",
                "identifier": "testuser",
                "createdAt": "2026-01-01T00:00:00+00:00",
                "metadata": {"provider": "credentials"},
            }
        }
    )

    import asyncio

    asyncio.run(dl.update_thread("thread-1", user_id="user-1"))

    res_by_id = asyncio.run(
        dl.list_threads(
            pagination=SimpleNamespace(cursor=None, first=20),
            filters=SimpleNamespace(userId="user-1", userIdentifier=None),
        )
    )
    assert [t["id"] for t in res_by_id.data] == ["thread-1"]

    res_by_identifier = asyncio.run(
        dl.list_threads(
            pagination=SimpleNamespace(cursor=None, first=20),
            filters=SimpleNamespace(userId=None, userIdentifier="testuser"),
        )
    )
    assert [t["id"] for t in res_by_identifier.data] == ["thread-1"]


def test_thread_name_defaults_to_datetime_when_missing(tmp_path: Path):
    from agent_workspace.memory.chainlit_data_layer import FileDataLayer

    import asyncio

    dl = FileDataLayer(storage_dir=tmp_path)
    asyncio.run(dl.update_thread("thread-1"))

    data = dl._load_thread("thread-1")
    assert data is not None
    data["name"] = None
    dl._save_thread("thread-1", data)

    thread = asyncio.run(dl.get_thread("thread-1"))
    assert thread is not None
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", thread["name"])


def test_delete_thread_removes_from_storage_and_listing(tmp_path: Path):
    from agent_workspace.memory.chainlit_data_layer import FileDataLayer

    import asyncio

    dl = FileDataLayer(storage_dir=tmp_path)
    asyncio.run(dl.update_thread("thread-1"))
    assert dl._get_thread_path("thread-1").exists()

    asyncio.run(dl.delete_thread("thread-1"))
    assert not dl._get_thread_path("thread-1").exists()

    res = asyncio.run(
        dl.list_threads(
            pagination=SimpleNamespace(cursor=None, first=20),
            filters=SimpleNamespace(userId=None, userIdentifier=None),
        )
    )
    assert res.data == []


def test_load_thread_tolerates_legacy_python_object_tags(tmp_path: Path):
    from agent_workspace.memory.chainlit_data_layer import FileDataLayer

    dl = FileDataLayer(storage_dir=tmp_path)
    thread_id = "thread-1"
    dl._get_thread_path(thread_id).write_text(
        "\n".join(
            [
                f"session_id: {thread_id}",
                "created_at: '2026-01-20T13:40:35.998801+00:00'",
                "updated_at: '2026-01-20T20:40:53.801486'",
                "user_id: user-1",
                "user_identifier: testuser",
                "name: hi",
                "metadata: {}",
                "tags: []",
                "messages: []",
                "steps:",
                "- step_type: !!python/object/apply:agent_workspace.memory.session_memory.StepType",
                "  - plan",
                "  category: working",
                "  content: '{}' ",
                "  metadata: {}",
                "  timestamp: '2026-01-20T20:40:28.070782'",
                "facts: []",
                "",
            ]
        ),
        encoding="utf-8",
    )

    data = dl._load_thread(thread_id)
    assert data is not None
    assert data["steps"][0]["step_type"] == "plan"


def test_get_thread_author_returns_user_identifier(tmp_path: Path):
    from agent_workspace.memory.chainlit_data_layer import FileDataLayer

    import asyncio

    dl = FileDataLayer(storage_dir=tmp_path)
    dl._save_users(
        {
            "testuser": {
                "id": "user-1",
                "identifier": "testuser",
                "createdAt": "2026-01-01T00:00:00+00:00",
                "metadata": {"provider": "credentials"},
            }
        }
    )
    asyncio.run(dl.update_thread("thread-1", user_id="user-1"))

    data = dl._load_thread("thread-1")
    assert data is not None
    data["user_identifier"] = None
    dl._save_thread("thread-1", data)

    author = asyncio.run(dl.get_thread_author("thread-1"))
    assert author == "testuser"
