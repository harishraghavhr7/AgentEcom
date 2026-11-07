"""
FastMCP Client for AgentEcom.
Allows Agent Services, LangChain tools, and external services to communicate
with the FastMCP Server via in-process direct memory transport or HTTP/SSE.
"""

import json
import logging
from typing import Dict, Any, List, Optional
import httpx

from agentecom.mcp.server import fastmcp_server

logger = logging.getLogger("agentecom.mcp.client")


class FastMCPClient:
    """
    Client for interacting with the FastMCP Server.
    Defaults to fast, in-memory transport when running in the same process,
    or switches to HTTP/SSE when given a base_url.
    """

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url.rstrip("/") if base_url else None
        self._in_memory = (self.base_url is None)

    async def list_tools(self) -> List[Dict[str, Any]]:
        """Fetch list of all tools exposed by the FastMCP server."""
        if self._in_memory:
            resp = await fastmcp_server.handle_jsonrpc({"id": 1, "method": "tools/list", "params": {}})
            return resp.get("result", {}).get("tools", [])
        
        async with httpx.AsyncClient() as client:
            res = await client.post(f"{self.base_url}/rpc", json={"id": 1, "method": "tools/list", "params": {}})
            data = res.json()
            return data.get("result", {}).get("tools", [])

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool through the FastMCP server."""
        if self._in_memory:
            return await fastmcp_server.call_tool(name, arguments)

        async with httpx.AsyncClient() as client:
            payload = {
                "id": 1,
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments}
            }
            res = await client.post(f"{self.base_url}/rpc", json=payload)
            data = res.json()
            result = data.get("result", {})
            if result.get("isError"):
                content = result.get("content", [{}])[0].get("text", "Unknown tool error")
                raise RuntimeError(content)
            
            # Parse text content if JSON
            raw_text = result.get("content", [{}])[0].get("text", "{}")
            try:
                return json.loads(raw_text)
            except Exception:
                return raw_text

    async def list_prompts(self) -> List[Dict[str, Any]]:
        """List prompts registered on the FastMCP server."""
        if self._in_memory:
            resp = await fastmcp_server.handle_jsonrpc({"id": 1, "method": "prompts/list", "params": {}})
            return resp.get("result", {}).get("prompts", [])

        async with httpx.AsyncClient() as client:
            res = await client.post(f"{self.base_url}/rpc", json={"id": 1, "method": "prompts/list", "params": {}})
            return res.json().get("result", {}).get("prompts", [])

    async def get_prompt(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Fetch and render prompt from FastMCP server."""
        if self._in_memory:
            return await fastmcp_server.get_prompt(name, arguments)

        async with httpx.AsyncClient() as client:
            payload = {"id": 1, "method": "prompts/get", "params": {"name": name, "arguments": arguments or {}}}
            res = await client.post(f"{self.base_url}/rpc", json=payload)
            return res.json().get("result", {})

    async def list_resources(self) -> List[Dict[str, Any]]:
        """List resources registered on the FastMCP server."""
        if self._in_memory:
            resp = await fastmcp_server.handle_jsonrpc({"id": 1, "method": "resources/list", "params": {}})
            return resp.get("result", {}).get("resources", [])

        async with httpx.AsyncClient() as client:
            res = await client.post(f"{self.base_url}/rpc", json={"id": 1, "method": "resources/list", "params": {}})
            return res.json().get("result", {}).get("resources", [])

    async def read_resource(self, uri: str) -> Dict[str, Any]:
        """Read resource content by URI from FastMCP server."""
        if self._in_memory:
            return await fastmcp_server.read_resource(uri)

        async with httpx.AsyncClient() as client:
            payload = {"id": 1, "method": "resources/read", "params": {"uri": uri}}
            res = await client.post(f"{self.base_url}/rpc", json=payload)
            return res.json().get("result", {})


# Default in-memory MCP client
mcp_client = FastMCPClient()
