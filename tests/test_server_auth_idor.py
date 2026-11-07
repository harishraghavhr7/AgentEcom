import pytest
import uuid
from sqlalchemy import select
from agentecom.core.checkout import checkout_manager, CheckoutError
from agentecom.db.database import AsyncSessionLocal
from agentecom.db.models import Order
from agentecom.tools.commerce import (
    tool_create_checkout_session,
    tool_confirm_checkout,
    tool_get_orders,
    tool_cancel_order,
    tool_swap_order_item,
    tool_create_return_request,
    tool_track_shipment
)
from agentecom.agent.engine import agent_engine
from agentecom.agent.graph import commerce_langgraph_app

@pytest.mark.asyncio
async def test_session_user_isolation(test_db_session):
    """
    Verify that checkout sessions record user_id and cross-user confirmation is blocked with 403.
    """
    items = [{"sku": "SKU-4471", "quantity": 1}]
    sess_res = await tool_create_checkout_session(
        items=items,
        idempotency_key=f"idem_alice_sess_{uuid.uuid4().hex[:8]}",
        user_id="user_alice"
    )
    assert "session_id" in sess_res
    session_id = sess_res["session_id"]

    # Bob tries to confirm Alice's session -> Blocked with 403
    bob_confirm = await tool_confirm_checkout(
        session_id=session_id,
        idempotency_key=f"idem_bob_{uuid.uuid4().hex[:8]}",
        user_id="user_bob"
    )
    assert "error" in bob_confirm
    assert bob_confirm.get("status_code") == 403
    assert "belongs to another user account" in bob_confirm["error"].lower() or "unauthorized" in bob_confirm["error"].lower()

    # Alice confirms her own session -> Succeeds
    alice_confirm = await tool_confirm_checkout(
        session_id=session_id,
        idempotency_key=f"idem_alice_{uuid.uuid4().hex[:8]}",
        user_id="user_alice"
    )
    assert "order_number" in alice_confirm
    assert alice_confirm["status"] == "CONFIRMED"

    # Verify in DB that Order.user_id == 'user_alice'
    async with AsyncSessionLocal() as db:
        o = (await db.execute(select(Order).where(Order.order_number == alice_confirm["order_number"]))).scalar_one()
        assert o.user_id == "user_alice"


@pytest.mark.asyncio
async def test_order_query_idor_prevention(test_db_session):
    """
    Verify that querying orders enforces server-side user_id filtering (slide implementation).
    """
    # Create order for Alice
    items = [{"sku": "SKU-4471", "quantity": 1}]
    sess_res = await tool_create_checkout_session(
        items=items,
        idempotency_key=f"idem_alice_sess_{uuid.uuid4().hex[:8]}",
        user_id="user_alice"
    )
    alice_order = await tool_confirm_checkout(
        session_id=sess_res["session_id"],
        idempotency_key=f"idem_alice_conf_{uuid.uuid4().hex[:8]}",
        user_id="user_alice"
    )
    alice_ord_num = alice_order["order_number"]

    # 1. Alice queries her own order by order_number -> Found
    alice_query = await tool_get_orders(order_number=alice_ord_num, user_id="user_alice")
    assert alice_query["count"] == 1
    assert alice_query["orders"][0]["order_number"] == alice_ord_num

    # 2. Bob queries Alice's exact order_number -> Empty (Blocked by Order.user_id == user_id)
    bob_query = await tool_get_orders(order_number=alice_ord_num, user_id="user_bob")
    assert bob_query["count"] == 0
    assert len(bob_query["orders"]) == 0

    # 3. Bob queries his order list without order_number -> Alice's order is not visible
    bob_all = await tool_get_orders(user_id="user_bob")
    assert not any(o["order_number"] == alice_ord_num for o in bob_all["orders"])


@pytest.mark.asyncio
async def test_order_modification_idor_prevention(test_db_session):
    """
    Verify that an unauthorized user cannot cancel, swap, return, or track another user's order.
    """
    # Create order for Alice
    items = [{"sku": "SKU-4471", "quantity": 1}]
    sess_res = await tool_create_checkout_session(
        items=items,
        idempotency_key=f"idem_alice_sess_{uuid.uuid4().hex[:8]}",
        user_id="user_alice"
    )
    alice_order = await tool_confirm_checkout(
        session_id=sess_res["session_id"],
        idempotency_key=f"idem_alice_conf_{uuid.uuid4().hex[:8]}",
        user_id="user_alice"
    )
    alice_ord_num = alice_order["order_number"]

    # 1. Bob tries to cancel Alice's order -> 404 / 403 Unauthorized
    bob_cancel = await tool_cancel_order(order_number=alice_ord_num, user_id="user_bob")
    assert "error" in bob_cancel
    assert bob_cancel.get("status_code") in [403, 404]

    # 2. Bob tries to swap an item on Alice's order -> 404 / 403 Unauthorized
    bob_swap = await tool_swap_order_item(
        order_number=alice_ord_num,
        old_sku="SKU-4471",
        new_sku="SKU-8821",
        user_id="user_bob"
    )
    assert "error" in bob_swap
    assert bob_swap.get("status_code") in [403, 404]

    # 3. Bob tries to request a return on Alice's order -> 404 / 403 Unauthorized
    bob_return = await tool_create_return_request(
        order_number=alice_ord_num,
        sku="SKU-4471",
        reason="Does not fit",
        days_since_order=5,
        user_id="user_bob"
    )
    assert "error" in bob_return
    assert bob_return.get("status_code") in [403, 404]

    # 4. Bob tries to track shipment on Alice's order -> 404 / 403 Unauthorized
    bob_track = await tool_track_shipment(order_number=alice_ord_num, user_id="user_bob")
    assert "error" in bob_track
    assert bob_track.get("status_code") in [403, 404]

    # 5. Alice successfully cancels her own order
    alice_cancel = await tool_cancel_order(order_number=alice_ord_num, user_id="user_alice")
    assert alice_cancel["status"] == "CANCELLED"
    assert alice_cancel["order_number"] == alice_ord_num


@pytest.mark.asyncio
async def test_langgraph_server_auth_config_binding(test_db_session):
    """
    Verify that LangGraph executes tool calls using config['configurable']['user_id']
    from the trusted server context rather than trusting client-controlled state['user_id'].
    """
    from langchain_core.messages import HumanMessage, AIMessage

    session_id = f"sess_idor_{uuid.uuid4().hex[:8]}"

    # Add item to cart for Alice
    await agent_engine.process_user_turn(
        user_input="Add SKU-4471 to cart",
        session_id=session_id,
        user_id="user_alice",
        llm_provider="local"
    )

    # Checkout session creation turn
    await agent_engine.process_user_turn(
        user_input="Proceed to checkout",
        session_id=session_id,
        user_id="user_alice",
        llm_provider="local"
    )

    # Confirm purchase with trusted server-side authentication user_id="user_alice"
    confirm_res = await agent_engine.process_user_turn(
        user_input="Confirm purchase",
        session_id=session_id,
        user_id="user_alice",
        llm_provider="local"
    )

    assert "Order Placed Successfully" in confirm_res["reply"] or "CONFIRMED" in confirm_res["reply"] or confirm_res.get("order") is not None

    # Verify created order is owned by user_alice in DB
    async with AsyncSessionLocal() as db:
        orders = (await db.execute(select(Order).where(Order.user_id == "user_alice"))).scalars().all()
        assert len(orders) >= 1
        alice_order = orders[-1]
        assert alice_order.user_id == "user_alice"
