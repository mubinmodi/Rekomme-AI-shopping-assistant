import requests
import streamlit as st

from frontend.config import settings


def set_tokens(tokens: dict[str, str]):
    st.session_state["access_token"] = tokens.get("access_token")
    st.session_state["refresh_token"] = tokens.get("refresh_token")


def get_access_token():
    if "access_token" in st.session_state:
        return st.session_state.get("access_token")
    raise ValueError("User not logged in!")


def get_refresh_token():
    if "refresh_token" in st.session_state:
        return st.session_state.get("refresh_token")
    raise ValueError("User not logged in!")


def make_authenticated_request(endpoint, method="GET", data=None, params=None):
    token = get_access_token()
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{settings.BACKEND_URI}/{endpoint}"

    if method == "POST":
        response = requests.post(url, json=data, headers=headers, params=params)
    else:
        response = requests.get(url, headers=headers, params=params)

    response.raise_for_status()
    if not response.content:
        return {}
    return response.json()


def make_unauthenticated_request(endpoint, method="GET", data=None, params=None):
    url = f"{settings.BACKEND_URI}/{endpoint}"

    if method == "POST":
        response = requests.post(url, json=data, params=params)
    else:
        response = requests.get(url, params=params)

    response.raise_for_status()
    if not response.content:
        return {}
    return response.json()
