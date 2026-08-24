"""
LangChain Tools definitions for AgentEcom.
Exposes commerce capabilities as decorated LangChain tools.
"""

from typing import List, Dict, Any, Optional
import json
import uuid
from langchain_core.tools import tool

from agentecom.tools.commerce import (
    tool_search_products,
    tool_get_product,
    tool_check_inventory,
    tool_create_checkout_session,
    tool_confirm_checkout
)

@tool
async def search_products(query: str, category: Optional[str] = None, max_price: Optional[float] = None, min_price: Optional[float] = None, limit: int = 5) -> str:
    """
    Search product catalog using Hybrid BM25 Lexical + Dense Vector retrieval with Reciprocal Rank Fusion.
    Use this to find products matching user descriptions, exact SKUs, categories, or price ranges.
    """
    res = await tool_search_products(
        query=query,
        category=category,
        min_price=min_price,
        max_price=max_price,
        limit=limit
    )
    products = res.get("products", [])
    if not products:
        return f"No products found for search query: '{query}'."

    summary = []
    for p in products:
        summary.append({
            "sku": p.get("sku"),
            "name": p.get("name"),
            "price": p.get("price"),
            "category": p.get("category"),
            "description": p.get("description", "")[:120],
            "rrf_score": p.get("_rrf_score")
        })
    return json.dumps(summary, indent=2)

@tool
async def get_product_details(sku: str) -> str:
    """
    Get full product specifications, attributes, pricing, and live stock availability for a specific SKU.
    """
    res = await tool_get_product(sku=sku)
    if "error" in res:
        return f"Product with SKU '{sku}' not found."
    return json.dumps(res["product"], indent=2)

@tool
async def check_inventory_stock(skus: List[str]) -> str:
    """
    Check real-time stock levels and availability for one or more SKU codes.
    """
    res = await tool_check_inventory(skus=skus)
    return json.dumps(res["inventory"], indent=2)

@tool
async def create_checkout_session(skus_and_quantities: List[Dict[str, Any]], ttl_minutes: int = 15) -> str:
    """
    Create a short-lived isolated checkout session for items.
    Items format: [{'sku': 'SKU-4471', 'quantity': 1}, ...]
    """
    idempotency_key = f"idem_sess_{uuid.uuid4().hex[:12]}"
    res = await tool_create_checkout_session(
        items=skus_and_quantities,
        idempotency_key=idempotency_key,
        ttl_minutes=ttl_minutes
    )
    return json.dumps(res, indent=2)

@tool
async def confirm_checkout_order(session_id: str, customer_email: str = "agent-shopper@internal.ai") -> str:
    """
    Confirm an isolated checkout session to convert it into a confirmed Order.
    This safely deducts inventory and generates the permanent order number idempotently.
    """
    idempotency_key = f"idem_order_{uuid.uuid4().hex[:12]}"
    res = await tool_confirm_checkout(
        session_id=session_id,
        idempotency_key=idempotency_key,
        customer_email=customer_email
    )
    return json.dumps(res, indent=2)

COMMERCE_TOOLS = [
    search_products,
    get_product_details,
    check_inventory_stock,
    create_checkout_session,
    confirm_checkout_order
]
