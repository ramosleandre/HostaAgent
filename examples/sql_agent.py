"""A data-analyst agent over a SQLite database — schema-aware, read-only SQL.

It inspects the schema, then writes SELECT queries to answer questions in plain
English. Writes are refused, so it's safe to point at a real database.

Run it:
    HOSTA_DB=shop.db hosta --agent examples/sql_agent.py "top 5 customers by spend?"
    HOSTA_DB=shop.db python examples/sql_agent.py        # interactive
"""
from __future__ import annotations

import os
import sqlite3

from hostaagent import Agent, Environment, tool

DB_PATH = os.environ.get("HOSTA_DB", "data.db")


class SQLite(Environment):
    """A body whose 'world' is one SQLite file. All tools are read-only."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def context(self) -> str:
        return (f"You analyze the SQLite database at {self.db_path}. "
                "List tables and inspect schemas before querying. Queries are read-only.")

    def tools(self) -> list:
        db = self.db_path

        def _rows(sql: str, params: tuple = ()) -> str:
            con = sqlite3.connect(db)
            try:
                cur = con.execute(sql, params)
                cols = [c[0] for c in cur.description] if cur.description else []
                rows = cur.fetchmany(50)
            finally:
                con.close()
            head = " | ".join(cols)
            body = "\n".join(" | ".join(str(v) for v in r) for r in rows)
            return f"{head}\n{body}" if head else body or "(no rows)"

        @tool(read_only=True)
        def list_tables() -> str:
            "List the tables in the database."
            return _rows("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")

        @tool(read_only=True)
        def schema(table: str) -> str:
            "Show the columns and types of a table."
            return _rows(f"PRAGMA table_info({table})")

        @tool(read_only=True)
        def query(sql: str) -> str:
            "Run a read-only SELECT query (first 50 rows)."
            if not sql.lstrip().lower().startswith(("select", "with")):
                return "error: only SELECT / WITH queries are allowed"
            return _rows(sql)

        return [list_tables, schema, query]


class DataAnalyst(Agent):
    persona = ("You are a precise data analyst. Inspect the schema first, then write a "
               "single SQL query to answer. Show the query and explain the result briefly.")


def make_agent() -> Agent:
    return DataAnalyst(env=SQLite(DB_PATH))


if __name__ == "__main__":
    from hostaagent.driver.cli import launch
    launch(make_agent())
