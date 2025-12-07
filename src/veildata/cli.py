import time
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

app = typer.Typer(help="VeilData — configurable PII redaction and revealing CLI")
console = Console()


@app.command("redact", help="Redact sensitive data from a file or stdin.")
def redact(
    input: str = typer.Argument(..., help="Input text or path to file"),
    output: Optional[str] = typer.Option(
        None, "--output", "-o", help="Write redacted text to this file"
    ),
    config_path: Optional[str] = typer.Option(
        None, "--config", "-c", help="Path to YAML/JSON config file"
    ),
    method: str = typer.Option(
        "regex",
        "--method",
        "-m",
        help="Redaction engine: regex | ner_spacy | ner_bert | all",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be redacted without replacing text"
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
    show_time: bool = typer.Option(
        False, "--time", help="Show timing information for the operation"
    ),
    stream: bool = typer.Option(
        False, "--stream", "-s", help="Enable streaming mode for large files"
    ),
    chunk_size: int = typer.Option(
        4096, "--chunk-size", help="Chunk size for streaming mode (bytes)"
    ),
    overlap: int = typer.Option(
        512, "--overlap", help="Overlap size for cross-chunk entity detection"
    ),
    is_json: bool = typer.Option(
        False, "--json", help="Treat input as JSON and redact values recursively"
    ),
):
    from pathlib import Path

    from veildata.engine import build_redactor
    from veildata.utils import Timer

    """Redact PII in text or files using a configurable engine."""

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

    # Initialize timing if requested
    load_timer = Timer() if show_time else None
    process_timer = Timer() if show_time else None

    if show_time:
        load_timer.start()

    try:
        redactor, store = build_redactor(
            method,
            detect_mode=detect_mode,
            config_path=config_path,
            ml_config_path=ml_config,
            verbose=verbose,
            config_dict=config,
        )

        if show_time:
            load_timer.stop()
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

    # Handle explain mode - output JSON instead of redacting
    if explain:
        import json

        # For explain mode, we need a DetectionPipeline with the redactor
        if hasattr(redactor, "detector"):
            # It's already a DetectionPipeline
            explanation = redactor.explain(text)
        elif hasattr(redactor, "modules"):
            # It's a Compose - not ideal for explain mode
            console.print(
                "[yellow]Warning: --explain works best with single detector modes (regex, spacy, bert)[/]"
            )
            # Try to extract first module if it's a pipeline
            first_module = redactor.modules[0] if redactor.modules else None
            if hasattr(first_module, "explain"):
                explanation = first_module.explain(text)
            else:
                console.print(
                    "[red]Error: Cannot explain with this redaction configuration[/]"
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

    # Handle streaming mode
    if stream:
        from veildata.streaming_buffer import StreamingRedactionBuffer

        # Streaming mode requires file input (not raw text)
        try:
            input_file = open(input, "r")
        except FileNotFoundError:
            console.print(
                "[red]Error: Streaming mode requires a valid file path, not raw text.[/]"
            )
            raise typer.Exit(code=1)

        # Create streaming buffer
        buffer = StreamingRedactionBuffer(redactor, overlap_size=overlap, store=store)

        if show_time:
            process_timer.start()

        # Open output file if specified
        output_file = open(output, "w") if output else None

        try:
            # Process file in chunks
            chunks_processed = 0
            while True:
                chunk = input_file.read(chunk_size)
                if not chunk:
                    break

                # Process chunk
                redacted_chunk = buffer.add_chunk(chunk)

                # Write output
                if redacted_chunk:
                    if output_file:
                        output_file.write(redacted_chunk)
                    elif not dry_run:
                        console.print(redacted_chunk, end="")

                chunks_processed += 1

            # Finalize buffer
            final_chunk = buffer.finalize()
            if final_chunk:
                if output_file:
                    output_file.write(final_chunk)
                elif not dry_run:
                    console.print(final_chunk, end="")

        finally:
            input_file.close()
            if output_file:
                output_file.close()

        if show_time:
            process_timer.stop()

        # Save store if requested
        if store_path and not dry_run:
            store.save(store_path)
            if verbose:
                console.print(f"\n🧠 TokenStore saved to {store_path}")

        # Show stats
        if verbose:
            stats = buffer.get_stats()
            console.print(f"\n📊 Processed {chunks_processed} chunks")
            console.print(f"  Input: {stats['total_input_chars']} chars")
            console.print(f"  Output: {stats['total_output_chars']} chars")
            console.print(f"  Entities redacted: {stats['total_entities_redacted']}")

        # Display timing
        if show_time:
            load_ms = load_timer.elapsed * 1000 if load_timer else 0
            process_ms = process_timer.elapsed * 1000
            total_ms = load_ms + process_ms
            console.print(
                f"\n⏱️  [dim]Load: {load_ms:.2f}ms | Processing: {process_ms:.2f}ms | Total: {total_ms:.2f}ms[/]"
            )

        return

    # Measure processing time
    if show_time:
        process_timer.start()

    if is_json:
        import json

        from veildata.utils.traversal import traverse_and_redact

        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            print_error(console, "JSON Error", str(e))
            raise typer.Exit(code=1)

        result_data = traverse_and_redact(data, redactor)
        redacted = json.dumps(result_data, indent=2)
    else:
        redacted = redactor(text)

    if show_time:
        process_timer.stop()

    if not dry_run:
        if output:
            with open(output, "w") as f:
                f.write(redacted)
            if verbose:
                console.print(f"✅ Redacted output written to {output}")
        else:
            console.print(redacted)

        if store_path:
            store.save(store_path)
            if verbose:
                console.print(f"🧠 TokenStore saved to {store_path}")
    elif preview:
        console.print(Panel.fit(redacted, title="[bold cyan]Preview[/]"))
    else:
        console.print(redacted)
        console.print("\n(Dry run — no file written.)")

    # Display timing information if requested
    if show_time:
        load_ms = load_timer.elapsed * 1000
        process_ms = process_timer.elapsed * 1000
        total_ms = load_ms + process_ms
        console.print(
            f"\n⏱️  [dim]Load: {load_ms:.2f}ms | Processing: {process_ms:.2f}ms | Total: {total_ms:.2f}ms[/]"
        )


@app.command("reveal", help="Reverse redaction using stored token mappings.")
def reveal(
    input: str = typer.Argument(..., help="Redacted text or file path"),
    store_path: str = typer.Option(
        ..., "--store", "-s", help="Path to stored TokenStore mapping"
    ),
    show_time: bool = typer.Option(
        False, "--time", help="Show timing information for the operation"
    ),
):
    from veildata.engine import build_revealer
    from veildata.utils import Timer

    """Reveal text using a stored TokenStore."""

    # Initialize timing if requested
    load_timer = Timer() if show_time else None
    process_timer = Timer() if show_time else None

    if show_time:
        load_timer.start()

    revealer = build_revealer(store_path)

    if show_time:
        load_timer.stop()

    try:
        with open(input, "r") as f:
            text = f.read()
    except FileNotFoundError:
        text = input

    # Measure processing time
    if show_time:
        process_timer.start()

    result = revealer(text)

    if show_time:
        process_timer.stop()

    typer.echo(result)

    # Display timing information if requested
    if show_time:
        load_ms = load_timer.elapsed * 1000
        process_ms = process_timer.elapsed * 1000
        total_ms = load_ms + process_ms
        console.print(
            f"\n⏱️  [dim]Load: {load_ms:.2f}ms | Processing: {process_ms:.2f}ms | Total: {total_ms:.2f}ms[/]"
        )


@app.command("benchmark", help="Run performance benchmarks.")
def benchmark(
    method: str = typer.Option(
        "regex", "--method", "-m", help="Redaction engine to benchmark"
    ),
    iterations: int = typer.Option(
        100, "--iterations", "-n", help="Number of iterations"
    ),
    size: str = typer.Option(
        "medium", "--size", "-s", help="Input size: small | medium | large"
    ),
):
    """Measure performance of redaction engines."""
    import json
    import statistics
    from pathlib import Path

    from veildata.engine import build_redactor
    from veildata.utils import Timer

    console.print(
        f"[bold]Running benchmark for method='{method}' with {iterations} iterations on '{size}' input...[/]"
    )

    # Generate sample data
    sample_text = {
        "small": "My email is test@example.com and phone is 555-0123.",
        "medium": "My email is test@example.com and phone is 555-0123. " * 50,
        "large": "My email is test@example.com and phone is 555-0123. " * 1000,
    }.get(size, "My email is test@example.com")

    # Prepare config with default patterns for benchmark
    from veildata.defaults import DEFAULT_PATTERNS

    config = {"patterns": DEFAULT_PATTERNS}

    # Measure load time
    with Timer() as load_timer:
        redactor, _ = build_redactor(method, verbose=False, config_dict=config)

    load_time_ms = load_timer.elapsed * 1000
    console.print(f"Model Load Time: [green]{load_time_ms:.2f} ms[/]")

    # Warmup
    redactor(sample_text)

    # Measure execution time
    times = []
    with console.status("[bold green]Benchmarking..."):
        for _ in range(iterations):
            with Timer() as t:
                redactor(sample_text)
            times.append(t.elapsed * 1000)

    avg_time = statistics.mean(times)
    p95_time = statistics.quantiles(times, n=20)[18]  # 95th percentile
    p99_time = statistics.quantiles(times, n=100)[98]  # 99th percentile

    # Print results
    table = Table(title="Benchmark Results")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Method", method)
    table.add_row("Input Size", f"{len(sample_text)} chars")
    table.add_row("Iterations", str(iterations))
    table.add_row("Load Time", f"{load_time_ms:.2f} ms")
    table.add_row("Avg Latency", f"{avg_time:.2f} ms")
    table.add_row("P95 Latency", f"{p95_time:.2f} ms")
    table.add_row("P99 Latency", f"{p99_time:.2f} ms")

    console.print(table)

    # Save results
    bench_dir = Path(".bench")
    bench_dir.mkdir(exist_ok=True)

    result = {
        "timestamp": str(time.time()),
        "method": method,
        "input_size": len(sample_text),
        "iterations": iterations,
        "load_time_ms": load_time_ms,
        "avg_latency_ms": avg_time,
        "p95_latency_ms": p95_time,
        "p99_latency_ms": p99_time,
    }

    output_file = bench_dir / "last_run.json"
    output_file.write_text(json.dumps(result, indent=2))
    console.print(f"\n[dim]Results saved to {output_file}[/]")


@app.command("inspect", help="Show available redaction engines and config paths.")
def inspect():
    """Show available redaction engines."""

    engines = list_engines()

    table = Table(title="Available Redaction Engines")
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
