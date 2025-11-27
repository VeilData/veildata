from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from veildata.diagnostics import (
    check_docker,
    check_engines,
    check_ghcr,
    check_os,
    check_python,
    check_spacy,
    check_version,
    check_write_permissions,
)
from veildata.engine import list_engines

app = typer.Typer(help="VeilData — configurable PII masking and unmasking CLI")
console = Console()


@app.command("mask", help="Redact sensitive data from a file or stdin.")
def mask(
    input: str = typer.Argument(..., help="Input text or path to file"),
    output: Optional[str] = typer.Option(
        None, "--output", "-o", help="Write masked text to this file"
    ),
    config_path: Optional[str] = typer.Option(
        None, "--config", "-c", help="Path to YAML/JSON config file"
    ),
    method: str = typer.Option(
        "regex",
        "--method",
        "-m",
        help="Masking engine: regex | ner_spacy | ner_bert | all",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be masked without replacing text"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed logs"),
    store_path: Optional[str] = typer.Option(
        None, "--store", help="Path to save reversible TokenStore mapping"
    ),
    preview: int = typer.Option(0, "--preview", help="Print N preview lines."),
    detect_mode: str = typer.Option(
        "rules",
        "--detect-mode",
        help="Detection mode: rules | ml | hybrid",
    ),
    ml_config: Optional[str] = typer.Option(
        None, "--ml-config", help="Path to ML-specific config file"
    ),
    no_ml: bool = typer.Option(
        False, "--no-ml", help="Force rules-only mode (overrides detect-mode)"
    ),
):
    from veildata.engine import build_masker

    """Mask PII in text or files using a configurable engine."""
    if no_ml:
        detect_mode = "rules"

    masker, store = build_masker(
        method,
        detect_mode=detect_mode,
        config_path=config_path,
        ml_config_path=ml_config,
        verbose=verbose,
    )

    # Read input
    try:
        with open(input, "r") as f:
            text = f.read()
    except FileNotFoundError:
        text = input  # treat as raw text input

    masked = masker(text)

    if not dry_run:
        if output:
            with open(output, "w") as f:
                f.write(masked)
            if verbose:
                console.print(f"✅ Masked output written to {output}")
        else:
            console.print(masked)

        if store_path:
            store.save(store_path)
            if verbose:
                console.print(f"🧠 TokenStore saved to {store_path}")
    elif preview:
        console.print(Panel.fit(masked, title="[bold cyan]Preview[/]"))
    else:
        console.print(masked)
        console.print("\n(Dry run — no file written.)")


@app.command("unmask", help="Reverse masking using stored token mappings.")
def unmask(
    input: str = typer.Argument(..., help="Masked text or file path"),
    store_path: str = typer.Option(
        ..., "--store", "-s", help="Path to stored TokenStore mapping"
    ),
):
    from veildata.engine import build_unmasker

    """Unmask text using a stored TokenStore."""
    unmasker = build_unmasker(store_path)

    try:
        with open(input, "r") as f:
            text = f.read()
    except FileNotFoundError:
        text = input

    typer.echo(unmasker(text))


@app.command("inspect", help="Show available masking engines and config paths.")
def inspect():
    """Show available masking engines."""

    engines = list_engines()

    table = Table(title="Available Masking Engines")
    table.add_column("Engine", style="cyan", no_wrap=True)
    table.add_column("Description", style="white")
    for name, desc in engines:
        table.add_row(name, desc)
    console.print(table)


@app.command("version", help="Show VeilData version.")
def version():
    """Show VeilData version."""
    from importlib.metadata import PackageNotFoundError, version
    from pathlib import Path

    import tomllib

    try:
        __version__ = version("package-name")
    except PackageNotFoundError:
        pyproject_path = Path(__file__).resolve().parents[2] / "pyproject.toml"
        if pyproject_path.exists():
            try:
                data = tomllib.loads(pyproject_path.read_text())
                __version__ = data.get("project", {}).get("version", "dev")
            except Exception:
                __version__ = "unknown"
    typer.echo(f"VeilData {__version__}")
    return __version__


@app.command("doctor", help="Run environment diagnostics to verify VeilData setup.")
def doctor():
    console.print(Panel.fit("[bold cyan]VeilData Environment Diagnostics[/]"))

    # Collect results from all diagnostics
    checks = [
        check_python(),
        check_os(),
        check_spacy(),
        check_version(),
        check_engines(list_engines),
        check_write_permissions(),
        check_docker(),
        check_ghcr(),
    ]

    # Render table
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Check", style="cyan", no_wrap=True)
    table.add_column("Result")
    table.add_column("Status", style="bold")

    for name, result, status in checks:
        color = {
            "OK": "green",
            "WARN": "yellow",
            "FAIL": "red",
        }[status]
        table.add_row(name, result, f"[{color}]{status}[/{color}]")

    console.print(table)

    failures = [x for x in checks if x[2] == "FAIL"]

    if failures:
        console.print(Panel.fit("[red]Some checks failed.[/]", title="Summary"))
        raise typer.Exit(code=1)

    console.print(Panel.fit("[green]All checks passed![/]", title="Summary"))


def main():
    app()


if __name__ == "__main__":
    import sys

    sys.exit(main())
