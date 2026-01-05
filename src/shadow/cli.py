"""
MoMo-Shadow CLI

Command-line interface for Shadow operations.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from shadow import __version__
from shadow.config import ShadowConfig

app = typer.Typer(
    name="shadow",
    help="🥷 MoMo-Shadow - Stealth Recon Device",
    no_args_is_help=True,
)
console = Console()


@app.command()
def run(
    config: str = typer.Option(
        None,
        "-c",
        "--config",
        help="Path to config file",
    ),
    mode: str = typer.Option(
        None,
        "-m",
        "--mode",
        help="Operation mode (passive, capture, drop)",
    ),
    debug: bool = typer.Option(
        False,
        "-d",
        "--debug",
        help="Enable debug logging",
    ),
):
    """Start Shadow in specified mode."""
    # Setup logging
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    console.print(Panel.fit(
        "[bold green]🥷 MoMo-Shadow[/bold green]\n"
        f"Version: {__version__}",
        border_style="green",
    ))

    # Load config
    try:
        cfg = ShadowConfig.load(config)
        if mode:
            cfg.autostart.mode = mode
    except Exception as e:
        console.print(f"[red]Config error: {e}[/red]")
        raise typer.Exit(1)

    # Run
    from shadow.main import run_shadow
    asyncio.run(run_shadow(config))


@app.command()
def status():
    """Show Shadow status."""
    console.print("[yellow]Status check not implemented in CLI[/yellow]")
    console.print("Use Web UI at http://192.168.4.1")


@app.command()
def config(
    show: bool = typer.Option(False, "--show", help="Show current config"),
    create: str = typer.Option(None, "--create", help="Create example config at path"),
):
    """Manage configuration."""
    if show:
        try:
            cfg = ShadowConfig.load()
            console.print_json(cfg.model_dump_json(indent=2))
        except Exception as e:
            console.print(f"[red]Config load error: {e}[/red]")
            console.print("Using default config:")
            cfg = ShadowConfig()
            console.print_json(cfg.model_dump_json(indent=2))

    if create:
        path = Path(create)
        cfg = ShadowConfig()
        cfg.to_yaml(path)
        console.print(f"[green]Config created: {path}[/green]")


@app.command()
def interfaces():
    """List WiFi interfaces."""
    async def list_ifaces():
        from shadow.network.manager import InterfaceManager
        ifaces = await InterfaceManager.list_interfaces()
        return ifaces

    ifaces = asyncio.run(list_ifaces())

    if not ifaces:
        console.print("[yellow]No WiFi interfaces found[/yellow]")
        return

    table = Table(title="WiFi Interfaces")
    table.add_column("Interface", style="cyan")

    for iface in ifaces:
        table.add_row(iface)

    console.print(table)


@app.command()
def export(
    pcap: str = typer.Argument(..., help="Path to pcap file"),
    output: str = typer.Option(None, "-o", "--output", help="Output directory"),
):
    """Export pcap to hashcat format."""
    async def do_export():
        from shadow.storage.export import HashcatExporter

        exporter = HashcatExporter(output or "/tmp")
        result = await exporter.export_pcap(pcap)

        if result:
            console.print(f"[green]Exported: {result}[/green]")
            cmd = exporter.generate_wordlist_cmd(result)
            console.print(f"[dim]Crack with: {cmd}[/dim]")
        else:
            console.print("[red]Export failed[/red]")

    asyncio.run(do_export())


@app.command()
def version():
    """Show version information."""
    console.print(f"MoMo-Shadow v{__version__}")


@app.command()
def web(
    host: str = typer.Option("0.0.0.0", "--host", help="Bind host"),
    port: int = typer.Option(80, "--port", help="Bind port"),
):
    """Start web UI only (for development)."""
    import uvicorn
    from shadow.web.server import create_app

    console.print(f"[green]Starting Web UI on http://{host}:{port}[/green]")

    app = create_app()
    uvicorn.run(app, host=host, port=port)


def main():
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()

