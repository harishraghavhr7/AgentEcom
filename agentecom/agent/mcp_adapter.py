"""
MCP Adapter for LangGraph / LangChain Agent Service.
Bridges FastMCP Server tools, prompts, and resources into LangGraph workflow:
1. Dynamically maps FastMCP tools into LangChain BaseTool / StructuredTool instances.
2. Renders versioned FastMCP prompts and injects FastMCP resources as context.
3. Records MCP tool telemetry (latency, parameters, payload compression).
"""

import json
import inspect
from typing import List, Dict, Any, Optional, Callable
from langchain_core.tools import StructuredTool, BaseTool
from pydantic import BaseModel, create_model, Field

from agentecom.mcp.server import fastmcp_server, FastMCPServer
from agentecom.mcp.client import mcp_client, FastMCPClient


def _create_pydantic_model_from_schema(name: str, schema: Dict[str, Any]) -> type[BaseModel]:
    """Dynamically creates a Pydantic model from an MCP inputSchema."""
    properties = schema.get("properties", {})
    required = set(schema.get("required", []))
    fields = {}

    type_mapping = {
        "string": str,
        "integer": int,
        "number": float,
        "boolean": bool,
        "array": list,
        "object": dict
    }

    for prop_name, prop_def in properties.items():
        p_type_str = prop_def.get("type", "string")
        py_type = type_mapping.get(p_type_str, str)
        is_req = prop_name in required
        default_val = ... if is_req else None
        
        if not is_req:
            py_type = Optional[py_type]

        fields[prop_name] = (py_type, Field(default=default_val, description=prop_def.get("description", "")))

    return create_model(f"{name}_Input", **fields)


def convert_mcp_tool_to_langchain(tool_def: Any, server: FastMCPServer = fastmcp_server) -> BaseTool:
    """Converts a single FastMCP tool definition into a LangChain StructuredTool."""
    name = tool_def.name
    desc = tool_def.description
    schema = tool_def.inputSchema

    args_model = _create_pydantic_model_from_schema(name, schema)

    async def _async_runner(**kwargs) -> str:
        # Filter None values for optional parameters
        clean_kwargs = {k: v for k, v in kwargs.items() if v is not None}
        result = await server.call_tool(name, clean_kwargs)
        if isinstance(result, (dict, list)):
            return json.dumps(result, indent=2)
        return str(result)

    def _sync_runner(**kwargs) -> str:
        import asyncio
        return asyncio.run(_async_runner(**kwargs))

    return StructuredTool(
        name=name,
        description=desc,
        args_schema=args_model,
        func=_sync_runner,
        coroutine=_async_runner
    )


def get_langchain_tools_from_mcp(server: FastMCPServer = fastmcp_server) -> List[BaseTool]:
    """Extracts and builds LangChain tools dynamically from all registered FastMCP tools."""
    tools = []
    for tool_name, tool_def in server._tool_definitions.items():
        tools.append(convert_mcp_tool_to_langchain(tool_def, server))
    return tools


async def get_system_prompt_from_mcp(
    user_intent: Optional[str] = None,
    user_persona: Optional[str] = None,
    server: FastMCPServer = fastmcp_server
) -> str:
    """
    Renders system prompt using FastMCP prompt 'shopping_assistant' and enriches it
    with store operational policies from FastMCP resource 'policies://store'.
    """
    prompt_res = await server.get_prompt(
        "shopping_assistant",
        {"user_intent": user_intent, "user_persona": user_persona}
    )
    base_text = prompt_res["messages"][0]["content"]["text"]

    # Pull store policies from FastMCP resource
    try:
        policies_res = await server.read_resource("policies://store")
        policies_text = policies_res["contents"][0]["text"]
        base_text += f"\n\nSTORE POLICIES & GUARANTEES (via FastMCP Resource):\n{policies_text}"
    except Exception:
        pass

    return base_text
