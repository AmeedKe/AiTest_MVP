from datetime import datetime

from backend.database import interactions


def get_user_history(username):
    return list(interactions.find({"username": username}).sort("timestamp", -1))


def save_interaction(username, topic, question, text, feedback):
    interactions.insert_one(
        {
            "username": username,
            "topic": topic,
            "question": question,
            "text": text,
            "feedback": feedback,
            "timestamp": datetime.now(),
        }
    )
