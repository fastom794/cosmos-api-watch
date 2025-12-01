# core/init_data.py
from pathlib import Path
from typing import Any, Dict, List
import logging

import yaml
from sqlalchemy.orm import Session

from db.session import SessionLocal
from models import Project, Network, Endpoint

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config" / "networks.yaml"


def load_config() -> Dict[str, Any]:
    if not CONFIG_PATH.exists():
        logger.warning("Config file %s not found", CONFIG_PATH)
        return {}

    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    return data


def sync_from_config(db: Session, cfg: Dict[str, Any]) -> None:
    """
    config/networks.yaml format:

    projects:
      - slug: cosmos
        name: Cosmos Hub
        networks:
          - slug: cosmos-hub-mainnet
            name: Cosmos Hub Mainnet
            chain_id: cosmoshub-4
            network_type: mainnet
            endpoints:
              - name: Notional RPC
                type: rpc
                url: https://...
                enabled: true
    """

    projects_cfg: List[Dict[str, Any]] = cfg.get("projects") or []
    if not projects_cfg:
        logger.info("No projects in config")
        return

    existing_projects = {p.slug: p for p in db.query(Project).all()}

    for proj_cfg in projects_cfg:
        proj_slug = proj_cfg["slug"]
        proj_name = proj_cfg["name"]

        project = existing_projects.get(proj_slug)
        if project is None:
            project = Project(slug=proj_slug, name=proj_name)
            db.add(project)
            db.flush()
            logger.info("Created project: %s", proj_slug)
        else:
            if project.name != proj_name:
                project.name = proj_name
                logger.info("Updated project name: %s -> %s", proj_slug, proj_name)

        networks_cfg: List[Dict[str, Any]] = proj_cfg.get("networks") or []

        existing_networks = {
            n.slug: n
            for n in db.query(Network).filter(Network.project_id == project.id).all()
        }

        for net_cfg in networks_cfg:
            net_slug = net_cfg["slug"]
            net_name = net_cfg["name"]
            chain_id = net_cfg["chain_id"]
            network_type = net_cfg["network_type"]

            network = existing_networks.get(net_slug)
            if network is None:
                network = Network(
                    project_id=project.id,
                    slug=net_slug,
                    name=net_name,
                    chain_id=chain_id,
                    network_type=network_type,
                )
                db.add(network)
                db.flush()
                logger.info("Created network: %s/%s", proj_slug, net_slug)
            else:
                changed = False
                if network.name != net_name:
                    network.name = net_name
                    changed = True
                if network.chain_id != chain_id:
                    network.chain_id = chain_id
                    changed = True
                if network.network_type != network_type:
                    network.network_type = network_type
                    changed = True
                if changed:
                    logger.info("Updated network: %s/%s", proj_slug, net_slug)

            # --- endpoints ---
            endpoints_cfg: List[Dict[str, Any]] = net_cfg.get("endpoints") or []

            existing_endpoints = {
                e.url: e
                for e in db.query(Endpoint).filter(
                    Endpoint.network_id == network.id
                ).all()
            }

            cfg_urls = set()

            for ep_cfg in endpoints_cfg:
                ep_name = ep_cfg["name"]
                ep_type = ep_cfg["type"]
                ep_url = ep_cfg["url"]
                ep_enabled = bool(ep_cfg.get("enabled", True))

                cfg_urls.add(ep_url)

                endpoint = existing_endpoints.get(ep_url)
                if endpoint is None:
                    endpoint = Endpoint(
                        network_id=network.id,
                        name=ep_name,
                        type=ep_type,
                        url=ep_url,
                        enabled=ep_enabled,
                    )
                    db.add(endpoint)
                    logger.info(
                        "Created endpoint: %s/%s [%s] %s",
                        proj_slug,
                        net_slug,
                        ep_type,
                        ep_url,
                    )
                else:
                    changed = False
                    if endpoint.name != ep_name:
                        endpoint.name = ep_name
                        changed = True
                    if endpoint.type != ep_type:
                        endpoint.type = ep_type
                        changed = True
                    if endpoint.enabled != ep_enabled:
                        endpoint.enabled = ep_enabled
                        changed = True

                    if changed:
                        logger.info(
                            "Updated endpoint: %s/%s [%s] %s",
                            proj_slug,
                            net_slug,
                            ep_type,
                            ep_url,
                        )

            # remove endpoints that not in config (by url)
            for ep_url, endpoint in existing_endpoints.items():
                if ep_url not in cfg_urls:
                    logger.info(
                        "Deleting endpoint not in config: %s/%s [%s] %s",
                        proj_slug,
                        net_slug,
                        endpoint.type,
                        ep_url,
                    )
                    db.delete(endpoint)

    db.commit()


def init_data() -> None:
    cfg = load_config()
    if not cfg:
        return

    db = SessionLocal()
    try:
        sync_from_config(db, cfg)
    finally:
        db.close()

