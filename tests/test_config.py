"""Config file round-trip + the single-import public surface."""
import hostaagent
from hostaagent import config as cfgmod


def test_set_value_persists_nested_key(tmp_path, monkeypatch):
    user = tmp_path / "config.toml"
    monkeypatch.setattr(cfgmod, "USER_CONFIG", user)
    monkeypatch.setattr(cfgmod, "PROJECT_CONFIG", tmp_path / "absent.toml")
    cfgmod.set_value("model.name", "gemini-2.0-flash")
    cfgmod.set_value("agent.path", "./my_agent.py")
    loaded = cfgmod.load_config()
    assert loaded["model"]["name"] == "gemini-2.0-flash"
    assert loaded["agent"]["path"] == "./my_agent.py"


def test_set_value_rejects_bad_key(tmp_path, monkeypatch):
    import pytest
    monkeypatch.setattr(cfgmod, "USER_CONFIG", tmp_path / "c.toml")
    monkeypatch.setattr(cfgmod, "PROJECT_CONFIG", tmp_path / "absent.toml")
    with pytest.raises(ValueError):
        cfgmod.set_value("modelname", "x")  # no section.key


def test_agent_registry_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(cfgmod, "USER_CONFIG", tmp_path / "config.toml")
    monkeypatch.setattr(cfgmod, "PROJECT_CONFIG", tmp_path / "absent.toml")
    af = tmp_path / "myagent.py"
    af.write_text("from hostaagent import Agent, LocalFS\n"
                  "def make_agent():\n    return Agent(env=LocalFS('.'))\n")

    cfgmod.add_agent("mine", str(af))
    assert cfgmod.list_agents() == {"mine": str(af.resolve())}
    assert cfgmod.resolve_agent("mine") == str(af.resolve())   # by name
    assert cfgmod.resolve_agent(str(af)) == str(af)            # by path
    assert cfgmod.resolve_agent("nope") is None                # unknown

    cfgmod.remove_agent("mine")
    assert cfgmod.list_agents() == {}


def _isolate(tmp_path, monkeypatch):
    monkeypatch.setattr(cfgmod, "USER_CONFIG", tmp_path / "config.toml")
    monkeypatch.setattr(cfgmod, "PROJECT_CONFIG", tmp_path / "absent.toml")


def test_dump_toml_flat_sections_unchanged(tmp_path, monkeypatch):
    # Regression guard: a flat-only config must still round-trip identically.
    _isolate(tmp_path, monkeypatch)
    cfgmod.set_value("model.name", "gpt-4o")
    cfgmod.set_value("agent.default", "mine")
    loaded = cfgmod.load_config()
    assert loaded["model"]["name"] == "gpt-4o"
    assert loaded["agent"]["default"] == "mine"
    # [agents] is name->str (flat) — must stay flat, not nest
    text = (tmp_path / "config.toml").read_text()
    assert "[model]" in text and "[models." not in text


def test_model_config_registry_roundtrip(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    cfgmod.add_model_config("local", {"name": "qwen2.5", "base_url": "http://localhost:11434/v1",
                                      "api_key": ""})
    cfgmod.add_model_config("oai", {"name": "gpt-4o", "base_url": "https://api.openai.com/v1",
                                    "api_key": "sk-x"})
    regs = cfgmod.list_model_configs()
    assert set(regs) == {"local", "oai"}
    assert regs["local"]["name"] == "qwen2.5" and regs["oai"]["api_key"] == "sk-x"
    # the nested table really wrote as [models.local] / [models.oai]
    text = (tmp_path / "config.toml").read_text()
    assert "[models.local]" in text and "[models.oai]" in text

    cfgmod.remove_model_config("local")
    assert set(cfgmod.list_model_configs()) == {"oai"}  # the other survives


def test_use_model_config_copies_to_active(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    cfgmod.add_model_config("local", {"name": "qwen2.5", "base_url": "http://localhost:11434/v1",
                                      "api_key": ""})
    cfgmod.use_model_config("local")
    active = cfgmod.load_config()["model"]
    assert active["name"] == "qwen2.5" and active["base_url"] == "http://localhost:11434/v1"


def test_use_model_config_unknown_raises(tmp_path, monkeypatch):
    import pytest
    _isolate(tmp_path, monkeypatch)
    with pytest.raises(KeyError):
        cfgmod.use_model_config("nope")


def test_add_model_config_rejects_bad_name(tmp_path, monkeypatch):
    import pytest
    _isolate(tmp_path, monkeypatch)
    with pytest.raises(ValueError):
        cfgmod.add_model_config("bad name", {"name": "x"})


def test_api_key_with_special_chars_survives_nested_dump(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    weird = 'sk-"quote"\\back\ttab'
    cfgmod.add_model_config("proxy", {"name": "m", "base_url": "http://x", "api_key": weird})
    assert cfgmod.list_model_configs()["proxy"]["api_key"] == weird  # escaped + re-read intact


def test_remove_agent_clears_default(tmp_path, monkeypatch):
    monkeypatch.setattr(cfgmod, "USER_CONFIG", tmp_path / "config.toml")
    monkeypatch.setattr(cfgmod, "PROJECT_CONFIG", tmp_path / "absent.toml")
    af = tmp_path / "a.py"
    af.write_text("from hostaagent import Agent, LocalFS\ndef make_agent():\n"
                  "    return Agent(env=LocalFS('.'))\n")
    cfgmod.add_agent("mine", str(af))
    cfgmod.set_value("agent.default", "mine")
    cfgmod.remove_agent("mine")
    assert cfgmod.load_config()["agent"]["default"] == ""


def test_add_agent_rejects_bad_name(tmp_path, monkeypatch):
    import pytest
    monkeypatch.setattr(cfgmod, "USER_CONFIG", tmp_path / "c.toml")
    monkeypatch.setattr(cfgmod, "PROJECT_CONFIG", tmp_path / "absent.toml")
    with pytest.raises(ValueError):
        cfgmod.add_agent("bad name", "/x")  # whitespace not allowed in a name


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
