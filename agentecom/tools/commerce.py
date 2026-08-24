"""
Stateless, Fast Commerce Tools for AI Agents.

Key architectural rules:
- Thin, idempotent functions with minimal computational overhead.
- Directly query aggressive cache layer (<2ms latency).
- Search delegates to hybrid engine (never blocking on embedding inference).
- Exports standard tool signatures for LLM tool binding (OpenAI / Anthropic / Gemini / LangChain / MCP).
"""

import json
import time
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from sqlalchemy import select
from agentecom.db.database import AsyncSessionLocal
from agentecom.db.models import Product, Inventory
from agentecom.core.cache import cache
from agentecom.search.hybrid import hybrid_engine
from agentecom.core.checkout import checkout_manager, CheckoutError
from agentecom.db.seed import SAMPLE_PRODUCTS

# --- Pydantic Schemas for Agent Tool Input/Output ---

class CartItemInput(BaseModel):
    sku: str = Field(..., description="The unique SKU code of the product to purchase (e.g. 'SKU-4471')")
    quantity: int = Field(1, ge=1, description="Quantity of items to purchase (must be >= 1)")

class SearchProductsInput(BaseModel):
    query: str = Field(..., description="Natural language search query, product name, or SKU code")
    category: Optional[str] = Field(None, description="Optional category filter (e.g. 'Apparel & Fashion')")
    min_price: Optional[float] = Field(None, ge=0, description="Minimum price filter in USD")
    max_price: Optional[float] = Field(None, ge=0, description="Maximum price filter in USD")
    limit: int = Field(5, ge=1, le=50, description="Maximum number of products to return")

class GetProductInput(BaseModel):
    sku: str = Field(..., description="The unique SKU of the product to fetch")

class CheckInventoryInput(BaseModel):
    skus: List[str] = Field(..., description="List of SKU strings to check real-time stock for")

class CreateCheckoutInput(BaseModel):
    items: List[CartItemInput] = Field(..., description="List of products and quantities for the checkout")
    idempotency_key: str = Field(..., description="Unique client-generated idempotency key (UUID or hash) to prevent duplicate sessions")
    ttl_minutes: Optional[int] = Field(15, description="Session expiration in minutes (default 15)")

class ConfirmCheckoutInput(BaseModel):
    session_id: str = Field(..., description="Checkout session ID returned by create_checkout")
    idempotency_key: str = Field(..., description="Unique idempotency key to prevent double charging on retry")
    customer_email: Optional[str] = Field("agent-user@example.com", description="Customer email address")


# --- Core Tool Functions ---

async def ensure_index_ready():
    """Auto-load index if not loaded yet."""
    if not hybrid_engine.is_indexed or not hybrid_engine.corpus_docs:
        prod_dicts = [
            {
                "id": i + 1,
                "sku": p["sku"],
                "name": p["name"],
                "description": p["description"],
                "category": p["category"],
                "price": p["price"],
                "attributes_json": json.dumps(p.get("attributes", {}))
            }
            for i, p in enumerate(SAMPLE_PRODUCTS)
        ]
        hybrid_engine.build_index(prod_dicts)

async def tool_search_products(
    query: str,
    category: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    limit: int = 5
) -> Dict[str, Any]:
    """
    Search catalog using Hybrid BM25 + Dense Vector retrieval with caching.
    """
    start = time.perf_counter()
    await ensure_index_ready()

    # 1. Check search cache
    cache_key = cache._generate_search_key(query, {"cat": category, "min": min_price, "max": max_price, "lim": limit})
    cached_res = await cache.get(cache_key)
    if cached_res is not None:
        elapsed = (time.perf_counter() - start) * 1000
        return {
            "query": query,
            "results_count": len(cached_res),
            "latency_ms": round(elapsed, 3),
            "cached": True,
            "products": cached_res
        }

    # 2. Execute Hybrid Search
    results = hybrid_engine.search_hybrid(
        query=query,
        top_k=limit,
        category=category,
        min_price=min_price,
        max_price=max_price
    )

    # Cache search results (tagged for surgical invalidation)
    await cache.set(cache_key, results, ttl_seconds=600, tags=["search_results"])

    elapsed = (time.perf_counter() - start) * 1000
    return {
        "query": query,
        "results_count": len(results),
        "latency_ms": round(elapsed, 3),
        "cached": False,
        "products": results
    }


async def tool_get_product(sku: str) -> Dict[str, Any]:
    """
    Get full product details and live inventory by SKU with sub-2ms caching.
    """
    start = time.perf_counter()
    cache_key = f"sku:{sku}"
    
    # 1. Try cache
    cached_prod = await cache.get(cache_key)
    if cached_prod:
        elapsed = (time.perf_counter() - start) * 1000
        return {
            "product": cached_prod,
            "latency_ms": round(elapsed, 3),
            "cached": True
        }

    # 2. Query Database
    async with AsyncSessionLocal() as db:
        stmt = select(Product).where(Product.sku == sku, Product.is_active == True)
        res = await db.execute(stmt)
        prod = res.scalar_one_or_none()

        if not prod:
            # Fallback to sample catalog if DB unseeded
            sample = next((p for p in SAMPLE_PRODUCTS if p["sku"] == sku), None)
            if sample:
                prod_data = {
                    "id": 1,
                    "sku": sample["sku"],
                    "name": sample["name"],
                    "description": sample["description"],
                    "category": sample["category"],
                    "price": sample["price"],
                    "attributes": sample.get("attributes", {}),
                    "in_stock": True,
                    "stock_count": sample.get("stock", 20)
                }
                await cache.set(cache_key, prod_data, ttl_seconds=3600, tags=[f"sku:{sku}"])
                elapsed = (time.perf_counter() - start) * 1000
                return {"product": prod_data, "latency_ms": round(elapsed, 3), "cached": False}

            return {"error": f"Product with SKU '{sku}' not found.", "status_code": 404}

        # Query stock
        inv_stmt = select(Inventory).where(Inventory.product_id == prod.id)
        inv_res = await db.execute(inv_stmt)
        inv = inv_res.scalar_one_or_none()

        stock_count = inv.available_count if inv else 0

        prod_data = {
            "id": prod.id,
            "sku": prod.sku,
            "name": prod.name,
            "description": prod.description,
            "category": prod.category,
            "price": prod.price,
            "attributes": json.loads(prod.attributes_json or "{}"),
            "in_stock": stock_count > 0,
            "stock_count": stock_count
        }

        # Cache aggressively with tags
        await cache.set(
            cache_key,
            prod_data,
            ttl_seconds=3600,
            tags=[f"sku:{sku}", f"category:{prod.category}"]
        )

        elapsed = (time.perf_counter() - start) * 1000
        return {
            "product": prod_data,
            "latency_ms": round(elapsed, 3),
            "cached": False
        }


async def tool_check_inventory(skus: List[str]) -> Dict[str, Any]:
    """
    Check stock availability for multiple SKUs in a single batch request.
    """
    async with AsyncSessionLocal() as db:
        stmt = select(Product, Inventory).join(Inventory, Product.id == Inventory.product_id).where(Product.sku.in_(skus))
        res = await db.execute(stmt)
        rows = res.all()

        inventory_status = {}
        for prod, inv in rows:
            inventory_status[prod.sku] = {
                "name": prod.name,
                "price": prod.price,
                "available_stock": inv.available_count,
                "in_stock": inv.available_count > 0
            }

        # Fill any missing SKUs
        for s in skus:
            if s not in inventory_status:
                inventory_status[s] = {"error": "SKU not found", "in_stock": False, "available_stock": 0}

        return {"inventory": inventory_status}


async def tool_create_checkout_session(
    items: List[Dict[str, Any]],
    idempotency_key: str,
    ttl_minutes: int = 15
) -> Dict[str, Any]:
    """
    Create a short-lived isolated checkout session with idempotency key.
    """
    async with AsyncSessionLocal() as db:
        try:
            session, is_new = await checkout_manager.create_checkout_session(
                db=db,
                items=items,
                idempotency_key=idempotency_key,
                ttl_minutes=ttl_minutes
            )
            return {
                "session_id": session.id,
                "idempotency_key": session.idempotency_key,
                "status": session.status.value,
                "total_amount": session.total_amount,
                "items": json.loads(session.cart_json),
                "expires_at": session.expires_at.isoformat(),
                "is_new_session": is_new
            }
        except CheckoutError as e:
            return {"error": e.message, "status_code": e.status_code}


async def tool_confirm_checkout(
    session_id: str,
    idempotency_key: str,
    customer_email: Optional[str] = "agent-user@example.com"
) -> Dict[str, Any]:
    """
    Confirm an isolated checkout session into a permanent Order idempotently.
    """
    async with AsyncSessionLocal() as db:
        try:
            order, is_new = await checkout_manager.confirm_checkout(
                db=db,
                session_id=session_id,
                idempotency_key=idempotency_key,
                customer_email=customer_email
            )
            return {
                "order_number": order.order_number,
                "idempotency_key": order.idempotency_key,
                "checkout_session_id": order.checkout_session_id,
                "status": order.status.value,
                "total_amount": order.total_amount,
                "items": json.loads(order.items_json),
                "customer_email": order.customer_email,
                "created_at": order.created_at.isoformat(),
                "is_new_order": is_new
            }
        except CheckoutError as e:
            return {"error": e.message, "status_code": e.status_code}
