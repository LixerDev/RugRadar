import logging
import os
from datetime import datetime
from rich.console import Console
from rich.logging import RichHandler
from config import config

console = Console()


def get_logger(name: str) -> logging.Logger:
    handlers = [RichHandler(console=console, rich_tracebacks=True, show_path=False, markup=True)]

    if config.LOG_TO_FILE:
        os.makedirs("logs", exist_ok=True)
        log_file = f"logs/rugradar_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        ))
        handlers.append(file_handler)

    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL, logging.INFO),
        handlers=handlers,
        format="%(message)s",
        datefmt="[%H:%M:%S]",
    )
    return logging.getLogger(name)


def print_banner():
    banner = """
[bold red]
  ██████╗ ██╗   ██╗ ██████╗ ██████╗  █████╗ ██████╗  █████╗ ██████╗ 
  ██╔══██╗██║   ██║██╔════╝ ██╔══██╗██╔══██╗██╔══██╗██╔══██╗██╔══██╗
  ██████╔╝██║   ██║██║  ███╗██████╔╝███████║██║  ██║███████║██████╔╝
  ██╔══██╗██║   ██║██║   ██║██╔══██╗██╔══██║██║  ██║██╔══██║██╔══██╗
  ██║  ██║╚██████╔╝╚██████╔╝██║  ██║██║  ██║██████╔╝██║  ██║██║  ██║
  ╚═╝  ╚═╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝
[/bold red]
[bold white]        AI-Powered Rug Pull Detector | Built by LixerDev[/bold white]
[dim]        v1.0.0 | Solana Mainnet | 6 Independent Checks + AI Synthesis[/dim]
    """
    console.print(banner)
