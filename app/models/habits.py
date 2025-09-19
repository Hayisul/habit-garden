# Data access layer

from datetime import date as _date
from .db import get_db
from sqlite3 import IntegrityError


# ---------- Habits ----------


def list_active_habits():
    """Return all non-archived habits (newest first)."""
    db = get_db()
    rows = db.execute(
        """
        SELECT id, name, created_at, archived_at
        FROM habits
        WHERE archived_at IS NULL
        ORDER BY id DESC;
        """
    ).fetchall()
    return [dict(row) for row in rows]


def create_habit(name: str):
    """Insert a new habit; return inserted row as dict."""
    name = (name or "").strip()
    if not name or len(name) > 80:
        raise ValueError("invalid_name")
    db = get_db()
    cur = db.execute("INSERT INTO habits(name) VALUES (?);", (name,))

    habit_id = cur.lastrowid
    row = db.execute(
        "SELECT id, name, created_at, archived_at FROM habits WHERE id=?", (habit_id,)
    ).fetchone()
    return dict(row)


def update_habit(habit_id: int, name: str | None = None, archived: bool | None = None):
    """Rename and/or archive a habit. Return updated row."""
    db = get_db()
    if name is not None:
        name = name.strip()
        if not name or len(name) > 80:
            raise ValueError("invalid_name")
        db.execute("UPDATE habits SET name=? WHERE id=?;", (name, habit_id))
    if archived is True:
        db.execute("UPDATE habits SET archived_at=DATE('now') WHERE id=?;", (habit_id,))
    elif archived is False:
        db.execute("UPDATE habits SET archived_at=NULL WHERE id=?;", (habit_id,))

    row = db.execute(
        "SELECT id, name, created_at, archived_at FROM habits WHERE id=?;", (habit_id,)
    ).fetchone()
    if not row:
        raise LookupError("not_found")
    return dict(row)


# ---------- Completions ----------


def _today_str():
    return _date.today().isoformat()  # YYYY-MM-DD


def complete_today(habit_id: int, date_str: str | None = None):
    """Mark the habit complete for a date (default: today)."""
    db = get_db()
    date_str = date_str or _today_str()
    try:
        db.execute(
            "INSERT INTO completions(habit_id, date) VALUES (?, ?);",
            (habit_id, date_str),
        )
    except IntegrityError as e:
        raise ValueError("duplicate_or_invalid") from e

    return {"habit_id": habit_id, "date": date_str}  # return new dict


def uncomplete_today(habit_id: int, date_str: str | None = None):
    """Remove completion for the given date (default: today)."""
    db = get_db()
    date_str = date_str or _today_str()
    cur = db.execute(
        "DELETE FROM completions WHERE habit_id=? AND date=?;",
        (habit_id, date_str),
    )
    return {"removed": cur.rowcount > 0}


def completions_in_range(habit_id: int, start_date: str, end_date: str):
    """Showcase progress. List completions between two dates (e.g., last 30 days)."""
    db = get_db()
    rows = db.execute(
        """
        SELECT date
        FROM completions
        WHERE habit_id=? AND date BETWEEN ? AND ?
        ORDER BY date ASC;
        """,
        (habit_id, start_date, end_date),
    ).fetchall()
    return [dict(row) for row in rows]


# ---------- Stats ----------


def fetch_all_completions():
    """Return all completions as a list of dicts: {'habit_id', 'date'}."""
    db = get_db()
    rows = db.execute(
        "SELECT habit_id, date FROM completions ORDER BY date ASC;"
    ).fetchall()
    return [dict(row) for row in rows]


def counts():
    """Return simple counts used in stats."""
    db = get_db()
    total_habits = db.execute(
        "SELECT COUNT(*) AS c FROM habits WHERE archived_at IS NULL;"
    ).fetchone()["c"]
    total_completions = db.execute("SELECT COUNT(*) AS c FROM completions").fetchone()[
        "c"
    ]
    return {"total_habits": total_habits, "total_completions": total_completions}


# ---------- Scheduling ----------


def habits_due_on(day: str | None = None):
    """Return the set of habits IDs due on a given date (default: today)."""
    db = get_db()
    d = _date.fromisoformat(day) if day else _date.today()
    weekday = d.weekday()
    rows = db.execute(
        """
        SELECT id, frequency, weekly_mask
        FROM habits
        WHERE archived_at IS NULL;
        """
    ).fetchall()

    due = set()
    for row in rows:
        if row["frequency"] == "daily":
            due.add(row["id"])
        elif row["frequency"] == "custom":
            mask = row["weekly_mask"] or "0000000"
            if len(mask) == 7 and mask[weekday] == "1":
                due.add(row["id"])

    return due
