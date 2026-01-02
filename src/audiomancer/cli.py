"""audiomancer CLI - Music production MCP server."""

import sys
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Tuple, cast

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich import print as rprint

from audiomancer.storage.interfaces import SampleMetadata

app = typer.Typer(
    name="audiomancer",
    help="Music production MCP server - search and analyze audio samples",
    no_args_is_help=True,
)
console = Console()


def check_python_package(package_name: str, version_attr: str = "__version__") -> Tuple[bool, str]:
    """Check if a Python package is importable via subprocess.

    Uses subprocess to avoid importing heavy C++ libraries (essentia, tensorflow)
    into the main process, which can cause mutex deadlocks.

    Returns (success, version_or_error_message).
    """
    # Script to import package and print version
    script = f"""
import sys
try:
    import {package_name}
    version = getattr({package_name}, '{version_attr}', 'installed')
    print(version)
    sys.exit(0)
except ImportError as e:
    print(str(e))
    sys.exit(1)
"""
    try:
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        else:
            return False, result.stderr.strip() or result.stdout.strip()
    except subprocess.TimeoutExpired:
        return False, "check timed out"
    except Exception as e:
        return False, str(e)


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

    # Create virtual environment
    venv_dir = project_path / ".venv"
    if not venv_dir.exists():
        # Try uv first (faster), fall back to python venv
        if shutil.which("uv"):
            subprocess.run(
                ["uv", "venv"],
                cwd=project_path,
                check=True,
                capture_output=True,
            )
        else:
            # Fallback to standard venv
            subprocess.run(
                [sys.executable, "-m", "venv", ".venv"],
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


def _check_python_version() -> Tuple[str, str, str, bool]:
    """Check Python version."""
    python_version = sys.version_info
    version_str = f"{python_version.major}.{python_version.minor}.{python_version.micro}"
    if python_version >= (3, 11):
        return ("Python version", "[green]✓[/green]", version_str, True)
    else:
        return ("Python version", "[red]✗[/red]", f"{version_str} (3.11+ required)", False)


def _check_supercollider() -> Tuple[str, str, str, bool]:
    """Check SuperCollider installation."""
    sclang_path = shutil.which("sclang")
    if not sclang_path:
        # Check macOS app bundle location
        macos_sclang = Path("/Applications/SuperCollider.app/Contents/MacOS/sclang")
        if macos_sclang.exists():
            sclang_path = str(macos_sclang)

    if sclang_path:
        return ("SuperCollider (sclang)", "[green]✓[/green]", sclang_path, True)
    else:
        return ("SuperCollider (sclang)", "[red]✗[/red]", "Install from https://supercollider.github.io/downloads", False)


def _check_tidal() -> Tuple[str, str, str, bool]:
    """Check TidalCycles installation."""
    ghci_path = shutil.which("ghci")
    if not ghci_path:
        return ("TidalCycles (ghci)", "[red]✗[/red]", "ghci not found. Install ghcup from https://www.haskell.org/ghcup/", False)

    try:
        result = subprocess.run(
            [ghci_path, "-e", "import Sound.Tidal.Context"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return ("TidalCycles (ghci)", "[green]✓[/green]", ghci_path, True)
        else:
            return ("TidalCycles (ghci)", "[red]✗[/red]", "ghci found but TidalCycles not installed", False)
    except subprocess.TimeoutExpired:
        return ("TidalCycles (ghci)", "[yellow]![/yellow]", "ghci check timed out", True)
    except Exception as e:
        return ("TidalCycles (ghci)", "[yellow]![/yellow]", f"Error: {e}", True)


def _check_ghc() -> Tuple[str, str, str, bool]:
    """Check GHC installation."""
    ghc_path = shutil.which("ghc")
    if not ghc_path:
        return ("GHC (Haskell compiler)", "[yellow]![/yellow]", "Not found (install ghcup)", True)

    try:
        result = subprocess.run(
            [ghc_path, "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            version = result.stdout.strip().split()[-1] if result.stdout else "unknown"
            return ("GHC (Haskell compiler)", "[green]✓[/green]", f"{ghc_path} ({version})", True)
        else:
            return ("GHC (Haskell compiler)", "[yellow]![/yellow]", "ghc found but version check failed", True)
    except subprocess.TimeoutExpired:
        return ("GHC (Haskell compiler)", "[yellow]![/yellow]", "ghc version check timed out", True)
    except Exception as e:
        return ("GHC (Haskell compiler)", "[yellow]![/yellow]", f"Error: {e}", True)


@app.command()
def doctor():
    """Check dependencies and configuration."""
    console.print()

    # Collect results as we go
    results = []
    all_passed = True

    # Define all checks
    required_packages = [
        ("numpy", "__version__", "pip install numpy"),
        ("librosa", "__version__", "pip install librosa"),
        ("faiss", None, "pip install faiss-cpu"),
        ("tensorflow", "__version__", "pip install tensorflow"),
    ]
    optional_packages = [
        ("essentia", "__version__", "pip install essentia-tensorflow", "AI audio analysis"),
    ]

    # Calculate total checks: python + required_pkgs + optional_pkgs + sc + tidal + ghc + config
    total_checks = 1 + len(required_packages) + len(optional_packages) + 4

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Running diagnostics...", total=total_checks)

        # Check Python version
        progress.update(task, description="[cyan]Checking Python version...")
        result = _check_python_version()
        results.append(result)
        if not result[3]:
            all_passed = False
        progress.advance(task)

        # Check required packages
        for pkg_name, version_attr, install_hint in required_packages:
            progress.update(task, description=f"[cyan]Checking {pkg_name}...")
            success, info = check_python_package(pkg_name, version_attr or "__version__")
            if success:
                results.append((pkg_name, "[green]✓[/green]", info if version_attr else "installed", True))
            else:
                results.append((pkg_name, "[red]✗[/red]", install_hint, False))
                all_passed = False
            progress.advance(task)

        # Check optional packages
        for pkg_name, version_attr, install_hint, feature in optional_packages:
            progress.update(task, description=f"[cyan]Checking {pkg_name}...")
            success, info = check_python_package(pkg_name, version_attr or "__version__")
            if success:
                results.append((pkg_name, "[green]✓[/green]", info if version_attr else "installed", True))
            else:
                results.append((pkg_name, "[yellow]![/yellow]", f"Optional ({feature}): {install_hint}", True))
            progress.advance(task)

        # Check SuperCollider
        progress.update(task, description="[cyan]Checking SuperCollider...")
        result = _check_supercollider()
        results.append(result)
        if not result[3]:
            all_passed = False
        progress.advance(task)

        # Check TidalCycles
        progress.update(task, description="[cyan]Checking TidalCycles...")
        result = _check_tidal()
        results.append(result)
        if not result[3]:
            all_passed = False
        progress.advance(task)

        # Check GHC
        progress.update(task, description="[cyan]Checking GHC...")
        result = _check_ghc()
        results.append(result)
        if not result[3]:
            all_passed = False
        progress.advance(task)

        # Check global config
        progress.update(task, description="[cyan]Checking config...")
        config_path = get_config_dir() / "config.yaml"
        if config_path.exists():
            results.append(("global config", "[green]✓[/green]", str(config_path), True))
        else:
            results.append(("global config", "[yellow]![/yellow]", f"Run 'audiomancer init' to create", True))
        progress.advance(task)

    # Display results table
    console.print()
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Check", style="white")
    table.add_column("Status", justify="center")
    table.add_column("Details", style="dim")

    for name, status, details, _ in results:
        table.add_row(name, status, details)

    console.print(table)
    console.print()

    # Check project-local settings (if in a project directory)
    cwd = Path.cwd()
    project_config = cwd / ".audiomancer.yaml"
    mcp_config = cwd / ".mcp.json"

    # Detect if we're in a project directory
    is_project = project_config.exists() or mcp_config.exists() or (cwd / "session.tidal").exists()

    if is_project:
        console.print("[bold]Project checks:[/bold]\n")
        project_table = Table(show_header=True, header_style="bold cyan")
        project_table.add_column("Check", style="white")
        project_table.add_column("Status", justify="center")
        project_table.add_column("Details", style="dim")

        # Check .audiomancer.yaml
        if project_config.exists():
            project_table.add_row(".audiomancer.yaml", "[green]✓[/green]", str(project_config))
        else:
            project_table.add_row(
                ".audiomancer.yaml",
                "[yellow]![/yellow]",
                "Optional project config (uses global defaults)",
            )

        # Check .mcp.json
        if mcp_config.exists():
            # Validate JSON
            import json
            try:
                with open(mcp_config) as f:
                    mcp_data = json.load(f)
                if "mcpServers" in mcp_data and "audiomancer" in mcp_data.get("mcpServers", {}):
                    project_table.add_row(".mcp.json", "[green]✓[/green]", "audiomancer server configured")
                else:
                    project_table.add_row(
                        ".mcp.json",
                        "[yellow]![/yellow]",
                        "exists but audiomancer server not configured",
                    )
            except json.JSONDecodeError as e:
                project_table.add_row(".mcp.json", "[red]✗[/red]", f"Invalid JSON: {e}")
                all_passed = False
        else:
            project_table.add_row(
                ".mcp.json",
                "[red]✗[/red]",
                "Missing - Claude won't detect this project",
            )
            all_passed = False

        # Check project directories
        required_dirs = ["library", "samples", "synths"]
        for dir_name in required_dirs:
            dir_path = cwd / dir_name
            if dir_path.exists() and dir_path.is_dir():
                # Count contents
                count = len(list(dir_path.iterdir()))
                project_table.add_row(f"{dir_name}/", "[green]✓[/green]", f"{count} items")
            else:
                project_table.add_row(
                    f"{dir_name}/",
                    "[yellow]![/yellow]",
                    "Directory missing",
                )

        # Check session.tidal
        session_file = cwd / "session.tidal"
        if session_file.exists():
            project_table.add_row("session.tidal", "[green]✓[/green]", "Ready for live coding")
        else:
            project_table.add_row(
                "session.tidal",
                "[yellow]![/yellow]",
                "No session file - create one to start coding",
            )

        # Check start_superdirt.scd
        superdirt_file = cwd / "start_superdirt.scd"
        if superdirt_file.exists():
            project_table.add_row("start_superdirt.scd", "[green]✓[/green]", "SuperDirt startup script")
        else:
            project_table.add_row(
                "start_superdirt.scd",
                "[red]✗[/red]",
                "Missing - SuperDirt won't load custom samples",
            )
            all_passed = False

        console.print(project_table)
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


def _analyze_single_file(file_path: Path) -> dict:
    """Analyze a single audio file. For use in parallel processing."""
    from datetime import datetime
    from audiomancer.analyzers.basic import get_basic_metadata
    from audiomancer.analyzers.spectral import extract_spectral_features
    from audiomancer.analyzers.rhythm import extract_rhythm_features
    from audiomancer.analyzers.tonal import extract_tonal_features
    from audiomancer.analyzers.embeddings import extract_audio_embedding
    from audiomancer.analyzers.classifier import classify_instrument
    import librosa

    # Extract basic metadata
    basic = get_basic_metadata(file_path)

    # Load audio for feature extraction
    audio, sr = librosa.load(str(file_path), sr=None, mono=False)

    # Extract features
    spectral = extract_spectral_features(audio, sr)
    rhythm = extract_rhythm_features(audio, sr)
    tonal = extract_tonal_features(audio, sr)

    # Classify instrument
    classification = classify_instrument(audio, sr)

    # Extract embedding
    embedding = extract_audio_embedding(audio, sr)

    # Combine all metadata
    sample_metadata = {
        'file_path': str(file_path.absolute()),
        **basic,
        **spectral,
        **rhythm,
        **tonal,
        'instrument_type': classification['instrument_type'],
        'instrument_confidence': classification['confidence'],
        'created_at': datetime.now(),
        'updated_at': datetime.now(),
    }

    return {
        'metadata': sample_metadata,
        'embedding': embedding,
        'file_hash': basic['file_hash'],
    }


@app.command()
def scan(
    path: Optional[Path] = typer.Argument(None, help="Directory to scan"),
    recursive: bool = typer.Option(True, help="Scan subdirectories"),
    workers: int = typer.Option(1, "--workers", "-w", help="Number of parallel workers (default: 1)"),
):
    """Index sample/synth folders."""
    import time
    from datetime import datetime

    # Lazy imports to avoid heavy dependencies at startup
    from audiomancer.config import load_config
    from audiomancer.storage.db import SampleStore
    from audiomancer.storage.vectors import LanceDBVectorStore

    start_time = time.time()

    # Load config
    config = load_config()

    # Determine scan paths
    scan_paths = []
    if path:
        scan_paths = [path]
    else:
        # Use configured source paths
        scan_paths.extend(config.sources.samples.paths)
        scan_paths.extend(config.sources.synths.paths)

    if not scan_paths:
        console.print("[yellow]No paths to scan. Specify a path or configure sources in config.yaml[/yellow]")
        return

    # Find audio files
    audio_extensions = {'.wav', '.flac', '.mp3', '.ogg', '.aiff', '.aif'}
    scd_extensions = {'.scd'}

    all_files = []
    for scan_path in scan_paths:
        if not scan_path.exists():
            console.print(f"[yellow]Path does not exist: {scan_path}[/yellow]")
            continue

        if recursive:
            for ext in audio_extensions:
                all_files.extend(scan_path.rglob(f'*{ext}'))
        else:
            for ext in audio_extensions:
                all_files.extend(scan_path.glob(f'*{ext}'))

    if not all_files:
        console.print(f"[yellow]No audio files found in {len(scan_paths)} path(s)[/yellow]")
        console.print(f"Scanned: {', '.join(str(p) for p in scan_paths)}")
        return

    # Initialize stores
    sample_store = SampleStore(str(config.storage.db_path))
    vector_store = LanceDBVectorStore(config.storage.embeddings_path)

    # Scan files with progress bar
    scanned = 0
    errors = 0
    skipped = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(f"Scanning {len(all_files)} files...", total=len(all_files))

        if workers > 1:
            # Parallel processing with ProcessPoolExecutor
            from concurrent.futures import ProcessPoolExecutor, as_completed

            # Filter out already-indexed files first (quick hash check)
            from audiomancer.analyzers.basic import get_basic_metadata

            files_to_process = []
            for file_path in all_files:
                try:
                    # Quick hash check
                    basic = get_basic_metadata(file_path)
                    if sample_store.get_by_hash(basic['file_hash']):
                        skipped += 1
                        progress.advance(task)
                    else:
                        files_to_process.append(file_path)
                except Exception as e:
                    errors += 1
                    console.print(f"[red]Error checking {file_path.name}: {e}[/red]")
                    progress.advance(task)

            # Process files in parallel
            with ProcessPoolExecutor(max_workers=workers) as executor:
                # Submit all analysis jobs
                future_to_file = {
                    executor.submit(_analyze_single_file, file_path): file_path
                    for file_path in files_to_process
                }

                # Process results as they complete
                for future in as_completed(future_to_file):
                    file_path = future_to_file[future]
                    try:
                        progress.update(task, description=f"Processing {file_path.name}...")
                        result = future.result()

                        # Store sample (cast dict to SampleMetadata)
                        sample_id = sample_store.add(cast(SampleMetadata, result['metadata']))

                        # Store embedding
                        if result['embedding'] is not None:
                            vector_store.add_embedding(sample_id, result['embedding'])

                        scanned += 1

                    except Exception as e:
                        errors += 1
                        console.print(f"[red]Error processing {file_path.name}: {e}[/red]")

                    progress.advance(task)

        else:
            # Sequential processing (original code)
            from audiomancer.analyzers.basic import get_basic_metadata
            from audiomancer.analyzers.spectral import extract_spectral_features
            from audiomancer.analyzers.rhythm import extract_rhythm_features
            from audiomancer.analyzers.tonal import extract_tonal_features
            from audiomancer.analyzers.embeddings import extract_audio_embedding
            from audiomancer.analyzers.classifier import classify_instrument
            import librosa

            for file_path in all_files:
                try:
                    progress.update(task, description=f"Analyzing {file_path.name}...")

                    # Extract basic metadata
                    basic = get_basic_metadata(file_path)

                    # Check if already in database
                    existing = sample_store.get_by_hash(basic['file_hash'])
                    if existing:
                        skipped += 1
                        progress.advance(task)
                        continue

                    # Load audio for feature extraction
                    audio, sr = librosa.load(str(file_path), sr=None, mono=False)

                    # Extract features
                    spectral = extract_spectral_features(audio, sr)
                    rhythm = extract_rhythm_features(audio, sr)
                    tonal = extract_tonal_features(audio, sr)

                    # Classify instrument
                    classification = classify_instrument(audio, sr)

                    # Extract embedding
                    embedding = extract_audio_embedding(audio, sr)

                    # Combine all metadata
                    sample_metadata = {
                        'file_path': str(file_path.absolute()),
                        **basic,
                        **spectral,
                        **rhythm,
                        **tonal,
                        'instrument_type': classification['instrument_type'],
                        'instrument_confidence': classification['confidence'],
                        'created_at': datetime.now(),
                        'updated_at': datetime.now(),
                    }

                    # Store sample (cast dict to SampleMetadata)
                    sample_id = sample_store.add(cast(SampleMetadata, sample_metadata))

                    # Store embedding
                    if embedding is not None:
                        vector_store.add_embedding(sample_id, embedding)

                    scanned += 1

                except Exception as e:
                    errors += 1
                    # Show error with details from AudiomancerError
                    from audiomancer.errors import AudiomancerError
                    error_msg = str(e)
                    if isinstance(e, AudiomancerError):
                        if 'stage' in e.details:
                            error_msg += f" (stage: {e.details['stage']})"
                        if 'error' in e.details:
                            error_msg += f"\n  Cause: {e.details['error']}"
                    console.print(f"[red]Error: {file_path.name}: {error_msg}[/red]")

                progress.advance(task)

    # Print summary
    elapsed = time.time() - start_time
    console.print("\n[bold green]Scan complete![/bold green]")
    console.print(f"Files scanned: {scanned}")
    console.print(f"Files skipped (already indexed): {skipped}")
    console.print(f"Errors: {errors}")
    console.print(f"Time taken: {elapsed:.1f}s")


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    limit: int = typer.Option(20, help="Maximum results"),
    bpm_min: Optional[float] = typer.Option(None, "--bpm-min", help="Minimum BPM"),
    bpm_max: Optional[float] = typer.Option(None, "--bpm-max", help="Maximum BPM"),
    key: Optional[str] = typer.Option(None, "--key", help="Musical key filter"),
    instrument: Optional[str] = typer.Option(None, "--instrument", help="Instrument type filter"),
    mood: Optional[str] = typer.Option(None, "--mood", help="Mood filter"),
):
    """Quick search from command line."""
    from audiomancer.config import load_config
    from audiomancer.storage.db import SampleStore
    import os

    # Get database path from env var or config
    db_path = os.environ.get("AUDIOMANCER_DB_PATH")
    if not db_path:
        config = load_config()
        db_path = str(config.storage.db_path)

    # Initialize store
    store = SampleStore(db_path)

    # Perform search
    results = store.search(
        query=query,
        instrument_type=instrument,
        bpm_min=bpm_min,
        bpm_max=bpm_max,
        key=key,
        mood=[mood] if mood else None,
        limit=limit,
        offset=0,
    )

    # Handle empty results
    if not results:
        console.print("[yellow]No results found[/yellow]")
        return

    # Display results in a Rich table
    table = Table(title=f"Search Results ({len(results)} found)")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="green")
    table.add_column("BPM", style="magenta")
    table.add_column("Key", style="blue")
    table.add_column("Instrument", style="yellow")
    table.add_column("Duration", style="white")

    for sample in results:
        # Extract filename from path
        name = Path(sample.get("file_path", "unknown")).name

        # Format BPM
        bpm_str = f"{sample.get('bpm', 0):.1f}" if sample.get('bpm') else "-"

        # Format key
        key_str = sample.get('key') or "-"

        # Format instrument
        instrument_str = sample.get('instrument_type') or "-"

        # Format duration (convert ms to seconds)
        duration_ms = sample.get('duration_ms', 0)
        duration_str = f"{duration_ms / 1000:.2f}s"

        table.add_row(
            sample.get('id', 'unknown'),
            name,
            bpm_str,
            key_str,
            instrument_str,
            duration_str,
        )

    console.print(table)


@app.command()
def stats():
    """Show library statistics."""
    from audiomancer.config import load_config
    from audiomancer.storage.db import SampleStore

    # Load config and database
    config = load_config()
    store = SampleStore(str(config.storage.db_path))

    # Get total count
    total_samples = store.count()

    # Handle empty database
    if total_samples == 0:
        console.print("[yellow]No samples in database[/yellow]")
        console.print("\n[dim]Run 'audiomancer scan' to analyze audio files[/dim]")
        return

    # Get distributions
    instrument_dist = store.get_instrument_distribution()
    bpm_dist = store.get_bpm_distribution()
    key_dist = store.get_key_distribution()

    # Display overview panel
    overview_text = f"[bold]Total Samples:[/bold] {total_samples}"
    console.print(Panel(overview_text, title="Library Overview", border_style="blue"))

    # Display instrument distribution
    if instrument_dist:
        instrument_table = Table(title="Instrument Types", show_header=True, header_style="bold magenta")
        instrument_table.add_column("Instrument", style="cyan")
        instrument_table.add_column("Count", justify="right", style="green")

        # Sort by count descending
        sorted_instruments = sorted(instrument_dist.items(), key=lambda x: x[1], reverse=True)
        for instrument, count in sorted_instruments:
            instrument_table.add_row(instrument or "(unknown)", str(count))

        console.print(instrument_table)

    # Display BPM distribution
    if any(count > 0 for count in bpm_dist.values()):
        bpm_table = Table(title="BPM Distribution", show_header=True, header_style="bold magenta")
        bpm_table.add_column("BPM Range", style="cyan")
        bpm_table.add_column("Count", justify="right", style="green")

        # Display in order
        bpm_ranges = ['<100', '100-120', '120-140', '140-160', '160+']
        for bpm_range in bpm_ranges:
            count = bpm_dist.get(bpm_range, 0)
            if count > 0:
                bpm_table.add_row(bpm_range, str(count))

        console.print(bpm_table)

    # Display key distribution
    if key_dist:
        key_table = Table(title="Musical Keys", show_header=True, header_style="bold magenta")
        key_table.add_column("Key", style="cyan")
        key_table.add_column("Count", justify="right", style="green")

        # Sort by count descending
        sorted_keys = sorted(key_dist.items(), key=lambda x: x[1], reverse=True)
        for key, count in sorted_keys:
            key_table.add_row(key or "(unknown)", str(count))

        console.print(key_table)


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
