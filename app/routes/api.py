# JSON API for the frontend

from __future__ import annotations
from datetime import date, timedelta
from flask import Blueprint, jsonify, request

from app.models import habits as habits_model
from app.models import db as db_model
from app.services import scoring

bp = Blueprint("api", __name__, url_prefix="/api")


# -------- Helpers --------


def ok(payload, status=200):
    """Wrap success responses in a consistent JSON shape."""
    return jsonify({"data": payload}), status


def err(code: str, message: str, status=400):
    """Wrap error response in a consistent JSON shape."""
    return jsonify({"error": code, "message": message}), status


def parse_iso_date(s: str | None):
    """Parse 'YYYY-MM-DD' to a date object. Return None if missing/empty."""
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        return "invalid"


# -------- Habits --------


@bp.get("/habits")
def list_habits():
    """Return all active habits (newest first)."""
    rows = habits_model.list_active_habits()
    return ok(rows)


@bp.post("/habits")
def create_habit():
    """Body: {"name": "Read 10 pages"}"""
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return err("name_required", "Please provide a non-empty name.", 400)
    try:
        row = habits_model.create_habit(name)
        return ok(row, 201)
    except ValueError as e:
        if str(e) == "invalid_name":
            return err("invalid_name", "Name must be 1-80 characters.", 400)
        return err("bad_request", "Could not create habit.", 400)


@bp.patch("/habits/<int:habit_id>")
def update_habit(habit_id: int):
    """Body may include: {"name": "New name"} and/or {"archived": true|false}"""
    data = request.get_json(silent=True) or {}
    try:
        row = habits_model.update_habit(
            habit_id,
            name=data.get("name"),
            archived=data.get("archived"),
        )
        return ok(row)
    except ValueError as e:
        if str(e) == "invalid_name":
            return err("invalid_name", "Name must be 1-80 characters.", 400)
        return err("bad_request", "Invalid fields.", 400)
    except LookupError:
        return err("not_found", "Habit not found.", 404)


# -------- Completions (specific date) --------


@bp.post("/habits/<int:habit_id>/complete")
def complete_day(habit_id: int):
    """Mark a habit completed for a date (default: today)."""
    d = parse_iso_date(request.args.get("date"))
    if d == "invalid":
        return err("invalid_date", "Use YYYY-MM-DD format.", 400)
    try:
        res = habits_model.complete_today(habit_id, (d.isoformat() if d else None))
        return ok(res, 201)
    except ValueError as e:
        if str(e) == "duplicate_or_invalid":
            return err(
                "duplicate", "Already completed for that date, or habit missing.", 409
            )
        return err("bad_request", "Could not mark completion.", 400)


@bp.delete("/habits/<int:habit_id>/complete")
def uncomplete_day(habit_id: int):
    """Remove completion for a date (default: today)."""
    d = parse_iso_date(request.args.get("date"))
    if d == "invalid":
        return err("invalid_date", "Use YYYY-MM-DD format.", 400)
    res = habits_model.uncomplete_today(habit_id, (d.isoformat() if d else None))
    if res.get("removed"):
        return ok(True, 200)
    return err("not_found", "No completion for that date.", 404)


@bp.get("/habits/<int:habit_id>/completions")
def range_completions(habit_id: int):
    """List completion dates for a habit in a range (default: last 30 days)."""
    today = date.today()
    d_from = parse_iso_date(request.args.get("from")) or (today - timedelta(days=30))
    d_to = parse_iso_date(request.args.get("to")) or today
    if d_from == "invalid" or d_to == "invalid" or d_from > d_to:
        return err("invalid_range", "Provide a valid date range.", 400)

    rows = habits_model.completions_in_range(
        habit_id, d_from.isoformat(), d_to.isoformat()
    )
    return ok(rows)


# -------- Stats --------


@bp.get("/stats")
def stats():
    """Return aggregate stats for the UI."""
    # ---- 1) Basic count and completions ----
    counts = habits_model.counts()
    allc = habits_model.fetch_all_completions()

    # ---- 2) Build a small window and compute "due habits" per day ----
    today = date.today()
    days_back = 60  # window for streak/longest calculations
    window_dates = [
        (today - timedelta(days=i)).isoformat() for i in range(days_back, -1, -1)
    ]

    # Build a transient due-by-date dict using the weekday-based helper
    due_by_date = {d: habits_model.habits_due_on(d) for d in window_dates}

    # ---- 3) Streaks using weekday schedule ----
    s = scoring.summarize_stats(
        total_active_habits=counts["total_habits"],
        total_completions=counts["total_completions"],
        all_completions=allc,
        due_by_date=due_by_date,
    )

    # ---- 4) Coins ----
    earned = db_model.earned_coins()
    spent = db_model.spent_coins()
    balance = db_model.current_balance()

    payload = {
        **s,
        "coins": {"earned": earned, "spent": spent, "balance": balance},
    }
    return ok(payload)
