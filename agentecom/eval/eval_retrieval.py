"""
Agent Query Retrieval Quality & Latency Benchmark.
Computes Recall@1, Recall@3, Recall@5, MRR (Mean Reciprocal Rank),
and Latency percentiles across BM25, Dense Vector, and Hybrid RRF.
"""

import time
import statistics
import asyncio
from typing import List, Dict, Any, Tuple
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from agentecom.eval.dataset import EVAL_QUERIES
from agentecom.search.hybrid import hybrid_engine
from agentecom.db.seed import SAMPLE_PRODUCTS

def calculate_metrics(results_per_query: List[Dict[str, Any]], k_values: List[int] = [1, 3, 5]) -> Dict[str, Any]:
    total = len(results_per_query)
    if total == 0:
        return {}

    recalls = {k: 0 for k in k_values}
    reciprocal_ranks = []
    latencies = []

    for item in results_per_query:
        target_sku = item["expected_sku"]
        retrieved_skus = [p["sku"] for p in item["retrieved_products"]]
        latencies.append(item["latency_ms"])

        # Check rank of expected SKU
        try:
            rank = retrieved_skus.index(target_sku) + 1
            reciprocal_ranks.append(1.0 / rank)
        except ValueError:
            rank = None
            reciprocal_ranks.append(0.0)

        for k in k_values:
            if rank is not None and rank <= k:
                recalls[k] += 1

    recall_rates = {f"Recall@{k}": round((recalls[k] / total) * 100, 2) for k in k_values}
    mrr = round(statistics.mean(reciprocal_ranks), 4)

    return {
        **recall_rates,
        "MRR": mrr,
        "p50_latency_ms": round(statistics.median(latencies), 3),
        "p95_latency_ms": round(statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else max(latencies), 3),
        "avg_latency_ms": round(statistics.mean(latencies), 3)
    }

def run_retrieval_benchmark():
    console = Console()
    console.print(Panel.fit(
        "[bold cyan]AgentEcom Retrieval Evaluation Suite[/bold cyan]\n"
        "[dim]Benchmarking Sparse Lexical (BM25) vs Dense Vector vs Hybrid Search (BM25 + Dense RRF)[/dim]",
        border_style="cyan"
    ))

    # Initialize index with sample products
    prod_dicts = [
        {
            "id": i + 1,
            "sku": p["sku"],
            "name": p["name"],
            "description": p["description"],
            "category": p["category"],
            "price": p["price"],
            "attributes_json": str(p.get("attributes", {}))
        }
        for i, p in enumerate(SAMPLE_PRODUCTS)
    ]
    hybrid_engine.build_index(prod_dicts)

    modes = ["bm25", "dense", "hybrid"]
    all_results: Dict[str, Dict[str, Any]] = {}
    query_breakdown: List[Dict[str, Any]] = []

    for mode in modes:
        mode_records = []
        for eq in EVAL_QUERIES:
            q = eq["query"]
            target = eq["expected_sku"]
            
            start = time.perf_counter()
            if mode == "bm25":
                products = hybrid_engine.search_bm25_only(q, top_k=5)
            elif mode == "dense":
                products = hybrid_engine.search_dense_only(q, top_k=5)
            else:
                products = hybrid_engine.search_hybrid(q, top_k=5)
            elapsed_ms = (time.perf_counter() - start) * 1000

            mode_records.append({
                "query": q,
                "expected_sku": target,
                "category_type": eq["category_type"],
                "retrieved_products": products,
                "latency_ms": elapsed_ms
            })

        metrics = calculate_metrics(mode_records, k_values=[1, 3, 5])
        all_results[mode] = metrics

    # Print Summary Table
    table = Table(title="Retrieval Performance & Quality Comparison", show_header=True, header_style="bold magenta")
    table.add_column("Retrieval Architecture", style="bold")
    table.add_column("Recall@1 (%)", justify="right")
    table.add_column("Recall@3 (%)", justify="right")
    table.add_column("Recall@5 (%)", justify="right")
    table.add_column("MRR (Score)", justify="right")
    table.add_column("Avg Latency (ms)", justify="right")
    table.add_column("P50 Latency (ms)", justify="right")

    mode_labels = {
        "bm25": "1. Sparse BM25 (Lexical Only)",
        "dense": "2. Dense Vector (Semantic Only)",
        "hybrid": "3. Hybrid RRF (BM25 + Dense)"
    }

    for mode in modes:
        m = all_results[mode]
        table.add_row(
            mode_labels[mode],
            f"{m['Recall@1']}%",
            f"{m['Recall@3']}%",
            f"{m['Recall@5']}%",
            f"{m['MRR']}",
            f"{m['avg_latency_ms']} ms",
            f"{m['p50_latency_ms']} ms"
        )

    console.print(table)

    # Detailed per-query breakdown for hybrid search
    breakdown_table = Table(title="Sample Query Retrieval Tracing (Hybrid RRF)", show_header=True, header_style="bold green")
    breakdown_table.add_column("Query Type", style="cyan")
    breakdown_table.add_column("Agent Query", style="white")
    breakdown_table.add_column("Target SKU", style="yellow")
    breakdown_table.add_column("Top Match SKU", style="bold green")
    breakdown_table.add_column("Hit Rank", justify="center")

    for eq in EVAL_QUERIES:
        products = hybrid_engine.search_hybrid(eq["query"], top_k=5)
        top_sku = products[0]["sku"] if products else "NONE"
        retrieved_skus = [p["sku"] for p in products]
        try:
            rank_str = f"#{retrieved_skus.index(eq['expected_sku']) + 1}"
        except ValueError:
            rank_str = "[red]MISS[/red]"

        breakdown_table.add_row(
            eq["category_type"],
            eq["query"][:45] + ("..." if len(eq["query"]) > 45 else ""),
            eq["expected_sku"],
            top_sku,
            rank_str
        )

    console.print(breakdown_table)
    return all_results

if __name__ == "__main__":
    run_retrieval_benchmark()
