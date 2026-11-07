"""
FastMCP Tools for AgentEcom.
All tools are registered on the FastMCP Server via @fastmcp_server.tool().
These tools are directly consumable by:
- FastMCP Server (MCP standard JSON-RPC tools/list and tools/call)
- LangGraph Commerce Agent via FastMCP in-memory or network bridge
- External Claude Desktop, Cursor, or any MCP client
"""

import json
from typing import List, Dict, Any, Optional
from agentecom.mcp.server import fastmcp_server
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
from agentecom.integrations.shopify.client import shopify_client

@fastmcp_server.tool(
    name="search_catalog",
    description="Search the product catalog using Hybrid BM25 Lexical + Dense Vector retrieval with Reciprocal Rank Fusion. Returns exact SKU matches and semantic matches."
)
async def mcp_search_catalog(
    query: str,
    category: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    limit: int = 5
) -> Dict[str, Any]:
    """Search catalog using hybrid retrieval with price and category filters."""
    return await tool_search_products(
        query=query,
        category=category,
        min_price=min_price,
        max_price=max_price,
        limit=limit
    )

@fastmcp_server.tool(
    name="get_product_details",
    description="Retrieve comprehensive product specifications, live pricing, stock count, and variant attributes by unique SKU code (e.g. 'SKU-4471')."
)
async def mcp_get_product_details(sku: str) -> Dict[str, Any]:
    """Fetch product details by SKU with sub-2ms aggressive caching."""
    return await tool_get_product(sku=sku)

@fastmcp_server.tool(
    name="check_inventory_stock",
    description="Bulk check real-time available stock levels for a list of SKU codes in a single request."
)
async def mcp_check_inventory_stock(skus: List[str]) -> Dict[str, Any]:
    """Batch query inventory stock levels for SKUs."""
    return await tool_check_inventory(skus=skus)

@fastmcp_server.tool(
    name="create_checkout_session",
    description="Create an isolated, short-TTL (15 min) checkout session with an idempotency key. Prevents cart pollution in core order database."
)
async def mcp_create_checkout_session(
    items: List[Dict[str, Any]],
    idempotency_key: str,
    ttl_minutes: int = 15
) -> Dict[str, Any]:
    """Create isolated checkout staging session."""
    return await tool_create_checkout_session(
        items=items,
        idempotency_key=idempotency_key,
        ttl_minutes=ttl_minutes
    )

@fastmcp_server.tool(
    name="confirm_checkout_order",
    description="Confirm an isolated checkout session into a permanent Order. Requires idempotency key to prevent double charging on agent retries."
)
async def mcp_confirm_checkout_order(
    session_id: str,
    idempotency_key: str,
    customer_email: Optional[str] = "agent-user@example.com"
) -> Dict[str, Any]:
    """Finalize checkout session and convert into production order."""
    return await tool_confirm_checkout(
        session_id=session_id,
        idempotency_key=idempotency_key,
        customer_email=customer_email
    )

@fastmcp_server.tool(
    name="get_order_history",
    description="Look up past orders and purchase history by order number (e.g. 'ORD-1234') or list recent customer orders."
)
async def mcp_get_order_history(
    order_number: Optional[str] = None,
    customer_email: Optional[str] = None,
    limit: int = 10
) -> Dict[str, Any]:
    """Retrieve orders and purchase details."""
    return await tool_get_orders(
        order_number=order_number,
        customer_email=customer_email,
        limit=limit
    )

@fastmcp_server.tool(
    name="track_shipment",
    description="Check real-time package shipping and carrier delivery tracking events by order number."
)
async def mcp_track_shipment(order_number: str) -> Dict[str, Any]:
    """Track shipment status, carrier, and transit milestones."""
    return await tool_track_shipment(order_number=order_number)

@fastmcp_server.tool(
    name="cancel_order",
    description="Cancel an active unshipped order, release reserved inventory, and issue an automatic refund."
)
async def mcp_cancel_order(order_number: str) -> Dict[str, Any]:
    """Cancel order before shipping."""
    return await tool_cancel_order(order_number=order_number)

@fastmcp_server.tool(
    name="swap_order_item",
    description="Exchange an item in an existing order for a different SKU (e.g. changing shoe or sweater size/color)."
)
async def mcp_swap_order_item(order_number: str, old_sku: str, new_sku: str) -> Dict[str, Any]:
    """Exchange line item in an order."""
    return await tool_swap_order_item(order_number=order_number, old_sku=old_sku, new_sku=new_sku)

@fastmcp_server.tool(
    name="create_return_request",
    description="Initiate a return authorization for an item within the 30-day window and generate a prepaid shipping label."
)
async def mcp_create_return_request(order_number: str, sku: str, reason: str) -> Dict[str, Any]:
    """Create return request and generate RMA tracking code."""
    return await tool_create_return_request(order_number=order_number, sku=sku, reason=reason)

@fastmcp_server.tool(
    name="get_user_profile",
    description="Retrieve shopper persona preferences, favorite categories, and default shipping address."
)
async def mcp_get_user_profile(user_id: Optional[str] = "default_shopper") -> Dict[str, Any]:
    """Fetch user profile and saved sizing preferences."""
    return await tool_get_user_profile(user_id=user_id)

@fastmcp_server.tool(
    name="update_user_profile",
    description="Update shopper sizing preferences, style categories, or delivery location."
)
async def mcp_update_user_profile(
    user_id: str,
    preferred_size: Optional[str] = None,
    favorite_categories: Optional[List[str]] = None,
    shipping_address: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Persist updated user preferences."""
    return await tool_update_user_profile(
        user_id=user_id,
        preferred_size=preferred_size,
        favorite_categories=favorite_categories,
        shipping_address=shipping_address
    )

@fastmcp_server.tool(
    name="get_shopify_checkout_url",
    description="Generate a pre-filled 1-Click Shopify checkout permalink URL (/cart/{variant_id}:{qty}) for a list of cart items."
)
async def mcp_get_shopify_checkout_url(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate direct Shopify checkout link from cart items."""
    shopify_items = []
    for it in items:
        v_id = it.get("variant_id") or it.get("shopify_variant_id")
        if v_id:
            shopify_items.append({"variant_id": str(v_id), "quantity": it.get("quantity", 1)})
    
    url = shopify_client.generate_cart_permalink(shopify_items) if shopify_items else f"https://{shopify_client.store_domain}/cart"
    return {
        "checkout_url": url,
        "items_count": len(shopify_items),
        "store_domain": shopify_client.store_domain
    }

