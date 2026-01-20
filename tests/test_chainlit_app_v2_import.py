import importlib
import importlib.util
import os
import sys
from pathlib import Path


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
