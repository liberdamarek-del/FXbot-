"""Small shared HTTP client for the keyless public sources.

One keep-alive session per host (new TLS handshakes through the network
proxy were slow), a short connect timeout, a few retries with backoff.
Returns the raw bytes: parsing and archiving are the caller's job.
"""

import threading
import time
from urllib.parse import urlparse

import requests

USER_AGENT = "Mozilla/5.0 (fxbot research; +https://github.com/)"
_local = threading.local()


class FetchError(RuntimeError):
    """The source did not deliver after retries (never replaced by a guess)."""


def _session(host: str) -> requests.Session:
    sessions = getattr(_local, "sessions", None)

    if sessions is None:
        sessions = _local.sessions = {}

    if host not in sessions:
        session = requests.Session()
        session.headers["User-Agent"] = USER_AGENT
        sessions[host] = session

    return sessions[host]


def fetch(
    url: str,
    params: dict | None = None,
    retries: int = 4,
    connect_timeout: float = 10,
    read_timeout: float = 90,
    ok_statuses: tuple[int, ...] = (200,),
) -> tuple[int, bytes, str]:
    """GET url -> (status, content, final_url). Raises FetchError."""
    host = urlparse(url).netloc
    delay = 2.0
    error = "no attempt"

    for attempt in range(retries):
        session = _session(host)

        try:
            response = session.get(url, params=params, timeout=(connect_timeout, read_timeout))
        except requests.RequestException as exc:
            error = type(exc).__name__
            _local.sessions.pop(host, None)
        else:
            if response.status_code in ok_statuses:
                return response.status_code, response.content, response.url

            error = f"HTTP {response.status_code}"

            if response.status_code in (400, 401, 403, 404):
                break

        if attempt + 1 < retries:
            time.sleep(delay)
            delay *= 2

    raise FetchError(f"{host}: {error}")
