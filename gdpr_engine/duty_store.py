"""
SQLite-backed storage for retention / deletion duties.

Each row represents an obligation created by the PDP when a *PERMIT* decision
includes `delete_after = N`.  A separate scheduler calls `tick()` once per
minute to mark expired duties as `overdue` and trigger the actual delete.

"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Tuple

_DB = Path(__file__).parent / "duties.sqlite3"

# ──────────────────────────────────────────────────────────────────────────
# Connection helper
# ──────────────────────────────────────────────────────────────────────────

def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(
        _DB,
        isolation_level="IMMEDIATE",     # ACID, allows concurrent reads
        check_same_thread=False,
    )
    conn.execute("PRAGMA journal_mode=WAL;")    # enable write‑ahead logging
    conn.execute("PRAGMA synchronous=NORMAL;")  # optional fsync tuning

    conn.execute(
        """CREATE TABLE IF NOT EXISTS duty (
               id          INTEGER PRIMARY KEY AUTOINCREMENT,
               asset_uid   TEXT,
               due_at      TIMESTAMP,
               state       TEXT CHECK(state IN ('scheduled','fulfilled','overdue'))
           )"""
    )
    return conn

# ──────────────────────────────────────────────────────────────────────────
# CRUD‑like helpers
# ──────────────────────────────────────────────────────────────────────────

def add(asset_uid: str, after_days: int) -> None:
    """Schedule a deletion duty `after_days` from now."""
    due = datetime.now(timezone.utc) + timedelta(days=after_days)
    with _conn() as c:
        c.execute(
            "INSERT INTO duty (asset_uid, due_at, state) VALUES (?,?,?)",
            (asset_uid, due.isoformat(), "scheduled"),
        )

def tick(now: datetime | None = None) -> None:
    """Mark scheduled duties whose `due_at` < *now* as overdue."""
    now = now or datetime.now(timezone.utc)
    with _conn() as c:
        c.execute(
            "UPDATE duty SET state='overdue' WHERE state='scheduled' AND due_at < ?",
            (now.isoformat(),),
        )

def list_all() -> List[Tuple[int, str, str, str]]:
    """Return a list of all duties: (id, asset_uid, due_at, state)."""
    with _conn() as c:
        return list(c.execute("SELECT id, asset_uid, due_at, state FROM duty"))
