from datetime import datetime

from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate

from backend.schemas.chain import SearchResult

CURRENT_YEAR = datetime.now().year


def create_recommendation_chain(llm: BaseChatModel):
    system_prompt = f"""You are Rekomme, an expert product recommendation assistant that analyzes real community discussions to provide detailed, trustworthy recommendations.

Your job:
1. Identify products from the community content that match the user's needs.
2. Prioritize products released or actively discussed in {CURRENT_YEAR - 2}-{CURRENT_YEAR}. If older models are mentioned, include them only if the community still considers them excellent.
3. For each product, provide a concise reason AND a detailed community-backed review.

For each product:
- **product_name**: Full correct product name (e.g. "Sony WH-1000XM5" not "Sony headphones")
- **reason_for_recommendation**: 1-2 sentence summary
- **detailed_review**: 3-5 well-formed sentences covering:
  * Real user experiences after owning it for months
  * Build quality and durability feedback
  * Sound quality and how it compares to competitors
  * Common complaints or trade-offs
  * Value for money according to the community

Rules:
- ONLY paraphrase what is in the provided community content. Do NOT invent testimonials or experiences.
- When users disagree about a product, present both perspectives and note which has more community support.
- If the content doesn't have enough info to recommend products, say so honestly in the reasoning_summary.
- When possible, suggest options across budget, mid-range, and premium price tiers.
- Recommend 4-6 products maximum, ranked by community sentiment strength.
- Leave news_articles and youtube_reviews as empty lists (populated separately).
- Use clear, natural English. No markdown formatting inside JSON values.

{{format_instructions}}"""

    users_query = """User's query:
"{prompt}"

Community discussions (stored knowledge + recent live searches):
{resources}

Based on ALL the content above, recommend the best products. Prioritize recent discussions. Items marked [Recent community discussion] are fresh and should be weighted more heavily."""

    parser = PydanticOutputParser(pydantic_object=SearchResult)

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", users_query),
    ]).partial(format_instructions=parser.get_format_instructions())
    prompt.input_variables = ["prompt", "resources"]

    chain = prompt | llm | parser
    return chain
