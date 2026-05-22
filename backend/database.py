import os

from dotenv import load_dotenv
from openai import OpenAI
from pymongo import MongoClient

from backend.config import ROOT_DIR

load_dotenv(ROOT_DIR / ".env")

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

try:
    mongo_client = MongoClient(os.getenv("MONGO_URI"), serverSelectionTimeoutMS=3000)
    db = mongo_client["iTest_DB"]
    interactions = db["interactions"]
    users = db["users"]
    config = db["config"]
except Exception:
    db = None
    interactions = None
    users = None
    config = None


def is_db_connected():
    return db is not None
