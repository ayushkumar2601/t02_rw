"""Main FastAPI application entrypoint for Ava Inbound Voice Agent."""

from contextlib import asynccontextmanager
import logging
from typing import Any, Dict
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import leads, sessions
from app.config import settings
from app.repositories.database import db_manager
from app.services.llm_client import llm_client

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("voice_agent.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan managing startup database initialization."""
    logger.info("Initializing database schema at: %s", settings.DATABASE_PATH)
    await db_manager.init_db()
    llm_status = "Groq API configured" if llm_client.is_configured else "Deterministic NLP fallback active"
    logger.info("Ava Voice Agent Backend ready. LLM Status: %s", llm_status)
    yield
    logger.info("Shutting down Ava Voice Agent Backend.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Autonomous Inbound Voice Agent for Digital Marketing Agency Lead Qualification (Ava SDR).",
    lifespan=lifespan,
)

# CORS configuration for Phase 2 frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(sessions.router)
app.include_router(leads.router)


@app.get("/", include_in_schema=False)
async def root():
    """Redirect root to Swagger API documentation."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/docs")


@app.get("/health", tags=["system"])
async def health_check() -> Dict[str, Any]:
    """Service health status endpoint. Never exposes sensitive environment variables."""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "llm_mode": "groq_api" if llm_client.is_configured else "deterministic_fallback",
    }
