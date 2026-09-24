# Abstract

This workshop will introduce an OpenSource spreadsheet called Grist, which supports Python and Excel syntax for declaring formulas.
Every Grist spreadsheet is a SQLite file you can move around. You can also query it as SQL from the API.
Finally, we will cover webhooks for detecting changes, and PyGrister a CLI client, and an uvx based MCP and how to interact
with reactive notebooks.


# Description

Grist is an Open Source alternative to popular services like Google Sheets that you can use as SaaS or self-host.
In this workshop we will run Grist locally with Docker, and will explore this database that presents itself as a Spreadhseet.
After creating some formulae with in its native UI and explore some basic widgets, we will look into its API using
reactive notebooks.
For closing we will interact with it using MCP and PyGrister, and evaluate how to prevent our AI harnesses (Claude,Codex,pi,etc)
goint to creative with our data.

## Local development environment

The workshop services run together with Docker Compose. Install Docker Desktop or another Docker installation with Compose v2, then start the environment from the repository root:

```bash
docker compose up -d --build
```

Compose reads the OpenRouter credential from the local `.envrc` through the `OR_API_KEY` environment variable and passes it to both Hermes containers as `OPENROUTER_API_KEY`. `.envrc` is intentionally ignored; copy `.envrc.example` to `.envrc`, add your own key, and load it with direnv before starting Compose:

```bash
cp .envrc.example .envrc
direnv allow
direnv exec . docker compose up -d
```

The Hermes WebUI uses the configured Hermes Agent gateway and provides model selection in its settings. Authentication is intentionally disabled because this is a loopback-only demo; keep the published port local. WebUI and Hermes state is persisted in the `hermes-data` volume.

With `OR_API_KEY` loaded, configure Hermes without the interactive wizard:

```bash
direnv exec . uv run tasks.py setup-hermes
```

This stops the Hermes services, writes the OpenRouter provider and default free model into the persisted Hermes configuration, and starts the services again. To choose another model from the generated catalog:

```bash
direnv exec . uv run tasks.py setup-hermes --model cohere/north-mini-code:free
```

The task does not perform Portal registration or OAuth; it is intentionally hands-off only for API-key-based OpenRouter setup.

Once started, visit the landing page at **<http://127.0.0.1:8000>** for quick access to all services.

### Services

| Service | Host URL | URL from another container |
| --- | --- | --- |
| **Landing Page** | <http://127.0.0.1:8000> | `http://caddy:80` |
| Grist | <http://127.0.0.1:8484> | `http://grist:8484` |
| marimo | <http://127.0.0.1:8081> | `http://marimo:8080` |
| Hermes WebUI | <http://127.0.0.1:4096> | `http://webui:8787` |
| Hermes gateway | Not published | `http://hermes:8642` |

#### Hermes WebUI, gateway, and profile

Hermes runs as two services. The `webui` container provides browser chat, model selection, sessions, workspace browsing, and configuration. The separate `hermes` container runs `hermes gateway run`. The WebUI backend communicates with the gateway over HTTP on the private Compose network:

```text
Browser --HTTP--> webui:8787 --HTTP + bearer API key--> hermes:8642
```

Only the WebUI is published to the host, at <http://127.0.0.1:4096>. The gateway port is available only to other Compose services. Authentication for the browser-facing WebUI is intentionally disabled for this loopback-only demo; do not expose it beyond the local machine.

Both containers mount the same `hermes-data` Docker volume, but at different paths:

| Container | Hermes profile path |
| --- | --- |
| `hermes` gateway | `/opt/data` |
| `webui` | `/home/hermeswebui/.hermes` |

These paths expose the same profile. Its principal files are `config.yaml` for non-secret settings, `.env` for provider keys and other secrets, `auth.json` for OAuth credentials, and `state.db` plus the `sessions/`, `memories/`, `skills/`, and `logs/` directories for persistent application state.

The profile's `.env` is therefore `/opt/data/.env` in the gateway and `/home/hermeswebui/.hermes/.env` in the WebUI. It is distinct from the host-side `./.envrc`, which supplies `OR_API_KEY` to Compose. This repository does not require a Compose `./.env` file.

To inspect the profile through the gateway container:

```bash
docker compose exec hermes hermes config
docker compose exec hermes sh -c 'ls -la "$HERMES_HOME"'
```

To run the interactive Hermes setup wizard against the shared profile, stop both services first so only the one-off setup process accesses the profile:

```bash
docker compose stop hermes webui
docker compose run --rm --no-deps hermes setup
docker compose up -d hermes webui
```

Keep the profile credentials local and do not commit them. On macOS, the named volume resides inside Docker's Linux VM; access it through the containers or Docker volume tooling rather than a host filesystem path.


Open any service with a published port using the interactive Invoke task:

```bash
uv run tasks.py open-service
```

The task reads the service list from `compose.yaml` and offers only services with a published host port. To skip the selector, pass a service name such as `--service-slug grist`.

Inspect service status and follow logs with:

```bash
docker compose ps
docker compose logs -f grist       # or marimo / webui / caddy
```

Grist documents and Hermes configuration, credentials, and application data are stored in named volumes. A normal shutdown preserves them:

```bash
docker compose down
```

To delete that persisted state and start over, remove the volumes explicitly:

```bash
docker compose down -v
```


Refresh the presentation's free-model catalog from the authenticated OpenRouter API:

```bash
direnv exec . uv run tasks.py update-models
```

The task writes `caddy/models.html`, which is linked from the landing page. It never embeds the API key in the generated HTML. Models are filtered to `:free` entries with at least 64K context and advertised tool support.


### Dev Container

Open this repository with the **Dev Containers: Reopen in Container** command in VS Code or another Dev Container client. The client attaches to the dedicated `devcontainer` Compose service, mounts the repository at `/workspace`, and starts Caddy, Grist, marimo, and the `webui` service alongside it. The development container includes Python, `uv`, and Quarto.

All published ports bind to `127.0.0.1`. The setup disables marimo token authentication and uses development-only Grist defaults, so it is intended only for local use and must not be exposed directly to a network.


## Services for the workshop 🐳

### Grist

This is the spreadhseet with Python formulas.

URL


### Marimo:

This is the reactive notebook.

URL:

### Hermes
