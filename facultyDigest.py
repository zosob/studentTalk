"""
facultyDigest.py

Weekly faculty analytics digest for FacultyTwin.

Why this exists: the grant proposal promises "Faculty reports: Weekly
analytic digests ... have enhanced timely responses to equity-related
trends," citing U-M's ECoach as precedent. The original repo's
/wellbeing_dashboard endpoint only returned a raw flag count -- no
per-student breakdown, no engagement trend, nothing a faculty member could
actually act on. This module builds that summary on top of the same
in-memory chat_history / wellbeing_flags used elsewhere in main.py.

Wire-up: main.py imports `build_weekly_digest` and exposes it at
GET /faculty_digest.
"""

import datetime
from collections import defaultdict
from typing import Any, Dict, List


def build_weekly_digest(chat_history: List[dict], wellbeing_flags: List[dict]) -> Dict[str, Any]:
    now = datetime.datetime.now()
    window_start = now - datetime.timedelta(days=7)

    def in_window(ts_str: str) -> bool:
        return datetime.datetime.fromisoformat(ts_str) >= window_start

    recent_messages = [m for m in chat_history if in_window(m["timestamp"])]
    recent_flags = [f for f in wellbeing_flags if in_window(f["timestamp"])]

    per_student: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {"message_count": 0, "wellbeing_scores": [], "flags": 0}
    )

    for msg in recent_messages:
        student = per_student[msg["student_id"]]
        student["message_count"] += 1
        if "wellbeing_score" in msg:
            student["wellbeing_scores"].append(msg["wellbeing_score"])

    for flag in recent_flags:
        per_student[flag["student_id"]]["flags"] += 1

    student_summary = {}
    at_risk_students = []
    for student_id, data in per_student.items():
        scores = data["wellbeing_scores"]
        avg_score = round(sum(scores) / len(scores), 2) if scores else None
        summary = {
            "message_count": data["message_count"],
            "flag_count": data["flags"],
            "avg_wellbeing_score": avg_score,
        }
        student_summary[student_id] = summary
        if data["flags"] > 0 or (avg_score is not None and avg_score < 3.0):
            at_risk_students.append(student_id)

    return {
        "window": {
            "start": window_start.isoformat(),
            "end": now.isoformat(),
        },
        "total_messages": len(recent_messages),
        "active_students": len(per_student),
        "total_flags": len(recent_flags),
        "at_risk_students": at_risk_students,
        "student_summary": student_summary,
    }


def render_digest_text(digest: Dict[str, Any], course_name: str = "your course") -> str:
    """Plain-text version suitable for an email nudge to faculty."""
    lines = [
        f"FacultyTwin weekly digest — {course_name}",
        f"Window: {digest['window']['start'][:10]} to {digest['window']['end'][:10]}",
        "",
        f"Active students: {digest['active_students']}",
        f"Total messages: {digest['total_messages']}",
        f"Wellbeing flags this week: {digest['total_flags']}",
        "",
    ]

    if digest["at_risk_students"]:
        lines.append("Students to check in on:")
        for student_id in digest["at_risk_students"]:
            s = digest["student_summary"][student_id]
            lines.append(
                f"  - {student_id}: {s['flag_count']} flag(s), "
                f"avg wellbeing {s['avg_wellbeing_score']}"
            )
    else:
        lines.append("No students flagged this week.")

    return "\n".join(lines)