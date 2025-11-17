from typing import Optional

import typer
from rich.table import Table
from rich.console import Console
from rich.panel import Panel

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
):
    from veildata.engine import build_masker

    """Mask PII in text or files using a configurable engine."""
    masker, store = build_masker(method, config_path=config_path, verbose=verbose)

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

def version():
    """Show VeilData version."""
    typer.echo(f"VeilData {__version__}")


def main():
    app()


if __name__ == "__main__":
    import sys

    sys.exit(main())
