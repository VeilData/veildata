from typing import Optional

import typer

from veildata.engine import build_masker, build_unmasker, list_available_maskers

app = typer.Typer(help="VeilData — configurable PII masking and unmasking CLI")


@app.command()
def mask(
    input: str = typer.Argument(..., help="Input text or path to file"),
    output: Optional[str] = typer.Option(
        None, "--output", "-o", help="Write masked text to this file"
    ),
    config: Optional[str] = typer.Option(
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
):
    """Mask PII in text or files using a configurable engine."""
    masker, store = build_masker(method, config=config, verbose=verbose)

    # Read input
    try:
        with open(input, "r") as f:
            text = f.read()
    except FileNotFoundError:
        text = input  # treat as raw text input

    # Mask
    masked = masker(text)
    if not dry_run:
        if output:
            with open(output, "w") as f:
                f.write(masked)
            if verbose:
                typer.echo(f"✅ Masked output written to {output}")
        else:
            typer.echo(masked)

        if store_path:
            store.save(store_path)
            if verbose:
                typer.echo(f"🧠 TokenStore saved to {store_path}")
    else:
        typer.echo(masked)
        typer.echo("\n(Dry run — no file written.)")


@app.command()
def unmask(
    input: str = typer.Argument(..., help="Masked text or file path"),
    store_path: str = typer.Option(
        ..., "--store", "-s", help="Path to stored TokenStore mapping"
    ),
):
    """Unmask text using a stored TokenStore."""
    unmasker = build_unmasker(store_path)

    try:
        with open(input, "r") as f:
            text = f.read()
    except FileNotFoundError:
        text = input

    typer.echo(unmasker(text))


@app.command()
def inspect():
    """Show available masking engines."""
    typer.echo("Available masking engines:")
    for name in list_available_maskers():
        typer.echo(f"  • {name}")


def main():
    app()


if __name__ == "__main__":
    main()
