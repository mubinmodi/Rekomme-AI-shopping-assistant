import json
from functools import lru_cache
from typing import List, Dict

import requests
from langchain_openai import ChatOpenAI

from backend.agent import agent_workflow
from backend.config import settings
from backend.database.chat_sessions import create_chat_session, update_chat_session_title, \
    fetch_chat_sessions_by_user_id
from backend.database.messages import get_messages_by_chat_id, create_message, MessageSenderEnum
from backend.schemas.search import InitialSearchResponse


@lru_cache(maxsize=128)
def manage_chat_sessions(chat_session_id):
    ...


async def process_initial_search_query(
    model: str, prompt: str, category: str, chat_session_id: int | None, user_id: int
) -> InitialSearchResponse:
    if chat_session_id is None:
        chat_session_id = create_chat_session(user_id,).id

    response = agent_workflow.invoke({"prompt": prompt, "category": category, "chat_session_id": chat_session_id})

    print(response["steps"])

    tools_used = ["vector_search"]
    if response.get("perform_web_search", False):
        tools_used.append("web_search")
    update_chat_session_title(chat_session_id, response["prompt"])

    return InitialSearchResponse(
        chat_session_id=chat_session_id,
        response=response["generation"],
        tools_used=tools_used
    )

def fetch_google_shopping_results(search_term: str) -> Dict:
    payload = {
        'source': 'google_shopping_search',
        'domain': 'com',
        'query': search_term,
        'pages': 1,
        'parse': True,
    }
    try:
        response = requests.post(
            'https://realtime.oxylabs.io/v1/queries',
            auth=(settings.OXYLABS_USERNAME, settings.OXYLABS_PASSWORD),
            json=payload,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error invoking API: {e}")
        return {}

def extract_product_details(api_response: Dict) -> List[Dict]:
    products = []
    if not api_response or 'results' not in api_response:
        print("Invalid API response.")
        return products

    for result in api_response['results']:
        content = result.get('content', {})
        organic_results = content.get('results', {}).get('organic', [])

        for product in organic_results:
            title = product.get('title', 'N/A')
            price = product.get('price_str', 'N/A')
            merchant_info = product.get('merchant', {})
            merchant_name = merchant_info.get('name', 'N/A')
            # Prefer merchant URL (direct store link) over Google search URL
            merchant_url = merchant_info.get('url', '')
            product_url = merchant_url or product.get('url') or f"https://www.google.com/search?tbm=shop&q={title.replace(' ', '+')}"

            products.append({
                'title': title,
                'price': price,
                'product_url': product_url,
                'merchant_name': merchant_name,
            })

    return products


async def get_chat_sessions_for_user(user_id: int):
    sessions = fetch_chat_sessions_by_user_id(user_id)
    return {str(session.id): session.title for session in sessions}


def get_messages_for_session(chat_session_id: int):
    messages = get_messages_by_chat_id(chat_session_id)
    return [
        {"role": sender, "content": content, "refs": refs, "tools": tools}
        for sender, content, refs, tools in messages
    ]


async def generate_followup_response(
    prompt: str, products_context: list, chat_session_id: int | None,
    follow_up_type: str, user_id: int
):
    """Handle follow-up queries: details, compare, or general questions."""
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.5, openai_api_key=settings.OPENAI_API_KEY)

    if chat_session_id is None:
        chat_session_id = create_chat_session(user_id).id

    products_text = json.dumps(products_context, indent=2)

    if follow_up_type == "details":
        system = """You are a product expert. The user wants detailed information about a product they're considering.
Provide: full specs, detailed community opinions, long-term durability, sound signature, comfort analysis, and comparison with closest competitors.
Use markdown formatting with headers. Be thorough but concise."""
        user_msg = f"Give me a deep dive on this product:\n{products_text}\n\nUser question: {prompt}"

    elif follow_up_type == "compare":
        system = """You are a product comparison expert. Create a detailed side-by-side comparison table.

Format as a markdown table with these columns:
| Feature | Product 1 | Product 2 | ... |

Include rows for: Price Range, Sound Quality, Noise Cancellation, Comfort, Battery Life, Build Quality, Connectivity, Best For, Community Rating, Pros, Cons, Verdict.

After the table, add a brief "Who should buy what" section."""
        user_msg = f"Compare these products side by side:\n{products_text}\n\nUser question: {prompt}"

    else:
        system = """You are a helpful product recommendation assistant. The user is asking a follow-up question about products they were shown.
Answer based on the product context provided. Be specific and helpful."""
        user_msg = f"Previous product recommendations:\n{products_text}\n\nUser follow-up: {prompt}"

    response = llm.invoke([
        {"role": "system", "content": system},
        {"role": "user", "content": user_msg}
    ])

    result = response.content

    # Persist
    create_message(content=prompt, chat_session_id=chat_session_id,
                   references=[], sender=MessageSenderEnum.USER, tools_used=["followup"])
    create_message(content=result, chat_session_id=chat_session_id,
                   references=[], sender=MessageSenderEnum.SYSTEM, tools_used=["followup"])

    return {"chat_session_id": chat_session_id, "response": result, "type": follow_up_type}