import pytest
from agentecom.core.cache import cache
from agentecom.tools.commerce import tool_get_product
from agentecom.db.models import Product
from agentecom.db.database import AsyncSessionLocal
from sqlalchemy import select

@pytest.mark.asyncio
async def test_webhook_invalidation_by_sku(test_db_session):
    sku = "SKU-4471"
    
    # 1. Warm cache
    res1 = await tool_get_product(sku)
    assert res1["cached"] is False
    
    res2 = await tool_get_product(sku)
    assert res2["cached"] is True
    assert res2["product"]["price"] == 58.50

    # 2. Simulate Merchant updating price in DB
    async with AsyncSessionLocal() as session:
        stmt = select(Product).where(Product.sku == sku)
        p_obj = (await session.execute(stmt)).scalar_one()
        p_obj.price = 65.00
        await session.commit()

    # 3. Trigger webhook invalidation for that SKU
    invalidated_count = await cache.invalidate_sku(sku)
    assert invalidated_count >= 1

    # 4. Next agent read should miss cache and fetch updated price without TTL wait
    res3 = await tool_get_product(sku)
    assert res3["cached"] is False
    assert res3["product"]["price"] == 65.00

    # 5. Subsequent read is cached with new price
    res4 = await tool_get_product(sku)
    assert res4["cached"] is True
    assert res4["product"]["price"] == 65.00
