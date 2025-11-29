import os
import platform
import shutil
import subprocess


def check_python():
    version = platform.python_version()
    ok = version.startswith("3.")
    return ("Python", version, "OK" if ok else "WARN")


def check_os():
    system = f"{platform.system()} {platform.release()}"
    return ("OS", system, "OK")


def check_spacy():
    try:
        import spacy

        models = spacy.util.get_installed_models()
        result = ", ".join(models) if models else "No models installed"
        return ("spaCy", result, "OK")
    except Exception as e:
        return ("spaCy", f"Unavailable ({e})", "WARN")


def check_version():
    from veildata.cli import version

    __version__ = version()
    try:
        return ("VeilData Version", __version__, "OK")
    except Exception:
        return ("VeilData Version", "Unknown", "WARN")


def check_engines(list_engines):
    try:
        engines = list_engines()
        names = ", ".join([e[0] for e in engines])
        return ("Masking Engines", names, "OK")
    except Exception:
        return ("Masking Engines", "Error loading engines", "FAIL")


def check_write_permissions():
    writable = os.access(".", os.W_OK)
    return (
        "Working Directory",
        "Writable" if writable else "No Write Access",
        "OK" if writable else "FAIL",
    )


def check_docker():
    docker_path = shutil.which("docker")
    if not docker_path:
        return ("Docker", "Not installed", "WARN")
    try:
        version = subprocess.check_output(["docker", "--version"], text=True).strip()
        return ("Docker", version, "OK")
    except Exception as e:
        return ("Docker", f"Error ({e})", "FAIL")


def check_ghcr():
    try:
        subprocess.check_output(
            ["docker", "manifest", "inspect", "ghcr.io/veildata/veildata:latest"],
            text=True,
            stderr=subprocess.STDOUT,
        )
        return ("GHCR Image", "Pullable", "OK")
    except Exception as e:
        return ("GHCR Image", f"Unavailable ({e})", "WARN")


def print_error(console, title: str, message: str, suggestion: str = None):
    """
    Print a formatted error message using Rich.

    Args:
        console: The Rich Console instance.
        title: The title of the error (e.g., "Configuration Error").
        message: The main error message.
        suggestion: An optional suggestion for the user.
    """
    from rich.panel import Panel
    from rich.text import Text

    content = Text()
    content.append(f"{message}\n", style="white")

    if suggestion:
        content.append("\nSuggestion:\n", style="bold yellow")
        content.append(f"{suggestion}", style="italic yellow")

    console.print(
        Panel(
            content,
            title=f"[bold red]❌ {title}[/]",
            border_style="red",
            expand=False,
        )
    )
