"""
Reporter — renders the RugRadar report to the terminal using Rich.
Also supports JSON export for programmatic use.
"""

import json
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box
from src.models import RugReport, RiskLevel, RISK_COLORS, RISK_EMOJIS, score_to_risk
from src.logger import get_logger

logger = get_logger(__name__)
console = Console()


def _score_bar(score: int, max_score: int) -> str:
    """Render a simple ASCII score bar."""
    filled = int((score / max_score) * 10)
    return "█" * filled + "░" * (10 - filled)


def render_report(report: RugReport):
    """Render a full RugRadar report to the terminal."""
    risk = score_to_risk(report.trust_score)
    color = RISK_COLORS.get(risk, "white")
    emoji = RISK_EMOJIS.get(risk, "❓")

    # Header
    console.print()
    console.rule(f"[bold]{emoji} RugRadar Report — ${report.metadata.symbol}[/bold]")
    console.print()

    # Main score panel
    score_table = Table(box=box.ROUNDED, show_header=False, padding=(0, 2), expand=True)
    score_table.add_column("Field", style="dim", width=22)
    score_table.add_column("Value")

    score_table.add_row(
        "Token",
        f"[bold]{report.metadata.name}[/bold] (${report.metadata.symbol})"
    )
    score_table.add_row(
        "Mint",
        f"[dim]{report.metadata.mint[:20]}...{report.metadata.mint[-8:]}[/dim]"
    )
    score_table.add_row(
        "Trust Score",
        f"[{color}][bold]{report.trust_score}/100[/bold]  {_score_bar(report.trust_score, 100)}[/{color}]"
    )
    score_table.add_row(
        "Risk Level",
        f"[{color}][bold]{emoji} {risk.value.replace('_', ' ')}[/bold][/{color}]"
    )
    score_table.add_row("AI Verdict", f"[{color}]{report.ai_verdict}[/{color}]")
    score_table.add_row("AI Reasoning", report.ai_reasoning)

    console.print(Panel(score_table, title="[bold]🛡️ Trust Score[/bold]", border_style=color))

    # Checks breakdown
    checks_table = Table(box=box.SIMPLE, show_header=True, padding=(0, 1), expand=True)
    checks_table.add_column("Check", style="bold", width=22)
    checks_table.add_column("Result")
    checks_table.add_column("Score", justify="right", width=10)

    m = report.mint_check
    mint_result = []
    if m.mint_authority_active:
        mint_result.append("[red]❌ Mint authority ACTIVE[/red]")
    else:
        mint_result.append("[green]✅ Mint authority revoked[/green]")
    if m.freeze_authority_active:
        mint_result.append("[red]❌ Freeze authority ACTIVE[/red]")
    else:
        mint_result.append("[green]✅ Freeze authority revoked[/green]")
    checks_table.add_row(
        "Mint Authority",
        "\n".join(mint_result),
        f"{m.score}/25"
    )

    h = report.holder_check
    conc = h.top10_concentration_pct
    conc_color = "green" if conc < 40 else ("yellow" if conc < 60 else "red")
    checks_table.add_row(
        "Holder Concentration",
        f"[{conc_color}]Top 10 hold {conc}% of supply[/{conc_color}]",
        f"{h.score}/20"
    )

    c = report.creator_check
    creator_parts = [f"Tokens created: {c.tokens_created}"]
    if c.tokens_abandoned > 0:
        creator_parts.append(f"[red]⚠ Abandoned: {c.tokens_abandoned}[/red]")
    if c.known_rugger:
        creator_parts.append("[bold red]💀 KNOWN RUGGER[/bold red]")
    if c.wallet_age_days < 7:
        creator_parts.append(f"[yellow]⚠ Wallet age: {c.wallet_age_days}d[/yellow]")
    checks_table.add_row(
        "Creator History",
        "\n".join(creator_parts),
        f"{c.score}/20"
    )

    b = report.bundle_check
    bundle_text = (
        f"[red]❌ {b.wallets_in_bundle} wallets, {b.bundle_sol_amount:.2f} SOL[/red]"
        if b.bundle_detected else "[green]✅ No bundle detected[/green]"
    )
    checks_table.add_row("Bundle Detection", bundle_text, f"{b.score}/15")

    s = report.social_check
    social_parts = []
    social_parts.append(f"Twitter: {'✅' if s.has_twitter else '❌'}")
    social_parts.append(f"Telegram: {'✅' if s.has_telegram else '❌'}")
    social_parts.append(f"Website: {'✅' if s.has_website else '❌'}")
    checks_table.add_row("Socials", "  ".join(social_parts), f"{s.score}/10")

    lq = report.liquidity_check
    lq_text = "[green]✅ LP burned[/green]" if lq.lp_burned else (
        "[green]✅ LP locked[/green]" if lq.lp_locked else "[red]❌ LP not locked[/red]"
    )
    checks_table.add_row("Liquidity", lq_text, f"{lq.score}/10")

    console.print(Panel(checks_table, title="[bold]📋 Check Breakdown[/bold]", border_style="dim"))

    # Red flags & positives
    if report.red_flags or report.positives:
        fp_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
        fp_table.add_column("Type", width=14)
        fp_table.add_column("Item")

        for flag in report.red_flags[:5]:
            fp_table.add_row("[red]⚠ Red Flag[/red]", flag)
        for pos in report.positives[:3]:
            fp_table.add_row("[green]✅ Positive[/green]", pos)

        console.print(Panel(fp_table, title="[bold]🔍 Key Signals[/bold]", border_style="dim"))

    console.print()


def export_json(report: RugReport, output_path: str):
    """Export the report as JSON to a file."""
    try:
        with open(output_path, "w") as f:
            json.dump(report.to_dict(), f, indent=2)
        logger.info(f"Report exported to {output_path}")
    except Exception as e:
        logger.error(f"Failed to export JSON: {e}")
