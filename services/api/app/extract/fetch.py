"""Fetch remote pages with SSRF, size, timeout, and robots.txt guards."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx

from app.cache import cache_get, cache_set

USER_AGENT = "SahaSlokaBot/1.0 (+https://github.com; respectful research crawler)"
MAX_BYTES = 2 * 1024 * 1024
FETCH_TIMEOUT = 12.0
BLOCKED_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}


class FetchError(Exception):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def _host_is_public(hostname: str) -> bool:
    host = hostname.lower().rstrip(".")
    if host in BLOCKED_HOSTS or host.endswith(".local") or host.endswith(".internal"):
        return False
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise FetchError(f"Could not resolve host: {host}") from exc
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            return False
    return True


def assert_public_http_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise FetchError("Only http and https URLs are allowed")
    if not parsed.hostname:
        raise FetchError("URL is missing a host")
    if not _host_is_public(parsed.hostname):
        raise FetchError("Refusing to fetch a private or local address")


def _robots_allowed(url: str) -> bool:
    parsed = urlparse(url)
    robots_url = urljoin(f"{parsed.scheme}://{parsed.netloc}", "/robots.txt")
    cache_key = f"robots:{robots_url}"
    cached = cache_get(cache_key)
    rp = RobotFileParser()
    if cached is not None:
        rp.parse(str(cached).splitlines())
    else:
        try:
            with httpx.Client(timeout=5.0, headers={"User-Agent": USER_AGENT}, follow_redirects=True) as client:
                response = client.get(robots_url)
            if response.status_code >= 400:
                cache_set(cache_key, "User-agent: *\nAllow: /\n", expire=60 * 60)
                return True
            cache_set(cache_key, response.text, expire=60 * 60 * 6)
            rp.parse(response.text.splitlines())
        except httpx.HTTPError:
            return True
    return rp.can_fetch(USER_AGENT, url)


async def fetch_url(url: str, client: httpx.AsyncClient | None = None) -> str:
    assert_public_http_url(url)
    if not _robots_allowed(url):
        raise FetchError("robots.txt disallows fetching this URL")

    headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"}
    timeout = httpx.Timeout(FETCH_TIMEOUT)

    async def _read(http: httpx.AsyncClient) -> str:
        async with http.stream("GET", url, headers=headers, follow_redirects=True) as response:
            if response.status_code >= 400:
                raise FetchError(f"Upstream returned HTTP {response.status_code}", response.status_code)
            content_type = response.headers.get("content-type", "")
            if content_type and "html" not in content_type and "xml" not in content_type and "text" not in content_type:
                raise FetchError(f"Unsupported content type: {content_type}")
            chunks: list[bytes] = []
            total = 0
            async for chunk in response.aiter_bytes():
                total += len(chunk)
                if total > MAX_BYTES:
                    raise FetchError("Page exceeds the 2 MB size cap")
                chunks.append(chunk)
            return b"".join(chunks).decode(response.encoding or "utf-8", errors="replace")

    if client is not None:
        return await _read(client)
    async with httpx.AsyncClient(timeout=timeout) as http:
        return await _read(http)
