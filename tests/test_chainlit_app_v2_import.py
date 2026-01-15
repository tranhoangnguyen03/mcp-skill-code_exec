import importlib


def test_chainlit_app_v2_imports():
    mod = importlib.import_module("chainlit_app_v2")
    assert hasattr(mod, "on_chat_start")
    assert hasattr(mod, "on_message")
