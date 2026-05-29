"""LocalFS body: read / grep / write / bash, plus the base Environment."""
import shutil

import pytest

from hostaagent import Environment, LocalFS


def _tools(env):
    return {t.__name__: t for t in env.tools()}


def test_base_environment_is_empty():
    env = Environment()
    assert env.tools() == []
    assert env.context() == ""


def test_localfs_context_has_root(tmp_path):
    env = LocalFS(str(tmp_path))
    assert str(tmp_path) in env.context()


def test_read_and_write(tmp_path):
    tools = _tools(LocalFS(str(tmp_path)))
    assert tools["write"](path="note.txt", content="hello world") == "ok"
    assert tools["read"](path="note.txt") == "hello world"


def test_write_creates_parent_dirs(tmp_path):
    tools = _tools(LocalFS(str(tmp_path)))
    assert tools["write"](path="a/b/c.txt", content="deep") == "ok"
    assert (tmp_path / "a" / "b" / "c.txt").read_text() == "deep"


def test_read_caps_at_8000_chars(tmp_path):
    (tmp_path / "big.txt").write_text("x" * 9000)
    assert len(_tools(LocalFS(str(tmp_path)))["read"](path="big.txt")) == 8000


def test_bash_runs_in_root(tmp_path):
    (tmp_path / "marker.txt").write_text("")
    out = _tools(LocalFS(str(tmp_path)))["bash"](command="ls")
    assert "marker.txt" in out


@pytest.mark.skipif(shutil.which("rg") is None, reason="ripgrep not installed")
def test_grep_finds_match(tmp_path):
    (tmp_path / "code.py").write_text("def validate_token():\n    pass\n")
    out = _tools(LocalFS(str(tmp_path)))["grep"](pattern="validate_token")
    assert "validate_token" in out


@pytest.mark.skipif(shutil.which("rg") is None, reason="ripgrep not installed")
def test_grep_no_match(tmp_path):
    (tmp_path / "code.py").write_text("nothing here\n")
    out = _tools(LocalFS(str(tmp_path)))["grep"](pattern="zzzznotfound")
    assert out == "no matches"


def test_read_only_metadata(tmp_path):
    tools = _tools(LocalFS(str(tmp_path)))
    assert tools["read"].__hosta_tool__.read_only is True
    assert tools["grep"].__hosta_tool__.read_only is True
    assert tools["write"].__hosta_tool__.read_only is False
    assert tools["bash"].__hosta_tool__.read_only is False
