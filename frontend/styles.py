from pathlib import Path

import streamlit as st

_CSS_PATH = Path(__file__).resolve().parent / "assets" / "styles.css"


def setup_page():
    st.set_page_config(page_title="iTest", page_icon="🪄", layout="centered")
    css = _CSS_PATH.read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    st.markdown("<h1>iTest ✨</h1>", unsafe_allow_html=True)
    st.markdown("<h3 class='subtitle'>המורה הווירטואלי והחכם לעברית</h3>", unsafe_allow_html=True)


def question_box(topic, question):
    st.markdown(
        f"""
        <div style='background:#fff;padding:20px;border-radius:20px;margin-bottom:20px;
        border-right:5px solid #6c5ce7;font-size:1.3rem;'>
        🎯 <b>השאלה שלך (בנושא {topic}):</b><br>
        {question}
        </div>
        """,
        unsafe_allow_html=True,
    )
