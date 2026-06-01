import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["iTest_DB"]
users_col = db["users"]
config_col = db["config"]

ROLE_STUDENT = "student"
ROLE_ADMIN = "admin"
CONFIG_ADMIN_TOKEN_ID = "admin_registration_token"
CONFIG_PASSWORD_RESET_TOKEN_ID = "password_reset_token"
DEFAULT_ADMIN_TOKEN = os.getenv("ADMIN_REGISTRATION_TOKEN", "AiTest-Admin-2026")
DEFAULT_PASSWORD_RESET_TOKEN = os.getenv("PASSWORD_RESET_TOKEN", "AiTest-Reset-2026")

users = [
    {"username": "gadi", "password": "123", "role": ROLE_STUDENT},
    {"username": "ameed", "password": "123", "role": ROLE_STUDENT},
    {"username": "student", "password": "123", "role": ROLE_STUDENT},
    {"username": "admin", "password": "admin123", "role": ROLE_ADMIN},
]

for u in users:
    existing = users_col.find_one({"username": u["username"]})
    if not existing:
        users_col.insert_one(u)
    elif "role" not in existing:
        users_col.update_one({"username": u["username"]}, {"$set": {"role": u["role"]}})

users_col.update_many({"role": {"$exists": False}}, {"$set": {"role": ROLE_STUDENT}})

if not config_col.find_one({"_id": CONFIG_ADMIN_TOKEN_ID}):
    config_col.insert_one({"_id": CONFIG_ADMIN_TOKEN_ID, "value": DEFAULT_ADMIN_TOKEN})
    print(f"Admin registration TOKEN created: {DEFAULT_ADMIN_TOKEN}")
else:
    print("Admin registration TOKEN already exists (unchanged).")

if not config_col.find_one({"_id": CONFIG_PASSWORD_RESET_TOKEN_ID}):
    config_col.insert_one({"_id": CONFIG_PASSWORD_RESET_TOKEN_ID, "value": DEFAULT_PASSWORD_RESET_TOKEN})
    print(f"Password reset TOKEN created: {DEFAULT_PASSWORD_RESET_TOKEN}")
else:
    print("Password reset TOKEN already exists (unchanged).")

print("Users ready!")
print("Students: gadi, ameed, student — password: 123")
print("Admin user: admin — password: admin123")
print("Forgot password TOKEN (for students):", DEFAULT_PASSWORD_RESET_TOKEN)
