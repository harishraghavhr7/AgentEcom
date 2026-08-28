import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "AgentEcom"
    API_V1_STR: str = "/api/v1"
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./agentecom.db")
    
    # Cache Settings
    CACHE_DEFAULT_TTL_SECONDS: int = 3600  # Long TTL because invalidation is webhook-driven!
    SEARCH_CACHE_TTL_SECONDS: int = 600
    
    # Checkout Session Settings
    CHECKOUT_SESSION_TTL_MINUTES: int = 15  # Short-lived isolated sessions
    
    # Search Engine
    EMBEDDING_MODEL_NAME: str = "sentence-transformers/all-MiniLM-L6-v2"
    HYBRID_RRF_K: int = 60  # Standard Reciprocal Rank Fusion constant
    BM25_WEIGHT: float = 0.5
    DENSE_WEIGHT: float = 0.5
    
    # Sync & Workers
    ASYNC_INDEXING_WORKER: bool = True

    # LLM Providers Configuration (Groq Cloud API & Local Zero-Key Fallback)
    GROQ_API_KEY: Optional[str] = os.getenv("GROQ_API_KEY")
    GROQ_MODEL_NAME: str = os.getenv("GROQ_MODEL_NAME", "llama-3.3-70b-versatile")
    DEFAULT_LLM_PROVIDER: str = os.getenv("DEFAULT_LLM_PROVIDER", "groq")

    # LangSmith Observability & Tracing
    LANGSMITH_TRACING: bool = os.getenv("LANGSMITH_TRACING", "false").lower() in ["true", "1", "yes"]
    LANGSMITH_API_KEY: Optional[str] = os.getenv("LANGSMITH_API_KEY")
    LANGSMITH_PROJECT: str = os.getenv("LANGSMITH_PROJECT", "AgentEcom")
    LANGSMITH_ENDPOINT: str = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")

    model_config = SettingsConfigDict(case_sensitive=True, env_file=".env", extra="allow")

settings = Settings()

# Ensure GROQ_API_KEY is available in os.environ for LangChain/Groq
if settings.GROQ_API_KEY:
    os.environ["GROQ_API_KEY"] = settings.GROQ_API_KEY

# Ensure LangSmith environment variables are set for LangChain/LangGraph automatic tracing
if settings.LANGSMITH_TRACING and settings.LANGSMITH_API_KEY:
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGSMITH_API_KEY"] = settings.LANGSMITH_API_KEY
    os.environ["LANGCHAIN_API_KEY"] = settings.LANGSMITH_API_KEY
    os.environ["LANGSMITH_PROJECT"] = settings.LANGSMITH_PROJECT
    os.environ["LANGCHAIN_PROJECT"] = settings.LANGSMITH_PROJECT
    os.environ["LANGSMITH_ENDPOINT"] = settings.LANGSMITH_ENDPOINT
