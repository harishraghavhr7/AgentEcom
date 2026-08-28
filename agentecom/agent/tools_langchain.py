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
    tool_get_orders,
    tool_cancel_order,
    tool_swap_order_item,
    tool_create_return_request,
    tool_track_shipment,
    tool_get_user_profile,
    tool_update_user_profile
)

@tool
async def search_products(query: str, category: Optional[str] = None, max_price: Optional[float] = None, min_price: Optional[float] = None, limit: int = 5) -> str:
    """
    Search product catalog using Hybrid BM25 Lexical + Dense Vector retrieval with Reciprocal Rank Fusion.
    Call this tool when the user wants to browse, find, discover, or search for products (e.g. 'find running shoes', 'cozy sweater under $60', 'show all products', 'what do you have').
    Do NOT call this tool for order tracking or past purchases.
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
    Get full product specifications, attributes (material, warranty, dimensions, battery, colors), pricing, and stock for a specific product SKU.
    Call this when the user asks for specs, details, warranty, or attributes of a product (e.g. 'Details for SKU-4471', 'what is the warranty for this product').
    """
    res = await tool_get_product(sku=sku)
    if "error" in res:
        return f"Product with SKU '{sku}' not found."
    return json.dumps(res["product"], indent=2)

@tool
async def check_inventory_stock(skus: List[str]) -> str:
    """
    Check real-time stock levels and availability count for one or more SKU codes.
    Call this when the user asks 'how many in stock', 'is this available', 'how many units left', or 'stock count'.
    """
    res = await tool_check_inventory(skus=skus)
    return json.dumps(res["inventory"], indent=2)

@tool
async def add_to_cart(sku: str, quantity: int = 1) -> str:
    """
    Add a product to the user's shopping cart by SKU and quantity.
    Call this when the user says 'add to cart', 'add this product to the cart', 'add it', 'buy this item', 'put in my cart', etc.
    """
    res = await tool_get_product(sku=sku)
    if "error" in res:
        return f"Cannot add product with SKU '{sku}' to cart: not found."
    return f"Successfully added {res['product']['name']} ({sku}) x{quantity} to cart."

@tool
async def get_order_history(order_number: Optional[str] = None, limit: int = 5) -> str:
    """
    Look up past orders, order details, order status, purchase dates, order totals, or tracking information.
    Call this whenever the user asks about orders, previous orders, order history, purchase dates, or tracking (e.g., 'get me informations of my previous order', 'my orders', 'what did I purchase', 'when did I buy it', 'order status', 'where is my order', 'track ORD-1234').
    Do NOT confuse this with product search.
    """
    res = await tool_get_orders(order_number=order_number, limit=limit)
    orders = res.get("orders", [])
    if not orders:
        return "No orders found in purchase history."
    return json.dumps(orders, indent=2)

@tool
async def create_checkout_session(skus_and_quantities: Optional[List[Dict[str, Any]]] = None, ttl_minutes: int = 15) -> str:
    """
    Create a short-lived isolated checkout session for items currently in cart or active product.
    Call this when the user says 'checkout', 'proceed to checkout', 'create checkout', or 'ready to pay'.
    Items format: [{'sku': 'SKU-4471', 'quantity': 1}, ...] or omit to checkout current cart items.
    """
    idempotency_key = f"idem_sess_{uuid.uuid4().hex[:12]}"
    res = await tool_create_checkout_session(
        items=skus_and_quantities or [],
        idempotency_key=idempotency_key,
        ttl_minutes=ttl_minutes
    )
    return json.dumps(res, indent=2)

@tool
async def confirm_checkout_order(session_id: Optional[str] = None, customer_email: str = "agent-shopper@internal.ai") -> str:
    """
    Confirm an isolated checkout session to convert it into a confirmed Order.
    Call this when the user confirms their purchase (e.g., 'confirm order', 'confirm purchase', 'place order', 'pay now', 'finalize order').
    This safely deducts inventory and generates the permanent order number idempotently.
    """
    idempotency_key = f"idem_order_{uuid.uuid4().hex[:12]}"
    res = await tool_confirm_checkout(
        session_id=session_id or "active_session",
        idempotency_key=idempotency_key,
        customer_email=customer_email
    )
    return json.dumps(res, indent=2)

@tool
async def cancel_order(order_number: str) -> str:
    """
    Cancel an existing unfulfilled order and issue an instant refund.
    Call this when the user wants to cancel an order (e.g. 'cancel my order', 'cancel ORD-1234', 'stop this order').
    """
    res = await tool_cancel_order(order_number=order_number)
    return json.dumps(res, indent=2)

@tool
async def swap_order_item(order_number: str, old_sku: str, new_sku: str) -> str:
    """
    Swap an item size, color, or variant on an existing order before shipment.
    Call this when the user says 'swap my order size to M', 'change color of my ordered item', or 'exchange SKU in my order'.
    """
    res = await tool_swap_order_item(order_number=order_number, old_sku=old_sku, new_sku=new_sku)
    return json.dumps(res, indent=2)

@tool
async def create_return_request(order_number: str, sku: str, reason: str, days_since_order: int = 5) -> str:
    """
    Initiate a return merchandise request (RMA) and generate prepaid shipping labels.
    If days_since_order > 30, it flags for human manager approval.
    Call this when the user says 'return my item', 'refund this product', 'it arrived damaged', 'it didn't fit'.
    """
    res = await tool_create_return_request(order_number=order_number, sku=sku, reason=reason, days_since_order=days_since_order)
    return json.dumps(res, indent=2)

@tool
async def track_shipment(order_number: str) -> str:
    """
    Track live courier delivery checkpoints and estimated delivery time.
    Call this when the user asks 'track my package', 'where is my shipment', 'tracking status', 'when will my order arrive'.
    """
    res = await tool_track_shipment(order_number=order_number)
    return json.dumps(res, indent=2)

@tool
async def update_user_persona(user_id: str, sizing: Optional[Dict[str, Any]] = None, brand_affinities: Optional[List[str]] = None, allergies: Optional[List[str]] = None) -> str:
    """
    Persist long-term customer sizing, brand affinities, or constraints across sessions.
    Call this when the user mentions their personal sizes or preferences (e.g. 'I wear size Medium', 'I am allergic to wool', 'I prefer FlexiSpot').
    """
    updates = {}
    if sizing:
        updates["sizing"] = sizing
    if brand_affinities:
        updates["brand_affinities"] = brand_affinities
    if allergies:
        updates["allergies"] = allergies
    res = await tool_update_user_profile(user_id=user_id, updates=updates)
    return json.dumps(res, indent=2)

COMMERCE_TOOLS = [
    search_products,
    get_product_details,
    check_inventory_stock,
    add_to_cart,
    get_order_history,
    create_checkout_session,
    confirm_checkout_order,
    cancel_order,
    swap_order_item,
    create_return_request,
    track_shipment,
    update_user_persona
]
