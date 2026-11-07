"""
Asynchronous Shopify Client for AgentEcom.
Provides secure API communication with Shopify Admin REST/GraphQL APIs,
Storefront Cart & Checkout links, and webhook HMAC signature verification.
"""

import hmac
import hashlib
import base64
import logging
from typing import Dict, Any, List, Optional
import httpx

from agentecom.config import settings

logger = logging.getLogger("agentecom.shopify")


def verify_shopify_webhook_hmac(raw_body: bytes, hmac_header: str, secret: str) -> bool:
    """
    Verify the authenticity of a Shopify webhook request using HMAC-SHA256.
    Shopify signs requests using the app's shared secret and provides the base64-encoded
    digest in the 'X-Shopify-Hmac-Sha256' header.
    """
    if not hmac_header or not secret:
        return False
    try:
        digest = hmac.new(
            secret.encode("utf-8"),
            raw_body,
            hashlib.sha256
        ).digest()
        computed_hmac = base64.b64encode(digest).decode("utf-8")
        return hmac.compare_digest(computed_hmac, hmac_header.strip())
    except Exception as e:
        logger.error(f"Error verifying Shopify HMAC signature: {e}")
        return False


class ShopifyClient:
    """
    Async client managing Shopify Admin and Storefront API operations.
    """

    def __init__(
        self,
        store_domain: Optional[str] = None,
        access_token: Optional[str] = None,
        api_version: Optional[str] = None,
        timeout: float = 15.0
    ):
        self.store_domain = (store_domain or settings.SHOPIFY_STORE_DOMAIN or "quickstart-demo.myshopify.com").strip()
        # Clean store domain (remove https:// or trailing slashes if passed)
        self.store_domain = self.store_domain.replace("https://", "").replace("http://", "").rstrip("/")
        self.access_token = access_token or settings.SHOPIFY_ACCESS_TOKEN or ""
        self.api_version = api_version or settings.SHOPIFY_API_VERSION or "2024-10"
        self.timeout = timeout

    @property
    def admin_base_url(self) -> str:
        return f"https://{self.store_domain}/admin/api/{self.api_version}"

    @property
    def headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        if self.access_token:
            headers["X-Shopify-Access-Token"] = self.access_token
        return headers

    async def execute_graphql(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute a GraphQL query or mutation against Shopify Admin GraphQL API.
        """
        url = f"{self.admin_base_url}/graphql.json"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                url,
                headers=self.headers,
                json={"query": query, "variables": variables or {}}
            )
            resp.raise_for_status()
            return resp.json()

    async def fetch_shop(self) -> Dict[str, Any]:
        """
        Fetch details for the connected shop.
        """
        url = f"{self.admin_base_url}/shop.json"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(url, headers=self.headers)
            resp.raise_for_status()
            return resp.json().get("shop", {})

    async def fetch_products(self, limit: int = 50, since_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Fetch products from Shopify Admin REST API.
        """
        url = f"{self.admin_base_url}/products.json"
        params: Dict[str, Any] = {"limit": min(limit, 250)}
        if since_id:
            params["since_id"] = since_id

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(url, headers=self.headers, params=params)
            resp.raise_for_status()
            return resp.json().get("products", [])

    async def fetch_product(self, product_id: int) -> Optional[Dict[str, Any]]:
        """
        Fetch a single product by ID.
        """
        url = f"{self.admin_base_url}/products/{product_id}.json"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(url, headers=self.headers)
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.json().get("product")

    async def fetch_orders(
        self,
        customer_email: Optional[str] = None,
        limit: int = 10,
        status: str = "any"
    ) -> List[Dict[str, Any]]:
        """
        Fetch orders for a customer or recent store orders.
        """
        url = f"{self.admin_base_url}/orders.json"
        params: Dict[str, Any] = {"limit": limit, "status": status}
        if customer_email:
            params["email"] = customer_email

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(url, headers=self.headers, params=params)
            resp.raise_for_status()
            return resp.json().get("orders", [])

    async def fetch_order(self, order_id_or_number: str) -> Optional[Dict[str, Any]]:
        """
        Fetch order by ID or order name (e.g. '#1001').
        """
        clean_id = str(order_id_or_number).strip().lstrip("#")
        
        # If numeric, query direct ID
        if clean_id.isdigit():
            url = f"{self.admin_base_url}/orders/{clean_id}.json"
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(url, headers=self.headers)
                if resp.status_code == 200:
                    return resp.json().get("order")

        # Otherwise query by name parameter
        url = f"{self.admin_base_url}/orders.json"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(url, headers=self.headers, params={"name": f"#{clean_id}", "status": "any"})
            if resp.status_code == 200:
                orders = resp.json().get("orders", [])
                if orders:
                    return orders[0]
        return None

    async def cancel_order(
        self,
        order_id: int,
        reason: str = "customer",
        email_customer: bool = True,
        restock: bool = True
    ) -> Dict[str, Any]:
        """
        Cancel an unfulfilled order and trigger inventory restock + refund.
        """
        url = f"{self.admin_base_url}/orders/{order_id}/cancel.json"
        payload = {
            "reason": reason,
            "email": email_customer,
            "restock": restock
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, headers=self.headers, json=payload)
            resp.raise_for_status()
            return resp.json().get("order", {})

    def generate_cart_permalink(self, items: List[Dict[str, Any]]) -> str:
        """
        Generate a direct 1-click Shopify Checkout Permalink URL.
        Format: https://{store_domain}/cart/{variant_id}:{quantity},{variant_id}:{quantity}
        """
        valid_pairs = []
        for it in items:
            vid = it.get("variant_id") or it.get("sku")
            qty = it.get("quantity", 1)
            if vid:
                valid_pairs.append(f"{vid}:{qty}")

        if not valid_pairs:
            return f"https://{self.store_domain}/cart"

        query_str = ",".join(valid_pairs)
        return f"https://{self.store_domain}/cart/{query_str}"

    async def create_return(
        self,
        order_id: str,
        return_line_items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Create a return request using Shopify GraphQL returnCreate mutation.
        """
        mutation = """
        mutation returnCreate($returnInput: ReturnInput!) {
            returnCreate(returnInput: $returnInput) {
                return {
                    id
                    status
                    name
                }
                userErrors {
                    field
                    message
                }
            }
        }
        """
        # Ensure order ID is GID format
        gid = order_id if order_id.startswith("gid://shopify/Order/") else f"gid://shopify/Order/{order_id}"

        formatted_items = []
        for it in return_line_items:
            line_gid = str(it["line_item_id"])
            if not line_gid.startswith("gid://shopify/LineItem/"):
                line_gid = f"gid://shopify/LineItem/{line_gid}"
            formatted_items.append({
                "returnLineItemId": line_gid,
                "quantity": it.get("quantity", 1),
                "returnReason": it.get("return_reason", "OTHER"),
                "customerNote": it.get("customer_note", "Created by AgentEcom Assistant")
            })

        variables = {
            "returnInput": {
                "orderId": gid,
                "returnLineItems": formatted_items
            }
        }
        return await self.execute_graphql(mutation, variables)

    async def edit_order_swap_variant(
        self,
        order_id: str,
        old_line_item_id: str,
        new_variant_id: str,
        quantity: int = 1
    ) -> Dict[str, Any]:
        """
        Execute pre-shipment variant exchange using Shopify Order Edit API.
        Flow: orderEditBegin -> orderEditAddVariant -> orderEditSetQuantity (0 for old) -> orderEditCommit
        """
        order_gid = order_id if order_id.startswith("gid://shopify/Order/") else f"gid://shopify/Order/{order_id}"
        variant_gid = new_variant_id if new_variant_id.startswith("gid://shopify/ProductVariant/") else f"gid://shopify/ProductVariant/{new_variant_id}"
        old_line_gid = old_line_item_id if old_line_item_id.startswith("gid://shopify/LineItem/") else f"gid://shopify/LineItem/{old_line_item_id}"

        # 1. Begin Edit
        begin_mutation = """
        mutation orderEditBegin($id: ID!) {
            orderEditBegin(id: $id) {
                calculatedOrder {
                    id
                }
                userErrors { field message }
            }
        }
        """
        begin_res = await self.execute_graphql(begin_mutation, {"id": order_gid})
        calc_order_id = begin_res.get("data", {}).get("orderEditBegin", {}).get("calculatedOrder", {}).get("id")
        if not calc_order_id:
            return {"error": "Failed to begin order edit", "details": begin_res}

        # 2. Add New Variant
        add_mutation = """
        mutation orderEditAddVariant($id: ID!, $variantId: ID!, $quantity: Int!) {
            orderEditAddVariant(id: $id, variantId: $variantId, quantity: $quantity) {
                calculatedOrder { id }
                userErrors { field message }
            }
        }
        """
        await self.execute_graphql(add_mutation, {"id": calc_order_id, "variantId": variant_gid, "quantity": quantity})

        # 3. Set Old Item Qty to 0
        remove_mutation = """
        mutation orderEditSetQuantity($id: ID!, $lineItemId: ID!, $quantity: Int!) {
            orderEditSetQuantity(id: $id, lineItemId: $lineItemId, quantity: $quantity) {
                calculatedOrder { id }
                userErrors { field message }
            }
        }
        """
        await self.execute_graphql(remove_mutation, {"id": calc_order_id, "lineItemId": old_line_gid, "quantity": 0})

        # 4. Commit Edit
        commit_mutation = """
        mutation orderEditCommit($id: ID!) {
            orderEditCommit(id: $id) {
                order { id name }
                userErrors { field message }
            }
        }
        """
        commit_res = await self.execute_graphql(commit_mutation, {"id": calc_order_id})
        return commit_res.get("data", {}).get("orderEditCommit", {})


shopify_client = ShopifyClient()
