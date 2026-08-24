from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from agentecom.db.database import get_db
from agentecom.tools.commerce import tool_get_product, tool_check_inventory
from agentecom.core.cache import cache

router = APIRouter(prefix="/catalog", tags=["Catalog & Products"])

@router.get("/products/{sku}")
async def get_product(sku: str):
    """
    Fetch product by SKU.
    Aggressively cached with sub-2ms response time for AI agents.
    """
    res = await tool_get_product(sku)
    if "error" in res:
        raise HTTPException(status_code=res.get("status_code", 404), detail=res["error"])
    return res

@router.post("/inventory/check")
async def check_inventory(payload: dict):
    """
    Check real-time stock for a list of SKUs.
    """
    skus = payload.get("skus", [])
    return await tool_check_inventory(skus)

@router.get("/cache/metrics")
async def get_cache_metrics():
    """
    Return cache hits, misses, hit rate %, and average latency metrics.
    """
    return cache.metrics.to_dict()
