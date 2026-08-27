"""
LangGraph State & Response Schema Definitions for AgentEcom AI Agent.
"""

from typing import List, Dict, Any, Optional, Sequence, Annotated
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

class ReadabilityMetric(BaseModel):
    estimated_raw_tokens: int = 0
    compressed_tool_tokens: int = 0
    token_reduction_pct: float = 0.0
    retrieval_relevance_score: float = 1.0
    execution_latency_ms: float = 0.0
    cache_hits: int = 0
    tools_executed: List[str] = Field(default_factory=list)
    graph_steps: int = 0

class ShortTermMemory(BaseModel):
    active_product: Optional[Dict[str, Any]] = None  # Last focused/retrieved product with full attributes & specs
    recent_products: List[Dict[str, Any]] = Field(default_factory=list)  # Recently retrieved product entities
    active_order: Optional[Dict[str, Any]] = None  # Last viewed/placed order entity with all dates, items, and attributes
    recent_orders: List[Dict[str, Any]] = Field(default_factory=list)  # Recent order entities
    recent_skus: List[str] = Field(default_factory=list)  # Recent SKU codes referenced in conversation
    recent_queries: List[str] = Field(default_factory=list)  # Recent search query intents
    last_category: Optional[str] = None  # Last filtered category
    user_preferences: Dict[str, Any] = Field(default_factory=dict)  # Budget, preferred brands, attributes

class AgentResponse(BaseModel):
    reply: str
    session_id: str
    tool_calls_made: List[Dict[str, Any]] = Field(default_factory=list)
    products: List[Dict[str, Any]] = Field(default_factory=list)
    cart: List[Dict[str, Any]] = Field(default_factory=list)
    checkout_session: Optional[Dict[str, Any]] = None
    order: Optional[Dict[str, Any]] = None
    short_term_memory: Optional[Dict[str, Any]] = None
    readability: ReadabilityMetric = Field(default_factory=ReadabilityMetric)

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    session_id: str
    cart: List[Dict[str, Any]]
    checkout_session: Optional[Dict[str, Any]]
    order: Optional[Dict[str, Any]]
    tool_calls_made: List[Dict[str, Any]]
    retrieved_products: List[Dict[str, Any]]
    short_term_memory: Optional[Dict[str, Any]]
    readability: Optional[Dict[str, Any]]
    provider: str  # "ollama", "groq", "local"
    model_name: Optional[str]
    groq_api_key: Optional[str]
    ollama_base_url: Optional[str]
    start_time: float

