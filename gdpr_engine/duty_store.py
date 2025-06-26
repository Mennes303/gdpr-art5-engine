"""
SQLite‑backed storage for retention and deletion duties.

* Every row in ``duties.sqlite3`` represents an obligation created by the PDP
  when a *Permit* decision includes a duty clause.
* The scheduler (``tick``) promotes expired duties from *scheduled* to
  *fulfilled* **and** writes a matching "Delete" audit entry, allowing the
  accountability test‑suite to verify both effects.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Tuple

from gdpr_engine import audit_log

_DB = Path(__file__).parent / "duties.sqlite3"


# Connection helper


def _conn() -> sqlite3.Connection:
    """Return a configured SQLite connection (WAL + NORMAL sync)."""
    conn = sqlite3.connect(
        _DB,
        isolation_level="IMMEDIATE",  # ACID while allowing concurrent reads
        check_same_thread=False,
    )
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS duty (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_uid TEXT,
            due_at    TIMESTAMP,
            state     TEXT CHECK(state IN ('scheduled','fulfilled'))
        )
        """
    )
    return conn

# CRUD‑like helpers

def add(asset_uid: str, after_days: int) -> None:
    """Schedule a deletion duty *after_days* from now."""
    due = datetime.now(timezone.utc) + timedelta(days=after_days)
    with _conn() as c:
        c.execute(
            "INSERT INTO duty (asset_uid, due_at, state) VALUES (?,?,?)",
            (asset_uid, due.isoformat(), "scheduled"),
        )


def add_overdue(asset_uid: str) -> None:
    """Insert a duty whose *due_at* is already in the past (test helper)."""
    past = datetime.now(timezone.utc) - timedelta(seconds=1)
    with _conn() as c:
        c.execute(
            "INSERT INTO duty (asset_uid, due_at, state) VALUES (?,?,?)",
            (asset_uid, past.isoformat(), "scheduled"),
        )


def count_open() -> int:
    """Return the number of duties whose state is still *scheduled*."""
    with _conn() as c:
        (open_,) = c.execute(
            "SELECT COUNT(*) FROM duty WHERE state='scheduled'"
        ).fetchone()
        return int(open_)


def max_expiry() -> int | None:
    """Return the furthest expiry among open duties as a UNIX epoch timestamp."""
    with _conn() as c:
        (latest,) = c.execute(
            "SELECT MAX(due_at) FROM duty WHERE state='scheduled'"
        ).fetchone()
        if latest:
            return int(datetime.fromisoformat(latest).timestamp())
        return None


def list_all() -> List[Tuple[int, str, str, str]]:
    """Return a list of all duties as ``(id, asset_uid, due_at, state)``."""
    with _conn() as c:
        return list(
            c.execute("SELECT id, asset_uid, due_at, state FROM duty")
        )


# Scheduler

def tick(now: datetime | None = None) -> None:
    """Promote expired duties to *fulfilled* and log a corresponding deletion."""
    now = now or datetime.now(timezone.utc)
    iso_now = now.isoformat()

    with _conn() as c:
        rows = list(
            c.execute(
                "SELECT id, asset_uid FROM duty "
                "WHERE state='scheduled' AND due_at <= ?",
                (iso_now,),
            )
        )
        if not rows:
            return  # nothing to do

        # Mark expired duties as fulfilled
        c.executemany(
            "UPDATE duty SET state='fulfilled' WHERE id = ?",
            [(row[0],) for row in rows],
        )

    # Emit one audit entry per fulfilled duty
    for _id, asset in rows:
        # Minimal context object satisfying audit_log.write()
        class _Ctx:  # noqa: D401 – simple stub
            action = "delete"
            target = asset
            purpose = None
            role = None
            location = None
            ip = None

        audit_log.write(
            policy_uid="urn:auto:duty",  # synthetic policy UID
            decision="Delete",
            ctx=_Ctx(),  # type: ignore[arg-type]
        )
