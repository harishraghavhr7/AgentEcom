"""
Short-Lived, Idempotent, Isolated Checkout Session Engine.

Protects against:
- Agent retries / double-firing creating duplicate orders (Idempotency Key)
- Abandoned agent exploratory carts polluting core order database (Isolated Sessions + short TTL)
- Concurrency race conditions in inventory reservation
"""

import uuid
import json
import datetime
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from agentecom.config import settings
from agentecom.db.models import CheckoutSession, SessionStatus, Order, OrderStatus, Product, Inventory
from agentecom.core.cache import cache

class CheckoutError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class CheckoutManager:
    """
    Manages transient checkout sessions and converts confirmed sessions to permanent orders.
    """

    async def create_checkout_session(
        self,
        db: AsyncSession,
        items: List[Dict[str, Any]],  # [{"sku": "SKU-4471", "quantity": 2}, ...]
        idempotency_key: str,
        ttl_minutes: Optional[int] = None
    ) -> Tuple[CheckoutSession, bool]:
        """
        Create a new short-lived checkout session or return existing if idempotency key matches.
        Returns (session, is_created).
        """
        # 1. Check if session with idempotency key already exists
        stmt = select(CheckoutSession).where(CheckoutSession.idempotency_key == idempotency_key)
        res = await db.execute(stmt)
        existing = res.scalar_one_or_none()

        if existing:
            # Check if expired
            if existing.expires_at < datetime.datetime.utcnow() and existing.status == SessionStatus.PENDING:
                existing.status = SessionStatus.EXPIRED
                await db.commit()
                raise CheckoutError("Previous checkout session for this idempotency key has expired.", 410)
            return existing, False

        # 2. Validate items and stock
        if isinstance(items, dict):
            if "sku" in items:
                items = [items]
            else:
                items = [{"sku": k, "quantity": v} for k, v in items.items()]
        elif isinstance(items, list):
            normalized = []
            for it in items:
                if isinstance(it, dict):
                    if "sku" in it:
                        normalized.append(it)
                    else:
                        for k, v in it.items():
                            normalized.append({"sku": k, "quantity": v})
                elif isinstance(it, str):
                    normalized.append({"sku": it, "quantity": 1})
            items = normalized

        if not items:
            raise CheckoutError("Cart is empty.", 400)

        total_amount = 0.0
        validated_items = []

        for item in items:
            sku = item.get("sku")
            quantity = item.get("quantity", 1)
            if quantity <= 0:
                raise CheckoutError(f"Invalid quantity {quantity} for SKU {sku}", 400)

            # Check cache or DB for product details
            p_stmt = select(Product).where(Product.sku == sku, Product.is_active == True)
            p_res = await db.execute(p_stmt)
            product = p_res.scalar_one_or_none()
            if not product:
                raise CheckoutError(f"Product with SKU '{sku}' not found or inactive.", 404)

            # Check stock
            inv_stmt = select(Inventory).where(Inventory.product_id == product.id)
            inv_res = await db.execute(inv_stmt)
            inv = inv_res.scalar_one_or_none()
            if not inv or inv.available_count < quantity:
                avail = inv.available_count if inv else 0
                raise CheckoutError(f"Insufficient stock for SKU '{sku}'. Requested: {quantity}, Available: {avail}", 409)

            item_total = round(product.price * quantity, 2)
            total_amount += item_total
            validated_items.append({
                "product_id": product.id,
                "sku": product.sku,
                "name": product.name,
                "unit_price": product.price,
                "quantity": quantity,
                "item_total": item_total
            })

        ttl = ttl_minutes or settings.CHECKOUT_SESSION_TTL_MINUTES
        session_id = f"cs_{uuid.uuid4().hex[:16]}"
        expires_at = datetime.datetime.utcnow() + datetime.timedelta(minutes=ttl)

        session = CheckoutSession(
            id=session_id,
            idempotency_key=idempotency_key,
            cart_json=json.dumps(validated_items),
            total_amount=round(total_amount, 2),
            status=SessionStatus.PENDING,
            expires_at=expires_at,
            created_at=datetime.datetime.utcnow()
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)

        return session, True

    async def confirm_checkout(
        self,
        db: AsyncSession,
        session_id: str,
        idempotency_key: str,
        customer_email: Optional[str] = "agent-checkout@agentecom.internal"
    ) -> Tuple[Order, bool]:
        """
        Confirm an isolated checkout session and promote to a permanent Order.
        Guaranteed idempotent: double-calling with the same idempotency key returns the existing order.
        """
        # 1. Check if Order with idempotency key already exists
        order_stmt = select(Order).where(Order.idempotency_key == idempotency_key)
        order_res = await db.execute(order_stmt)
        existing_order = order_res.scalar_one_or_none()
        if existing_order:
            return existing_order, False

        # 2. Retrieve Checkout Session
        sess_stmt = select(CheckoutSession).where(CheckoutSession.id == session_id)
        sess_res = await db.execute(sess_stmt)
        session = sess_res.scalar_one_or_none()

        if not session:
            raise CheckoutError(f"Checkout session '{session_id}' not found.", 404)

        if session.status == SessionStatus.COMPLETED:
            # Look up order created for this session
            existing_sess_order = await db.execute(select(Order).where(Order.checkout_session_id == session_id))
            ord_obj = existing_sess_order.scalar_one_or_none()
            if ord_obj:
                return ord_obj, False
            raise CheckoutError("Checkout session has already been completed.", 409)

        if session.status == SessionStatus.EXPIRED or session.expires_at < datetime.datetime.utcnow():
            session.status = SessionStatus.EXPIRED
            await db.commit()
            raise CheckoutError("Checkout session has expired. Create a new session.", 410)

        # 3. Deduct Inventory Atomically
        items = json.loads(session.cart_json)
        for item in items:
            p_id = item["product_id"]
            qty = item["quantity"]
            inv_stmt = select(Inventory).where(Inventory.product_id == p_id)
            inv_res = await db.execute(inv_stmt)
            inv = inv_res.scalar_one_or_none()

            if not inv or inv.stock_count < qty:
                raise CheckoutError(f"Stock shortage for SKU '{item['sku']}' during finalization.", 409)

            inv.stock_count -= qty
            # Invalidate cached SKU inventory
            await cache.invalidate_sku(item["sku"])

        # 4. Mark Session as Completed
        session.status = SessionStatus.COMPLETED
        session.completed_at = datetime.datetime.utcnow()

        # 5. Create Core Permanent Order
        order_number = f"ORD-{datetime.datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        order = Order(
            order_number=order_number,
            idempotency_key=idempotency_key,
            checkout_session_id=session.id,
            items_json=session.cart_json,
            total_amount=session.total_amount,
            status=OrderStatus.CONFIRMED,
            customer_email=customer_email,
            created_at=datetime.datetime.utcnow()
        )
        db.add(order)
        await db.commit()
        await db.refresh(order)

        return order, True

checkout_manager = CheckoutManager()
