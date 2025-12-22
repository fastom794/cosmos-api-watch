# worker/checker.py
import time
from datetime import datetime, timezone
from typing import Optional, Tuple

import httpx


def _parse_block_time(ts: str) -> Optional[datetime]:
    """
    Convert to UTC:
    2024-01-02T03:04:05Z
    2024-01-02T03:04:05.123456Z
    2024-01-02T03:04:05.123456789Z
    """
    if not ts:
        return None

    # Z -> +00:00
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"

    # cut nanoseconds to microseconds (6 digits)
    if "." in ts:
        before, after = ts.split(".", 1)
        if "+" in after:
            frac, tz = after.split("+", 1)
            frac = frac[:6]
            ts = f"{before}.{frac}+{tz}"
        elif "-" in after:
            frac, tz = after.split("-", 1)
            frac = frac[:6]
            ts = f"{before}.{frac}-{tz}"
        else:
            frac = after[:6]
            ts = f"{before}.{frac}"

    try:
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _calc_block_delay_ms(block_time_str: Optional[str]) -> Optional[int]:
    if not block_time_str:
        return None
    dt = _parse_block_time(block_time_str)
    if dt is None:
        return None
    now_utc = datetime.now(timezone.utc)
    diff_ms = int((now_utc - dt).total_seconds() * 1000)
    # if return delay < 0
    if diff_ms < 0:
        diff_ms = 0
    return diff_ms


def check_rpc_endpoint(
    base_url: str,
    expected_chain_id: Optional[str],
    timeout: float = 5.0,
) -> Tuple[bool, Optional[int], Optional[int], Optional[str], Optional[str]]:
    """
    RPC Check:
      GET {base_url}/status

    Returns:
      is_available        (bool)
      http_status_code    (int | None)
      block_delay_ms      (int | None)   # CURRENT BLOCK DELAY
      latest_block_height (str | None)
      error_message       (str | None)
    """
    url = base_url.rstrip("/") + "/status"
    start = time.monotonic()

    try:
        resp = httpx.get(url, timeout=timeout)
        http_status = resp.status_code

        if http_status < 200 or http_status >= 300:
            return False, http_status, None, None, f"HTTP_STATUS_{http_status}"

        try:
            data = resp.json()
        except Exception as e:
            return False, http_status, None, None, f"INVALID_JSON: {e}"

        result = data.get("result") or {}
        node_info = result.get("node_info") or {}
        sync_info = result.get("sync_info") or {}

        network = node_info.get("network")
        latest_block_height = sync_info.get("latest_block_height")
        latest_block_time_str = sync_info.get("latest_block_time")

        # check chain_id
        if expected_chain_id and network and network != expected_chain_id:
            err = f"CHAIN_ID_MISMATCH: expected={expected_chain_id}, got={network}"
            delay_ms = _calc_block_delay_ms(latest_block_time_str)
            return False, http_status, delay_ms, latest_block_height, err

        delay_ms = _calc_block_delay_ms(latest_block_time_str)
        if delay_ms is None:
            return False, http_status, None, latest_block_height, "INVALID_BLOCK_TIME"

        # if OK
        return True, http_status, delay_ms, latest_block_height, None

    except Exception as e:
        msg = str(e)

        if "handshake operation timed out" in msg:
            err = "TLS_HANDSHAKE_TIMEOUT"
        elif "Name or service not known" in msg or "Temporary failure in name resolution" in msg:
            err = "DNS_RESOLUTION_FAILED"
        elif "Connection refused" in msg:
            err = "CONNECTION_REFUSED"
        elif "timed out" in msg.lower():
            err = "REQUEST_TIMEOUT"
        else:
            err = f"EXCEPTION: {msg[:400]}"

        return False, None, None, None, err


def _check_rest_block_latest(
    base_url: str,
    path: str,
    expected_chain_id: Optional[str],
    timeout: float,
) -> Tuple[bool, Optional[int], Optional[int], Optional[str], Optional[str]]:
    """
    Helper function:
      GET base_url + path
    Expect Cosmos REST response with block.
    """
    url = base_url.rstrip("/") + path
    resp = httpx.get(url, timeout=timeout)
    http_status = resp.status_code

    if http_status < 200 or http_status >= 300:
        return False, http_status, None, None, f"HTTP_STATUS_{http_status}"

    try:
        data = resp.json()
    except Exception as e:
        return False, http_status, None, None, f"INVALID_JSON: {e}"

    # cosmos-sdk >= 0.47: /cosmos/base/tendermint/v1beta1/blocks/latest
    # old format /blocks/latest
    block = data.get("block") or {}
    header = block.get("header") or {}

    chain_id = header.get("chain_id")
    height = header.get("height")
    time_str = header.get("time")

    if expected_chain_id and chain_id and chain_id != expected_chain_id:
        err = f"CHAIN_ID_MISMATCH: expected={expected_chain_id}, got={chain_id}"
        delay_ms = _calc_block_delay_ms(time_str)
        return False, http_status, delay_ms, height, err

    delay_ms = _calc_block_delay_ms(time_str)
    if delay_ms is None:
        return False, http_status, None, height, "INVALID_BLOCK_TIME"

    return True, http_status, delay_ms, height, None


def check_api_endpoint(
    base_url: str,
    expected_chain_id: Optional[str],
    timeout: float = 5.0,
) -> Tuple[bool, Optional[int], Optional[int], Optional[str], Optional[str]]:
    """
    API Check:

    1) GET {base_url}/cosmos/base/tendermint/v1beta1/blocks/latest
    2) GET {base_url}/blocks/latest
    3) GET base_url (fallback)

    Returns:
      is_available
      http_status_code
      block_delay_ms
      latest_block_height
      error_message
    """

    # --- helper: ERROR normalization  ---
    def _normalize_error(e: Exception) -> str:
        msg = str(e)
        if "handshake operation timed out" in msg:
            return "TLS_HANDSHAKE_TIMEOUT"
        if "Name or service not known" in msg or "Temporary failure in name resolution" in msg:
            return "DNS_RESOLUTION_FAILED"
        if "Connection refused" in msg:
            return "CONNECTION_REFUSED"
        if "timed out" in msg.lower():
            return "REQUEST_TIMEOUT"
        return f"EXCEPTION: {msg[:400]}"

    # --- try #1: new Cosmos REST endpoint ---
    try:
        return _check_rest_block_latest(
            base_url=base_url,
            path="/cosmos/base/tendermint/v1beta1/blocks/latest",
            expected_chain_id=expected_chain_id,
            timeout=timeout,
        )
    except Exception as e:
        err1 = _normalize_error(e)

    # --- try #2: old Cosmos REST endpoint (/blocks/latest) ---
    try:
        return _check_rest_block_latest(
            base_url=base_url,
            path="/blocks/latest",
            expected_chain_id=expected_chain_id,
            timeout=timeout,
        )
    except Exception as e:
        err2 = _normalize_error(e)

    # --- fallback #3: is alive check ---
    try:
        url = base_url.rstrip("/")
        resp = httpx.get(url, timeout=timeout)
        http_status = resp.status_code
        if http_status < 200 or http_status >= 300:
            return False, http_status, None, None, f"HTTP_STATUS_{http_status}"
        return True, http_status, None, None, None
    except Exception as e:
        err3 = _normalize_error(e)

    # if does not work - return the most helpfull error
    # priority: DNS → TLS → TIMEOUT → EXCEPTION
    for err in (err1, err2, err3):
        if err.startswith("DNS_"):
            return False, None, None, None, err
    for err in (err1, err2, err3):
        if err.startswith("TLS_"):
            return False, None, None, None, err
    for err in (err1, err2, err3):
        if err.startswith("REQUEST_TIMEOUT"):
            return False, None, None, None, err

    # fallback
    return False, None, None, None, err1 or err2 or err3 or "UNKNOWN_ERROR"

