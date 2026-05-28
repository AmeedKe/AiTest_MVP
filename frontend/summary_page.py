import streamlit as st

from backend.ai_service import generate_level_summary
from backend.analytics import history_stats


def render_summary_page(username, history):
    st.markdown("### סיכום רמת התלמיד שלך")
    if not history:
        st.info("אין עדיין מספיק היסטוריה. בצע לפחות תרגול אחד כדי לקבל סיכום.")
        return
    stats = history_stats(history)
    m1, m2, m3 = st.columns(3)
    m1.metric("סה\"כ תרגולים", stats["count"])
    m2.metric("ממוצע ציון", f"{stats['avg']}/10" if stats["avg"] else "—")
    m3.metric("נושאים שונים", len(stats["topics"]))
    if stats["topics"]:
        st.markdown(
            "**פילוח לפי נושא:** "
            + ", ".join(f"{name} ({count})" for name, count in stats["topics"].items())
        )
    if st.button("✨ צור / עדכן סיכום מורה", key="btn_level_summary"):
        with st.spinner("המורה מנתח את ההיסטוריה שלך..."):
            try:
                summary_text, _ = generate_level_summary(username, history)
                st.session_state.level_summary_text = summary_text
            except Exception as e:
                st.error(f"שגיאה ביצירת סיכום: {e}")
    if st.session_state.get("level_summary_text"):
        st.markdown("#### סיכום המורה")
        st.markdown(st.session_state.level_summary_text)
