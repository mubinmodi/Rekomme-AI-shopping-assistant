from enum import StrEnum

from typing_extensions import TypedDict


class GraphState(TypedDict):
    prompt: str
    generation: str
    resources: list
    steps: list[str]
    perform_web_search: bool
    category: str
    chat_session_id: int
    retry_count: int
    source_urls: list


class Steps(StrEnum):
    VECTOR_STORE_RETRIEVAL = "vector_store_retrieval"
    VECTOR_STORE_EVALUATION = "vector_store_evaluation"
    QUERY_REWRITE = "query_rewrite"
    WEB_SEARCH_RETRIEVAL = "web_search_retrieval"
    LIVE_REDDIT_SEARCH = "live_reddit_search"
    LLM_GENERATION = "llm_generation"
    HALLUCINATION_CHECK = "hallucination_check"
    SOURCE_ENRICHMENT = "source_enrichment"
