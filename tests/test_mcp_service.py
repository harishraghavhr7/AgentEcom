import pytest
from httpx import AsyncClient
import agentecom.mcp as mcp
from agentecom.mcp.server import fastmcp_server
from agentecom.mcp.client import mcp_client

@pytest.mark.asyncio
async def test_mcp_server_initialization():
    resp = await fastmcp_server.handle_jsonrpc({
        "id": 1,
        "method": "initialize",
        "params": {}
    })
    assert resp["jsonrpc"] == "2.0"
    assert "result" in resp
    res = resp["result"]
    assert res["protocolVersion"] == "2024-11-05"
    assert "tools" in res["capabilities"]
    assert "prompts" in res["capabilities"]
    assert "resources" in res["capabilities"]
    assert "AgentEcom" in res["serverInfo"]["name"]

@pytest.mark.asyncio
async def test_mcp_tools_list():
    resp = await fastmcp_server.handle_jsonrpc({
        "id": 2,
        "method": "tools/list",
        "params": {}
    })
    tools = resp["result"]["tools"]
    tool_names = [t["name"] for t in tools]
    
    assert "search_catalog" in tool_names
    assert "get_product_details" in tool_names
    assert "check_inventory_stock" in tool_names
    assert "create_checkout_session" in tool_names
    assert "confirm_checkout_order" in tool_names
    assert "track_shipment" in tool_names
    assert "cancel_order" in tool_names
    assert "swap_order_item" in tool_names
    assert "create_return_request" in tool_names
    assert "get_shopify_checkout_url" in tool_names

@pytest.mark.asyncio
async def test_mcp_prompts():
    list_resp = await fastmcp_server.handle_jsonrpc({
        "id": 3,
        "method": "prompts/list",
        "params": {}
    })
    prompts = list_resp["result"]["prompts"]
    prompt_names = [p["name"] for p in prompts]
    assert "shopping_assistant" in prompt_names
    assert "product_advisor" in prompt_names
    assert "checkout_guidance" in prompt_names

    # Test prompt rendering
    get_resp = await fastmcp_server.handle_jsonrpc({
        "id": 4,
        "method": "prompts/get",
        "params": {
            "name": "shopping_assistant",
            "arguments": {"user_intent": "find a warm sweater"}
        }
    })
    result = get_resp["result"]
    assert "messages" in result
    assert len(result["messages"]) > 0
    text_content = result["messages"][0]["content"]["text"]
    assert "AgentEcom" in text_content
    assert "find a warm sweater" in text_content

@pytest.mark.asyncio
async def test_mcp_resources():
    # Read policies
    pol_resp = await fastmcp_server.handle_jsonrpc({
        "id": 5,
        "method": "resources/read",
        "params": {"uri": "policies://store"}
    })
    contents = pol_resp["result"]["contents"]
    assert len(contents) > 0
    assert "window_days" in contents[0]["text"]

    # Read database schema
    schema_resp = await fastmcp_server.handle_jsonrpc({
        "id": 6,
        "method": "resources/read",
        "params": {"uri": "schema://database"}
    })
    assert "products" in schema_resp["result"]["contents"][0]["text"]
    assert "orders" in schema_resp["result"]["contents"][0]["text"]

@pytest.mark.asyncio
async def test_mcp_tool_execution(test_db_session):
    # Test tool call via MCP JSON-RPC
    call_resp = await fastmcp_server.handle_jsonrpc({
        "id": 7,
        "method": "tools/call",
        "params": {
            "name": "check_inventory_stock",
            "arguments": {"skus": ["SKU-4471"]}
        }
    })
    assert call_resp["result"]["isError"] is False
    content_text = call_resp["result"]["content"][0]["text"]
    assert "SKU-4471" in content_text

@pytest.mark.asyncio
async def test_mcp_client_in_memory():
    tools = await mcp_client.list_tools()
    assert len(tools) >= 10
    
    prompt = await mcp_client.get_prompt("checkout_guidance", {"session_id": "cs_test_123"})
    assert "cs_test_123" in prompt["messages"][0]["content"]["text"]

@pytest.mark.asyncio
async def test_mcp_fastapi_endpoints(async_client: AsyncClient):
    # Health endpoint
    h_res = await async_client.get("/mcp/health")
    assert h_res.status_code == 200
    h_data = h_res.json()
    assert h_data["status"] == "online"
    assert h_data["registered_tools_count"] >= 10

    # API v1 health
    v1_res = await async_client.get("/api/v1/health")
    assert v1_res.status_code == 200
    assert "mcp_server" in v1_res.json()

    # Tools endpoint
    t_res = await async_client.get("/mcp/tools")
    assert t_res.status_code == 200
    assert len(t_res.json()["tools"]) >= 10

    # Prompts endpoint
    p_res = await async_client.get("/mcp/prompts")
    assert p_res.status_code == 200
    assert len(p_res.json()["prompts"]) >= 3

    # Resources endpoint
    r_res = await async_client.get("/mcp/resources")
    assert r_res.status_code == 200
    assert len(r_res.json()["resources"]) >= 3

    # JSON-RPC endpoint POST /mcp/rpc
    rpc_res = await async_client.post(
        "/mcp/rpc",
        json={
            "id": 99,
            "method": "tools/call",
            "params": {"name": "check_inventory_stock", "arguments": {"skus": ["SKU-4471"]}}
        }
    )
    assert rpc_res.status_code == 200
    rpc_data = rpc_res.json()
    assert rpc_data["id"] == 99
    assert rpc_data["result"]["isError"] is False

