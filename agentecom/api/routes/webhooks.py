from fastapi import APIRouter, HTTPException, BackgroundTasks, Request, Header
from pydantic import BaseModel, Field
import json
import logging
from typing import Dict, Any, Optional

from agentecom.core.cache import cache
from agentecom.search.worker import index_worker
from agentecom.db.database import AsyncSessionLocal
from agentecom.db.models import Product, Inventory
from agentecom.config import settings
from agentecom.integrations.shopify.client import verify_shopify_webhook_hmac
from agentecom.integrations.shopify.sync import shopify_sync
from sqlalchemy import select

logger = logging.getLogger("agentecom.webhooks")
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
    Generic webhook endpoint for Merchant DB sync.
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


# ==============================================================================
# Native Shopify Webhook Endpoints
# ==============================================================================

async def _verify_shopify_request(request: Request, hmac_header: Optional[str]) -> bytes:
    """Read raw body and verify Shopify HMAC signature if secret is configured."""
    body = await request.body()
    secret = settings.SHOPIFY_API_SECRET
    if secret:
        if not hmac_header or not verify_shopify_webhook_hmac(body, hmac_header, secret):
            logger.warning("Rejected Shopify webhook with invalid HMAC signature.")
            raise HTTPException(status_code=401, detail="Invalid Shopify HMAC signature")
    return body


@router.post("/shopify/products")
async def shopify_products_webhook(
    request: Request,
    x_shopify_hmac_sha256: Optional[str] = Header(None, alias="X-Shopify-Hmac-Sha256"),
    x_shopify_topic: Optional[str] = Header(None, alias="X-Shopify-Topic"),
    x_shopify_shop_domain: Optional[str] = Header(None, alias="X-Shopify-Shop-Domain")
):
    """
    Receives real-time product updates from Shopify (products/create, products/update, products/delete).
    Syncs variants, price, description, and stock into AgentEcom Hybrid Search index.
    """
    raw_body = await _verify_shopify_request(request, x_shopify_hmac_sha256)
    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Malformed JSON body")

    topic = x_shopify_topic or "products/update"
    logger.info(f"Received Shopify product webhook: topic={topic}, shop={x_shopify_shop_domain}")

    if topic in ["products/create", "products/update"]:
        affected_skus = await shopify_sync.sync_single_product(payload)
        return {
            "status": "success",
            "topic": topic,
            "product_id": payload.get("id"),
            "affected_skus": affected_skus
        }
    elif topic == "products/delete":
        prod_id = payload.get("id")
        # Soft-deactivate product
        async with AsyncSessionLocal() as db:
            stmt = select(Product).where(Product.attributes_json.contains(f'"shopify_product_id": {prod_id}'))
            res = await db.execute(stmt)
            prods = res.scalars().all()
            for p in prods:
                p.is_active = False
                await cache.invalidate_sku(p.sku)
            await db.commit()
        await shopify_sync.reload_hybrid_index()
        return {"status": "success", "topic": topic, "deleted_product_id": prod_id}

    return {"status": "ignored", "topic": topic}


@router.post("/shopify/inventory")
async def shopify_inventory_webhook(
    request: Request,
    x_shopify_hmac_sha256: Optional[str] = Header(None, alias="X-Shopify-Hmac-Sha256"),
    x_shopify_topic: Optional[str] = Header(None, alias="X-Shopify-Topic")
):
    """
    Receives real-time stock adjustments from Shopify (inventory_levels/update).
    Updates inventory table and surgically clears SKU cache.
    """
    raw_body = await _verify_shopify_request(request, x_shopify_hmac_sha256)
    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Malformed JSON body")

    inv_item_id = payload.get("inventory_item_id")
    available = payload.get("available", 0)

    # Invalidate cache
    await cache.invalidate_by_tag("search_results")
    return {"status": "success", "inventory_item_id": inv_item_id, "available": available}


@router.post("/shopify/sync-catalog")
async def shopify_trigger_catalog_sync(limit: int = 100):
    """
    Manual or scheduled endpoint to fetch and index full Shopify store catalog.
    """
    res = await shopify_sync.sync_catalog(limit=limit)
    return res

