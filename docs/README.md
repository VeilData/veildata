# VeilData Sphinx Documentation

This directory contains the Sphinx documentation for VeilData.

## Building the Documentation

### Prerequisites

Install Sphinx and required extensions:

```bash
pip install sphinx sphinx-rtd-theme
```

### Build HTML Documentation

```bash
cd docs
make html
```

The generated HTML documentation will be in `_build/html/`.

### View Documentation

Open `_build/html/index.html` in your browser, or use a local server:

```bash
cd _build/html
python -m http.server 8000
```

Then navigate to `http://localhost:8000`

## Documentation Structure

- `index.rst` - Main documentation index
- `quickstart.rst` - Getting started guide
- `streaming.rst` - Streaming redaction documentation
- `api.rst` - API reference (auto-generated from docstrings)
- `cli.rst` - Command-line interface documentation
- `conf.py` - Sphinx configuration

## Auto-generated Documentation

The API reference is auto-generated from docstrings using Sphinx autodoc. Make sure all modules have proper docstrings in Google or NumPy style format.

## Adding New Pages

1. Create a new `.rst` file in the `docs/` directory
2. Add it to the `toctree` in `index.rst`
3. Rebuild the documentation

## Deployment

To deploy to Read the Docs:

1. Create a `.readthedocs.yaml` configuration file in the project root
2. Push to GitHub
3. Import the project on Read the Docs

Example `.readthedocs.yaml`:

```yaml
version: 2

build:
  os: ubuntu-22.04
  tools:
    python: "3.10"

sphinx:
  configuration: docs/conf.py

python:
  install:
    - requirements: docs/requirements.txt
    - method: pip
      path: .
```

Create `docs/requirements.txt`:

```
sphinx>=7.0.0
sphinx-rtd-theme>=2.0.0
```
