"""
SQLite‑backed storage for ODRL / GDPR policies.

The table stores the **raw JSON text** plus bookkeeping fields so we can
version‑track (created_at / updated_at) and keep an external UID if needed.

"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

_DB = Path(__file__).parent / "policies.sqlite3"

# ──────────────────────────────────────────────────────────────────────────
# Connection helper
# ──────────────────────────────────────────────────────────────────────────

def _conn() -> sqlite3.Connection:
    """Return a WAL‑enabled connection; create the `policy` table on first use."""
    conn = sqlite3.connect(
        _DB,
        isolation_level="IMMEDIATE",     # ACID, allows parallel readers
        check_same_thread=False,          # FastAPI workers share the handle
    )
    conn.execute("PRAGMA journal_mode=WAL;")    # enable write‑ahead logging
    conn.execute("PRAGMA synchronous=NORMAL;")  # fsync once per checkpoint

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS policy (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            uid        TEXT,
            body       TEXT,            -- raw JSON string
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        )
        """
    )
    return conn

# ──────────────────────────────────────────────────────────────────────────
# CRUD helpers
# ──────────────────────────────────────────────────────────────────────────

def create(body: str, *, uid: str) -> int:
    """Insert a new policy and return its row‑id (int)."""
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO policy (uid, body, created_at, updated_at)"
            " VALUES (?, ?, ?, ?)",
            (uid, body, now, now),
        )
        rowid = cur.lastrowid
        if rowid is None:  # extremely unlikely – appeases the type checker
            raise RuntimeError("SQLite failed to return lastrowid")
        return int(rowid)

def read(id_: int) -> str:
    """Return the *raw JSON* string for one policy (KeyError if id unknown)."""
    cur = _conn().execute("SELECT body FROM policy WHERE id=?", (id_,))
    row = cur.fetchone()
    if row is None:
        raise KeyError(id_)
    return row[0]

def update(id_: int, body: str) -> None:
    """Replace JSON text and bump updated_at (KeyError if id unknown)."""
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
    """Remove one policy completely (KeyError if id unknown)."""
    with _conn() as c:
        if c.execute("DELETE FROM policy WHERE id=?", (id_,)).rowcount == 0:
            raise KeyError(id_)
