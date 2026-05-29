"""Config file round-trip + the single-import public surface."""
import hostaagent
from hostaagent import config as cfgmod


def test_canonical_import_surface():
    # The only import a user needs (from 01_VISION / 02_FINAL_SPEC).
    from hostaagent import Agent, CliDriver, LocalFS, tool  # noqa: F401
    assert hostaagent.__version__ == "0.1.0"
    assert set(["Agent", "LocalFS", "CliDriver", "DaemonDriver", "Environment",
                "AgentResult", "Turn", "ToolUse", "tool"]).issubset(hostaagent.__all__)


def test_load_config_none_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(cfgmod, "USER_CONFIG", tmp_path / "nope" / "config.toml")
    monkeypatch.setattr(cfgmod, "PROJECT_CONFIG", tmp_path / "absent.toml")
    assert cfgmod.load_config() is None


def test_save_then_load_roundtrip(tmp_path, monkeypatch):
    user = tmp_path / ".hostaagent" / "config.toml"
    monkeypatch.setattr(cfgmod, "USER_CONFIG", user)
    monkeypatch.setattr(cfgmod, "PROJECT_CONFIG", tmp_path / "absent.toml")
    cfgmod.save_config({
        "model": {"name": "gpt-4o", "base_url": "https://x/v1", "api_key": "sk-test"},
        "ui": {"theme": "violet"},
    }, path=user)
    loaded = cfgmod.load_config()
    assert loaded is not None
    assert loaded["model"]["name"] == "gpt-4o"
    assert loaded["model"]["api_key"] == "sk-test"
    assert loaded["ui"]["theme"] == "violet"


def test_project_overrides_user(tmp_path, monkeypatch):
    user = tmp_path / "user.toml"
    project = tmp_path / "project.toml"
    user.write_text('[model]\nname = "user-model"\nbase_url = "https://u/v1"\napi_key = ""\n')
    project.write_text('[model]\nname = "project-model"\n')
    monkeypatch.setattr(cfgmod, "USER_CONFIG", user)
    monkeypatch.setattr(cfgmod, "PROJECT_CONFIG", project)
    loaded = cfgmod.load_config()
    assert loaded["model"]["name"] == "project-model"      # project wins
    assert loaded["model"]["base_url"] == "https://u/v1"   # falls back to user


def test_toml_escapes_quotes(tmp_path, monkeypatch):
    user = tmp_path / "c.toml"
    monkeypatch.setattr(cfgmod, "USER_CONFIG", user)
    monkeypatch.setattr(cfgmod, "PROJECT_CONFIG", tmp_path / "absent.toml")
    cfgmod.save_config({"model": {"name": 'has"quote', "base_url": "u", "api_key": ""}}, path=user)
    assert cfgmod.load_config()["model"]["name"] == 'has"quote'


def test_build_model_from_config():
    model = cfgmod.build_model(
        {"model": {"name": "m", "base_url": "http://localhost:11434/v1", "api_key": "k"}})
    assert model.model_name == "m"
    assert hasattr(model, "respond")  # the tool-calling entry point
