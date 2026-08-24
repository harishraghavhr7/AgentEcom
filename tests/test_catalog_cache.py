import pytest
from agentecom.core.cache import cache
from agentecom.tools.commerce import tool_get_product

@pytest.mark.asyncio
async def test_cache_hit_and_latency(test_db_session):
    sku = "SKU-4471"
    
    # 1. First read -> Cache Miss (hits DB)
    res1 = await tool_get_product(sku)
    assert res1.get("cached") is False
    assert res1["product"]["sku"] == sku
    assert res1["product"]["price"] == 58.50
    assert cache.metrics.misses >= 1

    # 2. Second read -> Cache Hit (sub-millisecond)
    res2 = await tool_get_product(sku)
    assert res2.get("cached") is True
    assert res2["product"]["sku"] == sku
    assert res2["latency_ms"] < 10.0  # Typically < 1ms
    assert cache.metrics.hits >= 1

@pytest.mark.asyncio
async def test_cache_metrics_tracking(test_db_session):
    await cache.clear()
    
    # Miss
    await tool_get_product("SKU-4471")
    # Hit
    await tool_get_product("SKU-4471")
    # Hit
    await tool_get_product("SKU-4471")
    
    metrics = cache.metrics.to_dict()
    assert metrics["hits"] == 2
    assert metrics["misses"] == 1
    assert metrics["hit_rate_pct"] > 60.0
