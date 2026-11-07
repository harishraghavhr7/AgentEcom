"""
Standalone FastMCP Microservice for AgentEcom.
Exposes Model Context Protocol (MCP v2024-11-05) via FastAPI SSE and JSON-RPC.
Can run in an independent Docker container accessible to external AI agents,
Claude Desktop, Cursor, and microservice meshes.
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from agentecom.config import settings
from agentecom.db.database import init_db
from agentecom.db.seed import seed_database
from agentecom.mcp import fastmcp_server

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB & Seed catalog if necessary
    await init_db()
    await seed_database()
    yield

app = FastAPI(
    title="AgentEcom FastMCP Server Microservice",
    version="2.0.0",
    description="Dedicated Model Context Protocol (MCP) server exposing tools, prompts, and catalog resources.",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount MCP endpoints (both root and /mcp for maximum client compatibility)
fastmcp_server.mount_to_fastapi(app, prefix="")
fastmcp_server.mount_to_fastapi(app, prefix="/mcp")

@app.get("/health", tags=["Monitoring"])
async def health_check():
    """Health check endpoint for container orchestrators (Docker, Kubernetes)."""
    return {
        "status": "healthy",
        "service": "agentecom-mcp-service",
        "protocol_version": "2024-11-05",
        "tools_count": len(fastmcp_server._tool_definitions),
        "prompts_count": len(fastmcp_server._prompt_definitions),
        "resources_count": len(fastmcp_server._resource_definitions)
    }

@app.get("/", tags=["MCP Discovery"])
async def mcp_service_info():
    """Returns MCP server metadata and supported capabilities."""
    return {
        "name": "AgentEcom FastMCP Server",
        "version": "2.0.0",
        "protocol": "MCP v2024-11-05",
        "endpoints": {
            "sse": "/sse",
            "messages": "/messages",
            "tools": "/tools",
            "prompts": "/prompts",
            "resources": "/resources"
        },
        "capabilities": {
            "tools": list(fastmcp_server._tool_definitions.keys()),
            "prompts": list(fastmcp_server._prompt_definitions.keys()),
            "resources": list(fastmcp_server._resource_definitions.keys())
        }
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("MCP_PORT", 8001))
    uvicorn.run("agentecom.mcp.service:app", host="0.0.0.0", port=port, reload=False)
