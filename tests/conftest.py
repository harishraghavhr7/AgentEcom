import pytest
import pytest_asyncio
import asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from agentecom.db.database import init_db, AsyncSessionLocal
from agentecom.db.models import Product, Inventory
from agentecom.db.seed import seed_database, SAMPLE_PRODUCTS
from agentecom.core.cache import cache
from agentecom.search.hybrid import hybrid_engine
from agentecom.api.main import app

@pytest_asyncio.fixture(scope="function")
async def test_db_session():
    await init_db()
    await seed_database()

    async with AsyncSessionLocal() as session:
        yield session

@pytest_asyncio.fixture(autouse=True)
async def reset_cache_and_search():
    await cache.clear()
    cache.metrics.hits = 0
    cache.metrics.misses = 0
    cache.metrics.invalidations = 0
    cache.metrics.total_read_time_ms = 0.0

    prod_dicts = [
        {
            "id": i + 1,
            "sku": p["sku"],
            "name": p["name"],
            "description": p["description"],
            "category": p["category"],
            "price": p["price"],
            "attributes_json": str(p.get("attributes", {}))
        }
        for i, p in enumerate(SAMPLE_PRODUCTS)
    ]
    hybrid_engine.build_index(prod_dicts)
    yield

@pytest_asyncio.fixture
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
