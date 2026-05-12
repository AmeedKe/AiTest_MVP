import streamlit as st
import os
import random
from openai import OpenAI
from pymongo import MongoClient
from datetime import datetime
from dotenv import load_dotenv

# --- הגדרות ה-API ---
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

try:
    mongo_client = MongoClient(os.getenv("MONGO_URI"), serverSelectionTimeoutMS=3000)
    db = mongo_client["iTest_DB"]
    collection = db["interactions"]
    users_collection = db["users"]
except Exception:
    db = None

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
        if st.button("כניסה 🚀", key="btn_login"):
            if username and password:
                user = users_collection.find_one({"username": username.strip(), "password": password})
                if user:
                    st.session_state.logged_in = True
                    st.session_state.username = user["username"]
                    st.rerun()
                else:
                    st.error("❌ שם משתמש או סיסמה שגויים! אינך מורשה להיכנס.")
            else:
                st.warning("⚠️ אנא הזן שם משתמש וסיסמה")

    with register_tab:
        st.markdown("**פתיחת חשבון חדש** — השם ישמש אותך גם בהיסטוריית התרגול.")
        new_user = st.text_input("שם משתמש חדש", key="reg_username")
        new_pass = st.text_input("סיסמה", type="password", key="reg_password")
        new_pass2 = st.text_input("אימות סיסמה", type="password", key="reg_password2")
        if st.button("צור חשבון והמשך ✨", key="btn_register"):
            u = (new_user or "").strip()
            if not u or not new_pass:
                st.warning("⚠️ נא למלא שם משתמש וסיסמה")
            elif len(u) < 2:
                st.warning("⚠️ שם משתמש קצר מדי (לפחות 2 תווים)")
            elif len(new_pass) < 4:
                st.warning("⚠️ סיסמה קצרה מדי (לפחות 4 תווים)")
            elif new_pass != new_pass2:
                st.error("❌ הסיסמאות אינן תואמות")
            elif users_collection.find_one({"username": u}):
                st.error("❌ שם המשתמש כבר תפוס — בחר שם אחר")
            else:
                try:
                    users_collection.insert_one({"username": u, "password": new_pass})
                    st.session_state.logged_in = True
                    st.session_state.username = u
                    st.success("החשבון נוצר בהצלחה!")
                    st.rerun()
                except Exception as e:
                    st.error(f"שגיאה בשמירה: {e}")

    st.stop()

# =========================
# 🎯 מסך ראשי - מחובר
# =========================
st.markdown(f"<h4 style='text-align:center;'>שלום {st.session_state.username} 👋</h4>", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["🎯 תרגול ובחירת נושא", "📜 היסטוריית שיחות"])

# --- לשונית 2: היסטוריה ---
with tab2:
    st.markdown("### ההיסטוריה שלך")
    history = list(collection.find({"username": st.session_state.username}).sort("timestamp", -1))
    
    if history:
        for idx, item in enumerate(history):
            topic_name = item.get("topic", "כללי")
            with st.expander(f"תרגול #{len(history)-idx} | נושא: {topic_name}"):
                st.markdown(f"**השאלה:** {item.get('question', '')}")
                if item.get('text'):
                    st.markdown(f"**התשובה שלך:** {item.get('text', '')}")
                if item.get('feedback'):
                    st.markdown(f"**משוב המורה:** {item.get('feedback', '')}")
    else:
        st.info("עדיין אין לך היסטוריית שיחות. התחל לתרגל בלשונית השנייה!")

# --- לשונית 1: תרגול ---
with tab1:
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
                        {"role": "system", "content": f"אתה בוחן לעברית. בדוק אם התשובה קשורה לשאלה, תקן שגיאות כתיב/תחביר אם יש, ותן ציון 1-10.\nהשאלה הייתה: {question}"},
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