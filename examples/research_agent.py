"""A web-research agent — fetches URLs, reads them, and synthesizes a cited answer.

Pure stdlib (urllib), no extra dependencies. Give it links in your task; it pulls
the visible text and answers from what it read.

Run it:
    hosta --agent examples/research_agent.py "compare https://a.com and https://b.com"
    python examples/research_agent.py
"""
from __future__ import annotations

import re
import urllib.request

from hostaagent import Agent, Environment, tool


@tool(read_only=True)
def fetch_url(url: str) -> str:
    "Fetch a URL and return its visible text (capped at 6000 chars)."
    req = urllib.request.Request(url, headers={"User-Agent": "hostaagent/0.1"})
    with urllib.request.urlopen(req, timeout=20) as resp:  # noqa: S310 (user-provided URL)
        html = resp.read().decode("utf-8", "ignore")
    text = re.sub(r"<(script|style)\b.*?</\1>", " ", html, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()[:6000]


class WebEnv(Environment):
    def context(self) -> str:
        return "You can fetch web pages. Read the URLs in the task before answering."

    def tools(self) -> list:
        return [fetch_url]


class Researcher(Agent):
    persona = ("You are a research assistant. Fetch the URLs in the task, then write a "
               "concise, well-structured answer and cite which page each claim came from.")


def make_agent() -> Agent:
    return Researcher(env=WebEnv())


if __name__ == "__main__":
    from hostaagent.driver import cli
    cli.launch(make_agent)
