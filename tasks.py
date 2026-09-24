#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "invoke-toolkit>=0.0.59",
#     "pyyaml>=6.0",
# ]
# ///
"""Development tasks for the workshop slides."""

from __future__ import annotations

import json
import urllib.request
from html import escape
from datetime import date
import shlex
import shutil
import os
from pathlib import Path
from typing import Annotated, cast

import yaml
from invoke_toolkit import Context, script, task
from invoke_toolkit.utils.fzf import select

ROOT = Path(__file__).resolve().parent
SLIDES = ROOT / "slides.qmd"
SLIDES = SLIDES.relative_to(ROOT)

@task()
def _quarto_installed(ctx: Context):
    if not shutil.which("quarto"):
        ctx.rich_exit("quarto not found in [red]$PATH[/]")

@task(aliases=["p"], pre=[_quarto_installed])
def preview(
    ctx: Context,
    port: Annotated[int, "Local preview port; 0 lets Quarto choose"] = 0,
    host: Annotated[str, "Interface on which to serve the preview"] = "127.0.0.1",
    no_browser: Annotated[bool, "Do not open the preview in a browser"] = False,
) -> None:
    """Render and serve the Reveal.js deck with live reload."""
    command = \
        f"""
        quarto preview {SLIDES} --render revealjs --host {host} \
        {f'--port {port}' if port else ''} \
        {'--no-browser' if no_browser else ''}
        """
    with ctx.cd(ROOT):
        ctx.run(command, pty=True)


@task(aliases=["r"])
def render(ctx: Context) -> None:
    """Render the Reveal.js deck into _site/slides.html."""
    command = ["quarto", "render", str(SLIDES), "--to", "revealjs"]
    with ctx.cd(ROOT):
        ctx.run(shlex.join(command))


def _service_urls() -> dict[str, str]:
    """Return host URLs for Compose services with published ports."""
    compose = yaml.safe_load((ROOT / "compose.yaml").read_text())
    services = compose.get("services", {})
    urls: dict[str, str] = {}

    for service_name, service in services.items():
        for port in service.get("ports", []):
            published_port = None
            if isinstance(port, str):
                # Compose accepts HOST:CONTAINER and IP:HOST:CONTAINER.
                fields = port.split(":")
                if len(fields) >= 2:
                    published_port = fields[-2]
            elif isinstance(port, dict):
                published_port = port.get("published")

            if published_port not in (None, 0, "0"):
                urls[service_name] = f"http://127.0.0.1:{published_port}"
                break

    return urls


@task(positional=["service_slug"])
def open_service(
    ctx: Context,
    service_slug: Annotated[str, "Service to open; omit to select interactively"] = "",
) -> None:
    """Open a Compose service with a published port in the system browser."""
    service_urls = _service_urls()
    if not service_urls:
        ctx.rich_exit("No Compose services have a published port.", exit_code=1)

    selected_service = service_slug or cast(
        str | None,
        select(
            ctx,
            list(service_urls),
            prompt="Select a service to open",
            select_1=True,
        ),
    )
    if not selected_service:
        return
    if selected_service not in service_urls:
        ctx.rich_exit(f"Unknown service: {selected_service}", exit_code=1)

    opener = shutil.which("xdg-open") or shutil.which("open")
    if opener is None:
        ctx.rich_exit("Could not find xdg-open or open on this system.", exit_code=1)

    ctx.run(shlex.join([opener, service_urls[selected_service]]))


@task(aliases=["hermes"])
def setup_hermes(
    ctx: Context,
    model: Annotated[str, "OpenRouter model ID"] = "qwen/qwen3.8-27b:free",
) -> None:
    """Configure Hermes from OR_API_KEY and restart the Compose services."""
    if not os.environ.get("OR_API_KEY"):
        ctx.rich_exit("Load OR_API_KEY with direnv before running this task.", exit_code=1)
    if not model:
        ctx.rich_exit("A model ID is required.", exit_code=1)

    compose = ["docker", "compose"]
    with ctx.cd(ROOT):
        ctx.run(shlex.join([*compose, "stop", "hermes", "webui"]))
        ctx.run(
            shlex.join(
                [
                    *compose,
                    "run",
                    "--rm",
                    "--no-deps",
                    "hermes",
                    "config",
                    "set",
                    "model.provider",
                    "openrouter",
                ]
            )
        )
        ctx.run(
            shlex.join(
                [
                    *compose,
                    "run",
                    "--rm",
                    "--no-deps",
                    "hermes",
                    "config",
                    "set",
                    "model.default",
                    model,
                ]
            )
        )
        ctx.run(shlex.join([*compose, "up", "-d", "hermes", "webui"]))
    ctx.print(f"Hermes configured for OpenRouter model: {model}")


@task(aliases=["models"])
def update_models(ctx: Context) -> None:
    """Fetch free OpenRouter models and generate the Caddy model catalog page."""
    api_key = os.environ.get("OR_API_KEY")
    if not api_key:
        ctx.rich_exit("Load OR_API_KEY with direnv before running this task.", exit_code=1)

    request = urllib.request.Request(
        "https://openrouter.ai/api/v1/models",
        headers={"Authorization": f"Bearer {api_key}"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        catalog = json.load(response)

    models = [
        model
        for model in catalog["data"]
        if model["id"].endswith(":free")
        and model.get("context_length", 0) >= 64_000
        and "tools" in model.get("supported_parameters", [])
    ]
    models.sort(key=lambda model: model["id"])
    rows = "\n".join(
        "<tr><td><code>{}</code></td><td>{}</td><td>{:,}</td></tr>".format(
            escape(model["id"]),
            escape(model.get("name", "")),
            model["context_length"],
        )
        for model in models
    )
    generated = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Free Hermes Models</title>
<style>
body {{ margin: 0; padding: 2rem; font: 16px system-ui, sans-serif; background: #f7fafc; color: #1a202c; }}
main {{ max-width: 1100px; margin: auto; background: white; padding: 2rem; border-radius: 1rem; box-shadow: 0 8px 30px #0002; }}
a {{ color: #4c51bf; }} table {{ width: 100%; border-collapse: collapse; margin-top: 1.5rem; }}
th, td {{ text-align: left; padding: .75rem; border-bottom: 1px solid #e2e8f0; }} th {{ background: #edf2f7; }}
code {{ word-break: break-all; }} .meta {{ color: #718096; }}
</style></head><body><main>
<p><a href="/">← Workshop services</a></p>
<h1>Free OpenRouter models for Hermes</h1>
<p class="meta">Generated {date.today().isoformat()} · {len(models)} models · requires ≥64K context and tool support</p>
<table><thead><tr><th>Model ID</th><th>Name</th><th>Context</th></tr></thead><tbody>{rows}</tbody></table>
</main></body></html>
"""
    (ROOT / "caddy" / "models.html").write_text(generated, encoding="utf-8")
    ctx.print(f"Generated caddy/models.html with {len(models)} models")



script()
