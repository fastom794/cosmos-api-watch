# Cosmos API Watch

Service that monitors RPC/REST endpoints for Cosmos ecosystem (Cosmos Hub, Osmosis, etc.).

## Features (MVP)

- FastAPI API + HTML dashboard
- PostgreSQL for projects/networks/endpoints
- Worker that periodically checks endpoints and stores status
- YAML config with networks and endpoints

## Tech stack

- Python, FastAPI
- SQLAlchemy, PostgreSQL
- httpx
- Docker, docker-compose
