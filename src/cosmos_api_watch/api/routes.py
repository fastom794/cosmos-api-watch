from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from cosmos_api_watch.db.session import Base, engine
from cosmos_api_watch.api.deps import get_db
from cosmos_api_watch.core.config import APP_VERSION
from cosmos_api_watch.core.init_data import init_data
from cosmos_api_watch.models import Project, Network, Endpoint, EndpointStatus

BASE_DIR = Path(__file__).resolve().parent.parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    Base.metadata.create_all(bind=engine)
    init_data()
    yield
    # Shutdown (if needed)


app = FastAPI(title="Cosmos API Watch", lifespan=lifespan)

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "static")),
    name="static",
)


@app.get("/health")
def healthcheck():
    return {"status": "ok", "service": "CosmosAPIWatch", "version": APP_VERSION}


@app.get("/api/projects")
def list_projects(db: Session = Depends(get_db)):
    projects = db.query(Project).order_by(Project.slug).all()
    return [
        {
            "slug": p.slug,
            "name": p.name,
        }
        for p in projects
    ]


@app.get("/api/projects/{project_slug}/networks")
def list_networks(
    project_slug: str,
    db: Session = Depends(get_db),
):
    """
    Returns all networks of the project:
    - network_type (mainnet/testnet)
    - chain_id
    """
    project = (
        db.query(Project)
        .filter(Project.slug == project_slug)
        .first()
    )
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    networks = (
        db.query(Network)
        .filter(Network.project_id == project.id)
        .order_by(Network.network_type, Network.chain_id)
        .all()
    )

    return [
        {
            "network_type": n.network_type,
            "chain_id": n.chain_id,
        }
        for n in networks
    ]


@app.get("/api/projects/{project_slug}/{network_type}/endpoints")
def list_endpoints(
    project_slug: str,
    network_type: str,
    only_enabled: bool = Query(False, description="Return only enabled endpoints"),
    db: Session = Depends(get_db),
):
    """
    Endpoints of all networks of specified project with specified network type (mainnet/testnet).
    """
    project = (
        db.query(Project)
        .filter(Project.slug == project_slug)
        .first()
    )
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    networks = (
        db.query(Network)
        .filter(
            Network.project_id == project.id,
            Network.network_type == network_type,
        )
        .all()
    )
    if not networks:
        raise HTTPException(status_code=404, detail="No networks with this type")

    network_ids = [n.id for n in networks]

    q = db.query(Endpoint).filter(Endpoint.network_id.in_(network_ids))
    if only_enabled:
        q = q.filter(Endpoint.enabled.is_(True))

    endpoints = q.order_by(Endpoint.type, Endpoint.name).all()

    return [
        {
            "name": e.name,
            "type": e.type,
            "url": e.url,
            "enabled": e.enabled,
            "network_type": network_type,
        }
        for e in endpoints
    ]


@app.get("/api/projects/{project_slug}/{network_type}/summary")
def network_summary(
    project_slug: str,
    network_type: str,
    max_delay: int | None = Query(None, ge=0),  # optional
    db: Session = Depends(get_db),
):
    """
    Summary of ALL networks of the project of the given type (mainnet / testnet).
    Return a list of networks + their endpoints and statuses.

    If max_delay is specified (in milliseconds) — we remove endpoints from the output,
    for which block_delay_ms > max_delay.
    """
    project = (
        db.query(Project)
        .filter(Project.slug == project_slug)
        .first()
    )
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    networks = (
        db.query(Network)
        .filter(
            Network.project_id == project.id,
            Network.network_type == network_type,
        )
        .order_by(Network.chain_id)
        .all()
    )
    if not networks:
        raise HTTPException(status_code=404, detail="No networks with this type")

    networks_out = []

    for n in networks:
        endpoints = (
            db.query(Endpoint)
            .filter(Endpoint.network_id == n.id)
            .order_by(Endpoint.type, Endpoint.name)
            .all()
        )

        eps_out = []
        for e in endpoints:
            status = (
                db.query(EndpointStatus)
                .filter(EndpointStatus.endpoint_id == e.id)
                .first()
            )

            if status is not None:
                is_available = status.is_available
                delay_ms = status.block_delay_ms
                block_height = status.last_block_height
                status_code = status.status_code
                error_message = status.error_message
                checked_at = status.checked_at.isoformat() if status.checked_at else None
            else:
                is_available = None
                delay_ms = None
                block_height = None
                status_code = None
                error_message = None
                checked_at = None

            eps_out.append({
                "name": e.name,
                "type": e.type,
                "url": e.url,
                "enabled": e.enabled,
                "is_available": is_available,
                "status_code": status_code,
                "block_delay_ms": delay_ms,
                "last_block_height": block_height,
                "error_message": error_message,
                "checked_at": checked_at,
            })

        # 🔹 max_delay (ms), if parameter exists
        if max_delay is not None:
            eps_out = [
                ep for ep in eps_out
                if ep["block_delay_ms"] is None
                or ep["block_delay_ms"] <= max_delay
            ]

        networks_out.append({
            "chain_id": n.chain_id,
            "network_type": n.network_type,
            "endpoints": eps_out,
        })

    return {
        "project": project.slug,
        "network_type": network_type,
        "networks": networks_out,
    }


def _format_delay(ms):
    if ms is None:
        return ""
    if ms < 1000:
        return f"{ms} ms"
    seconds = ms // 1000
    if seconds < 60:
        return f"{seconds} s"
    minutes = seconds // 60
    seconds = seconds % 60
    if minutes < 60:
        return f"{minutes}m {seconds}s"
    hours = minutes // 60
    minutes = minutes % 60
    return f"{hours}h {minutes}m"


def _format_checked_at(dt):
    if dt is None:
        return ""
    return dt.replace(microsecond=0).isoformat()


@app.get("/", response_class=HTMLResponse)
def html_index(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    HTML table:
    - project_slug
    - network_type
    - chain_id
    - endpoint_* (+ status from EndpointStatus)
    """
    projects = db.query(Project).order_by(Project.slug).all()

    rows = []

    for p in projects:
        networks = (
            db.query(Network)
            .filter(Network.project_id == p.id)
            .order_by(Network.network_type, Network.chain_id)
            .all()
        )
        for n in networks:
            endpoints = (
                db.query(Endpoint)
                .filter(Endpoint.network_id == n.id)
                .order_by(Endpoint.type, Endpoint.name)
                .all()
            )

            if not endpoints:
                rows.append({
                    "project_slug": p.slug,
                    "network_type": n.network_type,
                    "chain_id": n.chain_id,
                    "endpoint_type": "",
                    "endpoint_name": "",
                    "url": "",
                    "enabled": False,
                    "is_available": None,
                    "status_code": None,
                    "block_height": None,
                    "block_delay_ms": None,
                    "block_delay_human": "",
                    "error_message": "",
                    "last_checked_iso": "",
                })
            else:
                for e in endpoints:
                    status = (
                        db.query(EndpointStatus)
                        .filter(EndpointStatus.endpoint_id == e.id)
                        .first()
                    )

                    if status is not None:
                        is_available = status.is_available
                        delay_ms = status.block_delay_ms
                        block_height = status.last_block_height
                        status_code = status.status_code
                        error_message = status.error_message or ""
                        last_checked_iso = _format_checked_at(status.checked_at)
                    else:
                        is_available = None
                        delay_ms = None
                        block_height = None
                        status_code = None
                        error_message = ""
                        last_checked_iso = ""

                    rows.append({
                        "project_slug": p.slug,
                        "network_type": n.network_type,
                        "chain_id": n.chain_id,
                        "endpoint_type": e.type,
                        "endpoint_name": e.name,
                        "url": e.url,
                        "enabled": e.enabled,
                        "is_available": is_available,
                        "status_code": status_code,
                        "block_height": block_height,
                        "block_delay_ms": delay_ms,
                        "block_delay_human": _format_delay(delay_ms),
                        "error_message": error_message,
                        "last_checked_iso": last_checked_iso,
                    })

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "rows": rows,
        },
    )

