"""
Rekomme Hackathon Pitch Deck Generator
Generates a 16:9 professional pitch deck as .pptx
"""
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

# Constants
SLIDE_WIDTH = Inches(13.333)
SLIDE_HEIGHT = Inches(7.5)
BG_COLOR = RGBColor(0x0D, 0x11, 0x17)
ACCENT = RGBColor(0x64, 0xB5, 0xF6)
GREEN = RGBColor(0x4C, 0xAF, 0x50)
ORANGE = RGBColor(0xFF, 0x6B, 0x35)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT_GRAY = RGBColor(0xAA, 0xAA, 0xAA)
DARK_CARD = RGBColor(0x1A, 0x1A, 0x2E)
YELLOW = RGBColor(0xFF, 0xD5, 0x4F)


def set_slide_bg(slide, color=BG_COLOR):
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = color


def add_text_box(slide, left, top, width, height, text, font_size=18,
                 color=WHITE, bold=False, alignment=PP_ALIGN.LEFT, font_name="Calibri"):
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(font_size)
    p.font.color.rgb = color
    p.font.bold = bold
    p.font.name = font_name
    p.alignment = alignment
    return txBox


def add_card(slide, left, top, width, height, fill_color=DARK_CARD):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill_color
    shape.line.fill.background()
    shape.shadow.inherit = False
    return shape


def add_image(slide, image_path, left, top, width, height):
    slide.shapes.add_picture(image_path, left, top, width, height)


def create_deck():
    prs = Presentation()
    prs.slide_width = SLIDE_WIDTH
    prs.slide_height = SLIDE_HEIGHT
    blank_layout = prs.slide_layouts[6]

    ARCH_DIR = "/Users/mubinmodi/FinalProject-AI-Shoping-Assistant/Architecture"

    # ═══════════════════════════════════════════
    # SLIDE 1 — TITLE
    # ═══════════════════════════════════════════
    slide = prs.slides.add_slide(blank_layout)
    set_slide_bg(slide)
    add_text_box(slide, Inches(1), Inches(2), Inches(11), Inches(1.5),
                 "Rekomme", font_size=60, bold=True, color=ACCENT, alignment=PP_ALIGN.CENTER)
    add_text_box(slide, Inches(1), Inches(3.5), Inches(11), Inches(1),
                 "AI Shopping Assistant Powered by Real Community Opinions",
                 font_size=24, color=WHITE, alignment=PP_ALIGN.CENTER)
    add_text_box(slide, Inches(1), Inches(5), Inches(11), Inches(0.5),
                 "Stop guessing. Start buying what real people actually recommend.",
                 font_size=16, color=LIGHT_GRAY, alignment=PP_ALIGN.CENTER)

    # ═══════════════════════════════════════════
    # SLIDE 2 — PROBLEM
    # ═══════════════════════════════════════════
    slide = prs.slides.add_slide(blank_layout)
    set_slide_bg(slide)
    add_text_box(slide, Inches(0.8), Inches(0.4), Inches(11), Inches(0.8),
                 "The Problem", font_size=40, bold=True, color=ORANGE)

    add_card(slide, Inches(0.8), Inches(1.4), Inches(11.5), Inches(1.2), DARK_CARD)
    add_text_box(slide, Inches(1.2), Inches(1.5), Inches(10.5), Inches(1),
                 "95% of online shoppers read reviews before buying.\n"
                 "But 42% of those reviews are fake, paid, or manipulated.",
                 font_size=22, color=YELLOW, bold=True, alignment=PP_ALIGN.CENTER)

    problems = [
        ("Fake Reviews", "Amazon, Google reviews\nare gamed by sellers"),
        ("Information Overload", "100+ reviews per product.\nNo one reads them all."),
        ("No Trusted Source", "Where do real users\nhonestly discuss products?"),
    ]
    for i, (title, desc) in enumerate(problems):
        x = Inches(0.8 + i * 4)
        add_card(slide, x, Inches(3.2), Inches(3.5), Inches(2.5), DARK_CARD)
        add_text_box(slide, x + Inches(0.3), Inches(3.4), Inches(3), Inches(0.6),
                     title, font_size=20, bold=True, color=ACCENT)
        add_text_box(slide, x + Inches(0.3), Inches(4.1), Inches(3), Inches(1.2),
                     desc, font_size=15, color=LIGHT_GRAY)

    add_text_box(slide, Inches(0.8), Inches(6.2), Inches(11), Inches(0.6),
                 "The real opinions are on Reddit, YouTube, and niche forums — but scattered and hard to find.",
                 font_size=16, color=LIGHT_GRAY, alignment=PP_ALIGN.CENTER)

    # ═══════════════════════════════════════════
    # SLIDE 3 — SOLUTION
    # ═══════════════════════════════════════════
    slide = prs.slides.add_slide(blank_layout)
    set_slide_bg(slide)
    add_text_box(slide, Inches(0.8), Inches(0.4), Inches(11), Inches(0.8),
                 "Our Solution", font_size=40, bold=True, color=GREEN)

    add_text_box(slide, Inches(0.8), Inches(1.4), Inches(11), Inches(0.8),
                 "One AI assistant that reads thousands of real community discussions\n"
                 "and gives you trusted, sourced product recommendations in seconds.",
                 font_size=20, color=WHITE)

    features = [
        ("Community Intelligence", "Analyzes Reddit threads,\nforums, and discussions"),
        ("Live Market Data", "Real-time prices from\nGoogle Shopping + merchants"),
        ("Expert + Video Reviews", "News articles and YouTube\nreviews auto-attached"),
        ("Price Tracking", "Track price trends and\nfind the best time to buy"),
    ]
    for i, (title, desc) in enumerate(features):
        x = Inches(0.5 + i * 3.1)
        add_card(slide, x, Inches(3), Inches(2.8), Inches(2.5), DARK_CARD)
        add_text_box(slide, x + Inches(0.2), Inches(3.2), Inches(2.5), Inches(0.6),
                     title, font_size=17, bold=True, color=ACCENT)
        add_text_box(slide, x + Inches(0.2), Inches(3.9), Inches(2.5), Inches(1.2),
                     desc, font_size=14, color=LIGHT_GRAY)

    add_text_box(slide, Inches(0.8), Inches(6), Inches(11), Inches(0.8),
                 "Every recommendation cites its source — users can verify and trust.",
                 font_size=18, color=YELLOW, bold=True, alignment=PP_ALIGN.CENTER)

    # ═══════════════════════════════════════════
    # SLIDE 4 — WHY REDDIT DATA
    # ═══════════════════════════════════════════
    slide = prs.slides.add_slide(blank_layout)
    set_slide_bg(slide)
    add_text_box(slide, Inches(0.8), Inches(0.4), Inches(11), Inches(0.8),
                 "Why Reddit?", font_size=40, bold=True, color=ACCENT)

    add_card(slide, Inches(0.8), Inches(1.4), Inches(11.5), Inches(1.2), DARK_CARD)
    add_text_box(slide, Inches(1.2), Inches(1.5), Inches(10.5), Inches(1),
                 "Reddit is the largest collection of unfiltered, honest product opinions on the internet.\n"
                 "Google now prioritizes Reddit results for shopping queries. Reddit IPO'd at $6.5B on this data.",
                 font_size=18, color=YELLOW, bold=True, alignment=PP_ALIGN.CENTER)

    reasons = [
        ("Unbiased Opinions", "Reddit users have no financial\nincentive. No affiliate links,\nno sponsored posts, no seller\nmanipulation."),
        ("Long-Term Reviews", "Users discuss products after\nmonths of ownership — not\nday-one hype. Real durability,\ncomfort, and quality insights."),
        ("Community Validation", "Upvotes and downvotes act as\ncrowdsourced quality filters.\nBad advice gets buried,\ngood advice rises."),
    ]
    for i, (title, desc) in enumerate(reasons):
        x = Inches(0.5 + i * 4.1)
        add_card(slide, x, Inches(3.2), Inches(3.8), Inches(3), DARK_CARD)
        add_text_box(slide, x + Inches(0.3), Inches(3.4), Inches(3.3), Inches(0.5),
                     title, font_size=20, bold=True, color=GREEN)
        add_text_box(slide, x + Inches(0.3), Inches(4.1), Inches(3.3), Inches(1.8),
                     desc, font_size=14, color=LIGHT_GRAY)

    add_text_box(slide, Inches(0.8), Inches(6.5), Inches(11), Inches(0.5),
                 "r/HeadphoneAdvice alone has 1M+ members sharing daily product comparisons and honest reviews.",
                 font_size=14, color=LIGHT_GRAY, alignment=PP_ALIGN.CENTER)

    # ═══════════════════════════════════════════
    # SLIDE 5 — SYSTEM ARCHITECTURE (diagram)
    # ═══════════════════════════════════════════
    slide = prs.slides.add_slide(blank_layout)
    set_slide_bg(slide)
    add_text_box(slide, Inches(0.8), Inches(0.2), Inches(11), Inches(0.6),
                 "System Architecture", font_size=36, bold=True, color=ACCENT)
    add_image(slide, f"{ARCH_DIR}/system_architecture.png",
              Inches(0.5), Inches(1.2), Inches(12.3), Inches(3.8))
    add_text_box(slide, Inches(0.8), Inches(5.2), Inches(11), Inches(0.5),
                 "Streamlit UI  >  FastAPI Backend  >  LangGraph Agent  >  Multi-Source Enrichment  >  Data Layer",
                 font_size=14, color=LIGHT_GRAY, alignment=PP_ALIGN.CENTER)

    # ═══════════════════════════════════════════
    # SLIDE 6 — DATA PIPELINE (diagram)
    # ═══════════════════════════════════════════
    slide = prs.slides.add_slide(blank_layout)
    set_slide_bg(slide)
    add_text_box(slide, Inches(0.8), Inches(0.15), Inches(11), Inches(0.5),
                 "Data Pipeline", font_size=36, bold=True, color=ACCENT)
    img_w2 = Inches(4.6)
    img_h2 = Inches(6.8)
    img_left2 = Inches((13.333 - 4.6) / 2)
    add_image(slide, f"{ARCH_DIR}/pipeline_flow.png",
              img_left2, Inches(0.7), img_w2, img_h2)

    # ═══════════════════════════════════════════
    # SLIDE 7 — HOW WE SCALE
    # ═══════════════════════════════════════════
    slide = prs.slides.add_slide(blank_layout)
    set_slide_bg(slide)
    add_text_box(slide, Inches(0.8), Inches(0.4), Inches(11), Inches(0.8),
                 "How We Scale", font_size=40, bold=True, color=ACCENT)

    phases = [
        ("Phase 1: Headphones", "Prove the model in one\nhigh-engagement category.\n"
         "r/HeadphoneAdvice = 1M+ members"),
        ("Phase 2: Consumer Electronics", "Expand to laptops, keyboards,\ncameras, smart home.\n"
         "Same pipeline, new subreddits."),
        ("Phase 3: All Categories", "Fashion, skincare, fitness gear.\n"
         "Any category with community\ndiscussions."),
        ("Phase 4: Platform + API", "Let other apps and AI agents\nuse Rekomme as a tool\nvia MCP / API."),
    ]
    for i, (title, desc) in enumerate(phases):
        x = Inches(0.5 + i * 3.1)
        add_card(slide, x, Inches(1.6), Inches(2.8), Inches(3.5), DARK_CARD)
        add_text_box(slide, x + Inches(0.2), Inches(1.8), Inches(2.5), Inches(0.5),
                     title, font_size=16, bold=True, color=GREEN)
        add_text_box(slide, x + Inches(0.2), Inches(2.5), Inches(2.5), Inches(2.2),
                     desc, font_size=14, color=LIGHT_GRAY)

    add_text_box(slide, Inches(0.8), Inches(5.8), Inches(11), Inches(0.8),
                 "Each new category = same tech stack + new data source. Scales horizontally with minimal effort.",
                 font_size=16, color=YELLOW, bold=True, alignment=PP_ALIGN.CENTER)

    # ═══════════════════════════════════════════
    # SLIDE 8 — MCP: THE DISTRIBUTION PLAY
    # ═══════════════════════════════════════════
    slide = prs.slides.add_slide(blank_layout)
    set_slide_bg(slide)
    add_text_box(slide, Inches(0.8), Inches(0.4), Inches(11), Inches(0.8),
                 "MCP: The Distribution Play", font_size=40, bold=True, color=ACCENT)

    add_text_box(slide, Inches(0.8), Inches(1.3), Inches(11), Inches(0.7),
                 "Rekomme as an MCP Server = every AI assistant becomes a distribution channel.",
                 font_size=18, color=WHITE)

    add_card(slide, Inches(0.8), Inches(2.2), Inches(11.5), Inches(1.2), DARK_CARD)
    add_text_box(slide, Inches(1.2), Inches(2.4), Inches(10.5), Inches(0.8),
                 'User  \u2192  Claude / GPT / Cursor  \u2192  Calls Rekomme MCP Tool  \u2192  Products + Reviews + Prices',
                 font_size=17, color=YELLOW, bold=True, alignment=PP_ALIGN.CENTER)

    mcp_users = [
        ("AI Assistants", "Claude, GPT, Copilot\nadd shopping as\na native tool"),
        ("E-commerce Sites", "Embed community-backed\nreviews directly on\nproduct pages"),
        ("Browser Extensions", "Show Reddit community\nopinion while browsing\nany store"),
    ]
    for i, (title, desc) in enumerate(mcp_users):
        x = Inches(0.5 + i * 4.1)
        add_card(slide, x, Inches(3.8), Inches(3.8), Inches(2.2), DARK_CARD)
        add_text_box(slide, x + Inches(0.3), Inches(4), Inches(3.3), Inches(0.4),
                     title, font_size=16, bold=True, color=GREEN)
        add_text_box(slide, x + Inches(0.3), Inches(4.5), Inches(3.3), Inches(1.2),
                     desc, font_size=14, color=LIGHT_GRAY)

    add_text_box(slide, Inches(0.8), Inches(6.3), Inches(11), Inches(0.6),
                 "Zero integration effort for end users — AI agents auto-discover and use the tool.",
                 font_size=15, color=LIGHT_GRAY, alignment=PP_ALIGN.CENTER)

    # ═══════════════════════════════════════════
    # SLIDE 9 — CLOSING
    # ═══════════════════════════════════════════
    slide = prs.slides.add_slide(blank_layout)
    set_slide_bg(slide)
    add_text_box(slide, Inches(1), Inches(1.5), Inches(11), Inches(1.5),
                 "Rekomme", font_size=60, bold=True, color=ACCENT, alignment=PP_ALIGN.CENTER)
    add_text_box(slide, Inches(1), Inches(3.2), Inches(11), Inches(1),
                 "The shopping assistant that reads the internet\nso you don't have to.",
                 font_size=26, color=WHITE, alignment=PP_ALIGN.CENTER)
    add_text_box(slide, Inches(1), Inches(4.8), Inches(11), Inches(1),
                 "github.com/mubinmodi/AI-shopping-assistant",
                 font_size=18, color=LIGHT_GRAY, alignment=PP_ALIGN.CENTER)
    add_text_box(slide, Inches(1), Inches(5.5), Inches(11), Inches(0.5),
                 "Built with LangGraph + GPT-4o-mini + Pinecone + Tavily",
                 font_size=14, color=LIGHT_GRAY, alignment=PP_ALIGN.CENTER)

    # Save
    output_path = "/Users/mubinmodi/FinalProject-AI-Shoping-Assistant/Rekomme_Pitch_Deck.pptx"
    prs.save(output_path)
    print(f"Pitch deck saved to: {output_path}")
    return output_path


if __name__ == "__main__":
    create_deck()
