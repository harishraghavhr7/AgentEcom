"""
Autonomous AI Shopping Agent Engine for AgentEcom.
Orchestrated via LangGraph with Ollama and Groq support.
"""

import time
import json
import uuid
from typing import Dict, Any, List, Optional
from langchain_core.messages import HumanMessage, AIMessage

from agentecom.agent.state import AgentState, ReadabilityMetric
from agentecom.agent.graph import commerce_langgraph_app

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
        llm_api_key: Optional[str] = None,
        llm_provider: str = "groq",
        model_name: Optional[str] = None,
        ollama_base_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a user conversation turn through the LangGraph StateGraph workflow
        with full short-term conversational working memory and multi-turn context.
        """
        start_time = time.perf_counter()
        session = self.get_or_create_session(session_id)
        session["updated_at"] = time.time()

        # Reconstruct recent conversation messages (sliding window of last 10 messages for short-term memory)
        history_messages = []
        for m in session.get("messages", [])[-10:]:
            role = m.get("role")
            content = m.get("content", "")
            if role == "user":
                history_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                history_messages.append(AIMessage(content=content))
        history_messages.append(HumanMessage(content=user_input))

        # Build initial LangGraph state with persistent short-term memory
        initial_state: AgentState = {
            "messages": history_messages,
            "session_id": session["session_id"],
            "cart": session.get("cart", []),
            "checkout_session": session.get("checkout_session"),
            "order": session.get("order"),
            "tool_calls_made": [],
            "retrieved_products": session.get("retrieved_products", []),
            "short_term_memory": session.get("short_term_memory", {
                "active_product": None,
                "recent_skus": [],
                "recent_queries": [],
                "last_category": None,
                "user_preferences": {}
            }),
            "readability": None,
            "provider": llm_provider or "groq",
            "model_name": model_name,
            "groq_api_key": llm_api_key,
            "ollama_base_url": ollama_base_url,
            "start_time": start_time
        }

        # Configure LangSmith & LangGraph execution run metadata
        run_config = {
            "run_name": f"commerce_turn_{session['session_id'][:8]}",
            "tags": ["AgentEcom", llm_provider, model_name or "default"],
            "metadata": {
                "session_id": session["session_id"],
                "llm_provider": llm_provider,
                "model_name": model_name,
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
        session["retrieved_products"] = result_state.get("retrieved_products", session.get("retrieved_products", []))
        session["short_term_memory"] = result_state.get("short_term_memory", session.get("short_term_memory", {}))
        session["messages"].append({"role": "user", "content": user_input})
        session["messages"].append({"role": "assistant", "content": final_msg})

        return {
            "reply": final_msg,
            "session_id": session["session_id"],
            "tool_calls_made": result_state.get("tool_calls_made", []),
            "products": result_state.get("retrieved_products", []),
            "cart": session["cart"],
            "checkout_session": session["checkout_session"],
            "order": session["order"],
            "short_term_memory": session["short_term_memory"],
            "readability": result_state.get("readability", {})
        }

agent_engine = AutonomousCommerceAgent()
