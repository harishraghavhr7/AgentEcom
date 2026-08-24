import os
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

    model_config = SettingsConfigDict(case_sensitive=True, env_file=".env")

settings = Settings()
