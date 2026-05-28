import re
from datetime import datetime

from backend.config import ROLE_STUDENT


def user_role(user):
    return user.get("role", ROLE_STUDENT) if user else ROLE_STUDENT


def extract_score(feedback):
    if not feedback:
        return None
    patterns = [
        r"ציון[:\s]*(\d{1,2})",
        r"(\d{1,2})\s*/\s*10",
        r"(\d{1,2})\s*מתוך\s*10",
        r"(\d{1,2})\s*מ-?10",
    ]
    for pattern in patterns:
        match = re.search(pattern, str(feedback), re.IGNORECASE)
        if match:
            score = int(match.group(1))
            if 1 <= score <= 10:
                return score
    return None


def history_stats(history):
    scores = [s for s in (extract_score(h.get("feedback")) for h in history) if s is not None]
    topics = {}
    for item in history:
        topic = item.get("topic", "כללי")
        topics[topic] = topics.get(topic, 0) + 1
    return {
        "count": len(history),
        "scores": scores,
        "avg": round(sum(scores) / len(scores), 1) if scores else None,
        "topics": topics,
    }


def format_activity_time(ts):
    if not ts:
        return "—"
    if isinstance(ts, datetime):
        return ts.strftime("%d/%m/%Y %H:%M")
    return str(ts)


def infer_student_level(stats):
    if stats["count"] == 0:
        return "לא התחיל"
    if stats["avg"] is None:
        return "בתהליך"
    if stats["avg"] >= 8:
        return "מתקדם"
    if stats["avg"] >= 5:
        return "בינוני"
    return "מתחיל"
