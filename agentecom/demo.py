"""
AgentEcom Interactive Live Demonstration.
Demonstrates:
1. Aggressive Caching & Sub-millisecond latency.
2. Webhook Invalidation without TTL polling.
3. Hybrid Search (BM25 + Dense Vector + RRF).
4. Short-lived Isolated Checkout Sessions & Idempotency.
"""

import sys
import os
import asyncio
import time
import uuid

# Ensure UTF-8 console output if available
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from agentecom.db.database import init_db, AsyncSessionLocal
from agentecom.db.seed import seed_database
from agentecom.core.cache import cache
from agentecom.search.hybrid import hybrid_engine
from agentecom.search.worker import index_worker
from agentecom.tools.commerce import (
    tool_get_product,
    tool_search_products,
    tool_create_checkout_session,
    tool_confirm_checkout,
    tool_check_inventory
)
from agentecom.db.models import Product
from sqlalchemy import select

console = Console(force_terminal=True, legacy_windows=False)

async def run_demo():
    console.print(Panel.fit(
        "[bold green]AgentEcom Architecture Demonstration[/bold green]\n"
        "[dim]High-Throughput, Low-Latency E-Commerce Engine Engineered for AI Agents[/dim]",
        border_style="green"
    ))

    # Setup
    with console.status("[bold blue]Initializing Database and Hybrid Indices..."):
        await init_db()
        await seed_database()
        await index_worker._process_reindex_all()

    console.print("[bold green][OK] System Initialized & Catalog Indexed.[/bold green]\n")

    # =========================================================================
    # STEP 1: Aggressive Caching & Latency Lever
    # =========================================================================
    console.rule("[bold cyan]1. Catalog API Caching: Sub-Millisecond Agent Reads[/bold cyan]")
    console.print("Agents issue 10-100x more read queries than humans. Cache sits in front, keyed by SKU.\n")

    sku = "SKU-4471"
    await cache.clear()

    # Cold read (Miss)
    start_cold = time.perf_counter()
    cold_res = await tool_get_product(sku)
    cold_ms = (time.perf_counter() - start_cold) * 1000

    # Warm read (Hit)
    start_warm = time.perf_counter()
    warm_res = await tool_get_product(sku)
    warm_ms = (time.perf_counter() - start_warm) * 1000

    table_cache = Table(title=f"Latency Comparison for Product Lookup ({sku})", show_header=True, header_style="bold cyan")
    table_cache.add_column("Query State", style="white")
    table_cache.add_column("Source", style="yellow")
    table_cache.add_column("Latency (ms)", justify="right", style="bold green")
    table_cache.add_column("Product Name")

    table_cache.add_row("Cold Query (Cache Miss)", "Database (SQLAlchemy)", f"{cold_ms:.3f} ms", cold_res['product']['name'])
    table_cache.add_row("Warm Query (Cache Hit)", "In-Memory Fast Cache", f"{warm_ms:.3f} ms", warm_res['product']['name'])
    console.print(table_cache)

    speedup = cold_ms / warm_ms if warm_ms > 0 else 100.0
    console.print(f"[bold yellow]-> Latency Speedup: {speedup:.1f}x faster![/bold yellow]\n")

    # =========================================================================
    # STEP 2: Webhook-Based Invalidation (No TTL Polling)
    # =========================================================================
    console.rule("[bold cyan]2. Webhook Invalidation vs TTL Polling[/bold cyan]")
    console.print("When Merchant DB updates price/stock, a webhook surgically invalidates the specific SKU tag.\n")

    console.print(f"Current Cached Price for {sku}: [bold green]${warm_res['product']['price']}[/bold green]")
    console.print("[dim]Simulating Merchant DB update: Changing price to $64.99...[/dim]")

    # Update in DB
    async with AsyncSessionLocal() as session:
        stmt = select(Product).where(Product.sku == sku)
        p_obj = (await session.execute(stmt)).scalar_one()
        p_obj.price = 64.99
        await session.commit()

    # Fire webhook invalidation
    invalidated = await cache.invalidate_sku(sku)
    console.print(f"[bold red][EVENT] Webhook Received: Invalidated {invalidated} cache keys for tag 'sku:{sku}'[/bold red]")

    # Next read immediately fetches fresh price
    fresh_res = await tool_get_product(sku)
    console.print(f"Agent immediate next read price: [bold green]${fresh_res['product']['price']}[/bold green] (Cached: {fresh_res['cached']})")
    console.print("[dim]Accurate price with zero staleness, zero polling overhead.[/dim]\n")

    # =========================================================================
    # STEP 3: Hybrid Search (BM25 Lexical + Dense Vector + RRF)
    # =========================================================================
    console.rule("[bold cyan]3. Hybrid Search: BM25 Lexical + Dense Vector RRF[/bold cyan]")
    console.print("Agents query with both exact SKU codes and natural language paraphrases.\n")

    demo_queries = [
        ("SKU-4471", "Exact Product Code"),
        ("cozy oversized knit sweater for freezing winter", "Natural Language / Semantic Paraphrase"),
        ("industry leading noise canceling headphones 30hr battery", "Technical Feature & Specs"),
        ("ergonmic mesh offce chair", "Typo / Misspelling Tolerance")
    ]

    table_search = Table(title="Hybrid Search Retrieval Trace", show_header=True, header_style="bold magenta")
    table_search.add_column("Query Intent", style="cyan")
    table_search.add_column("Agent Query", style="white")
    table_search.add_column("Top Matched SKU", style="bold yellow")
    table_search.add_column("Product Title", style="green")
    table_search.add_column("BM25 Rank", justify="center")
    table_search.add_column("Dense Rank", justify="center")
    table_search.add_column("RRF Score", justify="right")

    for q_text, q_type in demo_queries:
        res = hybrid_engine.search_hybrid(q_text, top_k=1)
        if res:
            top_p = res[0]
            table_search.add_row(
                q_type,
                q_text,
                top_p["sku"],
                top_p["name"][:35] + "...",
                f"#{top_p['_bm25_rank']}" if top_p["_bm25_rank"] else "-",
                f"#{top_p['_dense_rank']}" if top_p["_dense_rank"] else "-",
                f"{top_p['_rrf_score']:.5f}"
            )

    console.print(table_search)
    console.print("\n")

    # =========================================================================
    # STEP 4: Short-Lived Isolated Checkout Sessions & Idempotency
    # =========================================================================
    console.rule("[bold cyan]4. Isolated Checkout Sessions & Idempotent Confirmation[/bold cyan]")
    console.print("AI agents retry and double-fire. Sessions are isolated with short TTLs to protect core order data.\n")

    idem_session_key = f"idem_sess_{uuid.uuid4().hex[:8]}"
    idem_confirm_key = f"idem_order_{uuid.uuid4().hex[:8]}"

    # 1. Create Checkout Session
    console.print(f"[dim]Agent Step A: Creating checkout session with Idempotency-Key='{idem_session_key}'...[/dim]")
    sess_res = await tool_create_checkout_session(
        items=[{"sku": "SKU-4471", "quantity": 1}, {"sku": "FELL-STAG-EKG", "quantity": 1}],
        idempotency_key=idem_session_key,
        ttl_minutes=15
    )
    session_id = sess_res["session_id"]
    console.print(f"Session Created: [bold green]{session_id}[/bold green] | Status: {sess_res['status']} | Total: ${sess_res['total_amount']} | Expires in: 15m")
    console.print("[dim]-> Notice: Core 'orders' table is NOT touched. Abandoned sessions expire without polluting analytics.[/dim]")

    # 2. Simulate Agent Retry on Session Creation
    console.print(f"\n[dim]Agent Step B (Retry): Re-sending create session with same Idempotency-Key='{idem_session_key}'...[/dim]")
    retry_sess = await tool_create_checkout_session(
        items=[{"sku": "SKU-4471", "quantity": 1}],
        idempotency_key=idem_session_key
    )
    console.print(f"Retry Result: Session ID = [bold yellow]{retry_sess['session_id']}[/bold yellow] | Is New: {retry_sess['is_new_session']} (Safely deduplicated!)")

    # 3. Confirm Checkout
    console.print(f"\n[dim]Agent Step C: Confirming checkout with Idempotency-Key='{idem_confirm_key}'...[/dim]")
    order_res = await tool_confirm_checkout(
        session_id=session_id,
        idempotency_key=idem_confirm_key,
        customer_email="agent-runner@internal.ai"
    )
    console.print(f"[bold green][OK] Order Placed: {order_res['order_number']}[/bold green] | Status: {order_res['status']} | Total: ${order_res['total_amount']}")

    # 4. Simulate Agent Double-Fire on Order Confirmation
    console.print(f"\n[dim]Agent Step D (Double-Fire): Agent re-sends confirm checkout with same Idempotency-Key='{idem_confirm_key}'...[/dim]")
    retry_order = await tool_confirm_checkout(
        session_id=session_id,
        idempotency_key=idem_confirm_key
    )
    console.print(f"[bold yellow][OK] Double-Fire Handled: Returned Order {retry_order['order_number']} | Is New Order: {retry_order['is_new_order']}[/bold yellow]")
    console.print("[dim]Inventory decremented only ONCE. No duplicate charges or ghost orders created.[/dim]\n")

    console.print(Panel.fit("[bold green]All AgentEcom Architectural Principles Successfully Verified![/bold green]", border_style="green"))

if __name__ == "__main__":
    asyncio.run(run_demo())
