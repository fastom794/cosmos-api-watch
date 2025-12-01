# Cosmos API Watch

Service that monitors RPC/REST endpoints for Cosmos ecosystem (Cosmos Hub, Osmosis, etc.).

## Features

- FastAPI API + HTML dashboard
- PostgreSQL for projects/networks/endpoints
- Worker that periodically checks endpoints and stores status
- YAML config with networks and endpoints

## Tech stack

- Python, FastAPI
- SQLAlchemy, PostgreSQL
- httpx
- Docker, docker-compose

## Project structure
```
~/app.local/cosmos-api-watch/

  docker-compose.yml    # Docker services: API, Worker, PostgreSQL
  Dockerfile            # Build instructions for the FastAPI application container
  requirements.txt      # Python dependencies for API and Worker
  .env                  # Environment variables (DB credentials, config paths, etc.)

  config/               # External configuration files
    networks.yaml       # List of projects, networks and endpoints to load into the database

  api/
    __init__.py         # Package initializer
    routes.py           # FastAPI application and HTTP endpoints
    deps.py             # Shared dependencies (e.g., get_db session provider)

  core/
    __init__.py         # Package initializer
    config.py           # Application configuration (DATABASE_URL, settings)
    init_data.py        # Loads and synchronizes networks.yaml into the database

  db/
    __init__.py         # Package initializer
    session.py          # Database engine, SessionLocal factory, declarative Base

  models/               # SQLAlchemy ORM model definitions
    __init__.py         # Package initializer
    project.py          # Project model (e.g., cosmos, osmosis)
    network.py          # Network model (chain_id, mainnet/testnet)
    endpoint.py         # Endpoint model (RPC/API URLs)
    check.py            # Historical check records (per request)
    endpoint_status.py  # Last known status for each endpoint

  worker/
    __init__.py         # Package initializer
    runner.py           # Worker entry point; scheduler loop for periodic checks
    checker.py          # RPC/API request logic, block height/time parsing

  templates/
    index.html          # HTML dashboard rendered by FastAPI

  static/
    style.css           # Stylesheet for the dashboard
    table.js            # Frontend logic: filters, table rendering, UI helpers
```
## Run with Docker

```bash
git clone https://github.com/fastom794/cosmos-api-watch.git
cd cosmos-api-watch
cp env.example .env
docker compose up -d --build

# API: http://localhost:12081/
# Health: http://localhost:12081/health
```
