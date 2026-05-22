from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
TEMP_AUDIO_PATH = ROOT_DIR / "temp_audio.wav"

ROLE_ADMIN = "admin"
ROLE_STUDENT = "student"

CONFIG_ADMIN_TOKEN_ID = "admin_registration_token"
CONFIG_PASSWORD_RESET_TOKEN_ID = "password_reset_token"

PRACTICE_TOPICS = [
    "טכנולוגיה",
    "ספורט",
    "בית ספר ולימודים",
    "משפחה וחברים",
    "קריירה ועתיד",
    "תחביבים",
    "רשתות חברתיות",
]
