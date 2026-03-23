#!/usr/bin/env python3
"""
RugRadar — AI-Powered Rug Pull Detector for Solana
Built by LixerDev
"""

import asyncio
import json
import sys
import typer
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich import box

from config import config
from src.logger import get_logger, print_banner
from src.analyzer import Analyzer
from src.reporter import render_report, export_json
from src.database import init_db, save_scan, get_scan_history, get_stats

app = typer.Typer(help="RugRadar - AI-powered rug pull detector for Solana tokens")
console = Console()
logger = get_logger(__name__)


def _validate_config():
    errors = config.validate()
    if errors:
        for err in errors:
            console.print(f"[red]Config error: {err}[/red]")
        console.print("[dim]Fix your .env file and try again.[/dim]")
        raise typer.Exit(1)


@app.command()
def scan(
    mint: str = typer.Argument(..., help="Token mint address to scan"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Export report as JSON to this path"),
    name: str = typer.Option("", "--name", help="Token name (optional, fetched on-chain if omitted)"),
    symbol: str = typer.Option("", "--symbol", help="Token symbol"),
    creator: str = typer.Option("", "--creator", help="Creator wallet address"),
    twitter: str = typer.Option("", "--twitter", help="Twitter URL or handle"),
    telegram: str = typer.Option("", "--telegram", help="Telegram URL or handle"),
    website: str = typer.Option("", "--website", help="Website URL"),
):
    """Scan a single token by mint address and generate a RugRadar Trust Score."""
    print_banner()
    _validate_config()

    async def _run():
        await init_db()
        analyzer = Analyzer()
        report = await analyzer.analyze(
            mint=mint,
            name=name,
            symbol=symbol,
            creator=creator,
            twitter=twitter,
            telegram=telegram,
            website=website,
        )
        render_report(report)
        await save_scan(report)

        if output:
            export_json(report, output)
            console.print(f"[dim]Report saved to {output}[/dim]")

    asyncio.run(_run())


@app.command()
def watch():
    """Watch mode: monitor PumpFun and auto-scan every new token launch."""
    print_banner()
    _validate_config()

    console.print("[bold yellow]Watch mode starting — listening to PumpFun WebSocket...[/bold yellow]")
    console.print(f"[dim]Alert threshold: Trust Score < {config.ALERT_THRESHOLD}[/dim]\n")

    async def _run():
        import websockets

        await init_db()
        analyzer = Analyzer()

        async def handle_token(data: dict):
            mint = data.get("mint", "")
            if not mint:
                return
            try:
                report = await analyzer.analyze(
                    mint=mint,
                    name=data.get("name", ""),
                    symbol=data.get("symbol", ""),
                    description=data.get("description", ""),
                    twitter=data.get("twitter", ""),
                    telegram=data.get("telegram", ""),
                    website=data.get("website", ""),
                    creator=data.get("traderPublicKey", ""),
                    market_cap_sol=data.get("marketCapSol", 0),
                    created_at=data.get("timestamp"),
                )
                render_report(report)
                await save_scan(report)

                if report.trust_score < config.ALERT_THRESHOLD:
                    console.print(
                        f"[bold red]🚨 ALERT: {report.metadata.symbol} scored {report.trust_score}/100 "
                        f"[{report.risk_level.value}][/bold red]"
                    )
            except Exception as e:
                logger.error(f"Error scanning {mint[:12]}...: {e}")

        while True:
            try:
                async with websockets.connect(config.PUMP_WS_URL) as ws:
                    await ws.send(json.dumps({"method": "subscribeNewToken"}))
                    async for message in ws:
                        data = json.loads(message)
                        if data.get("txType") == "create":
                            asyncio.create_task(handle_token(data))
            except Exception as e:
                logger.warning(f"WebSocket error: {e}. Reconnecting in 5s...")
                await asyncio.sleep(5)

    asyncio.run(_run())


@app.command()
def history(limit: int = typer.Option(20, "--limit", "-n", help="Number of recent scans to show")):
    """Show recent scan history."""

    async def _run():
        await init_db()
        scans = await get_scan_history(limit)
        stats = await get_stats()

        console.print(f"\n[bold]📊 RugRadar Stats[/bold]")
        console.print(f"Total scans: {stats['total_scans']} | Avg Trust Score: {stats['avg_trust_score']}/100 | Likely Rugs: {stats['likely_rugs_detected']}\n")

        if not scans:
            console.print("[dim]No scan history found.[/dim]")
            return

        table = Table(box=box.ROUNDED, show_header=True)
        table.add_column("Token", style="bold")
        table.add_column("Mint")
        table.add_column("Score", justify="center")
        table.add_column("Risk Level")
        table.add_column("Scanned At", style="dim")

        for scan in scans:
            score = scan["trust_score"] or 0
            risk = scan["risk_level"] or "UNKNOWN"
            color = "green" if score >= 65 else ("yellow" if score >= 45 else "red")
            table.add_row(
                f"{scan['name']} (${scan['symbol']})",
                f"{(scan['mint'] or '')[:12]}...",
                f"[{color}]{score}/100[/{color}]",
                f"[{color}]{risk}[/{color}]",
                (scan["scanned_at"] or "")[:16],
            )

        console.print(table)

    asyncio.run(_run())


if __name__ == "__main__":
    app()
