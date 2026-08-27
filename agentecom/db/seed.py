import json
import asyncio
from sqlalchemy import select, delete
from agentecom.db.database import AsyncSessionLocal, init_db
from agentecom.db.models import Product, Inventory, CheckoutSession, Order, ProductEmbedding
from agentecom.core.cache import cache

from agentecom.db.catalog_data import CATALOG_PRODUCTS

SAMPLE_PRODUCTS = CATALOG_PRODUCTS


async def seed_database(force_reset: bool = False):
    await init_db()
    async with AsyncSessionLocal() as session:
        if force_reset:
            await session.execute(delete(Inventory))
            await session.execute(delete(ProductEmbedding))
            await session.execute(delete(CheckoutSession))
            await session.execute(delete(Order))
            await session.execute(delete(Product))
            await session.commit()
        else:
            result = await session.execute(select(Product))
            existing = result.scalars().all()
            if existing:
                return

        for p_data in SAMPLE_PRODUCTS:
            prod = Product(
                sku=p_data["sku"],
                name=p_data["name"],
                description=p_data["description"],
                category=p_data["category"],
                price=p_data["price"],
                attributes_json=json.dumps(p_data.get("attributes", {}))
            )
            session.add(prod)
            await session.flush()

            inv = Inventory(
                product_id=prod.id,
                stock_count=p_data["stock"],
                reserved_count=0
            )
            session.add(inv)

        await session.commit()
        await cache.clear()

if __name__ == "__main__":
    asyncio.run(seed_database(force_reset=True))
