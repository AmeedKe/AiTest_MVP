from backend.analytics import history_stats, infer_student_level, user_role
from backend.auth_service import count_admins
from backend.config import ROLE_ADMIN, ROLE_STUDENT
from backend.database import interactions, users


def list_all_users():
    return list(users.find({}, {"password": 0}).sort("username", 1))


def list_student_users():
    return [u for u in list_all_users() if user_role(u) == ROLE_STUDENT]


def add_student(username, password):
    users.insert_one({"username": username, "password": password, "role": ROLE_STUDENT})


def remove_user(username):
    users.delete_one({"username": username})
    interactions.delete_many({"username": username})


def can_remove_user(username, current_username):
    if username == current_username:
        return False, "לא ניתן להסיר את החשבון שאיתו אתה מחובר"
    target = users.find_one({"username": username})
    if target and user_role(target) == ROLE_ADMIN and count_admins() <= 1:
        return False, "לא ניתן להסיר את מנהל המערכת האחרון"
    return True, None


def build_student_snapshot(username):
    student_history = list(interactions.find({"username": username}).sort("timestamp", -1))
    stats = history_stats(student_history)
    return {
        "username": username,
        "practice_count": stats["count"],
        "avg_score": stats["avg"],
        "topics_count": len(stats["topics"]),
        "topics": stats["topics"],
        "last_activity": student_history[0].get("timestamp") if student_history else None,
        "level": infer_student_level(stats),
        "history": student_history,
        "stats": stats,
    }
