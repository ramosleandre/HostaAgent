"""The first-run config wizard — arrow-key provider select + prompts (questionary).

Writes ``~/.hostaagent/config.toml``. Falls back to plain prompts when stdin is
not a TTY (CI, pipes) so it never hangs.
"""
from __future__ import annotations

import sys
from typing import Any

import questionary
from rich.console import Console

from ...config import USER_CONFIG, save_config
from .theme import VIOLET, WIZARD_STYLE

# provider -> (base_url, default model). "Other" lets the user type both.
PRESETS: dict[str, tuple[str, str]] = {
    "OpenAI": ("https://api.openai.com/v1", "gpt-4o"),
    "Gemini": ("https://generativelanguage.googleapis.com/v1beta/openai/", "gemini-2.0-flash"),
    "LiteLLM proxy": ("http://localhost:4000", "claude-3-5-sonnet-latest"),
    "Local (Ollama / vLLM)": ("http://localhost:11434/v1", "qwen2.5"),
    "Other": ("", ""),
}


def _plain_wizard(console: Console) -> dict[str, Any]:
    """Fallback for non-interactive stdin: simple input() prompts."""
    name = input("Model name [gpt-4o]: ").strip() or "gpt-4o"
    base_url = input("Base URL [https://api.openai.com/v1]: ").strip() or "https://api.openai.com/v1"
    api_key = input("API key (blank for local): ").strip()
    cfg = {"model": {"name": name, "base_url": base_url, "api_key": api_key},
           "ui": {"theme": "violet"}}
    save_config(cfg)
    console.print(f"[ok]✓ Saved to {USER_CONFIG}[/ok]")
    return cfg


def run_config_wizard() -> dict[str, Any]:
    """Interactive setup; returns the saved config dict."""
    console = Console(theme=VIOLET)
    console.print("\n[primary]✦ Welcome to HostaAgent[/primary] — let's set up your model.\n")

    if not sys.stdin.isatty():
        return _plain_wizard(console)

    provider = questionary.select(
        "Provider", choices=list(PRESETS), default="OpenAI",
        instruction="(↑/↓ to move, ↵ to select)", style=WIZARD_STYLE, qmark="✦",
    ).ask()
    if provider is None:  # Ctrl-C / Esc
        console.print("[muted]cancelled[/muted]")
        sys.exit(0)

    preset_url, preset_model = PRESETS[provider]
    base_url = questionary.text(
        "Base URL", default=preset_url or "http://localhost:11434/v1",
        style=WIZARD_STYLE, qmark="✦",
    ).ask()
    name = questionary.text(
        "Model name", default=preset_model or "gpt-4o", style=WIZARD_STYLE, qmark="✦",
    ).ask()
    api_key = questionary.password(
        "API key (leave blank for local models)", style=WIZARD_STYLE, qmark="✦",
    ).ask()
    if base_url is None or name is None or api_key is None:
        console.print("[muted]cancelled[/muted]")
        sys.exit(0)

    cfg = {
        "model": {"name": name, "base_url": base_url, "api_key": api_key or ""},
        "ui": {"theme": "violet"},
    }
    save_config(cfg)
    console.print(f"\n[ok]✓ Saved to {USER_CONFIG}[/ok]\n")
    return cfg
