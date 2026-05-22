import streamlit as st

from backend.analytics import extract_score


def render_history_page(history):
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
