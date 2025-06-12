"""SQLite-backed storage for ODRL/GDPR policies."""

from __future__ import annotations
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

_DB = Path(__file__).parent / "policies.sqlite3"


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(_DB)
    c.execute(
        """CREATE TABLE IF NOT EXISTS policy (
               id         INTEGER PRIMARY KEY AUTOINCREMENT,
               uid        TEXT,
               body       TEXT,                -- raw JSON as string
               created_at TIMESTAMP,
               updated_at TIMESTAMP
           )"""
    )
    return c


def create(body: str, uid: str) -> int:
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO policy (uid, body, created_at, updated_at)"
            " VALUES (?, ?, ?, ?)",
            (uid, body, now, now),
        )
        rowid = cur.lastrowid          # type: Optional[int]
        if rowid is None:              # extremely unlikely, but appeases type-checker
            raise RuntimeError("SQLite failed to return lastrowid")
        return rowid                   # now plain int


def read(id_: int) -> str:
    cur = _conn().execute("SELECT body FROM policy WHERE id=?", (id_,))
    row = cur.fetchone()
    if not row:
        raise KeyError(id_)
    return row[0]  # raw JSON string


def update(id_: int, body: str, uid: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as c:
        if (
            c.execute("UPDATE policy SET body=?, uid=?, updated_at=? WHERE id=?",
                      (body, uid, now, id_))
            .rowcount
            == 0
        ):
            raise KeyError(id_)


def delete(id_: int) -> None:
    with _conn() as c:
        if c.execute("DELETE FROM policy WHERE id=?", (id_,)).rowcount == 0:
            raise KeyError(id_)
