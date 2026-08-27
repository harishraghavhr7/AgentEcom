"""
Hybrid Search Engine (BM25 Lexical + Dense Vector + Reciprocal Rank Fusion).
Achieves significantly higher recall than pure lexical or pure vector search:
- BM25 wins on exact matches like product codes (SKUs) and named entities.
- Dense vector search catches semantic/paraphrased queries.
- Reciprocal Rank Fusion (RRF) harmonizes both ranking signals.
"""

import time
from typing import List, Dict, Any, Optional
from agentecom.config import settings
from agentecom.search.bm25_retriever import BM25Retriever
from agentecom.search.dense_retriever import DenseRetriever

class HybridSearchEngine:
    def __init__(self, rrf_k: int = None, bm25_weight: float = None, dense_weight: float = None):
        self.rrf_k = rrf_k or settings.HYBRID_RRF_K
        self.bm25_weight = bm25_weight or settings.BM25_WEIGHT
        self.dense_weight = dense_weight or settings.DENSE_WEIGHT
        
        self.bm25_retriever = BM25Retriever()
        self.dense_retriever = DenseRetriever()
        self.corpus_docs: List[Dict[str, Any]] = []
        self.is_indexed = False

    def build_index(self, products: List[Dict[str, Any]], precomputed_embeddings: Optional[List[List[float]]] = None):
        """Build both sparse BM25 index and dense vector index."""
        self.corpus_docs = products
        self.bm25_retriever.build_index(products)
        self.dense_retriever.build_index(products, precomputed_embeddings)
        self.is_indexed = True

    def _apply_filters(
        self,
        product: Dict[str, Any],
        category: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None
    ) -> bool:
        if category and product.get("category", "").lower() != category.lower():
            return False
        price = float(product.get("price", 0.0))
        if min_price is not None:
            try:
                if price < float(min_price):
                    return False
            except (ValueError, TypeError):
                pass
        if max_price is not None:
            try:
                if price > float(max_price):
                    return False
            except (ValueError, TypeError):
                pass
        return True

    def search_bm25_only(
        self,
        query: str,
        top_k: int = 10,
        category: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        try:
            top_k = int(top_k) if top_k is not None else 10
        except (ValueError, TypeError):
            top_k = 10
        if top_k <= 0:
            return []

        raw_results = self.bm25_retriever.search(query, top_k=int(top_k * 2))
        filtered = []
        for prod, score in raw_results:
            if self._apply_filters(prod, category, min_price, max_price):
                prod_copy = dict(prod)
                prod_copy["_score"] = score
                prod_copy["_retrieval_method"] = "bm25"
                filtered.append(prod_copy)
                if len(filtered) >= top_k:
                    break
        return filtered

    def search_dense_only(
        self,
        query: str,
        top_k: int = 10,
        category: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        try:
            top_k = int(top_k) if top_k is not None else 10
        except (ValueError, TypeError):
            top_k = 10
        if top_k <= 0:
            return []

        raw_results = self.dense_retriever.search(query, top_k=int(top_k * 2))
        filtered = []
        for prod, score in raw_results:
            if self._apply_filters(prod, category, min_price, max_price):
                prod_copy = dict(prod)
                prod_copy["_score"] = score
                prod_copy["_retrieval_method"] = "dense"
                filtered.append(prod_copy)
                if len(filtered) >= top_k:
                    break
        return filtered

    def search_hybrid(
        self,
        query: str,
        top_k: int = 10,
        category: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute BM25 and Dense vector retrieval in parallel / sequence,
        then combine ranks via Reciprocal Rank Fusion (RRF).
        Handles broad/wildcard queries by returning catalog products.
        """
        try:
            top_k = int(top_k) if top_k is not None else 10
        except (ValueError, TypeError):
            top_k = 10
        if top_k <= 0:
            return []

        start_time = time.perf_counter()
        clean_q = query.strip()

        # Handle broad catalogue/wildcard browsing
        if clean_q in ["*", "", "all", "products", "items", "catalog", "everything"]:
            results = []
            for prod in self.corpus_docs:
                if self._apply_filters(prod, category, min_price, max_price):
                    prod_copy = dict(prod)
                    prod_copy["_rrf_score"] = 0.01667
                    prod_copy["_bm25_rank"] = 1
                    prod_copy["_dense_rank"] = 1
                    prod_copy["_retrieval_method"] = "catalog_browse"
                    results.append(prod_copy)
                    if len(results) >= top_k:
                        break
            return results

        # Retrieve candidates from both systems (oversample to allow rank blending)
        bm25_candidates = self.bm25_retriever.search(clean_q, top_k=int(top_k * 3))
        dense_candidates = self.dense_retriever.search(clean_q, top_k=int(top_k * 3))

        # SKU Map for RRF scoring
        sku_scores: Dict[str, Dict[str, Any]] = {}

        # 1. Process BM25 ranks
        for rank, (prod, score) in enumerate(bm25_candidates, start=1):
            if not self._apply_filters(prod, category, min_price, max_price):
                continue
            sku = prod["sku"]
            if sku not in sku_scores:
                sku_scores[sku] = {
                    "product": prod,
                    "bm25_rank": rank,
                    "bm25_raw_score": score,
                    "dense_rank": None,
                    "dense_raw_score": None,
                    "rrf_score": 0.0
                }
            else:
                sku_scores[sku]["bm25_rank"] = rank
                sku_scores[sku]["bm25_raw_score"] = score
            
            # Add RRF contribution from BM25
            sku_scores[sku]["rrf_score"] += self.bm25_weight * (1.0 / (self.rrf_k + rank))

        # 2. Process Dense ranks
        for rank, (prod, score) in enumerate(dense_candidates, start=1):
            if not self._apply_filters(prod, category, min_price, max_price):
                continue
            sku = prod["sku"]
            if sku not in sku_scores:
                sku_scores[sku] = {
                    "product": prod,
                    "bm25_rank": None,
                    "bm25_raw_score": None,
                    "dense_rank": rank,
                    "dense_raw_score": score,
                    "rrf_score": 0.0
                }
            else:
                sku_scores[sku]["dense_rank"] = rank
                sku_scores[sku]["dense_raw_score"] = score

            # Add RRF contribution from Dense
            sku_scores[sku]["rrf_score"] += self.dense_weight * (1.0 / (self.rrf_k + rank))

        # If no strict matches found, fallback to dense semantic matches or catalog
        if not sku_scores and self.corpus_docs:
            for prod in self.corpus_docs[:top_k]:
                if self._apply_filters(prod, category, min_price, max_price):
                    prod_copy = dict(prod)
                    prod_copy["_rrf_score"] = 0.005
                    prod_copy["_bm25_rank"] = None
                    prod_copy["_dense_rank"] = None
                    prod_copy["_retrieval_method"] = "fallback"
                    return [prod_copy]

        # Sort by total RRF score descending
        sorted_results = sorted(sku_scores.values(), key=lambda x: x["rrf_score"], reverse=True)

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        output = []
        for item in sorted_results[:top_k]:
            prod_out = dict(item["product"])
            prod_out["_rrf_score"] = round(item["rrf_score"], 6)
            prod_out["_bm25_rank"] = item["bm25_rank"]
            prod_out["_dense_rank"] = item["dense_rank"]
            prod_out["_retrieval_method"] = "hybrid_rrf"
            output.append(prod_out)

        return output

# Global singleton
hybrid_engine = HybridSearchEngine()
