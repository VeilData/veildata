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
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing files"),
    explain: bool = typer.Option(
        False, "--explain", help="Output detection explanations as JSON"
    ),
):
    from pathlib import Path

    from veildata.engine import build_masker

    """Mask PII in text or files using a configurable engine."""

    # Check for existing files
    if not force:
        if output and Path(output).exists():
            console.print(
                f"[red]Error: Output file '{output}' already exists. Use --force to overwrite.[/]"
            )
            raise typer.Exit(code=1)

        # Only check store_path if we are actually going to write to it (i.e., not dry_run)
        if not dry_run and store_path and Path(store_path).exists():
            console.print(
                f"[red]Error: TokenStore file '{store_path}' already exists. Use --force to overwrite.[/]"
            )
            raise typer.Exit(code=1)

    # Check for default config if none provided
    if not config_path:
        default_config = Path.home() / ".veildata" / "config.toml"
        if not default_config.exists():
            # Only prompt if interactive (stdin is a tty)
            import sys

            from rich.prompt import Confirm

            if sys.stdin.isatty():
                if Confirm.ask(
                    "[yellow]No configuration found. Would you like to run the setup wizard?[/]",
                    default=True,
                ):
                    from veildata.wizard import run_wizard

                    run_wizard()
                    # After wizard, try to use the new config
                    if default_config.exists():
                        config_path = str(default_config)

    if no_ml:
        detect_mode = "rules"

    from veildata.diagnostics import print_error
    from veildata.engine import load_config
    from veildata.exceptions import ConfigMissingError

    # Load config early to check for method override
    try:
        config = load_config(config_path, verbose=verbose)

        # If method wasn't explicitly set via CLI and config has a method, use it
        # We detect CLI default by checking if it's "regex" (the default)
        # This is a heuristic - ideally typer would tell us if the value was defaulted
        if method == "regex" and config.get("method"):
            method = config["method"]
            if verbose:
                console.print(f"[veildata] Using method '{method}' from config")

        # Map user-friendly names to internal engine names
        method_map = {
            "spacy": "ner_spacy",
            "bert": "ner_bert",
        }
        method = method_map.get(method, method)

        # Handle "hybrid" specially - it needs patterns + ML
        if method == "hybrid":
            # For hybrid mode, we need to use the detector-based approach
            # This requires patterns in the config
            if not config.get("patterns") and not config.get("pattern"):
                # Add default patterns for hybrid mode
                from veildata.defaults import DEFAULT_PATTERNS

                config["patterns"] = DEFAULT_PATTERNS
            # Use regex method but set detect_mode to hybrid
            method = "regex"
            if detect_mode == "rules":  # Only override if not explicitly set
                detect_mode = "hybrid"

        # Handle "regex" mode - if no patterns are provided, use defaults
        # This fixes the issue where wizard-generated config has no patterns
        if (
            method == "regex"
            and not config.get("patterns")
            and not config.get("pattern")
        ):
            from veildata.defaults import DEFAULT_PATTERNS

            config["patterns"] = DEFAULT_PATTERNS
    except ConfigMissingError as e:
        print_error(
            console,
            "Configuration Error",
            str(e),
            suggestion="Please check the file path or run without --config to use defaults.",
        )
        raise typer.Exit(code=1)

    try:
        masker, store = build_masker(
            method,
            detect_mode=detect_mode,
            config_path=config_path,
            ml_config_path=ml_config,
            verbose=verbose,
            config_dict=config,
        )
    except ConfigMissingError as e:
        print_error(
            console,
            "Configuration Error",
            str(e),
            suggestion="Please check the file path or run without --config to use defaults.",
        )
        raise typer.Exit(code=1)
    except OSError as e:
        # This catches model download failures (e.g. user declined download)
        print_error(
            console,
            "Model Error",
            str(e),
            suggestion="Run with --verbose to see more details or try installing the model manually.",
        )
        raise typer.Exit(code=1)

    # Read input
    try:
        with open(input, "r") as f:
            text = f.read()
    except FileNotFoundError:
        text = input  # treat as raw text input

    # Handle explain mode - output JSON instead of masking
    if explain:
        import json

        # For explain mode, we need a DetectionPipeline with the masker
        if hasattr(masker, "detector"):
            # It's already a DetectionPipeline
            explanation = masker.explain(text)
        elif hasattr(masker, "modules"):
            # It's a Compose - not ideal for explain mode
            console.print(
                "[yellow]Warning: --explain works best with single detector modes (regex, spacy, bert)[/]"
            )
            # Try to extract first module if it's a pipeline
            first_module = masker.modules[0] if masker.modules else None
            if hasattr(first_module, "explain"):
                explanation = first_module.explain(text)
            else:
                console.print(
                    "[red]Error: Cannot explain with this masking configuration[/]"
                )
                raise typer.Exit(code=1)
        else:
            console.print(
                "[red]Error: --explain is only supported in detector-based modes[/]"
            )
            raise typer.Exit(code=1)

        json_output = json.dumps(explanation, indent=2)
        if output:
            with open(output, "w") as f:
                f.write(json_output)
            if verbose:
                console.print(f"✅ Explanation written to {output}")
        else:
            console.print(json_output)
        return

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


@app.command("init", help="Run the first-time setup wizard.")
def init():
    """Run the interactive setup wizard."""
    from veildata.wizard import run_wizard

    run_wizard()


def main():
    app()


if __name__ == "__main__":
    import sys

    sys.exit(main())
