import streamlit as st

from backend.ai_service import generate_level_summary
from backend.analytics import extract_score, format_activity_time, user_role
from backend.auth_service import (
    find_user,
    get_admin_registration_token,
    get_password_reset_token,
    set_admin_registration_token,
    set_password_reset_token,
)
from backend.config import ROLE_ADMIN
from backend.users_service import (
    add_student,
    build_student_snapshot,
    can_remove_user,
    list_all_users,
    list_student_users,
    remove_user,
)


def render_admin_page(current_username):
    st.markdown("### ניהול מערכת")
    st.caption("גישה למנהלי מערכת בלבד")

    students_view_tab, users_mgmt_tab = st.tabs(["📊 מצב תלמידים", "⚙️ ניהול משתמשים"])

    with students_view_tab:
        _render_students_overview()

    with users_mgmt_tab:
        _render_users_management(current_username)


def _render_students_overview():
    st.markdown("#### סקירת מצב התלמידים")
    student_users = list_student_users()
    if not student_users:
        st.info("אין תלמידים רשומים במערכת.")
        return

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
            "**נושאים:** " + ", ".join(f"{n} ({c})" for n, c in detail["topics"].items())
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
                    text, _ = generate_level_summary(selected_student, detail["history"])
                    st.session_state[summary_key] = text
                except Exception as e:
                    st.error(f"שגיאה: {e}")
    if st.session_state.get(summary_key):
        st.markdown("##### סיכום מורה")
        st.markdown(st.session_state[summary_key])


def _render_users_management(current_username):
    all_users = list_all_users()
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
        elif find_user(name):
            st.error("שם המשתמש כבר קיים")
        else:
            add_student(name, add_pass)
            st.success(f"התלמיד {name} נוסף בהצלחה")
            st.rerun()

    st.divider()
    st.markdown("#### TOKEN הרשמת מנהל (MongoDB)")
    st.caption("ה-TOKEN נשמר בקולקציה `config`, מסמך `admin_registration_token`.")
    if get_admin_registration_token():
        st.info("TOKEN מוגדר במערכת (לא מוצג כאן מטעמי אבטחה).")
    else:
        st.warning("טרם הוגדר TOKEN — הרשמה כמנהל לא תעבוד עד שתגדיר.")
    new_admin_token = st.text_input("TOKEN חדש למנהלים", type="password", key="admin_new_token")
    confirm_admin_token = st.text_input("אימות TOKEN", type="password", key="admin_confirm_token")
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
    st.caption("מסמך `password_reset_token` — לתלמידים ב«שכחתי סיסמה».")
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
    if not usernames:
        st.info("אין משתמשים להסרה.")
        return
    remove_name = st.selectbox("בחר משתמש להסרה", usernames, key="admin_remove_user")
    if st.button("הסר משתמש", key="btn_admin_remove"):
        ok, err = can_remove_user(remove_name, current_username)
        if not ok:
            st.error(err)
        else:
            remove_user(remove_name)
            st.success(f"המשתמש {remove_name} הוסר מהמערכת")
            st.rerun()
