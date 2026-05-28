import streamlit as st

from backend.database import is_db_connected
from backend.practice_service import get_user_history
from frontend.admin_page import render_admin_page
from frontend.auth_page import render_auth_page
from frontend.history_page import render_history_page
from frontend.practice_page import render_practice_page
from frontend.session import clear_session_user, ensure_role_loaded
from frontend.styles import setup_page
from frontend.summary_page import render_summary_page


def run_app():
    setup_page()

    if not is_db_connected():
        st.error(
            "⚠️ לא ניתן להתחבר למסד הנתונים. ודא שה-MongoDB Cluster שלך פועל (Resume) ושה-MONGO_URI תקין."
        )
        st.stop()

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        render_auth_page()
        st.stop()

    _render_dashboard()


def _render_dashboard():
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

    ensure_role_loaded()
    username = st.session_state.username
    history = get_user_history(username)

    tab_labels = [
        "🎯 תרגול ובחירת נושא",
        "📜 היסטוריית שיחות",
        "📊 סיכום רמת התלמיד",
    ]
    if st.session_state.get("is_admin"):
        tab_labels.append("⚙️ ניהול משתמשים")

    tabs = st.tabs(tab_labels)
    with tabs[0]:
        render_practice_page(username)
    with tabs[1]:
        render_history_page(history)
    with tabs[2]:
        render_summary_page(username, history)
    if st.session_state.get("is_admin"):
        with tabs[3]:
            render_admin_page(username)
