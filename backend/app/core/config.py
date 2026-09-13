"""
Application configuration using Pydantic Settings.

All configuration values can be set via environment variables or a .env file.
This centralizes all configuration in one place so values are never scattered
across the codebase.
"""

from __future__ import annotations

from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables or .env file.
    Provides sensible defaults to make initial setup easier.
    """

    # --- Database ---
    DATABASE_URL: str = "postgresql+psycopg2://postgres:password@localhost:5432/financial_research"

    # --- Security ---
    # Generate a real secret with: python -c "import secrets; print(secrets.token_hex(32))"
    SECRET_KEY: str = "changethissecretkeyinproduction"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # --- LLM Provider Selection ---
    # Default is Gemini (Google AI Studio)
    LLM_PROVIDER: str = "gemini"  # gemini | openai | claude | ollama

    # --- 1. Google Gemini / Google AI Studio (First & Primary Option) ---
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-flash-lite-latest"  # gemini-flash-lite-latest | gemini-flash-latest | gemini-pro-latest


    # --- 2. OpenAI (Secondary Option) ---
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"

    # --- 3. Anthropic Claude (Third Option) ---
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-20240620"

    # --- 4. Ollama (Local LLM, optional) ---
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3"

    # --- Embeddings ---
    # BGE-small-en-v1.5 is ~130MB, downloads on first startup
    EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"

    # --- RAG Pipeline ---
    CHUNK_SIZE: int = 800           # Characters per chunk
    CHUNK_OVERLAP: int = 150        # Overlap between consecutive chunks
    MAX_CHUNKS_RETRIEVED: int = 20  # Candidates before reranking
    TOP_K_AFTER_RERANK: int = 5     # Final chunks sent to LLM
    DENSE_WEIGHT: float = 0.7       # Weight for semantic (dense) retrieval score
    BM25_WEIGHT: float = 0.3        # Weight for keyword (BM25) retrieval score

    # --- Chat Memory ---
    # We cap history at 10 messages to limit LLM context size and cost.
    MAX_HISTORY_MESSAGES: int = 10

    # --- File Upload ---
    MAX_UPLOAD_SIZE_MB: int = 50
    ALLOWED_EXTENSIONS: List[str] = [".pdf", ".docx", ".txt"]
    UPLOAD_DIR: str = "uploads"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    """
    Returns a cached Settings instance.
    """
    return Settings()
