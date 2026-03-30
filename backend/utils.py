import logging
import os
from functools import lru_cache

import boto3
from botocore.exceptions import ClientError
from langchain_community.retrievers import ArxivRetriever
from langchain_community.tools import TavilySearchResults
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from passlib.context import CryptContext

from backend.config import settings

LOCAL_EXTRACTS_DIRECTORY = os.path.join("resources", "extracts")
BASE_RESOURCES_PATH = os.path.join("resources")
SCRAPED_RESOURCES_PATH = os.path.join(BASE_RESOURCES_PATH, "scraped")
CACHED_RESOURCES_PATH = os.path.join(BASE_RESOURCES_PATH, "cached")


logger = logging.getLogger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(plain_password: str) -> str:
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def ensure_directory_exists(directory):
    os.makedirs(directory, exist_ok=True)


def get_s3_client():
    return boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
    )

def load_s3_bucket():
    bucket = os.environ.get("AWS_S3_BUCKET")
    if bucket:
        return bucket
    raise ValueError("Missing AWS S3 Bucket")


def fetch_file_from_s3(key: str, dest_filename: str | None):
    s3_client = get_s3_client()

    filename = (
        os.path.basename(key)
        if not dest_filename
        else f"{dest_filename}{os.path.splitext(key)[1]}"
    )
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
                logger.error(f"S3 error: {e}")
                return False


@lru_cache
def get_pinecone_vector_store():
    embeddings = OpenAIEmbeddings(model=settings.OPENAI_EMBEDDINGS_MODEL)
    return PineconeVectorStore(index_name=settings.PINECONE_INDEX_NAME, embedding=embeddings)


def get_tavily_web_search_tool():
    """Advanced Tavily tool for primary searches (web, Reddit)."""
    os.environ["TAVILY_API_KEY"] = settings.TAVILY_API_KEY
    return TavilySearchResults(max_results=5, search_depth="advanced", include_answer=True)


def get_tavily_basic_search_tool():
    """Fast Tavily tool for enrichment (news articles, YouTube links)."""
    os.environ["TAVILY_API_KEY"] = settings.TAVILY_API_KEY
    return TavilySearchResults(max_results=7, search_depth="basic", include_answer=False)
