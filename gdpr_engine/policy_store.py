"""
SQLite-backed storage for ODRL / GDPR policies.

The table stores the raw JSON plus bookkeeping fields so we can
version-track (created_at / updated_at) and keep an external UID if needed.

On first connection the DB is:
• switched to WAL mode for better concurrency,
• seeded with the two fixture policies (tests/fixtures/policy-1.json / -2.json)
  so the test-suite can load them by id = 1 / 2 without an extra helper.
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

# ──────────────────────────────────────────────────────────────────────────
# Connection helper
# ──────────────────────────────────────────────────────────────────────────
def _conn() -> sqlite3.Connection:
    """Return a WAL-enabled connection; create/seed the table on first use."""
    conn = sqlite3.connect(
        _DB,
        isolation_level="IMMEDIATE",   # ACID, allows parallel readers
        check_same_thread=False,       # FastAPI workers can share
    )
    conn.execute("PRAGMA journal_mode=WAL;")     # enable write-ahead logging
    conn.execute("PRAGMA synchronous=NORMAL;")   # fsync once per checkpoint

    # Create schema if missing
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

    # ── Seed fixture policies only if the table is empty ───────────────────
    if conn.execute("SELECT COUNT(*) FROM policy").fetchone()[0] == 0:
        now = datetime.now(timezone.utc).isoformat()
        for path, uid in _FIXTURES:
            raw = Path(path).read_text(encoding="utf-8")
            conn.execute(
                "INSERT INTO policy (uid, body, created_at, updated_at) "
                "VALUES (?, ?, ?, ?)",
                (uid, raw, now, now),
            )

    return conn


# ──────────────────────────────────────────────────────────────────────────
# CRUD helpers
# ──────────────────────────────────────────────────────────────────────────
def create(body: str, *, uid: str) -> int:
    """Insert a new policy and return its row-id (int)."""
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO policy (uid, body, created_at, updated_at)"
            " VALUES (?, ?, ?, ?)",
            (uid, body, now, now),
        )
        rowid = cur.lastrowid
        if rowid is None:
            raise RuntimeError("SQLite failed to return lastrowid")
        return int(rowid)


def read(id_: int) -> str:
    """Return the raw JSON string for one policy (KeyError if id unknown)."""
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
