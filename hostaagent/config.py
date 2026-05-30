"""Config: the only config *file* in the project — model + API key + UI theme.

Resolved from (lowest to highest precedence):
  1. ``~/.hostaagent/config.toml``         (user defaults, written by the wizard)
  2. ``./.hostaagent.toml``                (per-project override)
  3. CLI flags (handled in ``driver/cli``)

The interactive wizard that *writes* this file lives in ``driver/cli/wizard.py``.
Everything about the *agent* is Python (subclassing), never TOML.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

try:  # Python 3.11+
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10
    import tomli as tomllib

USER_CONFIG = Path.home() / ".hostaagent" / "config.toml"
PROJECT_CONFIG = Path(".hostaagent.toml")

DEFAULTS: dict[str, Any] = {
    "model": {"name": "gpt-4o", "base_url": "https://api.openai.com/v1", "api_key": ""},
    "agent": {"path": ""},   # optional: a Python file `hosta` loads by default
    "ui": {"theme": "violet"},
}


def _read_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as f:
        data: dict[str, Any] = tomllib.load(f)
    return data


def _merge(base: dict[str, Any], over: dict[str, Any]) -> dict[str, Any]:
    out = {k: dict(v) if isinstance(v, dict) else v for k, v in base.items()}
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k].update(v)
        else:
            out[k] = v
    return out


def load_config() -> dict[str, Any] | None:
    """Return the merged config, or ``None`` if no config file exists yet."""
    if not USER_CONFIG.exists() and not PROJECT_CONFIG.exists():
        return None
    cfg = _merge(DEFAULTS, {})
    if USER_CONFIG.exists():
        cfg = _merge(cfg, _read_toml(USER_CONFIG))
    if PROJECT_CONFIG.exists():
        cfg = _merge(cfg, _read_toml(PROJECT_CONFIG))
    return cfg


def _toml_escape(value: str) -> str:
    return (value.replace("\\", "\\\\").replace('"', '\\"')
            .replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t"))


def _dump_toml(cfg: dict[str, Any]) -> str:
    lines = []
    for section, values in cfg.items():
        lines.append(f"[{section}]")
        for key, val in values.items():
            lines.append(f'{key} = "{_toml_escape(str(val))}"')
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def save_config(cfg: dict[str, Any], path: Path | None = None) -> None:
    target = path or USER_CONFIG  # resolved at call time, not frozen at import
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(_dump_toml(cfg))


def set_value(dotted_key: str, value: str) -> dict[str, Any]:
    """Set one ``section.key`` (e.g. ``model.name``) in the user config and save it.

    Used by ``hosta config set <key> <value>``. Returns the updated config.
    """
    section, _, key = dotted_key.partition(".")
    if not section or not key:
        raise ValueError("expected section.key, e.g. model.name or agent.path")
    cfg = load_config() or _merge(DEFAULTS, {})
    cfg.setdefault(section, {})[key] = value
    save_config(cfg)
    return cfg


def build_model(cfg: dict[str, Any]) -> Any:
    """Construct an OpenHosta model from a resolved config dict."""
    from OpenHosta import OpenAICompatibleModel

    model = cfg.get("model", {})
    return OpenAICompatibleModel(
        model_name=model.get("name") or "gpt-4o",
        base_url=model.get("base_url") or "https://api.openai.com/v1",
        api_key=model.get("api_key") or None,
    )
