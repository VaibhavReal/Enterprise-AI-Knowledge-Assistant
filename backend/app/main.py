from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.api import auth, documents, chat, users
from app.db.database import create_tables
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup/shutdown lifecycle.
    Initialize database schema and tables immediately so server accepts requests in 0.1s.
    """
    logger.info("Starting Financial Research Assistant...")
    
    try:
        create_tables()
        logger.info("Database tables initialized successfully.")
    except Exception as e:
        logger.error(f"Error creating database tables on startup: {e}")
    
    logger.info("Financial Research Assistant ready and accepting requests!")
    
    yield
    
    logger.info("Shutting down Financial Research Assistant...")

app = FastAPI(
    title="Financial Research & Decision Support Assistant",
    description="RAG-powered financial document research system",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS: allow frontend to call backend from any local development origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(users.router)

@app.get("/health")
def health_check():
    """Simple health check endpoint for monitoring."""
    return {"status": "healthy", "service": "financial-research-assistant"}
