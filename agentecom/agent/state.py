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

class AgentResponse(BaseModel):
    reply: str
    session_id: str
    tool_calls_made: List[Dict[str, Any]] = Field(default_factory=list)
    products: List[Dict[str, Any]] = Field(default_factory=list)
    cart: List[Dict[str, Any]] = Field(default_factory=list)
    checkout_session: Optional[Dict[str, Any]] = None
    order: Optional[Dict[str, Any]] = None
    readability: ReadabilityMetric = Field(default_factory=ReadabilityMetric)

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    session_id: str
    cart: List[Dict[str, Any]]
    checkout_session: Optional[Dict[str, Any]]
    order: Optional[Dict[str, Any]]
    tool_calls_made: List[Dict[str, Any]]
    retrieved_products: List[Dict[str, Any]]
    readability: Optional[Dict[str, Any]]
    provider: str  # "ollama", "groq", "local"
    model_name: Optional[str]
    groq_api_key: Optional[str]
    ollama_base_url: Optional[str]
    start_time: float
