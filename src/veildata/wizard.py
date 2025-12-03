from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

console = Console()


def run_wizard():
    """Run the interactive setup wizard."""
    console.print(
        Panel.fit(
            "[bold cyan]Welcome to VeilData![/]\n\n"
            "It looks like this is your first time running VeilData.\n"
            "Let's set up a default configuration for you.",
            title="Setup Wizard",
        )
    )

    # 1. Choose Redaction Engine
    engine = Prompt.ask(
        "Which redaction engine would you like to use by default?",
        choices=["regex", "spacy", "hybrid"],
        default="regex",
    )

    # 2. Choose Output Behavior
    # For now, we'll just stick to engine selection as the main config
    # But we can add more options later.

    # 3. Generate Config
    config_dir = Path.home() / ".veildata"
    config_path = config_dir / "config.toml"

    config_content = f'# VeilData Configuration\n\nmethod = "{engine}"\n'

    if engine in ["spacy", "hybrid"]:
        model = Prompt.ask(
            "Which spaCy model should be used?",
            default="en_core_web_lg",
        )
        config_content += f'\n[ml.spacy]\nenabled = true\nmodel = "{model}"\n'

    console.print(f"\n[bold]Configuration to be written to {config_path}:[/]")
    console.print(Panel(config_content, title="config.toml"))

    if Confirm.ask("Save this configuration?", default=True):
        config_dir.mkdir(parents=True, exist_ok=True)
        config_path.write_text(config_content)
        console.print(f"[green]Configuration saved to {config_path}[/]")
    else:
        console.print("[yellow]Configuration not saved.[/]")
