"""audiomancer CLI - Music production MCP server."""

import sys
import shutil
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

app = typer.Typer(
    name="audiomancer",
    help="Music production MCP server - search and analyze audio samples",
    no_args_is_help=True,
)
console = Console()


def get_config_dir() -> Path:
    """Get the audiomancer config directory."""
    return Path.home() / ".config" / "audiomancer"


def get_data_dir() -> Path:
    """Get the audiomancer data directory."""
    return get_config_dir() / "data"


@app.command()
def init():
    """Initialize audiomancer (create config, download models)."""
    config_dir = get_config_dir()
    data_dir = get_data_dir()

    # Create directories
    config_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "samples").mkdir(exist_ok=True)
    (data_dir / "synths").mkdir(exist_ok=True)

    # Create default config
    config_path = config_dir / "config.yaml"
    if not config_path.exists():
        default_config = """# audiomancer configuration
# Audio analysis settings
analysis:
  sample_rate: 44100
  hop_size: 512
  frame_size: 2048

# Search settings
search:
  max_results: 20
  similarity_threshold: 0.7

# Directories to scan
scan_paths:
  samples: []
  synths: []

# Model settings
models:
  embeddings: "musicnn"  # musicnn, vggish, or openl3
  bpm_detection: "essentia"
"""
        config_path.write_text(default_config)
        console.print(f"[green]✓[/green] Created config: {config_path}")
    else:
        console.print(f"[yellow]![/yellow] Config already exists: {config_path}")

    # Success message
    welcome = f"""[bold green]audiomancer initialized successfully![/bold green]

[bold]Next steps:[/bold]
  1. Run [cyan]audiomancer doctor[/cyan] to check your environment
  2. Add sample/synth paths to [cyan]{config_path}[/cyan]
  3. Run [cyan]audiomancer scan[/cyan] to index your library
  4. Start the MCP server with [cyan]audiomancer serve[/cyan]

[dim]Config directory: {config_dir}
Data directory: {data_dir}[/dim]
"""
    console.print(Panel(welcome, border_style="green"))


@app.command()
def doctor():
    """Check dependencies and configuration."""
    console.print("\n[bold]Running diagnostics...[/bold]\n")

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Check", style="white")
    table.add_column("Status", justify="center")
    table.add_column("Details", style="dim")

    all_passed = True

    # Check Python version
    python_version = sys.version_info
    if python_version >= (3, 11):
        table.add_row(
            "Python version",
            "[green]✓[/green]",
            f"{python_version.major}.{python_version.minor}.{python_version.micro}",
        )
    else:
        table.add_row(
            "Python version",
            "[red]✗[/red]",
            f"{python_version.major}.{python_version.minor}.{python_version.micro} (3.11+ required)",
        )
        all_passed = False

    # Check essentia
    try:
        import essentia

        table.add_row("essentia", "[green]✓[/green]", essentia.__version__)
    except ImportError:
        table.add_row(
            "essentia",
            "[red]✗[/red]",
            "pip install essentia-tensorflow",
        )
        all_passed = False

    # Check tensorflow
    try:
        import tensorflow as tf

        table.add_row("tensorflow", "[green]✓[/green]", tf.__version__)
    except ImportError:
        table.add_row(
            "tensorflow",
            "[red]✗[/red]",
            "pip install tensorflow",
        )
        all_passed = False

    # Check numpy
    try:
        import numpy as np

        table.add_row("numpy", "[green]✓[/green]", np.__version__)
    except ImportError:
        table.add_row(
            "numpy",
            "[red]✗[/red]",
            "pip install numpy",
        )
        all_passed = False

    # Check librosa
    try:
        import librosa

        table.add_row("librosa", "[green]✓[/green]", librosa.__version__)
    except ImportError:
        table.add_row(
            "librosa",
            "[red]✗[/red]",
            "pip install librosa",
        )
        all_passed = False

    # Check faiss
    try:
        import faiss

        # faiss doesn't have __version__ in all builds
        table.add_row("faiss", "[green]✓[/green]", "installed")
    except ImportError:
        table.add_row(
            "faiss",
            "[red]✗[/red]",
            "pip install faiss-cpu",
        )
        all_passed = False

    # Check sclang binary
    sclang_path = shutil.which("sclang")
    if sclang_path:
        table.add_row("sclang", "[green]✓[/green]", sclang_path)
    else:
        table.add_row(
            "sclang",
            "[yellow]![/yellow]",
            "Not found (install SuperCollider for synth analysis)",
        )

    # Check config
    config_path = get_config_dir() / "config.yaml"
    if config_path.exists():
        table.add_row("config", "[green]✓[/green]", str(config_path))
    else:
        table.add_row(
            "config",
            "[yellow]![/yellow]",
            f"Run 'audiomancer init' to create {config_path}",
        )
        all_passed = False

    console.print(table)
    console.print()

    if all_passed:
        console.print("[bold green]All checks passed! ✓[/bold green]\n")
        sys.exit(0)
    else:
        console.print("[bold red]Some checks failed. Please install missing dependencies.[/bold red]\n")
        sys.exit(1)


@app.command()
def serve(
    host: str = typer.Option("localhost", help="Host to bind to"),
    port: int = typer.Option(8080, help="Port to bind to"),
):
    """Start the MCP server."""
    console.print(f"[yellow]MCP server not yet implemented[/yellow]")
    console.print(f"Would start on {host}:{port}")
    console.print("\n[dim]Coming soon: FastMCP server for audio analysis[/dim]")


@app.command()
def scan(
    path: Optional[Path] = typer.Argument(None, help="Directory to scan"),
    recursive: bool = typer.Option(True, help="Scan subdirectories"),
):
    """Index sample/synth folders."""
    console.print("[yellow]Scanning not yet implemented[/yellow]")
    if path:
        console.print(f"Would scan: {path}")
        console.print(f"Recursive: {recursive}")
    else:
        console.print("Would scan paths from config.yaml")
    console.print("\n[dim]Coming soon: Audio file indexing with feature extraction[/dim]")


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    limit: int = typer.Option(20, help="Maximum results"),
):
    """Quick search from command line."""
    console.print("[yellow]Search not yet implemented[/yellow]")
    console.print(f"Query: {query}")
    console.print(f"Limit: {limit}")
    console.print("\n[dim]Coming soon: Semantic audio search[/dim]")


@app.command()
def stats():
    """Show library statistics."""
    console.print("[yellow]Stats not yet implemented[/yellow]")
    console.print("\n[dim]Coming soon: Library statistics and visualizations[/dim]")


def main():
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
