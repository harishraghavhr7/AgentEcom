import os
from typing import Optional
from dotenv import load_dotenv
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Ensure .env is explicitly loaded into os.environ
load_dotenv(override=True)

def _sanitize_env_val(val: Optional[str]) -> Optional[str]:
    if not val:
        return None
    cleaned = str(val).strip().strip("'\"")
    if not cleaned or cleaned.lower() in [
        "none", "null", "undefined", "your_api_key_here",
        "gsk_...", "aizasy...", "sk-or-v1-..."
    ]:
        return None
    return cleaned

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

    # LLM Providers Configuration (Groq, Gemini, OpenRouter, Local Ollama & Fallback Cascade)
    GROQ_API_KEY: Optional[str] = _sanitize_env_val(os.getenv("GROQ_API_KEY"))
    GROQ_MODEL_NAME: str = os.getenv("GROQ_MODEL_NAME", "llama-3.3-70b-versatile")

    GEMINI_API_KEY: Optional[str] = _sanitize_env_val(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
    GEMINI_MODEL_NAME: str = os.getenv("GEMINI_MODEL_NAME", "gemini-1.5-flash")

    OPENROUTER_API_KEY: Optional[str] = _sanitize_env_val(os.getenv("OPENROUTER_API_KEY"))
    OPENROUTER_MODEL_NAME: str = os.getenv("OPENROUTER_MODEL_NAME", "meta-llama/llama-3.3-70b-instruct")
    OPENROUTER_BASE_URL: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL_NAME: str = os.getenv("OLLAMA_MODEL_NAME", "llama3.2")
    DEFAULT_LLM_PROVIDER: str = os.getenv("DEFAULT_LLM_PROVIDER", "groq")
    FALLBACK_CASCADE_ORDER: str = os.getenv("FALLBACK_CASCADE_ORDER", "groq,gemini,openrouter")

    # LangSmith Observability & Tracing
    LANGSMITH_TRACING: bool = os.getenv("LANGSMITH_TRACING", "false").lower() in ["true", "1", "yes"]
    LANGSMITH_API_KEY: Optional[str] = os.getenv("LANGSMITH_API_KEY")
    LANGSMITH_PROJECT: str = os.getenv("LANGSMITH_PROJECT", "AgentEcom")
    LANGSMITH_ENDPOINT: str = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")

    @field_validator("GROQ_API_KEY", "GEMINI_API_KEY", "OPENROUTER_API_KEY", "LANGSMITH_API_KEY", mode="before")
    @classmethod
    def sanitize_keys(cls, v: Optional[str]) -> Optional[str]:
        return _sanitize_env_val(v)

    model_config = SettingsConfigDict(case_sensitive=True, env_file=".env", extra="allow")

def reload_settings() -> Settings:
    """Reloads .env and returns refreshed Settings."""
    global settings
    load_dotenv(override=True)
    settings = Settings()
    if settings.GROQ_API_KEY:
        os.environ["GROQ_API_KEY"] = settings.GROQ_API_KEY
    if settings.GEMINI_API_KEY:
        os.environ["GEMINI_API_KEY"] = settings.GEMINI_API_KEY
    if settings.OPENROUTER_API_KEY:
        os.environ["OPENROUTER_API_KEY"] = settings.OPENROUTER_API_KEY
    return settings

settings = Settings()

# Ensure LLM provider keys and fallback config are available in os.environ
if settings.GROQ_API_KEY:
    os.environ["GROQ_API_KEY"] = settings.GROQ_API_KEY
if settings.GEMINI_API_KEY:
    os.environ["GEMINI_API_KEY"] = settings.GEMINI_API_KEY
if settings.OPENROUTER_API_KEY:
    os.environ["OPENROUTER_API_KEY"] = settings.OPENROUTER_API_KEY
if settings.FALLBACK_CASCADE_ORDER:
    os.environ["FALLBACK_CASCADE_ORDER"] = settings.FALLBACK_CASCADE_ORDER

# Ensure LangSmith environment variables are set for LangChain/LangGraph automatic tracing
if settings.LANGSMITH_TRACING and settings.LANGSMITH_API_KEY:
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGSMITH_API_KEY"] = settings.LANGSMITH_API_KEY
    os.environ["LANGCHAIN_API_KEY"] = settings.LANGSMITH_API_KEY
    os.environ["LANGSMITH_PROJECT"] = settings.LANGSMITH_PROJECT
    os.environ["LANGCHAIN_PROJECT"] = settings.LANGSMITH_PROJECT
    os.environ["LANGSMITH_ENDPOINT"] = settings.LANGSMITH_ENDPOINT
else:
    os.environ["LANGSMITH_TRACING"] = "false"
    os.environ["LANGCHAIN_TRACING_V2"] = "false"
    for k in ["LANGSMITH_API_KEY", "LANGCHAIN_API_KEY"]:
        os.environ.pop(k, None)
