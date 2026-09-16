"""
nudgeEngine.py

Deadline nudges for FacultyTwin.

Why this exists: the grant proposal promises "Nudges for deadlines: Email
and platform-based nudges show up to a 9% grade improvement, especially for
previously at-risk students." Nothing in the original repo tracked
assignments or sent reminders -- this module adds that.

Design:
- Faculty register deadlines via the FastAPI endpoint added in main.py
  (POST /deadlines).
- Students opt in via the Discord bot ("!subscribe_nudges" in discordBot.py).
- A background loop checks every few minutes for deadlines crossing the
  24-hour and 2-hour warning windows and DMs subscribed students once per
  window (tracked in `_sent_nudges` so no one gets spammed).

This is intentionally in-memory, matching the rest of the current codebase
(main.py still has "# In-memory storage (replace with database later)").
Swap the module-level dicts for real tables when the DB work happens.
"""

import asyncio
import datetime
from typing import Dict, List, Tuple

# assignment_id -> {"course": str, "title": str, "due": datetime.datetime}
deadlines: Dict[str, dict] = {}

# student_id -> discord user id (int)
subscribers: Dict[str, int] = {}

# (assignment_id, student_id, window_label) already nudged
_sent_nudges: set = set()

NUDGE_WINDOWS = [
    ("24h", datetime.timedelta(hours=24)),
    ("2h", datetime.timedelta(hours=2)),
]

CHECK_INTERVAL_SECONDS = 5 * 60  # check every 5 minutes


def add_deadline(assignment_id: str, course: str, title: str, due: datetime.datetime):
    deadlines[assignment_id] = {"course": course, "title": title, "due": due}


def remove_deadline(assignment_id: str):
    deadlines.pop(assignment_id, None)


def subscribe(student_id: str, discord_user_id: int):
    subscribers[student_id] = discord_user_id


def unsubscribe(student_id: str):
    subscribers.pop(student_id, None)


def _due_nudges(now: datetime.datetime) -> List[Tuple[str, dict, str]]:
    """Return (assignment_id, assignment, window_label) tuples that need a nudge right now."""
    due_now = []
    for assignment_id, assignment in deadlines.items():
        time_left = assignment["due"] - now
        for label, window in NUDGE_WINDOWS:
            # Nudge once the remaining time drops at/under the window,
            # as long as the deadline hasn't already passed.
            if datetime.timedelta(0) <= time_left <= window:
                due_now.append((assignment_id, assignment, label))
    return due_now


async def _send_nudge(bot, discord_user_id: int, assignment: dict, label: str):
    try:
        user = await bot.fetch_user(discord_user_id)
        readable_window = "tomorrow" if label == "24h" else "in 2 hours"
        await user.send(
            f"⏰ Reminder: **{assignment['title']}** ({assignment['course']}) "
            f"is due {readable_window} ({assignment['due'].strftime('%b %d, %I:%M %p')})."
        )
    except Exception as e:
        print(f"⚠️  Failed to send nudge to {discord_user_id}: {e}")


async def _nudge_loop(bot):
    while True:
        now = datetime.datetime.now()
        for assignment_id, assignment, label in _due_nudges(now):
            for student_id, discord_user_id in subscribers.items():
                key = (assignment_id, student_id, label)
                if key in _sent_nudges:
                    continue
                await _send_nudge(bot, discord_user_id, assignment, label)
                _sent_nudges.add(key)
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)


def start_nudge_loop(bot):
    """Call once, from discordBot.py's on_ready handler."""
    bot.loop.create_task(_nudge_loop(bot))