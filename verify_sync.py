"""
End-to-End Multi-Service Synchronization Verification for AgentEcom.
Validates live synchronization across:
1. Core Commerce Engine & DB
2. Decoupled Asynchronous Search Worker (BM25 + Dense Embeddings)
3. FastMCP Server (MCP v2024-11-05 Tools & Resources)
4. Autonomous Shopping Agent & Secure Checkout
"""

import sys
import asyncio
import json
import logging

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from agentecom.db.database import init_db, AsyncSessionLocal
from agentecom.db.seed import seed_database
from agentecom.services.merchant import merchant_service, ProductCreateSchema
from agentecom.search.worker import index_worker
from agentecom.search.hybrid import hybrid_engine
from agentecom.mcp import fastmcp_server
from agentecom.mcp.gateway import DatabaseGateway
from agentecom.tools.commerce import (
    tool_get_product,
    tool_search_products,
    tool_check_inventory,
    tool_create_checkout_session,
    tool_confirm_checkout,
    tool_get_orders
)
from agentecom.agent.engine import agent_engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("agentecom.sync_verifier")

async def verify_services_synchronization():
    print("=" * 80)
    print("🚀 STARTING AGENTECOM MULTI-SERVICE SYNCHRONIZATION VERIFICATION")
    print("=" * 80)

    # --------------------------------------------------------------------------
    # Step 1: Initialize Database & Core Tables
    # --------------------------------------------------------------------------
    print("\n[1/6] Initializing Database & Auto-Migrating Tables...")
    await init_db()
    await seed_database(force_reset=True)
    print("  -> Database initialized with catalog & user_id security schema.")

    # --------------------------------------------------------------------------
    # Step 2: Test Decoupled Search Worker Re-Indexing
    # --------------------------------------------------------------------------
    print("\n[2/6] Verifying Search Worker (Dense Embeddings + BM25 Catalog Indexing)...")
    await index_worker._process_reindex_all()
    print(f"  -> Hybrid Search Engine Index count: {len(hybrid_engine.corpus_docs)} products.")
    assert len(hybrid_engine.corpus_docs) >= 10, "Search index should contain seeded products"

    # --------------------------------------------------------------------------
    # Step 3: Merchant Adds New Product (Simulating Merchant Portal / Shopify Sync)
    # --------------------------------------------------------------------------
    test_sku = "SKU-SYNC-9999"
    test_name = "AeroSync Quantum Wireless Headphones"
    test_price = 199.99
    test_stock = 40
    print(f"\n[3/6] Store Owner Adds Product via Merchant Service: {test_sku}...")
    
    new_prod = await merchant_service.add_product(ProductCreateSchema(
        sku=test_sku,
        name=test_name,
        description="Next-generation spatial audio headphones with active noise cancellation and 40-hour battery life.",
        category="Electronics & Gadgets",
        price=test_price,
        stock=test_stock,
        attributes={"battery_life": "40h", "connectivity": "Bluetooth 5.4", "anc": True}
    ))
    prod_info = new_prod.get("product", new_prod)
    print(f"  -> Product created in DB: {prod_info['sku']} | Price: ${prod_info['price']} | Stock: {prod_info.get('stock', test_stock)}")

    # Worker processes the product indexing
    await index_worker._process_index_product(prod_info["id"])
    print("  -> Search Worker generated dense vector embedding and updated in-memory index.")

    # --------------------------------------------------------------------------
    # Step 4: Verify FastMCP Protocol Reflection
    # --------------------------------------------------------------------------
    print("\n[4/6] Verifying FastMCP Microservice Synchronization...")
    mcp_tools = [t.name for t in fastmcp_server._tool_definitions.values()]
    print(f"  -> FastMCP Registered Tools: {len(mcp_tools)} tools: {', '.join(mcp_tools[:5])}...")
    assert "search_catalog" in mcp_tools
    assert "get_product_details" in mcp_tools
    assert "confirm_checkout_order" in mcp_tools

    # Query FastMCP Resource
    schema_res = await DatabaseGateway.get_database_schema()
    assert "products" in schema_res["tables"]
    assert "orders" in schema_res["tables"]
    print("  -> FastMCP Resource `schema://database` introspected successfully.")

    # Query MCP Tool
    search_tool_func = fastmcp_server._tools.get("search_catalog")
    mcp_search_res = await search_tool_func(query="quantum headphones", limit=3)
    found_skus = [p["sku"] for p in mcp_search_res.get("products", [])]
    print(f"  -> FastMCP search_catalog result for 'quantum headphones': {found_skus}")
    assert test_sku in found_skus, f"FastMCP search must find newly added {test_sku}"

    # --------------------------------------------------------------------------
    # Step 5: Verify AI Shopping Agent Natural Language Discovery
    # --------------------------------------------------------------------------
    print("\n[5/6] Verifying AI Commerce Agent Multi-Turn Shopping Flow...")
    session_id = "sync_test_shopper_01"
    
    turn1 = await agent_engine.process_user_turn(
        user_input="Find quantum headphones",
        session_id=session_id,
        user_id="user_alice",
        llm_provider="local"
    )
    assert any(p["sku"] == test_sku for p in turn1.get("products", [])), "Agent should find the new product"
    print(f"  -> Agent Turn 1: Successfully retrieved {test_sku} via natural language.")

    # Add to cart
    turn2 = await agent_engine.process_user_turn(
        user_input=f"Add {test_sku} to cart",
        session_id=session_id,
        user_id="user_alice",
        llm_provider="local"
    )
    assert len(turn2["cart"]) == 1
    assert turn2["cart"][0]["sku"] == test_sku
    print(f"  -> Agent Turn 2: Cart synchronized with {test_sku}.")

    # Checkout session creation
    turn3 = await agent_engine.process_user_turn(
        user_input="Proceed to checkout",
        session_id=session_id,
        user_id="user_alice",
        llm_provider="local"
    )
    assert turn3["checkout_session"] is not None
    sess_id = turn3["checkout_session"]["session_id"]
    print(f"  -> Agent Turn 3: Isolated Checkout Session created: {sess_id}")

    # Confirm purchase with server-side authentication
    turn4 = await agent_engine.process_user_turn(
        user_input="Confirm purchase",
        session_id=session_id,
        user_id="user_alice",
        llm_provider="local"
    )
    assert turn4["order"] is not None
    ord_num = turn4["order"]["order_number"]
    print(f"  -> Agent Turn 4: Order Confirmed: {ord_num} (Total Paid: ${turn4['order']['total_amount']:.2f})")

    # --------------------------------------------------------------------------
    # Step 6: Verify Atomic Inventory Sync Across All Services
    # --------------------------------------------------------------------------
    print("\n[6/6] Verifying Live Inventory Reduction & IDOR Security...")
    inv_check = await tool_check_inventory(skus=[test_sku])
    remaining_stock = inv_check["inventory"][test_sku]["available_stock"]
    expected_stock = test_stock - 1
    print(f"  -> Initial Stock: {test_stock} | Post-Purchase Stock: {remaining_stock} (Expected: {expected_stock})")
    assert remaining_stock == expected_stock, f"Stock must be atomically decremented from {test_stock} to {expected_stock}"

    # Verify IDOR: Bob cannot see Alice's order
    bob_orders = await tool_get_orders(order_number=ord_num, user_id="user_bob")
    assert bob_orders["count"] == 0, "IDOR check failed: Bob should not see Alice's order"
    
    # Alice can see her order
    alice_orders = await tool_get_orders(order_number=ord_num, user_id="user_alice")
    assert alice_orders["count"] == 1
    print(f"  -> IDOR Check: Alice's order is secured and inaccessible to other users.")

    print("\n" + "=" * 80)
    print("✅ ALL SERVICES FULLY SYNCHRONIZED AND VERIFIED!")
    print("   1. Database & Schema: 🟢 SYNCHRONIZED")
    print("   2. Search Indexing Worker: 🟢 SYNCHRONIZED")
    print("   3. FastMCP Server: 🟢 SYNCHRONIZED")
    print("   4. AI Commerce Agent: 🟢 SYNCHRONIZED")
    print("   5. Inventory & Checkout: 🟢 SYNCHRONIZED")
    print("   6. Server-Side Security: 🟢 SYNCHRONIZED")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    asyncio.run(verify_services_synchronization())
