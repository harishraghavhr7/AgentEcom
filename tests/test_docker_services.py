import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from agentecom.mcp.service import app as mcp_app
from agentecom.mcp import fastmcp_server
from agentecom.db.database import init_db
from agentecom.db.seed import seed_database
from agentecom.search.worker import index_worker

@pytest.mark.asyncio
async def test_mcp_standalone_service_endpoints(test_db_session):
    """
    Validates that the dedicated FastMCP container service boots cleanly
    and serves the MCP protocol (health, discovery, tools, resources, prompts).
    """
    transport = ASGITransport(app=mcp_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Health check endpoint for Docker / K8s probes
        health_resp = await client.get("/health")
        assert health_resp.status_code == 200
        health_data = health_resp.json()
        assert health_data["status"] in ["online", "healthy"]
        tools_cnt = health_data.get("registered_tools_count") or health_data.get("tools_count", 0)
        assert tools_cnt >= 10

        # 2. Service discovery endpoint
        info_resp = await client.get("/")
        assert info_resp.status_code == 200
        info_data = info_resp.json()
        assert "AgentEcom FastMCP Server" in info_data["name"]
        assert "tools" in info_data["capabilities"]
        assert "search_catalog" in info_data["capabilities"]["tools"]
        assert "get_product_details" in info_data["capabilities"]["tools"]

        # 3. Direct MCP Tools listing endpoint
        tools_resp = await client.get("/tools")
        assert tools_resp.status_code == 200
        tools_data = tools_resp.json()
        assert len(tools_data["tools"]) >= 10
        tool_names = [t["name"] for t in tools_data["tools"]]
        assert "search_catalog" in tool_names
        assert "get_product_details" in tool_names

        # 4. Direct MCP Resources listing endpoint
        res_resp = await client.get("/resources")
        assert res_resp.status_code == 200
        res_data = res_resp.json()
        uris = [r["uri"] for r in res_data["resources"]]
        assert "schema://database" in uris
        assert "catalog://categories" in uris

@pytest.mark.asyncio
async def test_worker_service_logic(test_db_session):
    """
    Validates that the background indexing worker logic initializes,
    enqueues jobs, and starts/stops cleanly.
    """
    await index_worker._process_reindex_all()
    assert index_worker.queue.qsize() == 0

    # Start worker consumer
    await index_worker.start()
    assert index_worker._is_running is True

    # Enqueue a reindex job
    await index_worker.enqueue_job("REINDEX_ALL", {})
    await asyncio.sleep(0.1)

    # Stop worker consumer
    await index_worker.stop()
    assert index_worker._is_running is False
