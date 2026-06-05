import hashlib

import streamlit as st

from backend.ai_service import generate_question, get_examiner_feedback, transcribe_audio
from backend.config import PRACTICE_TOPICS
from backend.practice_service import save_interaction
from frontend.styles import question_box


def render_practice_page(username):
    st.markdown("### בחר נושא לתרגול")
    selected_topic = st.selectbox("בחר נושא:", PRACTICE_TOPICS)

    if st.session_state.get("last_selected_topic") != selected_topic:
        st.session_state["last_selected_topic"] = selected_topic
        for key in ["current_generated_question", "last_audio_hash", "current_user_text", "current_ai_feedback"]:
            st.session_state.pop(key, None)

    if st.button("✨ ייצר שאלה בנושא זה"):
        for key in ["last_audio_hash", "current_user_text", "current_ai_feedback"]:
            st.session_state.pop(key, None)
        with st.spinner("הבינה המלאכותית מנסחת עבורך שאלה..."):
            try:
                generated_q = generate_question(selected_topic)
                st.session_state.current_topic = selected_topic
                st.session_state.current_generated_question = generated_q
            except Exception as e:
                st.error(f"שגיאה ביצירת שאלה: {e}")

    if "current_generated_question" not in st.session_state:
        return

    question_box(st.session_state.current_topic, st.session_state.current_generated_question)
    recorded_audio = st.audio_input("👈 לחץ כאן והקלט תשובה לשאלה:")

    if recorded_audio is None:
        return

    audio_bytes = recorded_audio.getvalue()
    audio_hash = hashlib.md5(audio_bytes).hexdigest()

    if st.session_state.get("last_audio_hash") == audio_hash:
        _show_current_answer()
        return

    st.session_state["last_audio_hash"] = audio_hash
    try:
        with st.spinner("הבוחן מקשיב ובודק את התשובה..."):
            user_text = transcribe_audio(audio_bytes)
            ai_feedback = get_examiner_feedback(
                user_text, st.session_state.current_generated_question
            )
            st.session_state["current_user_text"] = user_text
            st.session_state["current_ai_feedback"] = ai_feedback
            try:
                save_interaction(
                    username,
                    st.session_state.current_topic,
                    st.session_state.current_generated_question,
                    user_text,
                    ai_feedback,
                )
            except Exception:
                pass
            st.rerun()
    except Exception as e:
        st.error(f"שגיאה: {e}")


def _show_current_answer():
    if "current_user_text" not in st.session_state:
        return
    st.markdown(
        f"<div class='ai-response-box'>🎤 {st.session_state['current_user_text']}</div>",
        unsafe_allow_html=True,
    )
    with st.chat_message("assistant"):
        st.markdown(st.session_state["current_ai_feedback"])
        st.success("✅ התשובה והמשוב נשמרו בהיסטוריית השיחות שלך!")
