import os

from dotenv import load_dotenv
from openai import OpenAI
from pymongo import MongoClient

from backend.config import ROOT_DIR

load_dotenv(ROOT_DIR / ".env")

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

db_error = None

try:
    mongo_uri = os.getenv("MONGO_URI")
    if not mongo_uri:
        raise ValueError("MONGO_URI is missing from environment variables / Streamlit Secrets.")
    
    mongo_client = MongoClient(mongo_uri, serverSelectionTimeoutMS=3000)
    # Force a connection check by sending a ping command
    mongo_client.admin.command('ping')
    
    db = mongo_client["iTest_DB"]
    interactions = db["interactions"]
    users = db["users"]
    config = db["config"]
except Exception as e:
    db = None
    interactions = None
    users = None
    config = None
    db_error = str(e)


def is_db_connected():
    return db is not None


def get_db_error():
    return db_error

