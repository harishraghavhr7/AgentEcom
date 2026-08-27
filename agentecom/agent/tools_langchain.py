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
    tool_confirm_checkout,
    tool_get_orders
)

@tool
async def search_products(query: str, category: Optional[str] = None, max_price: Optional[float] = None, min_price: Optional[float] = None, limit: int = 5) -> str:
    """
    Search product catalog using Hybrid BM25 Lexical + Dense Vector retrieval with Reciprocal Rank Fusion.
    Use this to find products matching user descriptions, exact SKUs, categories, or price ranges.
    """
    try:
        limit = int(limit) if limit is not None else 5
    except (ValueError, TypeError):
        limit = 5

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
async def add_to_cart(sku: str, quantity: int = 1) -> str:
    """
    Add a product to the user's shopping cart by SKU and quantity.
    Use this when the user says 'add to cart', 'add this product to the cart', 'add it', 'buy this', etc.
    """
    res = await tool_get_product(sku=sku)
    if "error" in res:
        return f"Cannot add product with SKU '{sku}' to cart: not found."
    return f"Successfully added {res['product']['name']} ({sku}) x{quantity} to cart."

@tool
async def get_order_history(order_number: Optional[str] = None, limit: int = 5) -> str:
    """
    Look up past orders, order details, order status, purchase dates, or tracking information for the user.
    Parameter 'order_number': Optional specific order ID code (e.g. 'ORD-20260826-5FFC36'). Pass None or omit to retrieve all user orders.
    Use this when the user asks 'when did I purchase it', 'when do I purchase it', 'when was it ordered', 'order date', 'what are my orders', 'get me information about my orders', 'order history', 'order details', 'status of my order', 'track my order', etc.
    """
    res = await tool_get_orders(order_number=order_number, limit=limit)
    orders = res.get("orders", [])
    if not orders:
        return "No orders found in purchase history."
    return json.dumps(orders, indent=2)

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
    add_to_cart,
    get_order_history,
    create_checkout_session,
    confirm_checkout_order
]
