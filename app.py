import streamlit as st
import os
import re
from openai import OpenAI
from pymongo import MongoClient
from datetime import datetime
from dotenv import load_dotenv

ROLE_ADMIN = "admin"
ROLE_STUDENT = "student"
CONFIG_ADMIN_TOKEN_ID = "admin_registration_token"
CONFIG_PASSWORD_RESET_TOKEN_ID = "password_reset_token"

# --- הגדרות ה-API ---
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

try:
    mongo_client = MongoClient(os.getenv("MONGO_URI"), serverSelectionTimeoutMS=3000)
    db = mongo_client["iTest_DB"]
    collection = db["interactions"]
    users_collection = db["users"]
    config_collection = db["config"]
except Exception:
    db = None
    config_collection = None


def user_role(user):
    return user.get("role", ROLE_STUDENT) if user else ROLE_STUDENT


def set_session_user(user):
    st.session_state.logged_in = True
    st.session_state.username = user["username"]
    st.session_state.role = user_role(user)
    st.session_state.is_admin = st.session_state.role == ROLE_ADMIN


def clear_session_user():
    for key in list(st.session_state.keys()):
        if key.startswith("_"):
            continue
        del st.session_state[key]
    st.session_state.logged_in = False


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


def generate_level_summary(openai_client, username, history):
    stats = history_stats(history)
    recent = history[:12]
    lines = []
    for i, item in enumerate(recent, 1):
        score = extract_score(item.get("feedback"))
        score_txt = f"ציון {score}/10" if score else "ללא ציון מפורש"
        lines.append(
            f"{i}. נושא: {item.get('topic', 'כללי')} | {score_txt}\n"
            f"   שאלה: {item.get('question', '')[:120]}\n"
            f"   תשובה: {(item.get('text') or '')[:200]}\n"
            f"   משוב: {(item.get('feedback') or '')[:300]}"
        )
    history_text = "\n\n".join(lines) if lines else "אין תרגולים"
    avg_line = f"ממוצע ציונים (מתוך תרגולים עם ציון): {stats['avg']}/10" if stats["avg"] else "אין מספיק ציונים מספריים"
    topics_line = ", ".join(f"{k} ({v})" for k, v in stats["topics"].items()) or "אין"

    response = openai_client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "אתה מורה לעברית. על בסיס היסטוריית התרגול, כתוב סיכום קצר בעברית לתלמיד/ה: "
                    "רמת כישורים (מתחיל/בינוני/מתקדם), חוזקות, נקודות לשיפור, והמלצה לתרגול הבא. "
                    "השתמש בכותרות קצרות ורשימות. 150-250 מילים."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"תלמיד: {username}\n"
                    f"סה\"כ תרגולים: {stats['count']}\n"
                    f"{avg_line}\n"
                    f"נושאים שתורגלו: {topics_line}\n\n"
                    f"תרגולים אחרונים:\n{history_text}"
                ),
            },
        ],
    )
    return response.choices[0].message.content, stats


def count_admins():
    return users_collection.count_documents({"role": ROLE_ADMIN})


def get_config_token(token_id):
    if config_collection is None:
        return None
    doc = config_collection.find_one({"_id": token_id})
    return (doc or {}).get("value")


def verify_config_token(token_id, token):
    stored = get_config_token(token_id)
    if not stored or not token:
        return False
    return token.strip() == stored.strip()


def set_config_token(token_id, new_token):
    config_collection.update_one(
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


def reset_user_password(username, new_password):
    result = users_collection.update_one(
        {"username": username.strip()},
        {"$set": {"password": new_password}},
    )
    return result.matched_count > 0


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


def build_student_snapshot(username):
    student_history = list(
        collection.find({"username": username}).sort("timestamp", -1)
    )
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


def list_student_users():
    return [
        u for u in users_collection.find({}, {"password": 0}).sort("username", 1)
        if user_role(u) == ROLE_STUDENT
    ]


# --- הגדרות עמוד ---
st.set_page_config(page_title="iTest", page_icon="🪄", layout="centered")

# --- CSS ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Heebo:wght@300;400;600;800;900&display=swap');
* { font-family: 'Heebo', sans-serif !important; }
.stApp {
    background: linear-gradient(-45deg, #FF9A9E, #FECFEF, #A1C4FD, #C2E9FB);
    background-size: 400% 400%;
    animation: gradientBG 15s ease infinite;
}
@keyframes gradientBG {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}
body, .stMarkdown, .stText, .stChatMessage, .ai-response-box, p, div[data-testid="stChatMessageContent"] {
    direction: rtl !important;
    text-align: right !important;
    color: #000000 !important;
}
ul, ol { direction: rtl !important; text-align: right !important; padding-right: 20px !important; }
li { text-align: right !important; }
div.block-container {
    background: rgba(255, 255, 255, 0.85);
    backdrop-filter: blur(25px);
    border-radius: 40px;
    box-shadow: 0 40px 80px rgba(0,0,0,0.1) !important;
    padding: 4rem 3rem 5rem 3rem !important;
    max-width: 800px !important;
    margin-top: 5vh;
}
h1 {
    font-weight: 900 !important; font-size: 4.5rem !important;
    background: linear-gradient(45deg, #ff416c, #ff4b2b);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    text-align: center;
}
h3.subtitle { text-align: center; color: #4A4A4A; margin-bottom: 3rem !important; }
.ai-response-box {
    font-size: 1.4rem; background: #fdfbfb; padding: 20px;
    border-radius: 20px; border-right: 5px solid #ff4b2b;
}

/* עיצוב כפתורים ברור ובולט */
.stButton > button {
    background-color: #ffffff !important;
    border: 2px solid #ff4b2b !important;
    border-radius: 12px !important;
    font-weight: bold !important;
    transition: 0.3s !important;
}
.stButton > button p {
    color: #000000 !important;
    transition: 0.3s !important;
}
.stButton > button:hover {
    background-color: #ff4b2b !important;
}
.stButton > button:hover p {
    color: #ffffff !important;
}
/* תיקון פונט של אייקונים ב-Streamlit כדי למנוע הופעת טקסט קוד */
.stIcon, .material-symbols-rounded, [data-testid="stIconMaterial"] {
    font-family: "Material Symbols Rounded" !important;
}

/* העלמת הכיתוב Press Enter to apply מתיבות הטקסט */
div[data-testid="InputInstructions"] {
    display: none !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown("<h1>iTest ✨</h1>", unsafe_allow_html=True)
st.markdown("<h3 class='subtitle'>המורה הווירטואלי והחכם לעברית</h3>", unsafe_allow_html=True)

if db is None:
    st.error("⚠️ לא ניתן להתחבר למסד הנתונים. ודא שה-MongoDB Cluster שלך פועל (Resume) ושה-MONGO_URI תקין.")
    st.stop()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# =========================
# 🔐 כניסה / הרשמת משתמש חדש
# =========================
if not st.session_state.logged_in:
    st.markdown("<h2 style='text-align:center;'>🔐 כניסה למערכת</h2>", unsafe_allow_html=True)
    login_tab, register_tab = st.tabs(["כניסה", "משתמש חדש — הרשמה"])

    with login_tab:
        username = st.text_input("שם משתמש", key="login_username")
        password = st.text_input("סיסמה", type="password", key="login_password")

        with st.expander("שכחתי סיסמה?"):
            st.caption("נדרש TOKEN איפוס מהמורה/מנהל (נשמר ב-MongoDB).")
            if not get_password_reset_token():
                st.warning("⚠️ TOKEN איפוס סיסמה לא הוגדר. הרץ create_users.py או עדכן בניהול משתמשים.")
            fp_user = st.text_input("שם משתמש (כמו למעלה)", key="fp_username")
            fp_token = st.text_input("TOKEN איפוס סיסמה", type="password", key="fp_token")
            fp_pass = st.text_input("סיסמה חדשה", type="password", key="fp_password")
            fp_pass2 = st.text_input("אימות סיסמה חדשה", type="password", key="fp_password2")
            if st.button("עדכן סיסמה 🔑", key="btn_forgot_password"):
                u = (fp_user or "").strip()
                if not u or not fp_pass or not fp_token:
                    st.warning("⚠️ נא למלא שם משתמש, TOKEN וסיסמה חדשה")
                elif len(fp_pass) < 4:
                    st.warning("⚠️ סיסמה קצרה מדי (לפחות 4 תווים)")
                elif fp_pass != fp_pass2:
                    st.error("❌ הסיסמאות החדשות אינן תואמות")
                elif not verify_password_reset_token(fp_token):
                    st.error("❌ TOKEN איפוס סיסמה שגוי")
                elif not users_collection.find_one({"username": u}):
                    st.error("❌ משתמש לא נמצא במערכת")
                else:
                    if reset_user_password(u, fp_pass):
                        st.success("✅ הסיסמה עודכנה! התחבר עם הסיסמה החדשה למעלה.")
                    else:
                        st.error("שגיאה בעדכון הסיסמה")

        if st.button("כניסה 🚀", key="btn_login"):
            if username and password:
                user = users_collection.find_one({"username": username.strip(), "password": password})
                if user:
                    set_session_user(user)
                    st.rerun()
                else:
                    st.error("❌ שם משתמש או סיסמה שגויים! אינך מורשה להיכנס.")
            else:
                st.warning("⚠️ אנא הזן שם משתמש וסיסמה")

    with register_tab:
        st.markdown("**פתיחת חשבון חדש** — השם ישמש אותך גם בהיסטוריית התרגול.")
        account_type = st.radio(
            "סוג חשבון",
            ["תלמיד/ה", "מנהל מערכת"],
            horizontal=True,
            key="reg_account_type",
        )
        new_user = st.text_input("שם משתמש חדש", key="reg_username")
        new_pass = st.text_input("סיסמה", type="password", key="reg_password")
        new_pass2 = st.text_input("אימות סיסמה", type="password", key="reg_password2")
        admin_token_input = ""
        if account_type == "מנהל מערכת":
            admin_token_input = st.text_input(
                "TOKEN מנהל (נשמר במסד הנתונים — מתקבל מבעל המערכת)",
                type="password",
                key="reg_admin_token",
            )
            if not get_admin_registration_token():
                st.warning("⚠️ TOKEN מנהל עדיין לא הוגדר במסד. הרץ create_users.py או עדכן בלשונית ניהול משתמשים.")

        if st.button("צור חשבון והמשך ✨", key="btn_register"):
            u = (new_user or "").strip()
            want_admin = account_type == "מנהל מערכת"
            role = ROLE_ADMIN if want_admin else ROLE_STUDENT

            if not u or not new_pass:
                st.warning("⚠️ נא למלא שם משתמש וסיסמה")
            elif len(u) < 2:
                st.warning("⚠️ שם משתמש קצר מדי (לפחות 2 תווים)")
            elif len(new_pass) < 4:
                st.warning("⚠️ סיסמה קצרה מדי (לפחות 4 תווים)")
            elif new_pass != new_pass2:
                st.error("❌ הסיסמאות אינן תואמות")
            elif want_admin and not verify_admin_registration_token(admin_token_input):
                st.error("❌ TOKEN מנהל שגוי. הרשמה כמנהל אפשרית רק עם TOKEN תקין מ-MongoDB.")
            elif users_collection.find_one({"username": u}):
                st.error("❌ שם המשתמש כבר תפוס — בחר שם אחר")
            else:
                try:
                    users_collection.insert_one(
                        {"username": u, "password": new_pass, "role": role}
                    )
                    set_session_user({"username": u, "role": role})
                    label = "מנהל מערכת" if want_admin else "תלמיד/ה"
                    st.success(f"החשבון נוצר בהצלחה ({label})!")
                    st.rerun()
                except Exception as e:
                    st.error(f"שגיאה בשמירה: {e}")

    st.stop()

# =========================
# 🎯 מסך ראשי - מחובר
# =========================
header_col, logout_col = st.columns([4, 1])
with header_col:
    role_label = "מנהל מערכת" if st.session_state.get("is_admin") else "תלמיד/ה"
    st.markdown(
        f"<h4 style='text-align:center;'>שלום {st.session_state.username} 👋 "
        f"<span style='font-size:0.9rem;color:#666;'>({role_label})</span></h4>",
        unsafe_allow_html=True,
    )
with logout_col:
    if st.button("יציאה", key="btn_logout"):
        clear_session_user()
        st.rerun()

if "role" not in st.session_state:
    db_user = users_collection.find_one({"username": st.session_state.username})
    st.session_state.role = user_role(db_user)
    st.session_state.is_admin = st.session_state.role == ROLE_ADMIN

history = list(
    collection.find({"username": st.session_state.username}).sort("timestamp", -1)
)

tab_labels = [
    "🎯 תרגול ובחירת נושא",
    "📜 היסטוריית שיחות",
    "📊 סיכום רמת התלמיד",
]
if st.session_state.get("is_admin"):
    tab_labels.append("⚙️ ניהול משתמשים")

tabs = st.tabs(tab_labels)
tab_practice, tab_history, tab_summary = tabs[0], tabs[1], tabs[2]
tab_admin = tabs[3] if st.session_state.get("is_admin") else None

# --- היסטוריה ---
with tab_history:
    st.markdown("### ההיסטוריה שלך")
    if history:
        for idx, item in enumerate(history):
            topic_name = item.get("topic", "כללי")
            score = extract_score(item.get("feedback"))
            score_tag = f" | ציון: {score}/10" if score else ""
            with st.expander(f"תרגול #{len(history)-idx} | נושא: {topic_name}{score_tag}"):
                st.markdown(f"**השאלה:** {item.get('question', '')}")
                if item.get("text"):
                    st.markdown(f"**התשובה שלך:** {item.get('text', '')}")
                if item.get("feedback"):
                    st.markdown(f"**משוב המורה:** {item.get('feedback', '')}")
    else:
        st.info("עדיין אין לך היסטוריית שיחות. התחל לתרגל בלשונית התרגול!")

# --- סיכום רמה ---
with tab_summary:
    st.markdown("### סיכום רמת התלמיד שלך")
    if not history:
        st.info("אין עדיין מספיק היסטוריה. בצע לפחות תרגול אחד כדי לקבל סיכום.")
    else:
        stats = history_stats(history)
        m1, m2, m3 = st.columns(3)
        m1.metric("סה\"כ תרגולים", stats["count"])
        m2.metric("ממוצע ציון", f"{stats['avg']}/10" if stats["avg"] else "—")
        m3.metric("נושאים שונים", len(stats["topics"]))
        if stats["topics"]:
            st.markdown("**פילוח לפי נושא:** " + ", ".join(
                f"{name} ({count})" for name, count in stats["topics"].items()
            ))
        if st.button("✨ צור / עדכן סיכום מורה", key="btn_level_summary"):
            with st.spinner("המורה מנתח את ההיסטוריה שלך..."):
                try:
                    summary_text, _ = generate_level_summary(
                        client, st.session_state.username, history
                    )
                    st.session_state.level_summary_text = summary_text
                except Exception as e:
                    st.error(f"שגיאה ביצירת סיכום: {e}")
        if st.session_state.get("level_summary_text"):
            st.markdown("#### סיכום המורה")
            st.markdown(st.session_state.level_summary_text)

# --- ניהול משתמשים (מנהל בלבד) ---
if tab_admin is not None:
    with tab_admin:
        st.markdown("### ניהול מערכת")
        st.caption("גישה למנהלי מערכת בלבד")

        students_view_tab, users_mgmt_tab = st.tabs(["📊 מצב תלמידים", "⚙️ ניהול משתמשים"])

        with students_view_tab:
            st.markdown("#### סקירת מצב התלמידים")
            student_users = list_student_users()
            if not student_users:
                st.info("אין תלמידים רשומים במערכת.")
            else:
                snapshots = [build_student_snapshot(u["username"]) for u in student_users]
                active = sum(1 for s in snapshots if s["practice_count"] > 0)
                not_started = len(snapshots) - active

                c1, c2, c3 = st.columns(3)
                c1.metric("סה\"כ תלמידים", len(snapshots))
                c2.metric("פעילים (עם תרגולים)", active)
                c3.metric("טרם התחילו", not_started)

                overview_rows = [
                    {
                        "תלמיד": s["username"],
                        "תרגולים": s["practice_count"],
                        "ממוצע ציון": f"{s['avg_score']}/10" if s["avg_score"] else "—",
                        "רמה": s["level"],
                        "נושאים": s["topics_count"],
                        "פעילות אחרונה": format_activity_time(s["last_activity"]),
                    }
                    for s in snapshots
                ]
                st.dataframe(overview_rows, use_container_width=True, hide_index=True)

                st.divider()
                st.markdown("#### פירוט תלמיד")
                selected_student = st.selectbox(
                    "בחר תלמיד",
                    [s["username"] for s in snapshots],
                    key="admin_student_select",
                )
                detail = next(s for s in snapshots if s["username"] == selected_student)

                d1, d2, d3, d4 = st.columns(4)
                d1.metric("תרגולים", detail["practice_count"])
                d2.metric("ממוצע", f"{detail['avg_score']}/10" if detail["avg_score"] else "—")
                d3.metric("רמה", detail["level"])
                d4.metric("פעילות אחרונה", format_activity_time(detail["last_activity"]))

                if detail["topics"]:
                    st.markdown(
                        "**נושאים:** "
                        + ", ".join(f"{n} ({c})" for n, c in detail["topics"].items())
                    )

                if detail["history"]:
                    st.markdown("**תרגולים אחרונים:**")
                    for idx, item in enumerate(detail["history"][:10], 1):
                        topic_name = item.get("topic", "כללי")
                        score = extract_score(item.get("feedback"))
                        score_tag = f" | ציון: {score}/10" if score else ""
                        when = format_activity_time(item.get("timestamp"))
                        with st.expander(f"#{idx} {topic_name}{score_tag} | {when}"):
                            st.markdown(f"**שאלה:** {item.get('question', '')}")
                            if item.get("text"):
                                st.markdown(f"**תשובה:** {item.get('text', '')}")
                            if item.get("feedback"):
                                st.markdown(f"**משוב:** {item.get('feedback', '')}")
                else:
                    st.info("לתלמיד זה אין עדיין היסטוריית תרגול.")

                summary_key = f"admin_summary_{selected_student}"
                if st.button("✨ צור סיכום AI לתלמיד", key="btn_admin_student_summary"):
                    if not detail["history"]:
                        st.warning("אין היסטוריה לסיכום.")
                    else:
                        with st.spinner(f"מנתח את {selected_student}..."):
                            try:
                                text, _ = generate_level_summary(
                                    client, selected_student, detail["history"]
                                )
                                st.session_state[summary_key] = text
                            except Exception as e:
                                st.error(f"שגיאה: {e}")
                if st.session_state.get(summary_key):
                    st.markdown("##### סיכום מורה")
                    st.markdown(st.session_state[summary_key])

        with users_mgmt_tab:
            all_users = list(users_collection.find({}, {"password": 0}).sort("username", 1))
            if all_users:
                st.markdown("**משתמשים רשומים:**")
                for u in all_users:
                    role = user_role(u)
                    badge = "🛡️ מנהל" if role == ROLE_ADMIN else "👤 תלמיד"
                    st.markdown(f"- **{u['username']}** — {badge}")
            else:
                st.info("אין משתמשים במערכת.")

            st.divider()
            st.markdown("#### הוספת תלמיד (ידני)")
            st.caption("מנהלים נרשמים דרך מסך ההרשמה עם TOKEN מ-MongoDB.")
            add_name = st.text_input("שם משתמש", key="admin_add_username")
            add_pass = st.text_input("סיסמה", type="password", key="admin_add_password")
            if st.button("הוסף תלמיד", key="btn_admin_add"):
                name = (add_name or "").strip()
                if not name or not add_pass:
                    st.warning("נא למלא שם משתמש וסיסמה")
                elif len(name) < 2:
                    st.warning("שם משתמש קצר מדי")
                elif users_collection.find_one({"username": name}):
                    st.error("שם המשתמש כבר קיים")
                else:
                    users_collection.insert_one(
                        {"username": name, "password": add_pass, "role": ROLE_STUDENT}
                    )
                    st.success(f"התלמיד {name} נוסף בהצלחה")
                    st.rerun()

            st.divider()
            st.markdown("#### TOKEN הרשמת מנהל (MongoDB)")
            st.caption("ה-TOKEN נשמר בקולקציה `config`, מסמך `admin_registration_token`.")
            current_token = get_admin_registration_token()
            if current_token:
                st.info("TOKEN מוגדר במערכת (לא מוצג כאן מטעמי אבטחה).")
            else:
                st.warning("טרם הוגדר TOKEN — הרשמה כמנהל לא תעבוד עד שתגדיר.")
            new_admin_token = st.text_input(
                "TOKEN חדש למנהלים",
                type="password",
                key="admin_new_token",
            )
            confirm_admin_token = st.text_input(
                "אימות TOKEN",
                type="password",
                key="admin_confirm_token",
            )
            if st.button("שמור TOKEN במסד", key="btn_save_admin_token"):
                if not new_admin_token or len(new_admin_token.strip()) < 6:
                    st.warning("TOKEN חייב להיות באורך 6 תווים לפחות")
                elif new_admin_token != confirm_admin_token:
                    st.error("ה-TOKEN ואימות ה-TOKEN אינם תואמים")
                else:
                    set_admin_registration_token(new_admin_token)
                    st.success("TOKEN מנהל עודכן ב-MongoDB")
                    st.rerun()

            st.divider()
            st.markdown("#### TOKEN איפוס סיסמה (MongoDB)")
            st.caption("מסמך `password_reset_token` בקולקציה `config` — לתלמידים בלשונית «שכחתי סיסמה».")
            if get_password_reset_token():
                st.info("TOKEN איפוס סיסמה מוגדר (לא מוצג מטעמי אבטחה).")
            else:
                st.warning("טרם הוגדר TOKEN איפוס סיסמה.")
            new_reset_token = st.text_input("TOKEN חדש לאיפוס", type="password", key="reset_new_token")
            confirm_reset_token = st.text_input("אימות TOKEN איפוס", type="password", key="reset_confirm_token")
            if st.button("שמור TOKEN איפוס", key="btn_save_reset_token"):
                if not new_reset_token or len(new_reset_token.strip()) < 6:
                    st.warning("TOKEN חייב להיות באורך 6 תווים לפחות")
                elif new_reset_token != confirm_reset_token:
                    st.error("ה-TOKEN ואימות ה-TOKEN אינם תואמים")
                else:
                    set_password_reset_token(new_reset_token)
                    st.success("TOKEN איפוס סיסמה עודכן ב-MongoDB")
                    st.rerun()

            st.divider()
            st.markdown("#### הסרת משתמש")
            usernames = [u["username"] for u in all_users]
            if usernames:
                remove_name = st.selectbox("בחר משתמש להסרה", usernames, key="admin_remove_user")
                if st.button("הסר משתמש", key="btn_admin_remove"):
                    if remove_name == st.session_state.username:
                        st.error("לא ניתן להסיר את החשבון שאיתו אתה מחובר")
                    else:
                        target = users_collection.find_one({"username": remove_name})
                        if target and user_role(target) == ROLE_ADMIN and count_admins() <= 1:
                            st.error("לא ניתן להסיר את מנהל המערכת האחרון")
                        else:
                            users_collection.delete_one({"username": remove_name})
                            collection.delete_many({"username": remove_name})
                            st.success(f"המשתמש {remove_name} הוסר מהמערכת")
                            st.rerun()
            else:
                st.info("אין משתמשים להסרה.")

# --- תרגול ---
with tab_practice:
    st.markdown("### בחר נושא לתרגול")
    topics = ["טכנולוגיה", "ספורט", "בית ספר ולימודים", "משפחה וחברים", "קריירה ועתיד", "תחביבים", "רשתות חברתיות"]
    selected_topic = st.selectbox("בחר נושא:", topics)
    
    # מחיקת השאלה והמשוב הישנים ברגע שמשנים נושא בתיבה
    if st.session_state.get("last_selected_topic") != selected_topic:
        st.session_state["last_selected_topic"] = selected_topic
        for key in ["current_generated_question", "last_audio_hash", "current_user_text", "current_ai_feedback"]:
            st.session_state.pop(key, None)
    
    if st.button("✨ ייצר שאלה בנושא זה"):
        for key in ["last_audio_hash", "current_user_text", "current_ai_feedback"]:
            st.session_state.pop(key, None)
            
        with st.spinner("הבינה המלאכותית מנסחת עבורך שאלה..."):
            try:
                response = client.chat.completions.create(
                    model="gpt-4.1-mini",
                    messages=[
                        {"role": "system", "content": "אתה מורה לעברית. חבר שאלה פתוחה אחת, קצרה, ברורה ומעניינת בעברית לתלמיד בנושא המבוקש. החזר רק את השאלה נטו, ללא שום הקדמה, מרכאות או טקסט נוסף."},
                        {"role": "user", "content": f"הנושא: {selected_topic}"}
                    ]
                )
                generated_q = response.choices[0].message.content
                st.session_state.current_topic = selected_topic
                st.session_state.current_generated_question = generated_q
            except Exception as e:
                st.error(f"שגיאה ביצירת שאלה: {e}")

    if "current_generated_question" in st.session_state:
        st.markdown(f"""
        <div style='background:#fff;padding:20px;border-radius:20px;margin-bottom:20px;border-right:5px solid #6c5ce7;font-size:1.3rem;'>
        🎯 <b>השאלה שלך (בנושא {st.session_state.current_topic}):</b><br>
        {st.session_state.current_generated_question}
        </div>
        """, unsafe_allow_html=True)

        def get_examiner_feedback(student_text, question):
            try:
                response = client.chat.completions.create(
                    model="gpt-4.1-mini",
                    messages=[
                        {"role": "system", "content": f"אתה בוחן לעברית. בדוק אם התשובה קשורה לשאלה, תקן שגיאות כתיב/תחביר אם יש, ותן ציון 1-10.\nסיים תמיד בשורה נפרדת בדיוק בפורמט: ציון: X/10\nהשאלה הייתה: {question}"},
                        {"role": "user", "content": student_text}
                    ]
                )
                return response.choices[0].message.content
            except Exception as e:
                return f"שגיאה: {e}"

        recorded_audio = st.audio_input("👈 לחץ כאן והקלט תשובה לשאלה:")
        
        if recorded_audio is not None:
            import hashlib
            audio_bytes = recorded_audio.getvalue()
            audio_hash = hashlib.md5(audio_bytes).hexdigest()
            
            if st.session_state.get("last_audio_hash") != audio_hash:
                st.session_state["last_audio_hash"] = audio_hash
                
                try:
                    with st.spinner('הבוחן מקשיב ובודק את התשובה...'):
                        with open("temp_audio.wav", "wb") as f:
                            f.write(audio_bytes)
                        
                        with open("temp_audio.wav", "rb") as audio_file:
                            transcript = client.audio.transcriptions.create(
                                model="whisper-1", file=audio_file, language="he"
                            )
                            user_text = transcript.text

                        ai_feedback = get_examiner_feedback(user_text, st.session_state.current_generated_question)

                        st.session_state["current_user_text"] = user_text
                        st.session_state["current_ai_feedback"] = ai_feedback

                        # שמירה להיסטוריה במסד הנתונים
                        try:
                            collection.insert_one({
                                "username": st.session_state.username,
                                "topic": st.session_state.current_topic,
                                "question": st.session_state.current_generated_question,
                                "text": user_text,
                                "feedback": ai_feedback,
                                "timestamp": datetime.now()
                            })
                        except:
                            pass
                except Exception as e:
                     st.error(f"שגיאה: {e}")

            if "current_user_text" in st.session_state:
                st.markdown(f"<div class='ai-response-box'>🎤 {st.session_state['current_user_text']}</div>", unsafe_allow_html=True)
                with st.chat_message("assistant"):
                    st.markdown(st.session_state["current_ai_feedback"])
                    st.success("✅ התשובה והמשוב נשמרו בהיסטוריית השיחות שלך!")