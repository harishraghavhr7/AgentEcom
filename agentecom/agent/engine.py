"""
Autonomous AI Shopping Agent Engine for AgentEcom.
Orchestrated via LangGraph with Ollama and Groq support.
"""

import os
import time
import json
import uuid
from typing import Dict, Any, List, Optional
from langchain_core.messages import HumanMessage, AIMessage

from agentecom.agent.state import AgentState, ReadabilityMetric
from agentecom.agent.graph import commerce_langgraph_app
from agentecom.config import settings, reload_settings

class AgentMessage(Dict[str, Any]):
    pass

class AgentResponse(Dict[str, Any]):
    pass

class AutonomousCommerceAgent:
    def __init__(self):
        self._sessions: Dict[str, Dict[str, Any]] = {}

    def get_or_create_session(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        if not session_id or session_id not in self._sessions:
            s_id = session_id or f"agent_sess_{uuid.uuid4().hex[:12]}"
            self._sessions[s_id] = {
                "session_id": s_id,
                "messages": [],
                "cart": [],
                "checkout_session": None,
                "order": None,
                "tool_calls_made": [],
                "retrieved_products": [],
                "short_term_memory": {
                    "active_product": None,
                    "recent_products": [],
                    "active_order": None,
                    "recent_orders": [],
                    "recent_skus": [],
                    "recent_queries": [],
                    "last_category": None,
                    "user_preferences": {}
                },
                "created_at": time.time(),
                "updated_at": time.time()
            }
        return self._sessions[session_id or s_id]

    def reset_session(self, session_id: str) -> bool:
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    async def process_user_turn(
        self,
        user_input: str,
        session_id: Optional[str] = None,
        llm_provider: Optional[str] = None,
        llm_api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        ollama_base_url: Optional[str] = None,
        user_id: Optional[str] = None,
        voice_mode: bool = False,
        gemini_api_key: Optional[str] = None,
        openrouter_api_key: Optional[str] = None,
        groq_api_key: Optional[str] = None,
        fallback_cascade: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Processes a multi-turn user conversation step through the upgraded LangGraph workflow.
        """
        start_time = time.perf_counter()
        session = self.get_or_create_session(session_id)

        active_provider = (llm_provider or getattr(settings, "DEFAULT_LLM_PROVIDER", "groq") or "groq").lower().strip()
        if active_provider in ["gemini", "google", "google_gemini"]:
            default_model = getattr(settings, "GEMINI_MODEL_NAME", "gemini-1.5-flash")
        elif active_provider in ["openrouter", "open_router"]:
            default_model = getattr(settings, "OPENROUTER_MODEL_NAME", "meta-llama/llama-3.3-70b-instruct")
        elif active_provider in ["ollama", "local_ollama"]:
            default_model = getattr(settings, "OLLAMA_MODEL_NAME", "llama3.2")
        else:
            default_model = getattr(settings, "GROQ_MODEL_NAME", "llama-3.3-70b-versatile")

        active_model = model_name or default_model
        active_ollama_url = ollama_base_url or getattr(settings, "OLLAMA_BASE_URL", "http://localhost:11434")
        active_groq_key = groq_api_key or (llm_api_key if active_provider in ["groq", "cloud"] else None) or getattr(settings, "GROQ_API_KEY", None) or os.getenv("GROQ_API_KEY")
        active_gemini_key = gemini_api_key or (llm_api_key if active_provider in ["gemini", "google"] else None) or getattr(settings, "GEMINI_API_KEY", None) or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        active_openrouter_key = openrouter_api_key or (llm_api_key if active_provider in ["openrouter", "open_router"] else None) or getattr(settings, "OPENROUTER_API_KEY", None) or os.getenv("OPENROUTER_API_KEY")
        active_cascade = fallback_cascade or getattr(settings, "FALLBACK_CASCADE_ORDER", "groq,gemini,openrouter")

        # Reconstruct LangChain BaseMessage history
        history_messages: List[BaseMessage] = []
        for msg in session["messages"]:
            role = msg.get("role")
            content = msg.get("content", "")
            if role == "user":
                history_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                history_messages.append(AIMessage(content=content))
        history_messages.append(HumanMessage(content=user_input))

        u_id = user_id or session.get("user_id") or "default_shopper"
        session["user_id"] = u_id

        # Build initial LangGraph state with persistent short-term memory
        initial_state: AgentState = {
            "messages": history_messages,
            "session_id": session["session_id"],
            "user_id": u_id,
            "user_persona": session.get("user_persona", {}),
            "cart": session.get("cart", []),
            "checkout_session": session.get("checkout_session"),
            "order": session.get("order"),
            "active_return_request": session.get("active_return_request"),
            "tracking_info": session.get("tracking_info"),
            "tool_calls_made": [],
            "retrieved_products": session.get("retrieved_products", []),
            "short_term_memory": session.get("short_term_memory", {
                "active_product": None,
                "recent_skus": [],
                "recent_queries": [],
                "last_category": None,
                "user_preferences": {}
            }),
            "security_flag": None,
            "security_reason": None,
            "requires_human_approval": False,
            "voice_mode": voice_mode,
            "readability": None,
            "provider": active_provider,
            "model_name": active_model,
            "groq_api_key": active_groq_key,
            "gemini_api_key": active_gemini_key,
            "openrouter_api_key": active_openrouter_key,
            "ollama_base_url": active_ollama_url,
            "fallback_cascade": active_cascade,
            "provider_used": None,
            "fallback_active": False,
            "fallback_reason": None,
            "start_time": start_time
        }

        # Configure LangSmith & LangGraph execution run metadata
        run_config = {
            "run_name": f"commerce_turn_{session['session_id'][:8]}",
            "tags": ["AgentEcom", active_provider, active_model or "default"],
            "metadata": {
                "session_id": session["session_id"],
                "user_id": u_id,
                "llm_provider": active_provider,
                "model_name": active_model,
                "cart_items_count": len(session.get("cart", [])),
                "has_active_order": bool(session.get("order")),
                "has_active_product": bool((session.get("short_term_memory") or {}).get("active_product"))
            }
        }

        # Run through LangGraph Workflow
        result_state = await commerce_langgraph_app.ainvoke(initial_state, config=run_config)

        # Extract final reply
        final_msg = result_state["messages"][-1].content if result_state.get("messages") else "No response generated."
        
        # Update session persistent state and short-term memory
        session["cart"] = result_state.get("cart", [])
        session["checkout_session"] = result_state.get("checkout_session")
        session["order"] = result_state.get("order")
        session["active_return_request"] = result_state.get("active_return_request")
        session["tracking_info"] = result_state.get("tracking_info")
        session["user_persona"] = result_state.get("user_persona", session.get("user_persona", {}))
        session["retrieved_products"] = result_state.get("retrieved_products", session.get("retrieved_products", []))
        session["short_term_memory"] = result_state.get("short_term_memory", session.get("short_term_memory", {}))
        session["messages"].append({"role": "user", "content": user_input})
        session["messages"].append({"role": "assistant", "content": final_msg})

        return {
            "reply": final_msg,
            "session_id": session["session_id"],
            "user_id": u_id,
            "user_persona": session["user_persona"],
            "tool_calls_made": result_state.get("tool_calls_made", []),
            "products": result_state.get("retrieved_products", []),
            "cart": session["cart"],
            "checkout_session": session["checkout_session"],
            "order": session["order"],
            "active_return_request": session["active_return_request"],
            "tracking_info": session["tracking_info"],
            "short_term_memory": session["short_term_memory"],
            "fallback_active": bool(result_state.get("fallback_active", False)),
            "fallback_reason": result_state.get("fallback_reason"),
            "provider_used": result_state.get("provider_used") or (result_state.get("readability") or {}).get("llm_provider"),
            "security_flag": result_state.get("security_flag"),
            "requires_human_approval": bool(result_state.get("requires_human_approval", False)),
            "voice_mode": voice_mode,
            "readability": result_state.get("readability", {})
        }

agent_engine = AutonomousCommerceAgent()
