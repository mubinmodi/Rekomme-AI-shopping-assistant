import os
import streamlit as st
from dotenv import load_dotenv

from frontend.pages.chat import qa_interface
from frontend.pages.register import create_user
from frontend.pages.login import login
from frontend.utils.chat import ensure_resource_dir_exists

def main():
    load_dotenv()

    st.set_page_config(
        page_title="Rekomme - AI Shopping Assistant",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.markdown("""
    <style>
        .stButton>button {
            color: #ffffff;
            background-color: #1e3d59;
            border-radius: 5px;
        }
        .stTextInput>div>div>input {
            border-radius: 5px;
        }
    </style>
    """, unsafe_allow_html=True)

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "just_registered" not in st.session_state:
        st.session_state.just_registered = False

    def logout():
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()

    login_page = st.Page(login, title="Login", icon=":material/login:", default=True)
    logout_page = st.Page(logout, title="Log Out", icon=":material/logout:")
    user_creation_page = st.Page(create_user, title="Create Account")
    qa_page = st.Page(qa_interface, title="Search", icon=":material/chat:")

    if st.session_state.logged_in:
        pg = st.navigation({"Rekomme": [qa_page], "Account": [logout_page]})
    elif st.session_state.just_registered:
        st.session_state.just_registered = False
        pg = st.navigation({"Account": [login_page, user_creation_page]})
    else:
        pg = st.navigation({"Account": [login_page, user_creation_page]})

    ensure_resource_dir_exists()
    pg.run()

if __name__ == "__main__":
    main()
