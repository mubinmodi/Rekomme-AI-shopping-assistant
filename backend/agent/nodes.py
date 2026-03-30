import json
import logging
from concurrent.futures import ThreadPoolExecutor

from langchain_community.tools import TavilySearchResults
from langchain_core.language_models import BaseChatModel

from backend.agent.generate_chain import create_recommendation_chain
from backend.agent.graph import Steps, GraphState
from backend.agent.vector_store import Retriever
from backend.database.messages import create_message, MessageSenderEnum
from backend.schemas.chain import NewsArticle, YouTubeReview, PricingInsight, CommunitySource

logger = logging.getLogger(__name__)


class GraphNodes:
    def __init__(
        self, llm: BaseChatModel, retriever: Retriever,
        batch_retrieval_grader, question_rewriter,
        web_search_tool: TavilySearchResults,
        enrichment_search_tool: TavilySearchResults,
    ):
        self.llm = llm
        self.retriever = retriever
        self.batch_retrieval_grader = batch_retrieval_grader
        self.question_rewriter = question_rewriter
        self.web_search_tool = web_search_tool
        self.enrichment_search_tool = enrichment_search_tool
        self.generate_chain = create_recommendation_chain(llm)

    # ── Retrieval ──

    def vector_store_retrieve(self, state):
        print("---RETRIEVE (MMR, k=10)---")
        prompt = state["prompt"]
        namespace = state["category"]

        documents = self.retriever.sim_search(prompt, namespace)

        # Extract source URLs from Pinecone metadata
        source_urls = []
        seen_ids = set()
        for doc in documents:
            meta = doc.metadata if hasattr(doc, "metadata") else {}
            title = meta.get("title", "")[:120]
            subreddit = meta.get("subreddit", "")
            post_id = meta.get("id", "")

            # Skip if no useful metadata
            if not title or not post_id:
                continue
            # Deduplicate by post_id (same post can have multiple chunks)
            if post_id in seen_ids:
                continue
            seen_ids.add(post_id)

            # Build Reddit URL
            if subreddit:
                url = f"https://reddit.com/r/{subreddit}/comments/{post_id}"
            else:
                url = f"https://reddit.com/search/?q={title.replace(' ', '+')}"

            source_urls.append({
                "url": url,
                "title": title,
                "subreddit": subreddit or "reddit",
                "content_preview": (doc.page_content[:200] if hasattr(doc, "page_content") else ""),
            })

        print(f"Extracted {len(source_urls)} unique sources from Pinecone")
        state["resources"] = documents
        state["source_urls"] = source_urls
        state["steps"] = [Steps.VECTOR_STORE_RETRIEVAL.value]
        state["retry_count"] = 0
        return state

    # ── Batch Grading (1 LLM call instead of N) ──

    def batch_grade_documents(self, state: GraphState):
        print("---BATCH GRADE DOCUMENTS---")
        prompt = state["prompt"]
        resources = state["resources"]

        # Format all docs into a numbered list
        doc_texts = []
        for i, r in enumerate(resources):
            text = r.page_content if hasattr(r, "page_content") else str(r)
            doc_texts.append(f"Document {i+1}: {text[:500]}")

        numbered_docs = "\n\n".join(doc_texts)

        try:
            result = self.batch_retrieval_grader.invoke({
                "prompt": prompt,
                "resources": numbered_docs
            })

            scores = result.get("scores", [])
            relevant_indices = {s["index"] for s in scores if s.get("relevant", "no").lower() == "yes"}

            filtered = [r for i, r in enumerate(resources) if (i + 1) in relevant_indices]

            if len(filtered) < len(resources) // 2:
                state["perform_web_search"] = True

            state["resources"] = filtered if filtered else resources[:3]  # Keep top 3 as fallback
        except Exception as e:
            logger.warning(f"Batch grading failed, keeping all docs: {e}")
            state["resources"] = resources

        state["steps"].append(Steps.VECTOR_STORE_EVALUATION.value)
        print(f"Kept {len(state['resources'])} of {len(resources)} documents")
        return state

    # ── Query Rewriter ──

    def transform_query(self, state):
        print("---TRANSFORM QUERY---")
        prompt = state["prompt"]

        try:
            better_question = self.question_rewriter.invoke({"question": prompt})
            state["prompt"] = better_question.strip()
            print(f"Rewrote: '{prompt[:50]}' → '{state['prompt'][:50]}'")
        except Exception as e:
            logger.warning(f"Query rewrite failed: {e}")

        state["steps"].append(Steps.QUERY_REWRITE.value)
        return state

    # ── Web Search ──

    def web_search(self, state: GraphState):
        print("---WEB SEARCH - TAVILY---")
        prompt = state["prompt"]
        web_results = self.web_search_tool.invoke({"query": prompt})
        state["resources"] = [result["content"] for result in web_results]
        state["steps"].append(Steps.WEB_SEARCH_RETRIEVAL.value)
        return state

    # ── Live Reddit Search ──

    def live_reddit_search(self, state):
        print("---LIVE REDDIT SEARCH---")
        prompt = state["prompt"]

        queries = [
            f"{prompt} site:reddit.com",
            f"{prompt} reddit recommendation 2024 2025",
        ]

        live_results = []
        source_urls = state.get("source_urls", [])
        seen_urls = set(s.get("url", "") for s in source_urls)

        def _search(query):
            try:
                results = self.web_search_tool.invoke({"query": query})
                found = []
                for r in results:
                    url = r.get("url", "")
                    content = r.get("content", "")
                    if url in seen_urls or len(content) < 50:
                        continue
                    seen_urls.add(url)
                    # Extract subreddit from URL
                    subreddit = ""
                    if "reddit.com/r/" in url:
                        subreddit = url.split("/r/")[1].split("/")[0]
                    title = content.strip().split("\n")[0][:120].lstrip("#").strip()
                    found.append({"content": content, "url": url, "title": title, "subreddit": subreddit})
                return found
            except Exception as e:
                logger.warning(f"Live Reddit search failed: {e}")
                return []

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(_search, queries))
            for result_list in results:
                live_results.extend(result_list)

        existing = state.get("resources", [])
        existing_text = [r.page_content if hasattr(r, "page_content") else r for r in existing]

        for item in live_results[:5]:
            existing_text.append(f"[Recent community discussion] {item['content']}")
            source_urls.append({
                "url": item["url"],
                "title": item["title"],
                "subreddit": item.get("subreddit", "")
            })

        state["resources"] = existing_text
        state["source_urls"] = source_urls
        state["steps"].append(Steps.LIVE_REDDIT_SEARCH.value)
        print(f"Added {min(len(live_results), 5)} live Reddit results, {len(source_urls)} total sources")
        return state

    # ── Generation ──

    def generate(self, state):
        print("---GENERATE---")
        prompt = state["prompt"]
        resources = [r.page_content if hasattr(r, "page_content") else r for r in state["resources"]]

        generation = self.generate_chain.invoke({
            "resources": '\n'.join(f"{i+1}. {item}" for i, item in enumerate(resources)),
            "prompt": prompt
        })

        state["generation"] = generation
        state["retry_count"] = state.get("retry_count", 0) + 1
        state["steps"].append(Steps.LLM_GENERATION.value)
        return state

    # ── Enrichment (combined news + YouTube in 1 call per product) ──

    def enrich_with_sources(self, state):
        print("---ENRICH WITH SOURCES---")
        generation = state["generation"]
        products = generation.products

        def _extract_title(content, url):
            if not content:
                return url.split("/")[-1].replace("-", " ").title()[:80]
            first_line = content.strip().split("\n")[0].strip().lstrip("#").strip()
            if len(first_line) > 10 and not first_line.startswith("http"):
                return first_line[:100]
            first_sentence = content.split(".")[0].strip()[:100]
            return first_sentence if first_sentence else url.split("/")[-1].replace("-", " ").title()[:80]

        def _extract_domain(url):
            try:
                return url.split("/")[2].replace("www.", "")
            except Exception:
                return ""

        def _search_combined(product_name):
            """Single Tavily call per product — split news vs YouTube by URL."""
            try:
                results = self.enrichment_search_tool.invoke(
                    {"query": f"{product_name} review 2024 2025"}
                )
                articles = []
                videos = []
                for r in results[:7]:
                    url = r.get("url", "")
                    content = r.get("content", "")
                    title = _extract_title(content, url)

                    if "youtube.com" in url or "youtu.be" in url:
                        if len(videos) < 2:
                            videos.append(YouTubeReview(title=title, url=url, channel=_extract_domain(url)))
                    else:
                        if len(articles) < 3:
                            articles.append(NewsArticle(
                                title=title, url=url,
                                snippet=content[:200].replace("\n", " ").strip(),
                                source=_extract_domain(url)
                            ))
                return product_name, articles, videos
            except Exception as e:
                logger.warning(f"Enrichment failed for {product_name}: {e}")
                return product_name, [], []

        def _search_price_history(product_name):
            """Search for price history and buying advice."""
            try:
                results = self.enrichment_search_tool.invoke(
                    {"query": f"{product_name} price history lowest price best time to buy"}
                )
                pricing = PricingInsight()
                for r in results[:3]:
                    url = r.get("url", "")
                    content = r.get("content", "").lower()

                    # Extract price mentions
                    if not pricing.source_url and ("camelcamelcamel" in url or "price" in url):
                        pricing.source_url = url

                    # Look for price patterns in content
                    import re
                    prices = re.findall(r'\$[\d,]+(?:\.\d{2})?', r.get("content", ""))
                    if prices and not pricing.current_price:
                        pricing.current_price = prices[0]
                    if len(prices) > 1 and not pricing.lowest_price:
                        sorted_prices = sorted(prices, key=lambda p: float(p.replace('$', '').replace(',', '')))
                        pricing.lowest_price = sorted_prices[0]

                    # Detect trends
                    if "dropping" in content or "price drop" in content or "sale" in content:
                        pricing.price_trend = "dropping"
                    elif "rising" in content or "price increase" in content:
                        pricing.price_trend = "rising"
                    elif not pricing.price_trend:
                        pricing.price_trend = "stable"

                # Best time to buy advice
                if pricing.price_trend == "dropping":
                    pricing.best_time_to_buy = "Prices are dropping — good time to buy now"
                elif "black friday" in str(results).lower():
                    pricing.best_time_to_buy = "Best deals typically during Black Friday and Prime Day"
                else:
                    pricing.best_time_to_buy = "Check around Prime Day (July) and Black Friday (November) for best deals"

                if not pricing.source_url:
                    pricing.source_url = f"https://www.google.com/search?q={product_name.replace(' ', '+')}+price+history"

                return product_name, pricing
            except Exception as e:
                logger.warning(f"Price search failed for {product_name}: {e}")
                return product_name, PricingInsight()

        product_names = [p.product_name for p in products]

        news_map = {}
        youtube_map = {}
        pricing_map = {}
        with ThreadPoolExecutor(max_workers=6) as executor:
            combined_futures = {executor.submit(_search_combined, name): ("combined", name) for name in product_names}
            price_futures = {executor.submit(_search_price_history, name): ("price", name) for name in product_names}

            for future in combined_futures:
                name, articles, videos = future.result()
                news_map[name] = articles
                youtube_map[name] = videos

            for future in price_futures:
                name, pricing = future.result()
                pricing_map[name] = pricing

        # Match community sources to products
        source_urls = state.get("source_urls", [])

        for product in products:
            product.news_articles = news_map.get(product.product_name, [])
            product.youtube_reviews = youtube_map.get(product.product_name, [])
            product.pricing_insight = pricing_map.get(product.product_name, PricingInsight())

            product_lower = product.product_name.lower()
            # Match partial names: "Sony WH-1000XM5" → ["sony", "wh-1000xm5"]
            name_parts = [p for p in product_lower.split() if len(p) > 2]

            matched_sources = []
            for src in source_urls:
                # Check title, subreddit, AND content preview for product mention
                src_text = f"{src.get('title', '')} {src.get('subreddit', '')} {src.get('content_preview', '')}".lower()
                if any(part in src_text for part in name_parts) or product_lower in src_text:
                    matched_sources.append(CommunitySource(
                        title=src.get("title", "Reddit discussion")[:100],
                        url=src.get("url", ""),
                        subreddit=src.get("subreddit", "reddit")
                    ))

            # If no specific match, all sources contributed context — assign top ones
            if not matched_sources and source_urls:
                for src in source_urls[:3]:
                    matched_sources.append(CommunitySource(
                        title=src.get("title", "Reddit discussion")[:100],
                        url=src.get("url", ""),
                        subreddit=src.get("subreddit", "reddit")
                    ))

            product.community_sources = matched_sources[:4]
            print(f"  {product.product_name}: {len(product.community_sources)} sources matched")

        # Persist messages
        prompt = state["prompt"]
        resources = [r.page_content if hasattr(r, "page_content") else r for r in state["resources"]]

        tools_used = [s for s in state.get("steps", [])]

        create_message(
            content=prompt, chat_session_id=state["chat_session_id"],
            references=[], sender=MessageSenderEnum.USER, tools_used=tools_used
        )
        create_message(
            content=json.dumps(generation.model_dump(mode="json")),
            chat_session_id=state["chat_session_id"],
            references=[r for r in resources],
            sender=MessageSenderEnum.SYSTEM, tools_used=tools_used
        )

        state["generation"] = generation
        state["steps"].append(Steps.SOURCE_ENRICHMENT.value)
        return state
