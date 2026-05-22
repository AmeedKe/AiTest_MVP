from datetime import datetime

from backend.analytics import user_role
from backend.config import (
    CONFIG_ADMIN_TOKEN_ID,
    CONFIG_PASSWORD_RESET_TOKEN_ID,
    ROLE_ADMIN,
    ROLE_STUDENT,
)
from backend.database import config, users


def get_config_token(token_id):
    if config is None:
        return None
    doc = config.find_one({"_id": token_id})
    return (doc or {}).get("value")


def verify_config_token(token_id, token):
    stored = get_config_token(token_id)
    if not stored or not token:
        return False
    return token.strip() == stored.strip()


def set_config_token(token_id, new_token):
    config.update_one(
        {"_id": token_id},
        {"$set": {"value": new_token.strip(), "updated_at": datetime.now()}},
        upsert=True,
    )


def get_admin_registration_token():
    return get_config_token(CONFIG_ADMIN_TOKEN_ID)


def verify_admin_registration_token(token):
    return verify_config_token(CONFIG_ADMIN_TOKEN_ID, token)


def set_admin_registration_token(new_token):
    set_config_token(CONFIG_ADMIN_TOKEN_ID, new_token)


def get_password_reset_token():
    return get_config_token(CONFIG_PASSWORD_RESET_TOKEN_ID)


def verify_password_reset_token(token):
    return verify_config_token(CONFIG_PASSWORD_RESET_TOKEN_ID, token)


def set_password_reset_token(new_token):
    set_config_token(CONFIG_PASSWORD_RESET_TOKEN_ID, new_token)


def authenticate(username, password):
    return users.find_one({"username": username.strip(), "password": password})


def find_user(username):
    return users.find_one({"username": username.strip()})


def register_user(username, password, role):
    users.insert_one({"username": username, "password": password, "role": role})
    return {"username": username, "role": role}


def reset_user_password(username, new_password):
    result = users.update_one(
        {"username": username.strip()},
        {"$set": {"password": new_password}},
    )
    return result.matched_count > 0


def count_admins():
    return users.count_documents({"role": ROLE_ADMIN})


def validate_registration(username, password, password2, want_admin, admin_token):
    u = (username or "").strip()
    if not u or not password:
        return False, "⚠️ נא למלא שם משתמש וסיסמה"
    if len(u) < 2:
        return False, "⚠️ שם משתמש קצר מדי (לפחות 2 תווים)"
    if len(password) < 4:
        return False, "⚠️ סיסמה קצרה מדי (לפחות 4 תווים)"
    if password != password2:
        return False, "❌ הסיסמאות אינן תואמות"
    if want_admin and not verify_admin_registration_token(admin_token):
        return False, "❌ TOKEN מנהל שגוי. הרשמה כמנהל אפשרית רק עם TOKEN תקין מ-MongoDB."
    if find_user(u):
        return False, "❌ שם המשתמש כבר תפוס — בחר שם אחר"
    role = ROLE_ADMIN if want_admin else ROLE_STUDENT
    return True, role


def validate_password_reset(username, new_password, new_password2, token):
    u = (username or "").strip()
    if not u or not new_password or not token:
        return False, "⚠️ נא למלא שם משתמש, TOKEN וסיסמה חדשה"
    if len(new_password) < 4:
        return False, "⚠️ סיסמה קצרה מדי (לפחות 4 תווים)"
    if new_password != new_password2:
        return False, "❌ הסיסמאות החדשות אינן תואמות"
    if not verify_password_reset_token(token):
        return False, "❌ TOKEN איפוס סיסמה שגוי"
    if not find_user(u):
        return False, "❌ משתמש לא נמצא במערכת"
    return True, None
