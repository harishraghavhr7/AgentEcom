"""
Catalog Ingestion & Real-Time Synchronization Service for Shopify.
Maps Shopify products and variants into AgentEcom schema and builds
the Hybrid Search (BM25 + Dense vector embeddings) index.
"""

import re
import json
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy import select, delete
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from agentecom.db.database import AsyncSessionLocal
from agentecom.db.models import Product, Inventory
from agentecom.search.hybrid import HybridSearchEngine
from agentecom.tools.commerce import hybrid_engine
from agentecom.core.cache import cache
from agentecom.integrations.shopify.client import ShopifyClient, shopify_client

logger = logging.getLogger("agentecom.shopify_sync")


def strip_html(html_str: Optional[str]) -> str:
    """Strip HTML markup from Shopify product descriptions."""
    if not html_str:
        return ""
    clean = re.sub(r'<[^<]+?>', ' ', html_str)
    return " ".join(clean.split()).strip()


class ShopifyCatalogSync:
    """
    Synchronizes Shopify store products, variants, and stock levels
    into AgentEcom's database and Hybrid Search index.
    """

    def __init__(self, client: Optional[ShopifyClient] = None):
        self.client = client or shopify_client

    def parse_shopify_product_to_records(self, sprod: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Convert a single Shopify product JSON (with its variants)
        into normalized AgentEcom product records.
        """
        records = []
        prod_id = sprod.get("id")
        base_title = sprod.get("title", "Untitled Product")
        desc = strip_html(sprod.get("body_html", ""))
        category = sprod.get("product_type") or "General"
        vendor = sprod.get("vendor", "")
        tags = sprod.get("tags", "")
        if isinstance(tags, str):
            tags_list = [t.strip() for t in tags.split(",") if t.strip()]
        else:
            tags_list = tags or []

        images = [img.get("src") for img in sprod.get("images", []) if img.get("src")]
        image_url = images[0] if images else None

        variants = sprod.get("variants", [])
        if not variants:
            # Fallback for product without explicit variant array
            variants = [{
                "id": prod_id,
                "title": "Default Title",
                "price": sprod.get("price", 0.0),
                "sku": f"SHOPIFY-{prod_id}",
                "inventory_quantity": 10
            }]

        has_multiple_variants = len(variants) > 1

        for v in variants:
            var_id = v.get("id")
            var_title = v.get("title", "")
            
            # Compose display name
            if has_multiple_variants and var_title and var_title != "Default Title":
                name = f"{base_title} - {var_title}"
            else:
                name = base_title

            sku = v.get("sku")
            if not sku or not str(sku).strip():
                sku = f"SPFY-{prod_id}-{var_id}"
            else:
                sku = str(sku).strip().upper()

            try:
                price = float(v.get("price", 0.0))
            except (ValueError, TypeError):
                price = 0.0

            stock = v.get("inventory_quantity", 10)
            if stock is None:
                stock = 10

            attributes = {
                "shopify_product_id": prod_id,
                "shopify_variant_id": var_id,
                "vendor": vendor,
                "tags": tags_list,
                "variant_title": var_title,
                "image_url": image_url,
                "weight": v.get("weight"),
                "weight_unit": v.get("weight_unit")
            }

            records.append({
                "sku": sku,
                "name": name,
                "description": desc or name,
                "category": category,
                "price": price,
                "stock": stock,
                "attributes_json": json.dumps(attributes)
            })

        return records

    async def sync_single_product(self, sprod: Dict[str, Any]) -> List[str]:
        """
        Sync or update a single product from Shopify into DB & invalidate cache.
        Returns list of affected SKUs.
        """
        records = self.parse_shopify_product_to_records(sprod)
        if not records:
            return []

        affected_skus = []
        async with AsyncSessionLocal() as db:
            for rec in records:
                sku = rec["sku"]
                affected_skus.append(sku)

                # Upsert Product
                p_stmt = select(Product).where(Product.sku == sku)
                p_res = await db.execute(p_stmt)
                prod = p_res.scalar_one_or_none()

                if prod:
                    prod.name = rec["name"]
                    prod.description = rec["description"]
                    prod.category = rec["category"]
                    prod.price = rec["price"]
                    prod.attributes_json = rec["attributes_json"]
                    prod.is_active = True
                else:
                    prod = Product(
                        sku=sku,
                        name=rec["name"],
                        description=rec["description"],
                        category=rec["category"],
                        price=rec["price"],
                        attributes_json=rec["attributes_json"],
                        is_active=True
                    )
                    db.add(prod)
                    await db.flush()

                # Upsert Inventory
                inv_stmt = select(Inventory).where(Inventory.product_id == prod.id)
                inv_res = await db.execute(inv_stmt)
                inv = inv_res.scalar_one_or_none()

                if inv:
                    inv.stock_count = rec["stock"]
                else:
                    inv = Inventory(
                        product_id=prod.id,
                        stock_count=rec["stock"],
                        reserved_count=0
                    )
                    db.add(inv)

            await db.commit()

        # Invalidate cache for affected SKUs
        for sku in affected_skus:
            await cache.invalidate_sku(sku)
        await cache.invalidate_by_tag("search_results")

        # Reload in-memory hybrid search index
        await self.reload_hybrid_index()
        return affected_skus

    async def sync_catalog(self, limit: int = 100) -> Dict[str, Any]:
        """
        Fetch store products from Shopify Admin API and ingest into database.
        """
        logger.info(f"Starting Shopify catalog sync from {self.client.store_domain} (limit={limit})")
        products = await self.client.fetch_products(limit=limit)

        total_synced_skus = []
        for sprod in products:
            synced = await self.sync_single_product(sprod)
            total_synced_skus.extend(synced)

        return {
            "store_domain": self.client.store_domain,
            "shopify_products_fetched": len(products),
            "total_skus_indexed": len(total_synced_skus),
            "skus": total_synced_skus
        }

    async def reload_hybrid_index(self) -> int:
        """
        Load all active products from DB and refresh the BM25 + Dense vector search index.
        """
        async with AsyncSessionLocal() as db:
            stmt = select(Product).where(Product.is_active == True)
            res = await db.execute(stmt)
            prods = res.scalars().all()

            corpus_docs = []
            for p in prods:
                corpus_docs.append({
                    "id": p.id,
                    "sku": p.sku,
                    "name": p.name,
                    "description": p.description,
                    "category": p.category,
                    "price": p.price,
                    "attributes_json": p.attributes_json or "{}"
                })

            if corpus_docs:
                hybrid_engine.build_index(corpus_docs)
            return len(corpus_docs)


shopify_sync = ShopifyCatalogSync()
