import streamlit as st

from backend.auth_service import (
    authenticate,
    get_admin_registration_token,
    get_password_reset_token,
    register_user,
    reset_user_password,
    validate_password_reset,
    validate_registration,
)
from frontend.session import set_session_user


def render_auth_page():
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
                ok, err = validate_password_reset(fp_user, fp_pass, fp_pass2, fp_token)
                if not ok:
                    st.error(err) if err.startswith("❌") else st.warning(err)
                elif reset_user_password(fp_user, fp_pass):
                    st.success("✅ הסיסמה עודכנה! התחבר עם הסיסמה החדשה למעלה.")
                else:
                    st.error("שגיאה בעדכון הסיסמה")

        if st.button("כניסה 🚀", key="btn_login"):
            if username and password:
                user = authenticate(username, password)
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
                st.warning("⚠️ TOKEN מנהל עדיין לא הוגדר במסד. הרץ create_users.py או עדכן בניהול משתמשים.")

        if st.button("צור חשבון והמשך ✨", key="btn_register"):
            want_admin = account_type == "מנהל מערכת"
            ok, result = validate_registration(
                new_user, new_pass, new_pass2, want_admin, admin_token_input
            )
            if not ok:
                st.error(result) if result.startswith("❌") else st.warning(result)
            else:
                try:
                    u = (new_user or "").strip()
                    user = register_user(u, new_pass, result)
                    set_session_user(user)
                    label = "מנהל מערכת" if want_admin else "תלמיד/ה"
                    st.success(f"החשבון נוצר בהצלחה ({label})!")
                    st.rerun()
                except Exception as e:
                    st.error(f"שגיאה בשמירה: {e}")
