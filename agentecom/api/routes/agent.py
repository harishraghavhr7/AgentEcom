from fastapi import APIRouter, HTTPException
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from agentecom.agent.engine import agent_engine
from agentecom.agent.state import AgentResponse

router = APIRouter(prefix="/agent", tags=["AI Shopping Agent"])

class AgentChatRequest(BaseModel):
    message: str = Field(..., description="User prompt or agent command")
    session_id: Optional[str] = Field(None, description="Optional conversation session ID")
    llm_provider: Optional[str] = Field("ollama", description="'ollama', 'local', or 'groq'")
    llm_api_key: Optional[str] = Field(None, description="Optional Groq API Key")
    model_name: Optional[str] = Field(None, description="Optional model name (e.g. 'llama-3.3-70b-versatile', 'llama3.2')")
    ollama_base_url: Optional[str] = Field(None, description="Optional custom Ollama base URL")

class ResetSessionResponse(BaseModel):
    session_id: str
    status: str

@router.post("/chat", response_model=AgentResponse)
async def chat_with_agent(req: AgentChatRequest):
    """
    Multi-turn Conversational AI Shopping Agent endpoint powered by LangGraph.
    Performs autonomous tool selection, execution, and returns structured
    recommendations along with an AI Readability & Token Economy report.
    """
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    res_dict = await agent_engine.process_user_turn(
        user_input=req.message,
        session_id=req.session_id,
        llm_api_key=req.llm_api_key,
        llm_provider=req.llm_provider or "ollama",
        model_name=req.model_name,
        ollama_base_url=req.ollama_base_url
    )
    return AgentResponse(**res_dict)

@router.get("/sessions/{session_id}")
async def get_agent_session(session_id: str):
    """Inspect current session state, cart items, and conversation history."""
    if session_id not in agent_engine._sessions:
        raise HTTPException(status_code=404, detail="Session not found.")
    return agent_engine._sessions[session_id]

@router.delete("/sessions/{session_id}", response_model=ResetSessionResponse)
async def reset_agent_session(session_id: str):
    """Reset a conversation session and empty the cart."""
    success = agent_engine.reset_session(session_id)
    return ResetSessionResponse(session_id=session_id, status="reset" if success else "not_found")
