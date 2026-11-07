import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from agentecom.config import settings
from agentecom.db.database import init_db
from agentecom.db.seed import seed_database
from agentecom.search.worker import index_worker
from agentecom.api.routes import catalog, search, checkout, webhooks, tools, agent, merchant
from agentecom.mcp import fastmcp_server

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup:
    await init_db()
    await seed_database()
    await index_worker.start()
    # Trigger initial indexing
    await index_worker.enqueue_job("REINDEX_ALL", {})
    yield
    # Shutdown:
    await index_worker.stop()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="High-throughput, low-latency e-commerce engine optimized for AI agents.",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routers
app.include_router(catalog.router, prefix=settings.API_V1_STR)
app.include_router(search.router, prefix=settings.API_V1_STR)
app.include_router(checkout.router, prefix=settings.API_V1_STR)
app.include_router(webhooks.router, prefix=settings.API_V1_STR)
app.include_router(webhooks.router)  # Direct /webhooks mounting for standard webhook endpoints
app.include_router(tools.router, prefix=settings.API_V1_STR)
app.include_router(agent.router, prefix=settings.API_V1_STR)
app.include_router(merchant.router, prefix=settings.API_V1_STR)

# Mount FastMCP Server (MCP standard JSON-RPC 2.0, SSE, Tools, Prompts, Resources)
fastmcp_server.mount_to_fastapi(app, prefix="/mcp")

WEB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "web")
INDEX_HTML = os.path.join(WEB_DIR, "index.html")
WIDGET_JS = os.path.join(WEB_DIR, "widget.js")

@app.get("/widget.js")
async def serve_widget_script():
    """Serves the embeddable storefront chat widget JavaScript."""
    if os.path.exists(WIDGET_JS):
        return FileResponse(WIDGET_JS, media_type="application/javascript")
    return HTMLResponse("// widget script not found", status_code=404)

@app.get("/", response_class=HTMLResponse)
@app.get("/chat", response_class=HTMLResponse)
async def serve_chat_ui():
    """Serves the interactive Conversational AI Shopping Agent and Readability Inspector."""
    if os.path.exists(INDEX_HTML):
        return FileResponse(INDEX_HTML)
    return HTMLResponse("<h1>AgentEcom API Online</h1><p>Visit <a href='/docs'>/docs</a> for Swagger.</p>")

@app.get("/api/v1/health")
async def health_check():
    return {
        "name": settings.PROJECT_NAME,
        "status": "online",
        "docs": "/docs",
        "chat_ui": "/chat",
        "tools_schema": f"{settings.API_V1_STR}/tools/schema",
        "mcp_server": {
            "server": fastmcp_server.name,
            "version": fastmcp_server.version,
            "protocol": "MCP 2024-11-05",
            "prefix": "/mcp",
            "tools_count": len(fastmcp_server._tools),
            "prompts_count": len(fastmcp_server._prompts),
            "resources_count": len(fastmcp_server._resources),
            "sse_endpoint": "/mcp/sse",
            "rpc_endpoint": "/mcp/rpc"
        }
    }
