from typing import Optional
from fastapi import APIRouter, Query
from agentecom.tools.commerce import tool_search_products
from agentecom.search.hybrid import hybrid_engine

router = APIRouter(prefix="/search", tags=["Hybrid Search"])

@router.get("")
async def search_catalog(
    q: str = Query(..., description="Search query string"),
    category: Optional[str] = Query(None, description="Filter by category"),
    min_price: Optional[float] = Query(None, ge=0, description="Minimum price filter"),
    max_price: Optional[float] = Query(None, ge=0, description="Maximum price filter"),
    limit: int = Query(5, ge=1, le=50, description="Number of results"),
    mode: str = Query("hybrid", enum=["hybrid", "bm25", "dense"], description="Retrieval mode")
):
    """
    Search product catalog with Hybrid Search (BM25 + Dense + RRF) or isolated modes for eval.
    """
    if mode == "hybrid":
        return await tool_search_products(
            query=q,
            category=category,
            min_price=min_price,
            max_price=max_price,
            limit=limit
        )
    elif mode == "bm25":
        results = hybrid_engine.search_bm25_only(
            query=q,
            top_k=limit,
            category=category,
            min_price=min_price,
            max_price=max_price
        )
        return {"query": q, "mode": "bm25", "results_count": len(results), "products": results}
    elif mode == "dense":
        results = hybrid_engine.search_dense_only(
            query=q,
            top_k=limit,
            category=category,
            min_price=min_price,
            max_price=max_price
        )
        return {"query": q, "mode": "dense", "results_count": len(results), "products": results}
