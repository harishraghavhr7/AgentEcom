"""
FastMCP Database Gateway & MCP Resources.
Provides secure, structured data access and schema introspection for AI agents.
Exposes MCP resources via standard URI schemes:
- schema://database
- catalog://categories
- catalog://featured
- policies://store
- orders://{order_number}
"""

import json
from typing import Dict, Any, List, Optional
from sqlalchemy import select, func
from agentecom.db.database import AsyncSessionLocal
from agentecom.db.models import (
    Product, Inventory, Order, CheckoutSession,
    UserProfile, ReturnRequest, ShipmentTracking
)
from agentecom.core.cache import cache
from agentecom.mcp.server import fastmcp_server


class DatabaseGateway:
    """
    Database Gateway providing safe querying, entity introspection,
    and caching for MCP Tools and Agents.
    """

    @staticmethod
    async def get_database_schema() -> Dict[str, Any]:
        """Introspects and returns database schema metadata."""
        return {
            "tables": {
                "products": {
                    "description": "Storefront product catalog with pricing and attributes",
                    "columns": ["id", "sku", "name", "description", "category", "price", "is_active", "attributes_json", "created_at"]
                },
                "inventory": {
                    "description": "Real-time stock counts and reservations",
                    "columns": ["id", "product_id", "stock_count", "reserved_count", "available_count", "last_updated"]
                },
                "checkout_sessions": {
                    "description": "Short-TTL isolated checkout staging sessions (prevents cart pollution)",
                    "columns": ["id", "idempotency_key", "cart_json", "status", "total_amount", "created_at", "expires_at"]
                },
                "orders": {
                    "description": "Confirmed production orders",
                    "columns": ["id", "order_number", "idempotency_key", "checkout_session_id", "status", "total_amount", "items_json", "customer_email", "created_at"]
                },
                "shipment_tracking": {
                    "description": "Fulfillment and delivery tracking events",
                    "columns": ["id", "order_number", "carrier", "tracking_number", "status", "current_location", "events_json"]
                },
                "return_requests": {
                    "description": "Returns, replacements, and refunds",
                    "columns": ["id", "return_id", "order_number", "sku", "reason", "status", "created_at"]
                },
                "user_profiles": {
                    "description": "Shopper personas, preferences, and saved addresses",
                    "columns": ["id", "user_id", "preferred_size", "favorite_categories_json", "shipping_address_json"]
                }
            }
        }

    @staticmethod
    async def get_categories_summary() -> List[Dict[str, Any]]:
        """Returns categories with item counts and price ranges."""
        cache_key = "gateway:categories_summary"
        cached = await cache.get(cache_key)
        if cached:
            return cached

        async with AsyncSessionLocal() as db:
            stmt = select(
                Product.category,
                func.count(Product.id).label("product_count"),
                func.min(Product.price).label("min_price"),
                func.max(Product.price).label("max_price")
            ).where(Product.is_active == True).group_by(Product.category)
            res = await db.execute(stmt)
            rows = res.all()

            categories = [
                {
                    "category": row.category,
                    "product_count": row.product_count,
                    "price_range": f"${float(row.min_price):.2f} - ${float(row.max_price):.2f}"
                }
                for row in rows
            ]
            await cache.set(cache_key, categories, ttl_seconds=3600, tags=["categories"])
            return categories

    @staticmethod
    async def get_featured_products(limit: int = 6) -> List[Dict[str, Any]]:
        """Returns featured active products."""
        async with AsyncSessionLocal() as db:
            stmt = select(Product, Inventory).join(
                Inventory, Product.id == Inventory.product_id
            ).where(Product.is_active == True).limit(limit)
            res = await db.execute(stmt)
            rows = res.all()

            featured = []
            for prod, inv in rows:
                attrs = {}
                if prod.attributes_json:
                    try:
                        attrs = json.loads(prod.attributes_json)
                    except Exception:
                        pass
                featured.append({
                    "sku": prod.sku,
                    "name": prod.name,
                    "category": prod.category,
                    "price": prod.price,
                    "stock": inv.available_count,
                    "in_stock": inv.available_count > 0,
                    "image_url": attrs.get("image_url", "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=600&auto=format&fit=crop&q=80")
                })
            return featured

    @staticmethod
    async def get_order_resource(order_number: str) -> Dict[str, Any]:
        """Fetches full order snapshot including shipment and return status."""
        ord_clean = order_number.strip().upper()
        async with AsyncSessionLocal() as db:
            stmt = select(Order).where(Order.order_number == ord_clean)
            res = await db.execute(stmt)
            order = res.scalar_one_or_none()

            if not order:
                return {"error": f"Order {ord_clean} not found", "status_code": 404}

            items = []
            if order.items_json:
                try:
                    items = json.loads(order.items_json)
                except Exception:
                    pass

            track_stmt = select(ShipmentTracking).where(ShipmentTracking.order_number == ord_clean)
            track_res = await db.execute(track_stmt)
            tracking = track_res.scalar_one_or_none()

            tracking_data = None
            if tracking:
                tracking_data = {
                    "carrier": tracking.carrier,
                    "tracking_number": tracking.tracking_number,
                    "status": tracking.status.value if hasattr(tracking.status, "value") else str(tracking.status),
                    "current_location": tracking.current_location
                }

            return {
                "order_number": order.order_number,
                "status": order.status.value if hasattr(order.status, "value") else str(order.status),
                "total_amount": order.total_amount,
                "customer_email": order.customer_email,
                "items": items,
                "created_at": order.created_at.isoformat() if order.created_at else None,
                "tracking": tracking_data
            }

    @staticmethod
    def get_store_policies() -> Dict[str, Any]:
        """Static store operational policies."""
        return {
            "returns": {
                "window_days": 30,
                "condition": "Items must be in original condition with tags attached.",
                "cost": "Free domestic return shipping on exchanges; $5 restock fee on refunds.",
                "process": "Trigger tool_create_return_request to receive an instant prepaid return label."
            },
            "shipping": {
                "standard": "3-5 business days ($4.99 or free over $50)",
                "express": "1-2 business days ($14.99)",
                "carriers": ["FedEx", "UPS", "USPS"]
            },
            "checkout_guarantee": {
                "idempotency": "Every transaction requires a unique idempotency key preventing duplicate charges.",
                "session_ttl": "15-minute price lock and stock reservation."
            }
        }


# ==============================================================================
# FastMCP Resource Declarations
# ==============================================================================

@fastmcp_server.resource("schema://database", name="Database Schema", description="Database tables, relationships, and metadata")
async def resource_database_schema():
    return await DatabaseGateway.get_database_schema()

@fastmcp_server.resource("catalog://categories", name="Catalog Categories", description="Live product categories with counts and price ranges")
async def resource_catalog_categories():
    return await DatabaseGateway.get_categories_summary()

@fastmcp_server.resource("catalog://featured", name="Featured Products", description="Curated featured products with current pricing and stock")
async def resource_featured_products():
    return await DatabaseGateway.get_featured_products()

@fastmcp_server.resource("policies://store", name="Store Policies", description="Store returns, exchanges, shipping, and checkout guarantees")
def resource_store_policies():
    return DatabaseGateway.get_store_policies()

@fastmcp_server.resource("orders://{order_number}", name="Order Details", description="Live order lookup with items and shipment tracking")
async def resource_order_details(order_number: str):
    return await DatabaseGateway.get_order_resource(order_number)
