import requests
import streamlit as st

from frontend.config import settings


def create_user():
    st.title("Create an Account")
    st.markdown("Join Rekomme to get AI-powered product recommendations from real community discussions.")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    st.caption("Use at least 8 characters with letters and numbers.")
    email = st.text_input("Email")
    full_name = st.text_input("Full Name")

    if st.button("Create Account", use_container_width=True):
        if not username or not password or not email:
            st.error("Username, password, and email are required.")
            return

        response = requests.post(
            f"{settings.BACKEND_URI}/users/",
            json={"username": username, "password": password, "email": email, "full_name": full_name},
        )
        if response.status_code == 201:
            st.success("Account created! Please log in.")
            st.session_state.just_registered = True
            st.rerun()
        elif response.status_code == 409:
            st.error("Username already taken. Please choose a different one.")
        else:
            try:
                detail = response.json().get("detail", response.text)
            except Exception:
                detail = response.text
            st.error(f"Registration failed: {detail}")
