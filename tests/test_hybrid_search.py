import pytest
from agentecom.search.hybrid import hybrid_engine

@pytest.mark.asyncio
async def test_exact_sku_search():
    # BM25 / exact SKU code search
    results = hybrid_engine.search_hybrid("SKU-4471", top_k=5)
    assert len(results) > 0
    assert results[0]["sku"] == "SKU-4471"
    assert results[0]["_bm25_rank"] == 1

@pytest.mark.asyncio
async def test_semantic_paraphrased_search():
    # Natural language query with synonyms
    results = hybrid_engine.search_hybrid("cozy oversized sweater for winter days", top_k=5)
    assert len(results) > 0
    # Top result should be the sweater SKU-4471
    assert results[0]["sku"] == "SKU-4471"

@pytest.mark.asyncio
async def test_technical_feature_search():
    # Search for Sony noise canceling headphones
    results = hybrid_engine.search_hybrid("wireless noise canceling headphones 30 hour battery", top_k=5)
    assert len(results) > 0
    assert results[0]["sku"] == "SONY-WH1000XM5"

@pytest.mark.asyncio
async def test_price_filtering():
    results = hybrid_engine.search_hybrid("sweater", max_price=50.0, top_k=5)
    for p in results:
        assert p["price"] <= 50.0
