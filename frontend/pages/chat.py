import json
from concurrent.futures import ThreadPoolExecutor
import streamlit as st
from dotenv import load_dotenv
from frontend.utils.auth import make_authenticated_request
from frontend.utils.chat import (
    get_categories,
    search_initial,
    search_followup,
    search_product_listings,
    fetch_chat_sessions,
    process_selected_chat_session,
)

load_dotenv()

EXAMPLE_QUERIES = [
    "Best headphones under $200 for working from home",
    "Wireless earbuds with good bass and long battery life",
    "Over-ear headphones for audiophiles under $500",
    "Best noise cancelling headphones for travel",
]

DEFAULT_MODEL = "gpt-4o-mini"

# Keywords that indicate a follow-up about existing products, not a new search
FOLLOWUP_SIGNALS = [
    "which one", "which is", "what about", "tell me more", "more about",
    "how does", "how is", "compare", "vs", "versus", "difference",
    "between", "better", "worse", "prefer", "recommend between",
    "why", "pros", "cons", "durability", "comfort", "sound quality",
    "battery", "price", "worth", "should i", "would you", "opinion",
    "first one", "second one", "third one", "last one", "#1", "#2", "#3",
    "that one", "this one", "the one", "it", "them", "those",
    "cheaper", "more expensive", "budget", "premium",
    "how long", "does it", "can it", "is it", "are they",
    "what's the", "whats the", "do they", "noise cancelling",
]


def _is_followup_query(prompt: str) -> bool:
    """Detect if a user message is a follow-up about existing products."""
    lower = prompt.lower().strip()

    # Short messages are almost always follow-ups when products exist
    if len(lower.split()) <= 5:
        return True

    # Check for follow-up signal words
    for signal in FOLLOWUP_SIGNALS:
        if signal in lower:
            return True

    # Messages starting with question words about existing context
    question_starts = ["which", "what", "how", "why", "is", "are", "do", "does", "can", "should", "would"]
    first_word = lower.split()[0] if lower else ""
    if first_word in question_starts and len(lower.split()) <= 12:
        return True

    return False


def load_session_messages(chat_session_id: int):
    """Load messages from DB for a given chat session."""
    try:
        messages = make_authenticated_request(f"/search/messages/{chat_session_id}", method="GET")
        history = []
        products_from_session = []
        for msg in messages:
            role = "assistant" if msg["role"] == "system" else "user"
            content = msg["content"]
            refs = msg.get("refs", "") or ""

            if role == "assistant":
                try:
                    parsed = json.loads(content)
                    products_from_session = parsed.get("products", [])
                    summary = parsed.get("reasoning_summary", "")
                    content = json.dumps({"products": products_from_session, "reasoning_summary": summary, "refs": refs})
                except Exception:
                    pass

            history.append({"role": role, "content": content})
        return history, products_from_session
    except Exception:
        return [], []


def fetch_listings_concurrent(products):
    """Fetch product listings in parallel."""
    product_listings = {}

    def _fetch(name):
        try:
            listings = search_product_listings(name)
            return name, listings[:3] if isinstance(listings, list) else []
        except Exception:
            return name, []

    names = [p.get("product_name", "") for p in products if p.get("product_name")]
    with ThreadPoolExecutor(max_workers=3) as executor:
        results = executor.map(_fetch, names)
        for name, listings in results:
            product_listings[name] = listings

    return product_listings


def render_unified_product_view(products, product_listings, reasoning_summary="", refs="", selectable=False):
    """Render a single unified view: each product with listings + review + news + YouTube."""
    if reasoning_summary:
        st.markdown(f"**Community Insight:** {reasoning_summary}")
        st.markdown("")

    if "selected_products" not in st.session_state:
        st.session_state.selected_products = set()

    for idx, product in enumerate(products):
        name = product.get("product_name", "Unknown")
        reason = product.get("reason_for_recommendation", "")
        detailed = product.get("detailed_review", "")
        news = product.get("news_articles", [])
        youtube = product.get("youtube_reviews", [])
        pricing = product.get("pricing_insight", {})
        listings = product_listings.get(name, [])

        # Product header with selection checkbox
        if selectable:
            selected = st.checkbox(f"**{idx + 1}. {name}**", key=f"select_{name}_{idx}", value=name in st.session_state.selected_products)
            if selected:
                st.session_state.selected_products.add(name)
            else:
                st.session_state.selected_products.discard(name)
        else:
            st.markdown(f"### {idx + 1}. {name}")

        col_listings, col_review = st.columns([1, 1])

        with col_listings:
            # Live product listings
            if listings:
                for listing in listings[:3]:
                    merchant = listing.get("merchant_name", "")
                    price = listing.get("price", "N/A")
                    url = listing.get("product_url", "#")
                    st.markdown(
                        f'<div style="background:#1a1a2e;border:1px solid #333;border-radius:10px;padding:14px;margin-bottom:10px;">'
                        f'<div style="font-weight:600;font-size:0.95em;">{merchant}</div>'
                        f'<div style="color:#4CAF50;font-size:1.2em;font-weight:700;margin:4px 0;">{price}</div>'
                        f'<a href="{url}" target="_blank" style="color:#64B5F6;text-decoration:none;font-size:0.9em;">Buy Now &rarr;</a>'
                        f'</div>',
                        unsafe_allow_html=True
                    )
            else:
                search_url = f"https://www.google.com/search?tbm=shop&q={name.replace(' ', '+')}"
                st.markdown(
                    f'<div style="background:#1a1a2e;border:1px solid #333;border-radius:10px;padding:14px;">'
                    f'<div style="color:#888;">No live listings found</div>'
                    f'<a href="{search_url}" target="_blank" style="color:#64B5F6;text-decoration:none;font-size:0.9em;">Search on Google Shopping &rarr;</a>'
                    f'</div>',
                    unsafe_allow_html=True
                )

            # Pricing insight
            if pricing and (pricing.get("lowest_price") or pricing.get("best_time_to_buy") or pricing.get("price_trend")):
                trend = pricing.get("price_trend", "stable")
                trend_color = "#4CAF50" if trend == "dropping" else "#FF9800" if trend == "rising" else "#888"
                trend_icon = "&#8595;" if trend == "dropping" else "&#8593;" if trend == "rising" else "&#8596;"
                source_url = pricing.get("source_url", "")

                price_html = f'<div style="background:#0d1117;border:1px solid #30363d;border-radius:10px;padding:14px;margin-top:10px;">'
                price_html += f'<div style="font-weight:600;font-size:0.95em;margin-bottom:6px;">Price Insight</div>'

                if pricing.get("lowest_price"):
                    price_html += f'<div style="font-size:0.85em;">Lowest seen: <span style="color:#4CAF50;font-weight:700;">{pricing["lowest_price"]}</span></div>'

                price_html += f'<div style="font-size:0.85em;">Trend: <span style="color:{trend_color};">{trend_icon} {trend}</span></div>'

                if pricing.get("best_time_to_buy"):
                    price_html += f'<div style="font-size:0.85em;margin-top:4px;">{pricing["best_time_to_buy"]}</div>'

                if source_url:
                    price_html += f'<a href="{source_url}" target="_blank" style="color:#64B5F6;text-decoration:none;font-size:0.8em;display:block;margin-top:6px;">View price history &rarr;</a>'

                price_html += '</div>'
                st.markdown(price_html, unsafe_allow_html=True)

        with col_review:
            # Community review
            st.markdown("**Community Review**")
            review_text = detailed if detailed else reason
            # Clean up any raw markdown/formatting artifacts
            review_text = review_text.replace("\\n", "\n").strip()
            st.markdown(review_text)

            # News articles
            if news:
                st.markdown("")
                st.markdown("**Expert Reviews**")
                for article in news[:3]:
                    title = article.get("title", "").strip()
                    url = article.get("url", "")
                    source = article.get("source", "").replace("www.", "")
                    if not title or not url or title.startswith("http"):
                        continue
                    # Clean title: remove markdown artifacts
                    clean_title = title.lstrip("#").strip()[:80]
                    label = f"{clean_title} - {source}" if source else clean_title
                    st.markdown(
                        f'<a href="{url}" target="_blank" style="color:#64B5F6;text-decoration:none;display:block;padding:4px 0;font-size:0.9em;">'
                        f'&#128240; {label}</a>',
                        unsafe_allow_html=True
                    )

            # YouTube reviews
            if youtube:
                st.markdown("")
                st.markdown("**YouTube Reviews**")
                for video in youtube[:2]:
                    title = video.get("title", "").strip()
                    url = video.get("url", "")
                    if not title or not url or title.startswith("http"):
                        continue
                    clean_title = title.lstrip("#").strip()[:80]
                    st.markdown(
                        f'<a href="{url}" target="_blank" style="color:#FF4444;text-decoration:none;display:block;padding:4px 0;font-size:0.9em;">'
                        f'&#9654; {clean_title}</a>',
                        unsafe_allow_html=True
                    )

        st.markdown("---")

    # Action buttons based on selection
    if selectable:
        selected = st.session_state.selected_products
        num_selected = len(selected)

        if num_selected > 0:
            cols = st.columns(3)
            with cols[0]:
                if st.button(f"More Details ({num_selected} selected)", use_container_width=True, key="btn_details"):
                    st.session_state.followup_action = "details"
                    st.session_state.followup_products = [
                        p for p in products if p.get("product_name") in selected
                    ]
            with cols[1]:
                if num_selected >= 2:
                    if st.button(f"Compare ({num_selected} selected)", use_container_width=True, key="btn_compare"):
                        st.session_state.followup_action = "compare"
                        st.session_state.followup_products = [
                            p for p in products if p.get("product_name") in selected
                        ]
            with cols[2]:
                if st.button("Clear Selection", use_container_width=True, key="btn_clear_sel"):
                    st.session_state.selected_products = set()
                    st.rerun()


def render_assistant_message(content, product_listings, selectable=False):
    """Render an assistant message — either structured products or plain text."""
    try:
        parsed = json.loads(content)
        products = parsed.get("products", [])
        summary = parsed.get("reasoning_summary", "")
        refs = parsed.get("refs", "")
        if products:
            render_unified_product_view(products, product_listings, summary, refs, selectable=selectable)
            return
    except (json.JSONDecodeError, TypeError):
        pass
    st.markdown(content)


def qa_interface():
    st.title("Rekomme")
    st.caption("AI shopping recommendations from real Reddit community discussions")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "recommended_products" not in st.session_state:
        st.session_state.recommended_products = []
    if "chat_session_id" not in st.session_state:
        st.session_state.chat_session_id = None
    if "last_loaded_session" not in st.session_state:
        st.session_state.last_loaded_session = None
    if "product_listings" not in st.session_state:
        st.session_state.product_listings = {}
    if "active_session_label" not in st.session_state:
        st.session_state.active_session_label = None

    categories = get_categories() or ["headphones"]

    # --- Sidebar ---
    with st.sidebar:
        st.markdown("### Category")
        category = st.selectbox(
            "What are you shopping for?",
            categories,
            help="Choose a product category to search."
        )

        st.markdown("---")

        if st.button("+ New Chat", use_container_width=True):
            st.session_state.chat_history = []
            st.session_state.recommended_products = []
            st.session_state.product_listings = {}
            st.session_state.chat_session_id = None
            st.session_state.last_loaded_session = None
            st.session_state.active_session_label = None
            st.rerun()

        st.markdown("### Recent Chats")
        try:
            sessions = fetch_chat_sessions()
        except Exception:
            sessions = []

        selected_session_from_sidebar = None
        for session_label in sessions:
            session_id = process_selected_chat_session(session_label)
            title = session_label.split(": ", 1)[1] if ": " in session_label else session_label
            is_active = st.session_state.active_session_label == session_label
            if st.button(
                f"{'> ' if is_active else ''}{title[:40]}",
                key=f"session_{session_id}",
                use_container_width=True,
            ):
                selected_session_from_sidebar = session_label

    # Handle sidebar session click
    if selected_session_from_sidebar:
        session_id = process_selected_chat_session(selected_session_from_sidebar)
        if session_id and session_id != st.session_state.last_loaded_session:
            st.session_state.chat_session_id = session_id
            st.session_state.last_loaded_session = session_id
            st.session_state.active_session_label = selected_session_from_sidebar
            history, old_products = load_session_messages(session_id)
            st.session_state.chat_history = history
            st.session_state.recommended_products = old_products
            if old_products:
                st.session_state.product_listings = fetch_listings_concurrent(old_products)
            else:
                st.session_state.product_listings = {}
            st.rerun()

    # --- Main area ---

    # Onboarding
    if not st.session_state.chat_history:
        st.markdown("### What would you like to find?")
        st.markdown("Get recommendations backed by real community discussions and reviews.")
        st.markdown("**Try asking:**")
        cols = st.columns(2)
        for i, example in enumerate(EXAMPLE_QUERIES):
            with cols[i % 2]:
                if st.button(example, use_container_width=True, key=f"example_{i}"):
                    st.session_state.prefill_prompt = example
                    st.rerun()

    # Display chat history — unified view, last assistant message is selectable
    for i, message in enumerate(st.session_state.chat_history):
        is_last_assistant = (
            message["role"] == "assistant" and
            i == len(st.session_state.chat_history) - 1 and
            st.session_state.recommended_products
        )
        with st.chat_message(message["role"]):
            if message["role"] == "assistant":
                render_assistant_message(
                    message["content"], st.session_state.product_listings,
                    selectable=is_last_assistant
                )
            else:
                st.markdown(message["content"])

    # Handle follow-up actions (More Details / Compare)
    followup_action = st.session_state.pop("followup_action", None)
    followup_products = st.session_state.pop("followup_products", None)

    if followup_action and followup_products:
        product_names = [p.get("product_name", "") for p in followup_products]
        if followup_action == "details":
            followup_prompt = f"Give me detailed information about: {', '.join(product_names)}"
        else:
            followup_prompt = f"Compare these products side by side: {', '.join(product_names)}"

        st.session_state.chat_history.append({"role": "user", "content": followup_prompt})
        with st.chat_message("user"):
            st.markdown(followup_prompt)

        with st.chat_message("assistant"):
            with st.spinner("Analyzing products..."):
                try:
                    resp = search_followup(
                        followup_prompt, followup_products,
                        st.session_state.chat_session_id, followup_action
                    )
                    result = resp.get("response", "")
                    st.markdown(result)
                    st.session_state.chat_history.append({"role": "assistant", "content": result})
                    if resp.get("chat_session_id"):
                        st.session_state.chat_session_id = resp["chat_session_id"]
                except Exception as e:
                    st.error(f"Follow-up failed: {e}")

    # Handle prefill
    prefill = st.session_state.pop("prefill_prompt", None)
    prompt = st.chat_input("Ask for a product recommendation...") or prefill

    if prompt:
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Decide: follow-up or new query?
        has_products = bool(st.session_state.recommended_products)
        is_followup = has_products and _is_followup_query(prompt)

        with st.chat_message("assistant"):
            if is_followup:
                # Follow-up: use product context, no full pipeline
                with st.spinner("Thinking..."):
                    try:
                        resp = search_followup(
                            prompt, st.session_state.recommended_products,
                            st.session_state.chat_session_id, "question"
                        )
                        result = resp.get("response", "")
                        st.markdown(result)
                        st.session_state.chat_history.append({"role": "assistant", "content": result})
                        if resp.get("chat_session_id"):
                            st.session_state.chat_session_id = resp["chat_session_id"]
                    except Exception as e:
                        st.error(f"Follow-up failed: {e}")
            else:
                # New query: full agent pipeline
                with st.spinner("Searching community discussions..."):
                    try:
                        # Reset products for new search
                        st.session_state.selected_products = set()
                        response = search_initial(
                            DEFAULT_MODEL, prompt, category,
                            str(st.session_state.chat_session_id) if st.session_state.chat_session_id else None,
                            st.session_state.chat_history
                        )

                        if isinstance(response, dict):
                            rag_output = response.get("response", {})
                            products = rag_output.get("products", [])
                            reasoning_summary = rag_output.get("reasoning_summary", "")
                            chat_session_id = response.get("chat_session_id")

                            if chat_session_id:
                                st.session_state.chat_session_id = chat_session_id
                                st.session_state.last_loaded_session = chat_session_id

                            if not products:
                                st.warning("No specific products found. Try rephrasing your query.")
                            else:
                                st.session_state.recommended_products = products

                                with st.spinner("Finding live prices..."):
                                    st.session_state.product_listings = fetch_listings_concurrent(products)

                                content_data = json.dumps({
                                    "products": products,
                                    "reasoning_summary": reasoning_summary,
                                    "refs": ""
                                })
                                st.session_state.chat_history.append(
                                    {"role": "assistant", "content": content_data}
                                )

                                render_unified_product_view(
                                    products, st.session_state.product_listings,
                                    reasoning_summary, selectable=True
                                )

                    except Exception as e:
                        st.error(f"Something went wrong: {e}")


if __name__ == "__main__":
    qa_interface()
