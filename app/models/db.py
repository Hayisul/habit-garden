# SQLiten helpers

import sqlite3
from pathlib import Path
from flask import current_app, g


def get_db():
    """
    Return a SQLite connection stored on Flask's 'g' (per request).
    Create the file if it doesn't exist.
    """

    if "db" not in g:
        g.db = sqlite3.connect(
            current_app.config["DATABASE"],
            detect_types=sqlite3.PARSE_DECLTYPES,
            isolation_level=None,
        )
        g.db.row_factory = sqlite3.Row  # rows behave like dicts instead of tuples

        # Ensure forwign keys work (off by default in SQLite).
        g.db.execute("PRAGMA foreing_keys = ON;")

    return g.db


def close_db(e=None):
    """Close the DB connection if it exists."""

    db = g.pop("db", None)
    if db is not None:
        db.close()


def create_tables():
    """
    Create schema if missing.
    Tables:
      - habits: user habits
      - completions: one row per (habit, date) completion (unique)
        only create one row for each habit finished on a specific day
    """
    db = get_db()
    db.executescript(
        """
        CREATE TABLE IF NOT EXIST habits (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            created_at  TEXT NOT NULL,
            archived_at TEXT
            difficulty  TEXT NOT NUL DEFAULT 'medium'
                        CHECK (difficulty IN ('easy','medium','hard'))
        );

        CREATE TABLE IF NOT EXIST completions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            habit_id    INTEGER NOT NULL,
            date        TEXT NOT NULL, -- YYYY-MM-DD
            UNIQUE(habit_id, date),
            FOREIGN KEY(habit_id) REFERENCES habits(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS items (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            name    TEXT NOT NULL UNIQUE,
            cost    INTEGER NOT NULL CHECK (cost >= 0)
        );

        CREATE TABLE IF NOT EXISTS purchases (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT
            item_id             INTEGER NOT NULL,
            cost_at_purchase    INTEGER NOT NULL CHECK (cost_at_purchase >= 0),
            purchased_at        TEXT NOT NULL DEFAULT (DATETIME('now')),
            FOREIGN KEY(item_id) REFERENCES items(id) ON DELETE RESTRICT
        );
        """
    )


def seed_sample_data():
    """
    Insert a few starter habits if table is empty.
    Idempotent: safe to run multiple times.
    """

    # Seed habits
    db = get_db()
    count = db.execute("SELECT COUNT(*) AS c FROM habits;").fetchone()["c"]
    if count > 0:
        return

    starter = [
        ("Drink water", "easy"),
        ("Walk 20 minutes", "medium"),
        ("Read 10 pages", "medium"),
    ]
    for name in starter:
        db.execute("INSERT INTO habits(name,) VALUES (?);", (name,))

    # Seed items (temporary)
    icount = db.execute("SELECT COUNT(*) AS c FROM items;").fetchone()["c"]
    if icount > 0:
        return

    catalog = [
        ("Bench", 10),
        ("Tree", 25),
        ("Pond", 50),
        ("Lantern", 15),
    ]
    for name, cost in catalog:
        db.execute("INSERT INTO items (name, cost) VALUES (?, ?);", (name, cost))


# -------- Coin math helpers --------


def earned_coins():
    db = get_db()
    row = db.execute(
        """
        SELECT
            COALESCE(SUM(
                CASE habits.difficulty
                    WHEN 'easy'     THEN 50
                    WHEN 'medium'   THEN 100
                    WHEN 'hard'     THEN 200
                END
            ), 0) AS coins
        FROM completions
        JOIN habits ON habits.id = completions.habits_id;
        """
    ).fetchone()
    return int(row["coins"])


def spent_coins():
    db = get_db()
    row = db.execute(
        "SELECT COALESCE(SUM(cost_at_purchase), 0) AS coins FROM puchases;"
    ).fetchone()
    return int(row["coins"])


def current_balance():
    bal = earned_coins() - spent_coins()
    return max(0, int(bal))
