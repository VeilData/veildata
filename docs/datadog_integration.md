# Integration Guide: VeilData + Datadog Agent

This guide explains how to use `veildata` to sanitize logs **before** they are collected by the Datadog Agent.

## Architecture

Since the Datadog Agent is a closed-source binary (typically), you cannot "plug in" Python code directly. Instead, you use `veildata pipe` as a middleware to sanitize your application's output stream before it reaches the Agent.

**Flow:** `[Your App] -> (stdout) -> [VeilData Pipe] -> (clean logs) -> [Datadog Agent]`

## Method 1: The Sidecar File (Recommended)

The most robust method is to have VeilData write to a file, which the Datadog Agent then "tails".

### 1. Configure the Agent
In your Datadog Agent configuration (e.g., `conf.d/myapp.d/conf.yaml`), add a log source tracking the **clean** file:

```yaml
logs:
  - type: file
    path: /var/log/myapp/clean.log
    service: myapp
    source: python
```

### 2. Run Your Application
Pipe your application's output through `veildata` and write to the target file.

```bash
# Standard Output Redirection
python myapp.py | veildata pipe > /var/log/myapp/clean.log

# OR using tee to see logs while writing
python myapp.py | veildata pipe | tee /var/log/myapp/clean.log
```

*Note: Ensure `veildata` has a valid configuration (e.g. `~/.veildata/config.toml` or via `--config`).*

## Method 2: Network Forwarding

If you prefer not to write to disk, you can pipe logs directly to the Agent's network listener (if enabled).

### 1. Configure the Agent
Enable UDP or TCP log reception in `datadog.yaml`:

```yaml
logs_config:
  use_tcp: true
  tcp_forward_port: 10518
```

### 2. Pipe to Network (using `nc`)

```bash
python myapp.py | veildata pipe | nc localhost 10518
```

## Method 3: Docker / Kubernetes

In a containerized environment, you can use `veildata` as the entrypoint or in a pipe chain within `CMD`.

**Dockerfile:**
```dockerfile
FROM python:3.9
RUN pip install veildata

# Copy your app and config
COPY . /app
WORKDIR /app

# Pipeline execution
CMD ["sh", "-c", "python app.py | veildata pipe"]
```

The Docker logging driver will capture the **sanitized** stdout from the container, which the Datadog Agent (running on the host or as a sidecar) will then collect.
