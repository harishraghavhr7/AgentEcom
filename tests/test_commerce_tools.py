import pytest
from httpx import AsyncClient
from agentecom.tools.commerce import tool_check_inventory, tool_search_products

@pytest.mark.asyncio
async def test_check_inventory(test_db_session):
    res = await tool_check_inventory(["SKU-4471", "NON-EXISTENT"])
    inv = res["inventory"]
    assert "SKU-4471" in inv
    assert inv["SKU-4471"]["in_stock"] is True
    assert inv["NON-EXISTENT"]["in_stock"] is False

@pytest.mark.asyncio
async def test_tools_api_endpoint(async_client: AsyncClient):
    # Test tool schema retrieval
    res_schema = await async_client.get("/api/v1/tools/schema")
    assert res_schema.status_code == 200
    data = res_schema.json()
    assert "tools" in data
    tool_names = [t["name"] for t in data["tools"]]
    assert "search_products" in tool_names
    assert "create_checkout_session" in tool_names

    # Test dynamic execution
    exec_res = await async_client.post(
        "/api/v1/tools/execute",
        json={
            "tool_name": "search_products",
            "arguments": {"query": "warm knit sweater", "limit": 2}
        }
    )
    assert exec_res.status_code == 200
    exec_data = exec_res.json()
    assert "products" in exec_data
    assert len(exec_data["products"]) > 0
