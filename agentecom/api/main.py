from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from agentecom.config import settings
from agentecom.db.database import init_db
from agentecom.db.seed import seed_database
from agentecom.search.worker import index_worker
from agentecom.api.routes import catalog, search, checkout, webhooks, tools

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

app.include_router(catalog.router, prefix=settings.API_V1_STR)
app.include_router(search.router, prefix=settings.API_V1_STR)
app.include_router(checkout.router, prefix=settings.API_V1_STR)
app.include_router(webhooks.router, prefix=settings.API_V1_STR)
app.include_router(tools.router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    return {
        "name": settings.PROJECT_NAME,
        "status": "online",
        "docs": "/docs",
        "tools_schema": f"{settings.API_V1_STR}/tools/schema"
    }
