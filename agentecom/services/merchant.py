"""
Merchant & Retail Store Owner Service for AgentEcom.
Provides high-level catalog, inventory, and pricing management operations
for store personnel, merchant dashboards, and administrative MCP tooling.

When products or inventory are modified:
- Changes are persisted to the database.
- Targeted cache keys and reverse index tags are invalidated.
- Background asynchronous vector & lexical re-indexing is triggered.
"""

import json
import uuid
import datetime
from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field
from sqlalchemy import select, func, update, delete
from sqlalchemy.orm import selectinload

from agentecom.db.database import AsyncSessionLocal
from agentecom.db.models import Product, Inventory, ProductEmbedding
from agentecom.core.cache import cache
from agentecom.search.worker import index_worker
from agentecom.search.hybrid import hybrid_engine


class ProductCreateSchema(BaseModel):
    name: str = Field(..., min_length=2, max_length=255, description="Product title / name")
    category: str = Field(..., min_length=2, max_length=128, description="Product category (e.g. 'Apparel & Fashion', 'Electronics')")
    price: float = Field(..., gt=0, description="Unit price in USD")
    stock: int = Field(default=0, ge=0, description="Initial stock quantity")
    sku: Optional[str] = Field(None, max_length=64, description="Unique SKU code. Auto-generated if omitted.")
    description: Optional[str] = Field("", description="Detailed product description")
    attributes: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Custom specifications (size, color, brand, material, tags)")
    is_active: Optional[bool] = Field(True, description="Whether product is active for sale")


class ProductUpdateSchema(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    category: Optional[str] = Field(None, min_length=2, max_length=128)
    price: Optional[float] = Field(None, gt=0)
    description: Optional[str] = None
    attributes: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class StockAdjustSchema(BaseModel):
    quantity: int = Field(..., description="Stock quantity. If mode is 'set', becomes new stock. If mode is 'adjust', adds/subtracts.")
    mode: str = Field("set", description="'set' to overwrite, 'adjust' to add or subtract")
    reason: Optional[str] = Field(None, description="Optional restock or audit reason")


class BulkStockItem(BaseModel):
    sku: str
    quantity: int
    mode: str = "set"


class MerchantService:
    """
    Core management service for retail store personnel to manage
    inventory, pricing, and product specifications.
    """

    @staticmethod
    def _generate_sku(name: str, category: str) -> str:
        """Generate a clean unique SKU if merchant didn't provide one."""
        prefix = "".join([c for c in category if c.isalnum()][:3]).upper() or "GEN"
        random_suffix = uuid.uuid4().hex[:6].upper()
        return f"SKU-{prefix}-{random_suffix}"

    async def add_product(self, data: ProductCreateSchema) -> Dict[str, Any]:
        """
        Create a new product with price, stock, and attributes.
        Immediately updates DB, invalidates cache, and enqueues vector indexing.
        """
        sku = (data.sku or "").strip()
        if not sku:
            sku = self._generate_sku(data.name, data.category)
        else:
            sku = sku.upper()

        async with AsyncSessionLocal() as session:
            # Check for duplicate SKU
            existing = await session.execute(select(Product).where(Product.sku == sku))
            if existing.scalar_one_or_none():
                raise ValueError(f"Product with SKU '{sku}' already exists.")

            attributes_dict = data.attributes or {}
            product = Product(
                sku=sku,
                name=data.name.strip(),
                description=data.description.strip() if data.description else f"{data.name} in {data.category}",
                category=data.category.strip(),
                price=round(float(data.price), 2),
                attributes_json=json.dumps(attributes_dict),
                is_active=bool(data.is_active)
            )
            session.add(product)
            await session.flush()

            inventory = Inventory(
                product_id=product.id,
                stock_count=max(0, int(data.stock)),
                reserved_count=0
            )
            session.add(inventory)
            await session.commit()
            await session.refresh(product)

            # Invalidate relevant caches
            await cache.invalidate_sku(sku)
            await cache.invalidate_category(product.category)
            await cache.invalidate_by_tag("gateway:categories_summary")

            # Asynchronously index product for BM25 and Dense Vector search
            try:
                await index_worker.enqueue_job("INDEX_PRODUCT", {"product_id": product.id})
            except Exception:
                pass

            # Update hybrid engine in-memory if initialized
            if hybrid_engine.is_indexed:
                new_doc = {
                    "id": product.id,
                    "sku": product.sku,
                    "name": product.name,
                    "description": product.description,
                    "category": product.category,
                    "price": product.price,
                    "attributes_json": product.attributes_json
                }
                hybrid_engine.corpus_docs.append(new_doc)
                hybrid_engine.bm25_retriever.build_index(hybrid_engine.corpus_docs)

            return {
                "success": True,
                "message": f"Product '{product.name}' created successfully with SKU {product.sku}.",
                "product": {
                    "id": product.id,
                    "sku": product.sku,
                    "name": product.name,
                    "description": product.description,
                    "category": product.category,
                    "price": product.price,
                    "stock": inventory.stock_count,
                    "available_count": inventory.available_count,
                    "attributes": attributes_dict,
                    "is_active": product.is_active,
                    "created_at": product.created_at.isoformat() if product.created_at else None
                }
            }

    async def update_product(self, sku: str, data: ProductUpdateSchema) -> Dict[str, Any]:
        """
        Update product information (price, name, description, category, attributes, is_active).
        """
        sku_clean = sku.strip().upper()
        async with AsyncSessionLocal() as session:
            stmt = select(Product).options(selectinload(Product.inventory)).where(Product.sku == sku_clean)
            res = await session.execute(stmt)
            product = res.scalar_one_or_none()
            if not product:
                raise KeyError(f"Product with SKU '{sku_clean}' not found.")

            old_category = product.category
            if data.name is not None:
                product.name = data.name.strip()
            if data.category is not None:
                product.category = data.category.strip()
            if data.price is not None:
                product.price = round(float(data.price), 2)
            if data.description is not None:
                product.description = data.description.strip()
            if data.attributes is not None:
                product.attributes_json = json.dumps(data.attributes)
            if data.is_active is not None:
                product.is_active = bool(data.is_active)

            product.updated_at = datetime.datetime.utcnow()
            await session.commit()
            await session.refresh(product)

            # Invalidate cache
            await cache.invalidate_sku(sku_clean)
            if old_category != product.category:
                await cache.invalidate_category(old_category)
            await cache.invalidate_category(product.category)
            await cache.invalidate_by_tag("gateway:categories_summary")

            # Trigger indexing
            try:
                await index_worker.enqueue_job("INDEX_PRODUCT", {"product_id": product.id})
            except Exception:
                pass

            stock_val = product.inventory.stock_count if product.inventory else 0
            available_val = product.inventory.available_count if product.inventory else 0

            return {
                "success": True,
                "message": f"Product '{product.sku}' updated successfully.",
                "product": {
                    "id": product.id,
                    "sku": product.sku,
                    "name": product.name,
                    "description": product.description,
                    "category": product.category,
                    "price": product.price,
                    "stock": stock_val,
                    "available_count": available_val,
                    "attributes": json.loads(product.attributes_json) if product.attributes_json else {},
                    "is_active": product.is_active,
                    "updated_at": product.updated_at.isoformat() if product.updated_at else None
                }
            }

    async def update_stock(self, sku: str, quantity: int, mode: str = "set", reason: Optional[str] = None) -> Dict[str, Any]:
        """
        Adjust or set stock count for a specific SKU.
        - mode='set': Overwrite stock count to given quantity (>= 0).
        - mode='adjust': Add quantity (positive or negative delta) to current stock.
        """
        sku_clean = sku.strip().upper()
        async with AsyncSessionLocal() as session:
            stmt = select(Product).options(selectinload(Product.inventory)).where(Product.sku == sku_clean)
            res = await session.execute(stmt)
            product = res.scalar_one_or_none()
            if not product:
                raise KeyError(f"Product with SKU '{sku_clean}' not found.")

            inv = product.inventory
            if not inv:
                inv = Inventory(product_id=product.id, stock_count=0, reserved_count=0)
                session.add(inv)

            old_stock = inv.stock_count
            if mode == "set":
                if quantity < 0:
                    raise ValueError("Stock count cannot be negative.")
                inv.stock_count = int(quantity)
            elif mode == "adjust":
                new_count = old_stock + int(quantity)
                if new_count < 0:
                    raise ValueError(f"Cannot adjust stock by {quantity}. Current stock is {old_stock}, result would be negative.")
                inv.stock_count = new_count
            else:
                raise ValueError(f"Invalid mode '{mode}'. Use 'set' or 'adjust'.")

            inv.updated_at = datetime.datetime.utcnow()
            await session.commit()
            await session.refresh(inv)

            await cache.invalidate_sku(sku_clean)

            return {
                "success": True,
                "sku": sku_clean,
                "product_name": product.name,
                "previous_stock": old_stock,
                "current_stock": inv.stock_count,
                "reserved_count": inv.reserved_count,
                "available_count": inv.available_count,
                "mode": mode,
                "reason": reason
            }

    async def bulk_update_stock(self, items: List[BulkStockItem]) -> Dict[str, Any]:
        """
        Batch update stock levels for multiple SKUs.
        """
        results = []
        errors = []

        for item in items:
            try:
                res = await self.update_stock(sku=item.sku, quantity=item.quantity, mode=item.mode)
                results.append(res)
            except Exception as e:
                errors.append({"sku": item.sku, "error": str(e)})

        return {
            "success": len(errors) == 0,
            "updated_count": len(results),
            "errors_count": len(errors),
            "results": results,
            "errors": errors
        }

    async def get_product(self, sku: str) -> Dict[str, Any]:
        """
        Get complete product and inventory details by SKU.
        """
        sku_clean = sku.strip().upper()
        async with AsyncSessionLocal() as session:
            stmt = select(Product).options(selectinload(Product.inventory)).where(Product.sku == sku_clean)
            res = await session.execute(stmt)
            product = res.scalar_one_or_none()
            if not product:
                raise KeyError(f"Product with SKU '{sku_clean}' not found.")

            inv = product.inventory
            attributes = json.loads(product.attributes_json) if product.attributes_json else {}

            return {
                "id": product.id,
                "sku": product.sku,
                "name": product.name,
                "description": product.description,
                "category": product.category,
                "price": product.price,
                "stock_count": inv.stock_count if inv else 0,
                "reserved_count": inv.reserved_count if inv else 0,
                "available_count": inv.available_count if inv else 0,
                "attributes": attributes,
                "is_active": product.is_active,
                "created_at": product.created_at.isoformat() if product.created_at else None,
                "updated_at": product.updated_at.isoformat() if product.updated_at else None
            }

    async def list_products(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        stock_status: Optional[str] = None,  # 'all', 'in_stock', 'low_stock', 'out_of_stock'
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        List store catalog products with real-time stock levels, search, and filtering.
        """
        async with AsyncSessionLocal() as session:
            stmt = select(Product).options(selectinload(Product.inventory))

            if is_active is not None:
                stmt = stmt.where(Product.is_active == is_active)

            if category and category.lower() != "all":
                stmt = stmt.where(Product.category == category)

            if query:
                q_like = f"%{query.strip()}%"
                stmt = stmt.where(
                    (Product.name.ilike(q_like)) |
                    (Product.sku.ilike(q_like)) |
                    (Product.description.ilike(q_like))
                )

            stmt = stmt.order_by(Product.id.desc())
            res = await session.execute(stmt)
            all_matching = res.scalars().all()

            # Filter by stock status in memory if requested
            filtered = []
            for p in all_matching:
                inv = p.inventory
                stock = inv.stock_count if inv else 0
                avail = inv.available_count if inv else 0

                if stock_status == "out_of_stock" and avail > 0:
                    continue
                if stock_status == "low_stock" and (avail <= 0 or avail > 5):
                    continue
                if stock_status == "in_stock" and avail <= 0:
                    continue

                attrs = json.loads(p.attributes_json) if p.attributes_json else {}
                filtered.append({
                    "id": p.id,
                    "sku": p.sku,
                    "name": p.name,
                    "description": p.description,
                    "category": p.category,
                    "price": p.price,
                    "stock_count": stock,
                    "reserved_count": inv.reserved_count if inv else 0,
                    "available_count": avail,
                    "attributes": attrs,
                    "is_active": p.is_active,
                    "created_at": p.created_at.isoformat() if p.created_at else None
                })

            total = len(filtered)
            paginated = filtered[skip : skip + limit]

            return {
                "total": total,
                "skip": skip,
                "limit": limit,
                "products": paginated
            }

    async def delete_product(self, sku: str, soft_delete: bool = True) -> Dict[str, Any]:
        """
        Delete or soft-delete (deactivate) a product.
        """
        sku_clean = sku.strip().upper()
        async with AsyncSessionLocal() as session:
            stmt = select(Product).where(Product.sku == sku_clean)
            res = await session.execute(stmt)
            product = res.scalar_one_or_none()
            if not product:
                raise KeyError(f"Product with SKU '{sku_clean}' not found.")

            if soft_delete:
                product.is_active = False
                product.updated_at = datetime.datetime.utcnow()
                await session.commit()
                msg = f"Product '{sku_clean}' deactivated (soft deleted)."
            else:
                await session.delete(product)
                await session.commit()
                msg = f"Product '{sku_clean}' permanently removed from catalog."

            await cache.invalidate_sku(sku_clean)
            await cache.invalidate_category(product.category)
            await cache.invalidate_by_tag("gateway:categories_summary")

            try:
                await index_worker.enqueue_job("DELETE_PRODUCT", {"sku": sku_clean})
            except Exception:
                pass

            # Update in-memory corpus if needed
            if hybrid_engine.is_indexed:
                hybrid_engine.corpus_docs = [d for d in hybrid_engine.corpus_docs if d.get("sku") != sku_clean]
                hybrid_engine.bm25_retriever.build_index(hybrid_engine.corpus_docs)

            return {
                "success": True,
                "sku": sku_clean,
                "message": msg,
                "soft_delete": soft_delete
            }

    async def get_store_metrics(self) -> Dict[str, Any]:
        """
        Retrieve catalog and inventory KPIs for store owners:
        - Total products
        - Total stock quantity
        - Low stock items (< 5)
        - Out of stock items
        - Total inventory retail value ($)
        - Categories list
        """
        async with AsyncSessionLocal() as session:
            # Query products with inventory
            stmt = select(Product, Inventory).join(Inventory, Product.id == Inventory.product_id)
            res = await session.execute(stmt)
            rows = res.all()

            total_products = len(rows)
            active_products = sum(1 for p, _ in rows if p.is_active)
            total_stock_units = sum(inv.stock_count for _, inv in rows)
            total_valuation = sum(p.price * inv.stock_count for p, inv in rows if p.is_active)
            out_of_stock_count = sum(1 for _, inv in rows if inv.available_count == 0)
            low_stock_count = sum(1 for _, inv in rows if 0 < inv.available_count <= 5)

            categories = {}
            for p, inv in rows:
                if p.category not in categories:
                    categories[p.category] = {"count": 0, "stock": 0}
                categories[p.category]["count"] += 1
                categories[p.category]["stock"] += inv.stock_count

            return {
                "total_products": total_products,
                "active_products": active_products,
                "total_stock_units": total_stock_units,
                "total_valuation": round(total_valuation, 2),
                "out_of_stock_count": out_of_stock_count,
                "low_stock_count": low_stock_count,
                "categories": categories
            }


merchant_service = MerchantService()
