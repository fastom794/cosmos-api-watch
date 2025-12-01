# worker/runner.py
import os
import time
import logging

from datetime import datetime, timezone
from sqlalchemy.orm import Session

from db.session import SessionLocal
from models import Endpoint, Network, Check, EndpointStatus
from worker.checker import check_rpc_endpoint, check_api_endpoint

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("worker")

CHECK_INTERVAL_SECONDS = int(os.getenv("CHECK_INTERVAL_SECONDS", "30"))
BATCH_LIMIT = int(os.getenv("BATCH_LIMIT", "100"))
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "5.0"))


def process_batch(db: Session) -> None:
    """
    Take enabled endpoints and check:
      - rpc: /status, height, delay, chain_id
      - api: blocks/latest, height, delay, chain_id
    """
    rows = (
        db.query(Endpoint, Network)
        .join(Network, Endpoint.network_id == Network.id)
        .filter(Endpoint.enabled.is_(True))
        .limit(BATCH_LIMIT)
        .all()
    )

    if not rows:
        logger.info("No enabled endpoints to check")
        return

    logger.info("Checking %d endpoints...", len(rows))

    for ep, net in rows:
        expected_chain_id = net.chain_id or None
        now_utc = datetime.now(timezone.utc)

        if ep.type == "rpc":
            is_ok, http_status, block_delay_ms, block_height, error_msg = check_rpc_endpoint(
                ep.url,
                expected_chain_id=expected_chain_id,
                timeout=REQUEST_TIMEOUT,
            )
        elif ep.type == "api":
            is_ok, http_status, block_delay_ms, block_height, error_msg = check_api_endpoint(
                ep.url,
                expected_chain_id=expected_chain_id,
                timeout=REQUEST_TIMEOUT,
            )
        else:
            # unknown type, without chain_id
            is_ok, http_status, block_delay_ms, block_height, error_msg = check_api_endpoint(
                ep.url,
                expected_chain_id=None,
                timeout=REQUEST_TIMEOUT,
            )

        check = Check(
            endpoint_id=ep.id,
            is_available=is_ok,
            status_code=http_status,
            block_delay_ms=block_delay_ms,
            last_block_height=block_height,
            error_message=error_msg,
            checked_at=now_utc,
        )
        db.add(check)

        status = (
            db.query(EndpointStatus)
            .filter(EndpointStatus.endpoint_id == ep.id)
            .first()
        )

        if status is None:
            status = EndpointStatus(
                endpoint_id=ep.id,
                is_available=is_ok,
                status_code=http_status,
                block_delay_ms=block_delay_ms,
                last_block_height=block_height,
                error_message=error_msg,
                checked_at=now_utc,
            )
            db.add(status)
        else:
            status.is_available = is_ok
            status.status_code = http_status
            status.block_delay_ms = block_delay_ms
            status.last_block_height = block_height
            status.error_message = error_msg
            status.checked_at = now_utc

        logger.info(
            "Endpoint %s (%s, %s) -> ok=%s http=%s height=%s delay_ms=%s err=%s",
            ep.name,
            ep.type,
            ep.url,
            is_ok,
            http_status,
            block_height,
            block_delay_ms,
            error_msg,
        )

    db.commit()


def main_loop() -> None:
    logger.info(
        "Worker started, interval=%s sec, timeout=%s sec, batch_limit=%s",
        CHECK_INTERVAL_SECONDS,
        REQUEST_TIMEOUT,
        BATCH_LIMIT,
    )
    while True:
        db = SessionLocal()
        try:
            logger.info("Worker iteration start")
            process_batch(db)
            logger.info("Worker iteration done, sleeping %s sec", CHECK_INTERVAL_SECONDS)
        except Exception as e:
            logger.exception("Error in worker loop: %s", e)
            db.rollback()
        finally:
            db.close()

        time.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    main_loop()

