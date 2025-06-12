import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Tuple

_DB = Path(__file__).parent / "duties.sqlite3"


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(_DB)
    c.execute(
        """CREATE TABLE IF NOT EXISTS duty (
               id          INTEGER PRIMARY KEY AUTOINCREMENT,
               asset_uid   TEXT,
               due_at      TIMESTAMP,
               state       TEXT CHECK(state IN ('scheduled','fulfilled','overdue'))
           )"""
    )
    return c


def add(asset_uid: str, after_days: int) -> None:
    due = datetime.now(timezone.utc) + timedelta(days=after_days)
    with _conn() as c:
        c.execute(
            "INSERT INTO duty (asset_uid, due_at, state) VALUES (?,?,?)",
            (asset_uid, due.isoformat(), "scheduled"),
        )


def tick(now: datetime | None = None) -> None:
    """Mark scheduled duties whose due_at < now as overdue."""
    now = now or datetime.now(timezone.utc)
    with _conn() as c:
        c.execute(
            "UPDATE duty SET state='overdue' WHERE state='scheduled' AND due_at < ?",
            (now.isoformat(),),
        )


def list_all() -> List[Tuple[int, str, str, str]]:
    with _conn() as c:
        return list(c.execute("SELECT id, asset_uid, due_at, state FROM duty"))
