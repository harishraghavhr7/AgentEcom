"""
FastMCP Service Package for AgentEcom.
Holds all Tools, Prompts, Resources, and Database Gateways.
"""

from agentecom.mcp.server import fastmcp_server, FastMCPServer
from agentecom.mcp.client import mcp_client, FastMCPClient
from agentecom.mcp.gateway import DatabaseGateway

# Import tools and prompts to ensure all decorators register onto fastmcp_server
import agentecom.mcp.tools
import agentecom.mcp.prompts
import agentecom.mcp.gateway

__all__ = [
    "fastmcp_server",
    "FastMCPServer",
    "mcp_client",
    "FastMCPClient",
    "DatabaseGateway"
]
