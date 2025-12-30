"""audiomancer CLI - Music production MCP server."""

import sys
import shutil
import subprocess
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


def scaffold_project(
    project_path: Path,
    project_name: str,
    sample_source: Path,
    create_git: bool = True,
) -> None:
    """Create a new TidalCycles project with scaffolding.

    Args:
        project_path: Path to create project directory
        project_name: Name of the project
        sample_source: Path to sample source directory
        create_git: Whether to initialize git repo (default: True)
    """
    from audiomancer.templates import (
        get_template_dir,
        render_template,
        get_template_variables,
    )

    # Create project directory if it doesn't exist
    project_path.mkdir(parents=True, exist_ok=True)

    # Create subdirectories
    (project_path / "library").mkdir(exist_ok=True)
    (project_path / "synths").mkdir(exist_ok=True)

    # Create samples directory or symlink
    samples_dir = project_path / "samples"
    sample_source_abs = sample_source.resolve()
    project_path_abs = project_path.resolve()

    # Check if sample_source is inside project_path
    try:
        sample_source_abs.relative_to(project_path_abs)
        is_inside_project = True
    except ValueError:
        is_inside_project = False

    if is_inside_project:
        # Create as regular directory
        samples_dir.mkdir(exist_ok=True)
    else:
        # Create as symlink to external source
        if samples_dir.exists() or samples_dir.is_symlink():
            # Remove existing before creating symlink
            if samples_dir.is_symlink():
                samples_dir.unlink()
            elif samples_dir.is_dir():
                shutil.rmtree(samples_dir)
            else:
                samples_dir.unlink()
        samples_dir.symlink_to(sample_source_abs)

    # Render templates
    template_dir = get_template_dir() / "project"
    variables = get_template_variables(project_name, project_path, sample_source)

    for template_file in template_dir.glob("*.template"):
        # Get output filename (remove .template extension)
        output_name = template_file.stem
        output_path = project_path / output_name

        # Render and write template
        rendered_content = render_template(template_file, variables)
        output_path.write_text(rendered_content, encoding='utf-8')

    # Initialize git repo if requested and not already a repo
    if create_git:
        git_dir = project_path / ".git"
        if not git_dir.exists():
            subprocess.run(
                ["git", "init"],
                cwd=project_path,
                check=True,
                capture_output=True,
            )


@app.command()
def init(
    path: Optional[Path] = typer.Option(None, "--path", help="Project directory (default: current directory)"),
):
    """Initialize a new TidalCycles project with interactive prompts."""
    # Determine project path
    project_path = path if path else Path.cwd()

    # Check if project already has .audiomancer.yaml
    config_file = project_path / ".audiomancer.yaml"
    if config_file.exists():
        console.print(f"[yellow]Project already initialized at {project_path}[/yellow]")
        console.print(f"Config file: {config_file}")
        return

    # Prompt for project name with default from directory name
    default_name = project_path.name
    project_name = typer.prompt("Project name", default=default_name)

    # Prompt for sample source path with validation
    while True:
        sample_source_str = typer.prompt("Sample source directory")
        sample_source = Path(sample_source_str).expanduser().resolve()

        if sample_source.exists() and sample_source.is_dir():
            break
        else:
            console.print(f"[red]Path does not exist or is not a directory: {sample_source}[/red]")
            console.print("Please enter a valid directory path.")

    # Call scaffold_project with gathered values
    scaffold_project(
        project_path=project_path,
        project_name=project_name,
        sample_source=sample_source,
        create_git=True,
    )

    # Success message with next steps
    console.print(f"\n[bold green]Project '{project_name}' initialized successfully![/bold green]\n")
    console.print("[bold]Next steps:[/bold]")
    console.print("  1. Start SuperCollider: [cyan]open -a SuperCollider start_superdirt.scd[/cyan]")
    console.print("  2. Open session.tidal in VS Code with TidalCycles extension")
    console.print("  3. Start coding live music!")
    console.print(f"\n[dim]Project directory: {project_path}[/dim]")


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
def serve():
    """Start the MCP server (stdio mode for Claude Desktop)."""
    try:
        from .server import main
        import asyncio

        # Run the async main function
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Server stopped[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]Error starting server:[/red] {e}")
        sys.exit(1)


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


@app.command()
def benchmark(
    baseline: bool = typer.Option(False, "--baseline", help="Create new baseline"),
    check: bool = typer.Option(False, "--check", help="Check for regressions"),
    threshold: float = typer.Option(20.0, "--threshold", help="Regression threshold (%)"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file"),
):
    """Run performance benchmarks."""
    import subprocess
    import json
    from datetime import datetime

    benchmarks_dir = Path(__file__).parent.parent.parent.parent / "benchmarks"

    if not benchmarks_dir.exists():
        console.print("[red]Error:[/red] Benchmarks directory not found")
        console.print(f"Expected: {benchmarks_dir}")
        sys.exit(1)

    if baseline:
        # Run benchmarks and create baseline
        console.print("[bold]Running benchmarks to create baseline...[/bold]\n")

        result = subprocess.run(
            [sys.executable, str(benchmarks_dir / "run_benchmarks.py")],
            cwd=benchmarks_dir,
            capture_output=False,
        )

        if result.returncode != 0:
            console.print("\n[red]Benchmarks failed[/red]")
            sys.exit(1)

        console.print("\n[green]✓ Baseline created successfully[/green]")
        sys.exit(0)

    elif check:
        # Run benchmarks and check for regressions
        console.print("[bold]Running benchmarks and checking for regressions...[/bold]\n")

        # Run benchmarks to temporary file
        temp_results = benchmarks_dir / f"results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        # First run benchmarks
        result = subprocess.run(
            [sys.executable, str(benchmarks_dir / "run_benchmarks.py")],
            cwd=benchmarks_dir,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            console.print("\n[red]Benchmarks failed[/red]")
            console.print(result.stderr)
            sys.exit(1)

        # Move baseline.json to temp location
        baseline_file = benchmarks_dir / "baseline.json"
        if baseline_file.exists():
            import shutil
            shutil.copy(baseline_file, temp_results)
        else:
            console.print("[red]Error:[/red] No baseline found. Run with --baseline first.")
            sys.exit(2)

        # Check for regressions
        console.print("\n[bold]Checking for regressions...[/bold]\n")

        # Load current results (just created)
        with open(baseline_file) as f:
            current_data = json.load(f)

        # Save to output if specified
        if output:
            with open(output, 'w') as f:
                json.dump(current_data, f, indent=2)
            console.print(f"[dim]Results saved to: {output}[/dim]\n")

        result = subprocess.run(
            [
                sys.executable,
                str(benchmarks_dir / "check_regression.py"),
                str(baseline_file),
                "--baseline",
                str(temp_results),
                "--threshold",
                str(threshold),
            ],
            cwd=benchmarks_dir,
        )

        sys.exit(result.returncode)

    else:
        # Just run benchmarks
        console.print("[bold]Running performance benchmarks...[/bold]\n")

        result = subprocess.run(
            [sys.executable, str(benchmarks_dir / "run_benchmarks.py")],
            cwd=benchmarks_dir,
        )

        if result.returncode == 0:
            baseline_file = benchmarks_dir / "baseline.json"
            console.print(f"\n[green]✓ Results saved to:[/green] {baseline_file}")

            if output:
                import shutil
                shutil.copy(baseline_file, output)
                console.print(f"[green]✓ Copied to:[/green] {output}")

        sys.exit(result.returncode)


def main():
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
