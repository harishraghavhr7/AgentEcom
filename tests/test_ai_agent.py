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
    assert "short_term_memory" in sess_data

    # Test Web Chat UI route
    web_res = await async_client.get("/chat")
    assert web_res.status_code == 200
    assert "AgentEcom" in web_res.text


@pytest.mark.asyncio
async def test_short_term_memory_anaphoric_add_to_cart(test_db_session):
    """
    Tests that when a product is viewed/discussed in turn 1,
    the user saying 'add this product to the cart' in turn 2 resolves correctly
    using Short-Term Conversational Working Memory.
    """
    session_id = f"test_mem_sess_{uuid.uuid4().hex[:8]}"

    # Turn 1: Lookup SkinCeuticals C E Ferulic
    res1 = await agent_engine.process_user_turn("Details for SKCEUT-CE-FERULIC", session_id=session_id)
    assert len(res1["products"]) >= 1
    assert res1["products"][0]["sku"] == "SKCEUT-CE-FERULIC"
    assert res1["short_term_memory"]["active_product"]["sku"] == "SKCEUT-CE-FERULIC"
    assert "SKCEUT-CE-FERULIC" in res1["short_term_memory"]["recent_skus"]

    # Turn 2: User says 'add this product to the cart' (without explicitly typing the SKU)
    res2 = await agent_engine.process_user_turn("add this product to the cart", session_id=session_id)
    assert len(res2["cart"]) == 1
    assert res2["cart"][0]["sku"] == "SKCEUT-CE-FERULIC"
    assert res2["cart"][0]["quantity"] == 1
    assert "Added" in res2["reply"] or "SKCEUT-CE-FERULIC" in res2["reply"]

    # Turn 3: Ask 'how much is this' (resolves details via short term memory)
    res3 = await agent_engine.process_user_turn("how much is this", session_id=session_id)
    assert len(res3["tool_calls_made"]) >= 1
    assert res3["tool_calls_made"][0]["tool"] in ["get_product_details", "check_inventory_stock"]
    assert ("sku" in res3["tool_calls_made"][0]["args"] and res3["tool_calls_made"][0]["args"]["sku"] == "SKCEUT-CE-FERULIC") or ("skus" in res3["tool_calls_made"][0]["args"] and "SKCEUT-CE-FERULIC" in res3["tool_calls_made"][0]["args"]["skus"])


@pytest.mark.asyncio
async def test_short_term_memory_stock_inquiry(test_db_session):
    """
    Tests that asking 'how many stocks avaialable' or 'is it in stock'
    resolves the active product in short-term memory and returns live inventory numbers.
    """
    session_id = f"test_mem_stock_{uuid.uuid4().hex[:8]}"

    # Turn 1: Lookup Cuisinart Custom 14-Cup Food Processor
    res1 = await agent_engine.process_user_turn("Details for CUIS-FP-14-PROC", session_id=session_id)
    assert len(res1["products"]) >= 1
    assert res1["products"][0]["sku"] == "CUIS-FP-14-PROC"

    # Turn 2: User asks 'how many stocks avaialable' (with typo / pronoun intent)
    res2 = await agent_engine.process_user_turn("how many stocks avaialable", session_id=session_id)
    assert len(res2["tool_calls_made"]) >= 1
    assert res2["tool_calls_made"][0]["tool"] in ["check_inventory_stock", "get_product_details"]
    assert "in stock" in res2["reply"] or "available in stock" in res2["reply"] or "Stock" in res2["reply"]
    assert "CUIS-FP-14-PROC" in res2["reply"]


@pytest.mark.asyncio
async def test_short_term_memory_search_refinement(test_db_session):
    """
    Tests that follow-up search queries (e.g. 'under $300') retain the previous
    product context from short-term memory.
    """
    session_id = f"test_mem_search_{uuid.uuid4().hex[:8]}"

    # Turn 1: Search headphones
    res1 = await agent_engine.process_user_turn("Show me noise canceling headphones", session_id=session_id)
    assert len(res1["products"]) > 0
    assert "noise canceling headphones" in res1["short_term_memory"]["recent_queries"]

    # Turn 2: Contextual refinement 'under $300'
    res2 = await agent_engine.process_user_turn("under $300", session_id=session_id)
    assert len(res2["tool_calls_made"]) >= 1
    assert res2["tool_calls_made"][0]["tool"] == "search_products"
    assert float(res2["tool_calls_made"][0]["args"]["max_price"]) == 300.0
    assert "noise canceling headphones" in res2["tool_calls_made"][0]["args"]["query"]


@pytest.mark.asyncio
async def test_order_history_inquiry(test_db_session):
    """
    Tests that asking 'get me informations of all my orders' or 'my orders'
    calls get_order_history instead of searching catalog products.
    """
    session_id = f"test_order_sess_{uuid.uuid4().hex[:8]}"

    # Turn 1: Buy a product and confirm order
    await agent_engine.process_user_turn("Add SKU-4471 to cart", session_id=session_id)
    await agent_engine.process_user_turn("Proceed to checkout", session_id=session_id)
    confirm_res = await agent_engine.process_user_turn("Confirm purchase", session_id=session_id)
    assert confirm_res["order"] is not None
    order_num = confirm_res["order"]["order_number"]

    # Turn 2: Inquire 'get me informations of all my orders'
    orders_res = await agent_engine.process_user_turn("get me informations of all my orders", session_id=session_id)
    assert len(orders_res["tool_calls_made"]) >= 1
    assert orders_res["tool_calls_made"][0]["tool"] == "get_order_history"
    assert "Purchase & Order History" in orders_res["reply"] or "Order" in orders_res["reply"]
    assert order_num in orders_res["reply"]
    assert len(orders_res["products"]) == 0  # Should NOT return 100 random catalog products


@pytest.mark.asyncio
async def test_direct_place_the_order_from_cart_or_product(test_db_session):
    """
    Tests that saying 'place the order' directly (even before creating a separate checkout session)
    automatically creates the session from the cart/focused product and confirms the order cleanly.
    """
    session_id = f"test_direct_order_{uuid.uuid4().hex[:8]}"

    # Turn 1: Add FlexiSpot Desk to cart
    res1 = await agent_engine.process_user_turn("Details for FLEX-E7-DESK", session_id=session_id)
    assert len(res1["products"]) >= 1

    # Turn 2: Directly type 'place the order'
    res2 = await agent_engine.process_user_turn("place the order", session_id=session_id)
    assert res2["order"] is not None
    assert "Order Placed Successfully" in res2["reply"] or "Order Number" in res2["reply"]
    assert "FLEX-E7-DESK" in res2["reply"] or "FlexiSpot" in res2["reply"]
    assert res2["order"]["status"] in ["CONFIRMED", "COMPLETED"]

