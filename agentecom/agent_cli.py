"""
Interactive Terminal Conversational Interface for AgentEcom AI Agent.
Enables real-time natural language dialogue with tool execution tracing and readability inspection.
"""

import sys
import asyncio
import uuid

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from rich.prompt import Prompt

from agentecom.db.database import init_db
from agentecom.db.seed import seed_database
from agentecom.search.worker import index_worker
from agentecom.agent.engine import agent_engine

console = Console(force_terminal=True, legacy_windows=False)

async def run_agent_cli():
    console.clear()
    console.print(Panel.fit(
        "[bold cyan]AgentEcom — Conversational AI Agent & Readability Inspector[/bold cyan]\n"
        "[dim]Type your shopping requests in natural language. Type 'exit' or 'quit' to end session.[/dim]",
        border_style="cyan"
    ))

    # Initialize environment
    with console.status("[bold blue]Initializing Database & Search Index..."):
        await init_db()
        await seed_database()
        await index_worker._process_reindex_all()

    session_id = f"cli_sess_{uuid.uuid4().hex[:8]}"
    console.print(f"[bold green][OK] Ready! Active Session: [yellow]{session_id}[/yellow][/bold green]\n")
    console.print("[dim]Suggested prompts:[/dim]")
    console.print("  * 'Find cozy knit sweater under $60'")
    console.print("  * 'Show me Sony noise canceling headphones'")
    console.print("  * 'Add SKU-4471 to cart'")
    console.print("  * 'View cart'")
    console.print("  * 'Checkout' and 'Confirm purchase'\n")

    while True:
        try:
            user_input = Prompt.ask("\n[bold cyan]You[/bold cyan]")
            if not user_input.strip():
                continue
            if user_input.lower() in ["exit", "quit", "q"]:
                console.print("[bold yellow]Session ended. Goodbye![/bold yellow]")
                break

            with console.status("[bold magenta]AI Agent thinking & selecting commerce tools..."):
                response = await agent_engine.process_user_turn(
                    user_input=user_input,
                    session_id=session_id
                )

            # 1. Print AI Agent Reply
            console.print("\n[bold green]AI Agent:[/bold green]")
            console.print(Markdown(response.reply))

            # 2. Print Tool Telemetry Table
            r = response.readability
            telemetry_table = Table(title="AI Readability & Execution Audit", show_header=True, header_style="bold blue")
            telemetry_table.add_column("Latency", justify="right", style="emerald")
            telemetry_table.add_column("Tools Invoked", style="cyan")
            telemetry_table.add_column("Token Reduction", justify="right", style="bold green")
            telemetry_table.add_column("Cache Hits", justify="right", style="yellow")
            telemetry_table.add_column("Active Cart Items", justify="right", style="white")

            tool_names = ", ".join([tc["tool"] for tc in response.tool_calls_made]) if response.tool_calls_made else "None (Direct)"
            cart_count = sum(i["quantity"] for i in response.cart) if response.cart else 0

            telemetry_table.add_row(
                f"{r.execution_latency_ms:.2f} ms",
                tool_names,
                f"{r.token_reduction_pct}%",
                str(r.cache_hits),
                str(cart_count)
            )
            console.print(telemetry_table)

        except (KeyboardInterrupt, EOFError):
            console.print("\n[bold yellow]Session ended.[/bold yellow]")
            break
        except Exception as e:
            console.print(f"[bold red]Error: {e}[/bold red]")

if __name__ == "__main__":
    asyncio.run(run_agent_cli())
