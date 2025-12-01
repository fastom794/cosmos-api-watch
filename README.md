# Cosmos API Watch

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-green.svg)](https://fastapi.tiangolo.com/)

Service that monitors RPC/REST endpoints for Cosmos ecosystem (Cosmos Hub, Osmosis, Celestia, etc.).

## ✨ Features

- 🚀 **FastAPI REST API** + HTML dashboard
- 🗄️ **PostgreSQL storage** for projects/networks/endpoints with historical data
- 🔄 **Background worker** that periodically checks endpoints and stores status
- ⚙️ **YAML configuration** with networks and endpoints (easy to extend)
- 📊 **Real-time monitoring** of block height, block delay, and availability
- 🎯 **Multi-network support** (Cosmos Hub, Osmosis, Celestia, and more)
- 🔍 **Advanced filtering** by project, network type, and endpoint status
- 🐳 **Docker ready** with docker-compose setup

## 🛠️ Tech Stack

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy 2.0
- **Database**: PostgreSQL with psycopg3
- **HTTP Client**: httpx for async requests
- **Frontend**: HTML5, CSS3, Vanilla JavaScript
- **Deployment**: Docker & docker-compose

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
## 🚀 Quick Start

### With Docker (Recommended)

```bash
# Clone repository
git clone https://github.com/fastom794/cosmos-api-watch.git
cd cosmos-api-watch

# Copy environment file
cp env.example .env

# Start all services
docker compose up -d --build

# Access the application
# Dashboard: http://localhost:12081/
# Health check: http://localhost:12081/health
```

### Local Development

```bash
# Clone and setup
git clone https://github.com/fastom794/cosmos-api-watch.git
cd cosmos-api-watch
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Setup PostgreSQL database
# Then run:
uvicorn api.routes:app --reload

# Access at: http://localhost:8000
```

## 📖 API Documentation

Once running, visit:
- **API Docs**: http://localhost:12081/docs (Swagger UI)

### Key Endpoints

- `GET /health` - Service health check
- `GET /api/projects` - List all projects
- `GET /api/projects/{project}/networks` - Networks for a project
- `GET /api/projects/{project}/{network}/endpoints` - Endpoints
- `GET /api/projects/{project}/{network}/summary` - Full status summary
- `GET /` - Web dashboard

## ⚙️ Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+psycopg://cosmos:cosmos@db:5432/cosmos` | PostgreSQL connection string |
| `CHECK_INTERVAL_SECONDS` | `300` | How often to check endpoints |
| `BATCH_LIMIT` | `300` | Max endpoints to check per batch |
| `REQUEST_TIMEOUT` | `5.0` | HTTP request timeout in seconds |

### Adding New Networks

Edit `config/networks.yaml` to add new projects, networks, or endpoints:

```yaml
projects:
  - slug: my-project
    name: My Blockchain Project
    networks:
      - slug: mainnet
        name: Mainnet
        chain_id: my-chain-1
        network_type: mainnet
        endpoints:
          - name: my-rpc
            type: rpc
            url: https://rpc.myproject.com
            enabled: true
```

### Logs

```bash
# View API logs
docker logs cosmos_api

# View worker logs
docker logs cosmos_worker

# View database logs
docker logs cosmos_db
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
