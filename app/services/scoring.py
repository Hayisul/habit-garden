# Streak and currency calculations

from __future__ import annotations
from datetime import date as _date
from collections import defaultdict
from typing import Dict, Set, List


# -------- Helpers --------


def _index_comps_by_date(
    all_completions: List[dict],
) -> Dict[str, Set[int]]:
    """
    Turn a list like [{'habit_id': 1, 'date': 'YYYY-MM-DD'}, ...]
    into a dict like 'YYYY-MM-DD' -> {habit_id, ...}
    """
    by_date: Dict[str, Set[int]] = defaultdict(set)
    for row in all_completions:
        by_date[row["date"]].add(int(row["habit_id"]))
    return by_date


def _today_str() -> str:
    return _date.today().isoformat()


# -------- Current streak --------


def current_streak(
    all_completions: List[dict],
    due_by_date: Dict[str, Set[int]],
) -> int:
    """
    Count the *current* streak up to today, walking backward.
    Return the consecutive *due* days where all due habits were completed.
    """
    if not due_by_date:
        return 0

    comps_by_date = _index_comps_by_date(all_completions)
    streak = 0
    today = _today_str()
    dates = sorted(set([*due_by_date.keys(), today]), reverse=True)

    for d in dates:
        due_set = due_by_date.get(d, set())
        if not due_set:
            continue

        completed = comps_by_date.get(d, set())
        if due_set.issubset(completed):
            streak += 1
        else:
            break

    return streak


# -------- Longest streak --------


def longest_streak(
    all_completions: List[dict],
    due_by_date: Dict[str, Set[int]],
) -> int:
    """Keep track of max seen."""
    if not due_by_date:
        return 0

    comps_by_date = _index_comps_by_date(all_completions)
    best = cur = 0

    for d in sorted(due_by_date.keys()):
        due_set = due_by_date[d]
        if not due_set:
            continue

        completed = comps_by_date.get(d, set())
        if due_set.issubset(completed):
            cur += 1
            if cur > best:
                best = cur
        else:
            cur = 0

    return best


# -------- Currency --------


def currency(total_completions: int, cur_streak: int) -> int:
    return int(total_completions + max(0, cur_streak - 1))


# -------- Public summarizer --------


def summarize_stats(
    total_active_habits: int,
    total_completions: int,
    all_completions: List[dict],
    due_by_date: Dict[str, Set[int]],
) -> dict:
    """
    Produce the full stats payload using the streak rule.
    Return keys the UI expects.
    """
    cur = current_streak(all_completions, due_by_date)
    long = longest_streak(all_completions, due_by_date)
    coins = currency(total_completions, cur)
    return {
        "total_habits": total_active_habits,
        "total_completions": total_completions,
        "current_streak": cur,
        "longest_streak": long,
        "currency": coins,
    }
