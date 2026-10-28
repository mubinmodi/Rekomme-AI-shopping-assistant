import logging.config
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database import db_session
from backend.schemas import HealthSchema
from backend.views import central_router

# Load logging configuration from file
logging.config.fileConfig("backend/logging.conf", disable_existing_loggers=False)

logger = logging.getLogger(__name__)
logging.getLogger("passlib").setLevel(logging.ERROR)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("[FastAPI] Startup lifespan invoked")
    # await init_db()
    yield


app = FastAPI(title=settings.APP_TITLE, version=settings.APP_VERSION, lifespan=lifespan)

# Include routers
app.include_router(central_router)

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", response_model=HealthSchema, tags=["health"])
async def health_check(db: AsyncSession = Depends(db_session)):
    return {"api": True, "database": True}


# A production image can build React into /app/frontend_dist. During local
# development Vite serves the UI separately and proxies API requests here.
frontend_dist = Path(__file__).resolve().parent.parent / "frontend_dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
