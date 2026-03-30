from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.schemas.search import InitialSearchRequest, Product, SearchQuery, InitialSearchResponse
from backend.services.auth_bearer import get_current_user_id
from backend.services.search import process_initial_search_query, fetch_google_shopping_results, \
    extract_product_details, get_chat_sessions_for_user, get_messages_for_session, \
    generate_followup_response

search_router = APIRouter(prefix="/search", tags=["search"])


@search_router.post("/product-listings", response_model=list[Product])
def search_products(query: SearchQuery):
    api_response = fetch_google_shopping_results(query.query)
    if not api_response:
        raise HTTPException(status_code=500, detail="Error fetching data from API")
    products = extract_product_details(api_response)
    return products


@search_router.post(
    "/initial",
)
async def initial_search(
    request: InitialSearchRequest, user_id: int = Depends(get_current_user_id)
) -> InitialSearchResponse:
    return await process_initial_search_query(request.model, request.prompt, request.category, request.chat_session_id, user_id)

"""
    Initial Search -> List[Products]
    
    Product:
        name: Sony MX4  -> Oxxylabs API
        review summary
        
    ProductL:
        name: Sony MZ3  -> Oxxylabs API
        review summary
        
    
    Refined Search -> 
"""


@search_router.get("/chat-sessions")
async def list_chat_sessions(user_id: int = Depends(get_current_user_id)):
    return await get_chat_sessions_for_user(user_id)


@search_router.get("/messages/{chat_session_id}")
async def get_session_messages(chat_session_id: int, user_id: int = Depends(get_current_user_id)):
    return get_messages_for_session(chat_session_id)


class FollowUpRequest(BaseModel):
    prompt: str
    products_context: list[dict]
    chat_session_id: int | None
    follow_up_type: str  # "details", "compare", "question"


@search_router.post("/followup")
async def followup_search(request: FollowUpRequest, user_id: int = Depends(get_current_user_id)):
    return await generate_followup_response(
        request.prompt, request.products_context,
        request.chat_session_id, request.follow_up_type, user_id
    )
