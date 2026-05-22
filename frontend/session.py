import streamlit as st

from backend.analytics import user_role
from backend.auth_service import find_user
from backend.config import ROLE_ADMIN


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


def ensure_role_loaded():
    if "role" not in st.session_state:
        db_user = find_user(st.session_state.username)
        st.session_state.role = user_role(db_user)
        st.session_state.is_admin = st.session_state.role == ROLE_ADMIN
