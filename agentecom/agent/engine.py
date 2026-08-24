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
        llm_provider: str = "local",
        model_name: Optional[str] = None,
        ollama_base_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a user conversation turn through the LangGraph StateGraph workflow.
        """
        start_time = time.perf_counter()
        session = self.get_or_create_session(session_id)
        session["updated_at"] = time.time()

        # Build initial LangGraph state
        initial_state: AgentState = {
            "messages": [HumanMessage(content=user_input)],
            "session_id": session["session_id"],
            "cart": session["cart"],
            "checkout_session": session["checkout_session"],
            "order": session["order"],
            "tool_calls_made": [],
            "retrieved_products": [],
            "readability": None,
            "provider": llm_provider or "local",
            "model_name": model_name,
            "groq_api_key": llm_api_key,
            "ollama_base_url": ollama_base_url,
            "start_time": start_time
        }

        # Run through LangGraph Workflow
        result_state = await commerce_langgraph_app.ainvoke(initial_state)

        # Extract final reply
        final_msg = result_state["messages"][-1].content if result_state.get("messages") else "No response generated."
        
        # Update session persistent state
        session["cart"] = result_state.get("cart", [])
        session["checkout_session"] = result_state.get("checkout_session")
        session["order"] = result_state.get("order")
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
            "readability": result_state.get("readability", {})
        }

agent_engine = AutonomousCommerceAgent()
