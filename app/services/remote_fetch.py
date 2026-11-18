"""Bounded public HTTP downloads with validation on every redirect."""

import asyncio
import ipaddress
import socket
from urllib.parse import urljoin, urlsplit

import httpx


async def fetch_public(url: str, *, allowed_hosts=None, max_bytes=2 * 1024 * 1024):
    async with httpx.AsyncClient(timeout=20, follow_redirects=False) as client:
        for _ in range(6):
            parsed = urlsplit(url)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.hostname
                or parsed.username is not None
                or parsed.password is not None
                or parsed.port not in {None, 80, 443}
            ):
                raise ValueError("Use a public http(s) URL without credentials or custom ports.")
            host = parsed.hostname.lower()
            if allowed_hosts is not None and host not in allowed_hosts:
                raise ValueError("Supported sites: Hungry Huy, Helen Recipes, and Vicky Pham blogs.")
            addresses = await asyncio.to_thread(
                socket.getaddrinfo, host, parsed.port or (443 if parsed.scheme == "https" else 80),
                type=socket.SOCK_STREAM,
            )
            if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
                raise ValueError("Recipe and image URLs must resolve to public addresses.")
            async with client.stream("GET", url, headers={"User-Agent": "CleanViet/2.0 recipe-import"}) as response:
                if response.status_code in {301, 302, 303, 307, 308}:
                    location = response.headers.get("location")
                    if not location:
                        raise ValueError("Redirect has no destination.")
                    url = urljoin(url, location)
                    continue
                response.raise_for_status()
                chunks = []
                size = 0
                async for chunk in response.aiter_bytes():
                    size += len(chunk)
                    if size > max_bytes:
                        raise ValueError("Remote file exceeds the download limit.")
                    chunks.append(chunk)
                return httpx.Response(
                    response.status_code, headers={
                        k: v for k, v in response.headers.items()
                        if k.lower() not in {"content-encoding", "content-length", "transfer-encoding"}
                    },
                    content=b"".join(chunks), request=response.request,
                )
        raise ValueError("Too many redirects.")
