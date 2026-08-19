"""
streak_service.py
Tracks the student's daily study streak.

Rules:
  - Completing at least one quiz on a calendar day counts that day.
  - Multiple quizzes on the same day still count as just one day.
  - If the previous study day was yesterday, the streak continues (+1).
  - If a day (or more) was missed, the streak resets to 1.
  - The longest streak ever reached is remembered separately.
"""

from datetime import date, timedelta
from database import get_db


def get_streak_info() -> dict:
    """
    Return the current streak state for display.
    If more than one day has passed since the last study date, the
    *displayed* current streak shows as broken (0) even though the stored
    value only officially resets the next time a quiz is completed.
    """
    db = get_db()
    row = db.execute("SELECT * FROM streak WHERE id = 1").fetchone()
    db.close()

    if row is None:
        return {"current_streak": 0, "longest_streak": 0, "last_study_date": None}

    current = row["current_streak"]
    last = row["last_study_date"]

    if last:
        last_date = date.fromisoformat(last)
        days_since = (date.today() - last_date).days
        if days_since > 1:
            current = 0  # streak is broken, will officially reset on next quiz

    return {
        "current_streak": current,
        "longest_streak": row["longest_streak"],
        "last_study_date": last,
    }


def record_study_session() -> dict:
    """
    Call this whenever a quiz is completed. Updates the streak according
    to the rules above and returns the fresh streak info.
    """
    db = get_db()
    row = db.execute("SELECT * FROM streak WHERE id = 1").fetchone()
    today = date.today().isoformat()

    if row is None:
        db.execute(
            "INSERT INTO streak (id, current_streak, longest_streak, last_study_date) "
            "VALUES (1, 1, 1, ?)",
            (today,),
        )
        db.commit()
        db.close()
        return {"current_streak": 1, "longest_streak": 1, "last_study_date": today}

    last = row["last_study_date"]
    current = row["current_streak"]
    longest = row["longest_streak"]

    if last == today:
        # Already studied today - no change, just keep it as is.
        pass
    else:
        if last is not None:
            last_date = date.fromisoformat(last)
            yesterday = date.today() - timedelta(days=1)
            if last_date == yesterday:
                current += 1
            else:
                current = 1
        else:
            current = 1

        longest = max(longest, current)

        db.execute(
            "UPDATE streak SET current_streak = ?, longest_streak = ?, last_study_date = ? "
            "WHERE id = 1",
            (current, longest, today),
        )
        db.commit()

    db.close()
    return {"current_streak": current, "longest_streak": longest, "last_study_date": today}
