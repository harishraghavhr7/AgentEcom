import pytest
from httpx import AsyncClient
from agentecom.services.merchant import (
    merchant_service,
    ProductCreateSchema,
    ProductUpdateSchema
)
from agentecom.mcp.server import fastmcp_server
from agentecom.tools.commerce import tool_get_product, tool_search_products

@pytest.mark.asyncio
async def test_merchant_add_product(test_db_session):
    """Test store person adds a new product with custom stock and price."""
    sku = "SKU-TEST-MERCHANT-01"
    create_data = ProductCreateSchema(
        sku=sku,
        name="Artisan Ceramic Coffee Dripper",
        category="Home & Kitchen",
        price=34.50,
        stock=45,
        description="Handcrafted ceramic pour-over coffee dripper with spiral ridges.",
        attributes={"color": "Matte White", "material": "Ceramic", "brand": "BaristaCraft"}
    )

    res = await merchant_service.add_product(create_data)
    assert res["success"] is True
    assert res["product"]["sku"] == sku
    assert res["product"]["price"] == 34.50
    assert res["product"]["stock"] == 45
    assert res["product"]["available_count"] == 45
    assert res["product"]["attributes"]["color"] == "Matte White"

    # Verify retrieval via commerce tool (used by AI agent)
    prod_details = await tool_get_product(sku)
    assert "error" not in prod_details
    assert prod_details["product"]["sku"] == sku
    assert prod_details["product"]["price"] == 34.50
    assert prod_details["product"]["stock_count"] == 45
    assert prod_details["product"]["in_stock"] is True

    # Verify merchant_service.get_product
    m_get = await merchant_service.get_product(sku)
    assert m_get["stock_count"] == 45
    assert m_get["available_count"] == 45


@pytest.mark.asyncio
async def test_merchant_update_price_and_attributes(test_db_session):
    """Test store person updates price and attributes."""
    sku = "SKU-4471"
    update_data = ProductUpdateSchema(
        price=64.99,
        attributes={"material": "100% Organic Merino Wool", "warmth_rating": "Heavyweight"}
    )

    res = await merchant_service.update_product(sku, update_data)
    assert res["success"] is True
    assert res["product"]["price"] == 64.99
    assert res["product"]["attributes"]["warmth_rating"] == "Heavyweight"

    # Invalidation verification: get_product returns the updated price
    fresh = await tool_get_product(sku)
    assert fresh["product"]["price"] == 64.99


@pytest.mark.asyncio
async def test_merchant_stock_adjustments(test_db_session):
    """Test setting, incrementing, and decrementing inventory stock."""
    sku = "SKU-4471"
    
    # 1. Set absolute stock
    res_set = await merchant_service.update_stock(sku=sku, quantity=100, mode="set")
    assert res_set["current_stock"] == 100
    assert res_set["available_count"] == 100

    # 2. Add delta stock (+15)
    res_add = await merchant_service.update_stock(sku=sku, quantity=15, mode="adjust")
    assert res_add["current_stock"] == 115

    # 3. Deduct delta stock (-20)
    res_sub = await merchant_service.update_stock(sku=sku, quantity=-20, mode="adjust")
    assert res_sub["current_stock"] == 95

    # 4. Verify negative adjustment is rejected
    with pytest.raises(ValueError):
        await merchant_service.update_stock(sku=sku, quantity=-500, mode="adjust")


@pytest.mark.asyncio
async def test_merchant_list_and_filters(test_db_session):
    """Test listing catalog with filters."""
    # List all
    all_res = await merchant_service.list_products(limit=100)
    assert all_res["total"] > 0
    assert len(all_res["products"]) > 0

    # Filter by category
    apparel_res = await merchant_service.list_products(category="Apparel & Fashion")
    for p in apparel_res["products"]:
        assert p["category"] == "Apparel & Fashion"

    # Query search
    q_res = await merchant_service.list_products(query="Wool")
    assert any("wool" in p["name"].lower() or "wool" in p["description"].lower() for p in q_res["products"])


@pytest.mark.asyncio
async def test_merchant_store_metrics(test_db_session):
    """Test inventory KPI calculation for store owners."""
    metrics = await merchant_service.get_store_metrics()
    assert metrics["total_products"] > 0
    assert metrics["total_stock_units"] > 0
    assert metrics["total_valuation"] > 0.0
    assert "categories" in metrics
    assert len(metrics["categories"]) > 0


@pytest.mark.asyncio
async def test_merchant_fastapi_endpoints(async_client: AsyncClient, test_db_session):
    """Test REST API routes at /api/v1/merchant."""
    # 1. Create product via API
    new_sku = "SKU-API-NEW-99"
    create_res = await async_client.post(
        "/api/v1/merchant/products",
        json={
            "sku": new_sku,
            "name": "Bluetooth Wireless Noise Cancelling Headphones",
            "category": "Electronics & Audio",
            "price": 149.99,
            "stock": 30,
            "description": "High-fidelity wireless active noise-cancelling over-ear headphones.",
            "attributes": {"color": "Midnight Black", "battery_hours": 40}
        }
    )
    assert create_res.status_code == 201
    created_data = create_res.json()
    assert created_data["success"] is True
    assert created_data["product"]["sku"] == new_sku

    # 2. Get product via API
    get_res = await async_client.get(f"/api/v1/merchant/products/{new_sku}")
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "Bluetooth Wireless Noise Cancelling Headphones"

    # 3. Adjust stock via API
    stock_res = await async_client.post(
        f"/api/v1/merchant/products/{new_sku}/stock",
        json={"quantity": 10, "mode": "adjust", "reason": "Restock shipment"}
    )
    assert stock_res.status_code == 200
    assert stock_res.json()["current_stock"] == 40

    # 4. Get store metrics via API
    m_res = await async_client.get("/api/v1/merchant/metrics")
    assert m_res.status_code == 200
    metrics_data = m_res.json()
    assert metrics_data["total_products"] >= 1
    assert metrics_data["total_valuation"] > 0


@pytest.mark.asyncio
async def test_merchant_tools_not_exposed_to_agent(test_db_session):
    """
    Verify security isolation: Merchant management tools (product creation,
    stock adjustment, price modification) must NOT be exposed to the shopping agent via MCP.
    Store operations must remain strictly in the merchant portal/service.
    """
    list_resp = await fastmcp_server.handle_jsonrpc({
        "id": 101,
        "method": "tools/list",
        "params": {}
    })
    tool_names = [t["name"] for t in list_resp["result"]["tools"]]
    
    # Ensure merchant mutation tools are NOT exposed to the agent
    assert "merchant_add_product" not in tool_names
    assert "merchant_update_inventory" not in tool_names
    assert "merchant_update_price" not in tool_names
    assert "merchant_get_store_metrics" not in tool_names

    # Ensure agent tools for consumer shopping ARE present
    assert "search_catalog" in tool_names
    assert "get_product_details" in tool_names
    assert "check_inventory_stock" in tool_names
    assert "create_checkout_session" in tool_names
