import pytest
import uuid
from httpx import AsyncClient
from agentecom.agent.engine import agent_engine

@pytest.mark.asyncio
async def test_langgraph_agent_multi_turn_shopping_flow(test_db_session):
    session_id = f"test_lg_sess_{uuid.uuid4().hex[:8]}"

    # Turn 0: General catalog browse / "what are the products there"
    res0 = await agent_engine.process_user_turn("what are the products there", session_id=session_id)
    assert len(res0["tool_calls_made"]) >= 1
    assert res0["tool_calls_made"][0]["tool"] == "search_products"
    assert len(res0["products"]) > 0

    # Turn 1: Search for products via LangGraph
    res1 = await agent_engine.process_user_turn("Find a cozy knit sweater under $60", session_id=session_id)
    assert len(res1["tool_calls_made"]) >= 1
    assert res1["tool_calls_made"][0]["tool"] == "search_products"
    assert any(p["sku"] == "SKU-4471" for p in res1["products"])
    assert res1["readability"]["execution_latency_ms"] > 0
    assert res1["readability"]["token_reduction_pct"] >= 0

    # Turn 2: Ask for product details by SKU
    res2 = await agent_engine.process_user_turn("Details for SKU-4471", session_id=session_id)
    assert len(res2["tool_calls_made"]) >= 1
    assert res2["tool_calls_made"][0]["tool"] == "get_product_details"
    assert res2["products"][0]["sku"] == "SKU-4471"

    # Turn 3: Add to cart
    res3 = await agent_engine.process_user_turn("Add SKU-4471 to cart", session_id=session_id)
    assert len(res3["cart"]) == 1
    assert res3["cart"][0]["sku"] == "SKU-4471"
    assert res3["cart"][0]["quantity"] == 1

    # Turn 4: Create Checkout Session
    res4 = await agent_engine.process_user_turn("Proceed to checkout", session_id=session_id)
    assert res4["checkout_session"] is not None
    assert res4["checkout_session"]["session_id"].startswith("cs_")
    assert res4["checkout_session"]["status"] == "PENDING"
    assert res4["checkout_session"]["total_amount"] == 58.50

    # Turn 5: Confirm Purchase
    res5 = await agent_engine.process_user_turn("Confirm purchase", session_id=session_id)
    assert res5["order"] is not None
    assert res5["order"]["order_number"].startswith("ORD-")
    assert res5["order"]["status"] == "CONFIRMED"
    assert len(res5["cart"]) == 0  # Cart cleared on success

@pytest.mark.asyncio
async def test_agent_api_endpoints(async_client: AsyncClient, test_db_session):
    # Test POST /api/v1/agent/chat
    session_id = f"api_lg_sess_{uuid.uuid4().hex[:8]}"
    chat_payload = {
        "message": "what are the products there",
        "session_id": session_id,
        "llm_provider": "local"
    }
    res = await async_client.post("/api/v1/agent/chat", json=chat_payload)
    assert res.status_code == 200
    data = res.json()
    assert "reply" in data
    assert "readability" in data
    assert data["readability"]["token_reduction_pct"] >= 0
    assert len(data["products"]) > 0

    # Test GET /api/v1/agent/sessions/{session_id}
    sess_res = await async_client.get(f"/api/v1/agent/sessions/{session_id}")
    assert sess_res.status_code == 200
    sess_data = sess_res.json()
    assert sess_data["session_id"] == session_id
    assert len(sess_data["messages"]) >= 2

    # Test Web Chat UI route
    web_res = await async_client.get("/chat")
    assert web_res.status_code == 200
    assert "AgentEcom" in web_res.text
