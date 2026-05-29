# HostaAgent

> **Claude Code in ~50 lines you can fork.**

HostaAgent takes the irreducible core of a coding agent — the ReAct loop — and
exposes it as a **~50-line class you subclass** to build any agent: coding
assistant, computer-use, business automation, game NPC.

It sits on two layers:

| | |
|---|---|
| **[OpenHosta](https://github.com/hand-e-fr/OpenHosta)** | the typed LLM call + tool calling (`@tool`, `tool_to_schema`, `Model.respond`). |
| **HostaAgent** | the loop + 2 seams (`Environment`, `Driver`) + a violet CLI. |

**Rule of thumb:** one typed call → OpenHosta; a loop with state → HostaAgent.

## Install

```bash
pip install hostaagent          # once published to PyPI
```

### From source

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"         # installs dev tools
```

Working on OpenHosta and HostaAgent together (sibling folders)? Install OpenHosta
from your local checkout so edits are live:

```bash
pip install -e ../OpenHosta && pip install -e . --no-deps && pip install rich
```

## One-minute example

```python
from hostaagent import Agent, LocalFS, CliDriver, tool

@tool
def run_tests(suite: str = "all") -> str:
    "Run pytest on the project."
    import subprocess
    return subprocess.run(["pytest", suite], capture_output=True, text=True).stdout[:3000]

class CodeAgent(Agent):
    persona = "You are a coding agent. Read before editing. Run tests after changes."
    def register_tools(self):
        self.use(run_tests)

CliDriver(lambda: CodeAgent(env=LocalFS("."))).run()
```

That's a complete, specific agent. **Configuration = subclassing** — no TOML/JSON/DSL
for the agent itself. The only config *file* is the CLI's model + API key.

## The CLI

```bash
hosta                          # interactive REPL in the current dir
hosta "summarize README.md"    # one-shot task
hosta --agent examples/code_agent.py "run the tests"
hosta --model gpt-4o "..."     # override the model
hosta config                   # first-run wizard (model + API key)
hosta config show              # print resolved config
```

The first run launches a wizard that saves `~/.hostaagent/config.toml`.
A project can override it with `./.hostaagent.toml`.

## The 3 axes

1. **Agent = brain** — the invariant async ReAct loop (`hostaagent/core.py`, ~50 lines). You rarely touch it.
2. **Environment = body** — what the agent can do/touch (`tools()` + `context()`). `LocalFS` is the default.
3. **Driver = lifecycle** — how/when it runs (`CliDriver`, `DaemonDriver`).

Plug a new body → new agent type. Plug a new driver → new way to run. The loop is unchanged.

See [`examples/`](examples/) for a code agent, a custom (read-only) environment, and a daemon driver.

## How it works (one task)

```
Driver → Agent.run(task)
   → build system prompt (persona + Environment.context())
   → OpenHosta Model.respond(system, msgs, tools=schemas)
   → tool_calls?  yes → run tools (Environment) → append results → loop
                  no  → AgentResult(answer, turns)
```

## Design depth

The full design lives in [`blueprint/`](blueprint/) — vision, the exact spec, the
OpenHosta tool-calling MVP, the leak-reference mapping, and what's deliberately
deferred (permissions, streaming, MCP, sandboxing, …).

## Contributing

- CI (ruff + mypy + pytest, Python 3.10–3.12) runs on every PR — see `.github/workflows/ci.yml`.
- **Never push to `main`.** Open a PR from a feature branch.
- Run `ruff check . && mypy hostaagent && pytest -q` before opening a PR.

## License

MIT — see [LICENSE](LICENSE).
