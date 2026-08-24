import json
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from agentecom.core.cache import cache
from agentecom.search.worker import index_worker
from agentecom.db.database import AsyncSessionLocal
from agentecom.db.models import Product, Inventory
from sqlalchemy import select

router = APIRouter(prefix="/webhooks", tags=["Merchant Webhook Sync"])

class WebhookEvent(BaseModel):
    event_type: str = Field(..., description="e.g. 'product.updated', 'product.created', 'stock.adjusted', 'catalog.reindex'")
    sku: Optional[str] = None
    product_id: Optional[int] = None
    category_id: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None

@router.post("/merchant-sync")
async def merchant_sync_webhook(event: WebhookEvent, background_tasks: BackgroundTasks):
    """
    Webhook endpoint for Merchant DB sync.
    Invalidates cache surgically and triggers decoupled async indexing
    instead of blocking the caller or forcing polling.
    """
    invalidated_keys = 0

    if event.event_type == "product.updated":
        if event.sku:
            invalidated_keys = await cache.invalidate_sku(event.sku)
        
        # Enqueue background re-embedding off-request-thread
        if event.product_id:
            await index_worker.enqueue_job("INDEX_PRODUCT", {"product_id": event.product_id})
        elif event.sku:
            async with AsyncSessionLocal() as session:
                stmt = select(Product).where(Product.sku == event.sku)
                res = await session.execute(stmt)
                p = res.scalar_one_or_none()
                if p:
                    await index_worker.enqueue_job("INDEX_PRODUCT", {"product_id": p.id})

    elif event.event_type == "product.created":
        if event.product_id:
            await index_worker.enqueue_job("INDEX_PRODUCT", {"product_id": event.product_id})
        await cache.invalidate_by_tag("search_results")

    elif event.event_type == "stock.adjusted":
        # Price or stock changed -> surgically invalidate SKU cache immediately
        if event.sku:
            invalidated_keys = await cache.invalidate_sku(event.sku)

    elif event.event_type == "catalog.reindex":
        await index_worker.enqueue_job("REINDEX_ALL", {})
        invalidated_keys = await cache.clear()

    return {
        "status": "received",
        "event_type": event.event_type,
        "sku": event.sku,
        "cache_keys_invalidated": invalidated_keys,
        "async_worker_enqueued": True
    }
