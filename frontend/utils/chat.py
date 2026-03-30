import logging
import os
from functools import lru_cache

import boto3
import requests
import streamlit as st
from botocore.exceptions import ClientError

from frontend.utils.auth import make_authenticated_request, make_unauthenticated_request

logger = logging.getLogger(__name__)

BASE_RESOURCES_PATH = os.path.join("resources")
SCRAPED_RESOURCES_PATH = os.path.join(BASE_RESOURCES_PATH, "scraped")
CACHED_RESOURCES_PATH = os.path.join(BASE_RESOURCES_PATH, "cached")


@lru_cache
def get_openai_model_choices():
    return make_unauthenticated_request(
        endpoint="/choices/openai-models", method="GET"
    )["choices"]


@lru_cache
def get_extraction_mechanism_choices():
    return make_unauthenticated_request(
        endpoint="/choices/pdf-extraction-mechanisms", method="GET"
    )["choices"]

def get_categories():
    # GET /choices/categories
    return make_authenticated_request(
        endpoint="/choices/categories",
        method="GET"
    ).get("choices", [])

@lru_cache
def _get_pdf_files_list():
    return make_authenticated_request(endpoint="/choices/pdfs", method="GET")


def get_unique_pdf_filenames():
    return set(pdf["filename"] for pdf in _get_pdf_files_list()["docs"])


def get_pdf_object_from_db(pdf_filename: str, extraction_mechanism: str):
    return make_authenticated_request(
        endpoint="/choices/pdf",
        method="GET",
        params={"filename": pdf_filename, "extraction-mechanism": extraction_mechanism},
    )
def search_initial(model: str, prompt: str, category: str, chat_session_id: str | None, chat_history):
    # POST /search/initial
    if chat_history:
        prompt = " ".join([i["content"] for i in chat_history if i["role"] == "user"]) + prompt

    chat_session_id = process_selected_chat_session(chat_session_id)

    payload = {
        "model": model,
        "prompt": prompt,
        "category": category,
        "chat_session_id": chat_session_id,
    }
    return make_authenticated_request(
        endpoint="/search/initial",
        method="POST",
        data=payload
    )

def search_followup(prompt: str, products_context: list, chat_session_id: int | None, follow_up_type: str):
    payload = {
        "prompt": prompt,
        "products_context": products_context,
        "chat_session_id": chat_session_id,
        "follow_up_type": follow_up_type,
    }
    return make_authenticated_request(
        endpoint="/search/followup",
        method="POST",
        data=payload
    )


def fetch_chat_sessions():
    resp = make_authenticated_request(
        endpoint="/search/chat-sessions",
        method="GET"
    )
    resp1 =  sorted(resp.keys(), reverse=True, key=lambda d: int(d))
    return [f"{k}: {resp[k]}" for k in resp1]


def process_selected_chat_session(chat_session: str) -> int | None:
    try:
       return int(chat_session.split(":")[0]) if chat_session else None
    except Exception:
        return None

def search_product_listings(query: str):
    # POST /search/product-listings (no auth required)
    payload = {
        "query": query
    }
    return make_unauthenticated_request(
        endpoint="/search/product-listings",
        method="POST",
        data=payload
    )

def set_chat_id(chat_id: str):
    st.session_state.chat_id = chat_id


def get_chat_id():
    if hasattr(st.session_state, "chat_id") and st.session_state.chat_id is not None:
        return st.session_state.chat_id
    logger.error("chat_id not set")


def revoke_chat_id():
    st.session_state.chat_id = None


def initiate_chat(model, extraction_mechanism, filename):
    response = make_authenticated_request(
        endpoint="/chat/initiate",
        method="POST",
        data={
            "openai_model": model,
            "extraction_mechanism": extraction_mechanism,
            "filename": filename,
        },
    )
    set_chat_id(response["chat_id"])


def ask_question(question: str, model: str, extraction_mechanism: str, filename: str):
    if get_chat_id() is None:
        initiate_chat(model, extraction_mechanism, filename)

    response = make_authenticated_request(
        endpoint=f"/chat/{get_chat_id()}/qa",
        method="POST",
        data={
            "question": question,
            "model": model,
        },
    )

    return response["llm_response"]


def get_file_content_from_backend(filename: str, model: str, extraction_mechanism: str):
    verify_valid_chat(filename, model, extraction_mechanism)
    return make_authenticated_request(
        endpoint=f"/chat/{get_chat_id()}/file-content",
        method="GET",
    )["file_contents"]


def verify_valid_chat(filename: str, model: str, extraction_mechanism: str):
    if get_chat_id() is None:
        initiate_chat(model, extraction_mechanism, filename)
    else:
        chat_session = make_authenticated_request(
            endpoint=f"/chat/{get_chat_id()}",
            method="GET",
        )
        if filename != chat_session["filename"]:
            initiate_chat(model, extraction_mechanism, filename)


def load_aws_tokens():
    required_keys = ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_REGION"]
    if all(key in os.environ for key in required_keys):
        return {
            "aws_access_key_id": os.environ["AWS_ACCESS_KEY_ID"],
            "aws_secret_access_key": os.environ["AWS_SECRET_ACCESS_KEY"],
            "region_name": os.environ["AWS_REGION"],
        }
    raise ValueError("Missing AWS Credentials in environment")


def load_s3_bucket():
    bucket = os.environ.get("AWS_S3_BUCKET")
    if bucket:
        return bucket
    raise ValueError("Missing AWS S3 Bucket")


@lru_cache
def get_s3_client():
    return boto3.client("s3", **load_aws_tokens())

def fetch_file_from_s3(key: str, dest_filename: str | None):
    s3_client = get_s3_client()

    filename = (
        os.path.basename(key)
        if not dest_filename
        else f"{dest_filename}{os.path.splitext(key)[1]}"
    )
    key = "/".join(key.split("/")[-3:])
    local_filepath = os.path.join(CACHED_RESOURCES_PATH, filename)
    # Check locally before downloading
    if os.path.exists(local_filepath):
        return local_filepath
    else:
        try:
            _ = s3_client.head_object(Bucket=load_s3_bucket(), Key=key)
            s3_client.download_file(load_s3_bucket(), key, local_filepath)
            logger.info(f"Downloaded file {key} from S3")
            return local_filepath
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":  # File not found
                logger.error(f"File {key} not found on S3")
                return False
            else:
                logger.error("")
                return False

def _ensure_directory_exists(directory):
    os.makedirs(directory, exist_ok=True)


def ensure_resource_dir_exists():
    _ensure_directory_exists(os.path.join(CACHED_RESOURCES_PATH, "pdfs"))
    _ensure_directory_exists(os.path.join(CACHED_RESOURCES_PATH, "images"))

def fetch_documents():
    """Fetch all documents from the backend API."""
    try:
        response = make_authenticated_request("/articles/", "GET")

        return response
    except requests.exceptions.RequestException as e:
        st.error("Failed to load documents from the server.")
        return []
