# Rekomme - AI-Powered Shopping Assistant

An intelligent shopping recommendation system that leverages Reddit community discussions, live web search, news articles, YouTube reviews, and real-time pricing to help users find the best products.

## Features

### Intelligent Recommendation Engine
- **Community-backed recommendations** from real Reddit discussions (r/HeadphoneAdvice, r/headphones, r/audiophile)
- **Live Reddit search** via Tavily for fresh community opinions on every query
- **Hallucination detection** ensures recommendations are grounded in real user experiences
- **Answer quality evaluation** verifies responses actually address the user's question
- **Batch document grading** efficiently evaluates retrieval relevance in a single LLM call

### Multi-Source Enrichment
- **News & expert reviews** from tech publications (auto-fetched via Tavily)
- **YouTube review links** for each recommended product
- **Price history & buying advice** with trend detection and best-time-to-buy suggestions
- **Live product listings** with real merchant prices from OxyLabs/Google Shopping

### Smart Follow-Up System
- **Context-aware conversations** — follow-up questions use product context instead of triggering new searches
- **Product selection** — checkboxes to select products for comparison or deep dives
- **Side-by-side comparison tables** — full specs, pros/cons, community ratings, and verdict
- **Detailed product analysis** — deep community review with long-term usage insights
- **Auto-detection** of follow-up vs. new query based on intent analysis

### User Experience
- **Onboarding** with example queries for new users
- **Claude-style chat sidebar** with recent chat history
- **Unified product view** — listings, community review, news, YouTube, and pricing all in one card
- **Session persistence** — chat history and product data stored in PostgreSQL

## Architecture

```
User Query
    |
    v
[Vector Search (Pinecone MMR k=10)]
    |
    v
[Batch Grade Documents (1 LLM call)]
    |
    +--> Relevant: [Live Reddit Search (Tavily)]
    |
    +--> Irrelevant: [Rewrite Query] --> [Web Search] --> [Live Reddit Search]
    |
    v
[Generate Recommendations (GPT-4o-mini)]
    |
    v
[Hallucination + Quality Check]
    |
    +--> Grounded: [Enrich with Sources]
    |
    +--> Not Grounded: [Retry Generation]
    |
    v
[Enrich: News + YouTube + Price History (parallel Tavily)]
    |
    v
[Response with Product Cards]
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Streamlit |
| **Backend API** | FastAPI + Uvicorn |
| **AI/LLM** | OpenAI GPT-4o-mini, LangChain, LangGraph |
| **Vector Store** | Pinecone (text-embedding-3-small) |
| **Database** | PostgreSQL (Supabase) |
| **Object Storage** | AWS S3 |
| **Web Search** | Tavily (advanced + basic) |
| **Product Listings** | OxyLabs (Google Shopping) |
| **Data Pipeline** | Apache Airflow |
| **Auth** | JWT (python-jose + bcrypt) |
| **Containerization** | Docker + Docker Compose |

## Prerequisites

- Python 3.12.x (recommended: 3.12.9 via pyenv)
- Docker Desktop
- Poetry

## Setup

### 1. Clone and install

```bash
git clone https://github.com/mubinmodi/AI-shopping-assistant.git
cd AI-shopping-assistant

# Install Python 3.12.9
pyenv install 3.12.9
pyenv local 3.12.9

# Install dependencies
poetry install --with backend,frontend
```

### 2. Environment variables

```bash
cp .env.template .env
```

Fill in the following in `.env`:

| Variable | Source |
|----------|--------|
| `OPENAI_API_KEY` | platform.openai.com |
| `PINECONE_API_KEY` | app.pinecone.io |
| `PINECONE_INDEX_NAME` | Your Pinecone index name |
| `PINECONE_ENVIRONMENT` | Your Pinecone host URL |
| `TAVILY_API_KEY` | app.tavily.com |
| `POSTGRES_CONN_STRING` | Supabase pooler connection string |
| `POSTGRES_HOSTNAME` | Supabase pooler host |
| `POSTGRES_USER` | Supabase user |
| `POSTGRES_PASSWORD` | Supabase password |
| `POSTGRES_PORT` | `5432` |
| `POSTGRES_DB` | `postgres` |
| `AWS_ACCESS_KEY_ID` | AWS IAM |
| `AWS_SECRET_ACCESS_KEY` | AWS IAM |
| `AWS_S3_BUCKET` | Your S3 bucket name |
| `JWT_SECRET_KEY` | `openssl rand -hex 32` |
| `OXYLABS_USERNAME` | oxylabs.io |
| `OXYLABS_PASSWORD` | oxylabs.io |
| `REDDIT_CLIENT_ID` | reddit.com/prefs/apps |
| `REDDIT_CLIENT_SECRET` | reddit.com/prefs/apps |
| `REDDIT_USERNAME` | Your Reddit username |
| `REDDIT_PASSWORD` | Your Reddit password |

### 3. Database setup

Run this SQL in the Supabase SQL Editor:

```sql
CREATE SEQUENCE IF NOT EXISTS user_id_seq;
CREATE TABLE IF NOT EXISTS public.users (
    id INTEGER PRIMARY KEY DEFAULT nextval('user_id_seq'),
    username VARCHAR NOT NULL UNIQUE,
    password VARCHAR NOT NULL,
    email VARCHAR NOT NULL,
    full_name VARCHAR,
    active BOOLEAN DEFAULT TRUE,
    password_timestamp INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE SEQUENCE IF NOT EXISTS chat_session_id_seq;
CREATE TABLE IF NOT EXISTS public.chat_session (
    id INTEGER PRIMARY KEY DEFAULT nextval('chat_session_id_seq'),
    user_id INTEGER NOT NULL,
    title VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_message_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE SEQUENCE IF NOT EXISTS messages_id_seq;
CREATE TABLE IF NOT EXISTS public.messages (
    id INTEGER PRIMARY KEY DEFAULT nextval('messages_id_seq'),
    chat_session_id INTEGER NOT NULL,
    sender VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ref TEXT,
    tools_used TEXT
);

CREATE TABLE IF NOT EXISTS public.reddit_posts (
    post_id TEXT PRIMARY KEY,
    source_url TEXT,
    processed_s3_url TEXT,
    created_date DATE,
    subreddit TEXT
);
```

### 4. Run the application

**Option A: Docker (recommended)**

```bash
# Start the app (FastAPI + Streamlit)
docker compose -f docker-compose-app.yml up --build -d

# Optional: Start Airflow for batch data pipeline
docker compose up --build -d
```

**Option B: Local**

```bash
# Backend
poetry run uvicorn backend.main:app --host 0.0.0.0 --port 8000

# Frontend (separate terminal)
poetry run streamlit run app.py
```

### 5. Access

| Service | URL |
|---------|-----|
| Frontend | http://localhost:8501 |
| Backend API docs | http://localhost:8000/docs |
| Airflow UI | http://localhost:8080 (user: airflow, pass: airflow) |

## Agent Pipeline

### LangGraph Nodes

| Node | Purpose |
|------|---------|
| `vector_search` | MMR search on Pinecone (k=10, fetch_k=20) |
| `batch_grade` | Single LLM call to grade all retrieved docs |
| `transform_query` | Rewrites vague queries for better search |
| `web_search` | Tavily advanced search fallback |
| `live_reddit_search` | Real-time Reddit content via Tavily |
| `generate` | GPT-4o-mini product recommendations |
| `enrich_with_sources` | Parallel fetch: news + YouTube + price history |

### Graders (all actively used)

| Grader | Purpose |
|--------|---------|
| Batch Retrieval Grader | Grades all docs in 1 call (replaces N individual calls) |
| Hallucination Grader | Ensures generation is grounded in source docs |
| Answer Quality Evaluator | Verifies response answers the user's question |
| Question Rewriter | Improves vague queries when docs are irrelevant |

## Airflow Pipeline

The batch pipeline scrapes Reddit and populates the Pinecone vector store:

```
Reddit Scrape (PRAW / OxyLabs fallback)
    --> Quality Filter (score, content length, bot removal)
    --> Semantic Chunking (800 char, high-score comments as individual chunks)
    --> Batched Embedding (50 chunks per API call)
    --> Store: Pinecone + S3 + PostgreSQL
```

## Project Structure

```
.
├── app.py                          # Streamlit entry point
├── backend/
│   ├── agent/
│   │   ├── __init__.py             # LangGraph compilation
│   │   ├── nodes.py                # All graph nodes
│   │   ├── edges.py                # Decision edges
│   │   ├── generate_chain.py       # LLM recommendation prompt
│   │   ├── grader.py               # All grading prompts
│   │   ├── vector_store.py         # Pinecone MMR retriever
│   │   └── graph.py                # State definition
│   ├── database/                   # SQLAlchemy models
│   ├── schemas/                    # Pydantic models
│   ├── services/                   # Business logic
│   ├── views/                      # FastAPI routes
│   ├── config.py                   # Settings
│   └── main.py                     # FastAPI app
├── frontend/
│   ├── pages/
│   │   ├── chat.py                 # Main chat interface
│   │   ├── login.py                # Login page
│   │   └── register.py             # Registration page
│   └── utils/                      # API + auth helpers
├── dags/                           # Airflow DAGs
│   ├── reddit_pipeline.py          # Main scraping DAG
│   ├── reddit_scrapper.py          # Reddit scraper (PRAW + OxyLabs)
│   └── reddit_data_processor.py    # Chunking + embedding
├── docker-compose.yaml             # Airflow stack
├── docker-compose-app.yml          # App stack (FastAPI + Streamlit)
├── backend.Dockerfile
├── frontend.Dockerfile
├── airflow.Dockerfile
└── pyproject.toml                  # Dependencies (Poetry)
```
