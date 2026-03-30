from pydantic import BaseModel, Field


class NewsArticle(BaseModel):
    """A news or review article about a product"""
    title: str = Field("", description="Title of the article")
    url: str = Field("", description="URL to the article")
    snippet: str = Field("", description="Short excerpt from the article")
    source: str = Field("", description="Publication or website name")


class YouTubeReview(BaseModel):
    """A YouTube review video for a product"""
    title: str = Field("", description="Title of the YouTube video")
    url: str = Field("", description="URL to the YouTube video")
    channel: str = Field("", description="YouTube channel name")


class PricingInsight(BaseModel):
    """Price history and buying advice for a product"""
    current_price: str = Field("", description="Current typical price")
    lowest_price: str = Field("", description="Lowest recorded price found")
    best_time_to_buy: str = Field("", description="Advice on when to buy (e.g. Black Friday, Prime Day)")
    price_trend: str = Field("", description="Price trend: rising, stable, or dropping")
    source_url: str = Field("", description="URL to price tracking page")


class ExtractedProduct(BaseModel):
    """Product details for each of the extracted products"""
    product_name: str = Field(..., description="The name of the product extracted from the text")
    reason_for_recommendation: str = Field(..., description="A concise 1-2 sentence reason for recommending this product")
    detailed_review: str = Field(
        "",
        description="A detailed 3-5 sentence community review including user testimonials, long-term usage insights, pros/cons, and any caveats mentioned by real users"
    )
    news_articles: list[NewsArticle] = Field(default_factory=list, description="News and review articles about this product (populated separately)")
    youtube_reviews: list[YouTubeReview] = Field(default_factory=list, description="YouTube review videos for this product (populated separately)")
    pricing_insight: PricingInsight = Field(default_factory=PricingInsight, description="Price history and buying advice (populated separately)")


class SearchResult(BaseModel):
    """Search result containing extracted products"""
    products: list[ExtractedProduct] = Field(..., description="List of extracted products")
    reasoning_summary: str = Field(..., description="A brief summary of how the LLM derived these suggestions")
