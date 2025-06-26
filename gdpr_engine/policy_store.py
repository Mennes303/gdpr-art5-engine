"""
SQLite-backed storage layer for ODRL/GDPR policies.

Features
~~~~~~~~
* Raw JSON is stored alongside ``uid``, ``created_at`` and ``updated_at``
  timestamps.
* Database is switched to WAL mode for concurrent read access.
* On first connection the table is created (if absent) and seeded with
  ``policy-1.json`` and ``policy-2.json`` from *tests/fixtures* so the test
  suite can load these by ID without extra setup.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

_DB = Path(__file__).parent / "policies.sqlite3"
_FIXTURES = [
    ("tests/fixtures/policy-1.json", "urn:data:customers"),
    ("tests/fixtures/policy-2.json", "urn:data:orders"),
]


# Connection helper

def _conn() -> sqlite3.Connection:
    """Return a WAL-enabled connection, creating/seed the table on first use."""
    conn = sqlite3.connect(
        _DB,
        isolation_level="IMMEDIATE",  # ACID while allowing parallel readers
        check_same_thread=False,
    )
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS policy (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            uid        TEXT,
            body       TEXT,
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        )
        """
    )

    # Seed fixtures if table is empty
    if conn.execute("SELECT COUNT(*) FROM policy").fetchone()[0] == 0:
        now = datetime.now(timezone.utc).isoformat()
        for path, uid in _FIXTURES:
            raw = Path(path).read_text(encoding="utf-8")
            conn.execute(
                "INSERT INTO policy (uid, body, created_at, updated_at) VALUES (?,?,?,?)",
                (uid, raw, now, now),
            )
        conn.commit()

    return conn


# CRUD helpers

def create(body: str, *, uid: str) -> int:
    """Insert *body* and return its numeric row ID."""
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO policy (uid, body, created_at, updated_at) VALUES (?,?,?,?)",
            (uid, body, now, now),
        )
        rowid = cur.lastrowid
        if rowid is None:
            raise RuntimeError("SQLite failed to return lastrowid")
        return int(rowid)


def read(id_: int) -> str:
    """Return raw JSON for *id_*; raise ``KeyError`` if missing."""
    cur = _conn().execute("SELECT body FROM policy WHERE id=?", (id_,))
    row = cur.fetchone()
    if row is None:
        raise KeyError(id_)
    return row[0]


def update(id_: int, body: str) -> None:
    """Overwrite policy *id_* with *body*; ``KeyError`` if missing."""
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as c:
        if (
            c.execute(
                "UPDATE policy SET body=?, updated_at=? WHERE id=?",
                (body, now, id_),
            ).rowcount
            == 0
        ):
            raise KeyError(id_)


def delete(id_: int) -> None:
    """Remove policy *id_* completely; ``KeyError`` if missing."""
    with _conn() as c:
        if c.execute("DELETE FROM policy WHERE id=?", (id_,)).rowcount == 0:
            raise KeyError(id_)
