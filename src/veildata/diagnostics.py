import os
import platform
import shutil
import subprocess
from pathlib import Path

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
    try:
        from veildata import __version__
        return ("VeilData Version", __version__, "OK")
    except Exception:
        return ("VeilData Version", "Unknown", "WARN")

def check_engines(list_engines):
    try:
        engines = list_engines()
        names = ", ".join([e[0] for e in engines])
        return ("Masking Engines", names, "OK")
    except:
        return ("Masking Engines", "Error loading engines", "FAIL")

def check_write_permissions():
    writable = os.access(".", os.W_OK)
    return ("Working Directory", "Writable" if writable else "No Write Access",
            "OK" if writable else "FAIL")

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
            text=True, stderr=subprocess.STDOUT
        )
        return ("GHCR Image", "Pullable", "OK")
    except Exception as e:
        return ("GHCR Image", f"Unavailable ({e})", "WARN")
