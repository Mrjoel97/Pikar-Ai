# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Shared outbound async HTTP client pool.

Most app code should reuse these clients instead of opening a fresh
``httpx.AsyncClient`` for every request. The pool keeps TCP/TLS connections
alive across calls and is closed from the FastAPI lifespan shutdown hook.
"""

from __future__ import annotations

import asyncio
import logging
import os
import threading
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger(__name__)


def _env_int(name: str, default: int) -> int:
    try:
        return max(1, int(os.getenv(name, str(default))))
    except ValueError:
        logger.warning(
            "Invalid integer for %s=%r; using %s", name, os.getenv(name), default
        )
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return max(0.1, float(os.getenv(name, str(default))))
    except ValueError:
        logger.warning("Invalid float for %s=%r; using %s", name, os.getenv(name), default)
        return default


def _current_loop_id() -> int:
    try:
        return id(asyncio.get_running_loop())
    except RuntimeError:
        return 0


@dataclass(frozen=True)
class AsyncHttpClientPoolConfig:
    """Connection limits for shared outbound HTTP clients."""

    max_connections: int
    max_keepalive_connections: int
    keepalive_expiry_seconds: float
    timeout_seconds: float

    @classmethod
    def from_env(cls) -> "AsyncHttpClientPoolConfig":
        return cls(
            max_connections=_env_int("OUTBOUND_HTTP_MAX_CONNECTIONS", 200),
            max_keepalive_connections=_env_int(
                "OUTBOUND_HTTP_KEEPALIVE_CONNECTIONS", 50
            ),
            keepalive_expiry_seconds=_env_float(
                "OUTBOUND_HTTP_KEEPALIVE_EXPIRY_SECONDS", 30.0
            ),
            timeout_seconds=_env_float("OUTBOUND_HTTP_TIMEOUT_SECONDS", 30.0),
        )


class AsyncHttpClientPool:
    """Per-event-loop pool of named shared ``httpx.AsyncClient`` instances."""

    _instance: "AsyncHttpClientPool | None" = None
    _instance_lock = threading.RLock()

    def __new__(cls) -> "AsyncHttpClientPool":
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return

        with self.__class__._instance_lock:
            if self._initialized:
                return

            self._config = AsyncHttpClientPoolConfig.from_env()
            self._clients: dict[tuple[int, str], httpx.AsyncClient] = {}
            self._initialized = True

    @property
    def config(self) -> AsyncHttpClientPoolConfig:
        return self._config

    def get_client(self, name: str = "default") -> httpx.AsyncClient:
        """Return a shared async HTTP client for the current event loop."""
        normalized_name = (name or "default").strip() or "default"
        key = (_current_loop_id(), normalized_name)

        with self.__class__._instance_lock:
            client = self._clients.get(key)
            if client is not None and not client.is_closed:
                return client

            client = httpx.AsyncClient(
                limits=httpx.Limits(
                    max_connections=self._config.max_connections,
                    max_keepalive_connections=self._config.max_keepalive_connections,
                    keepalive_expiry=self._config.keepalive_expiry_seconds,
                ),
                timeout=httpx.Timeout(self._config.timeout_seconds),
            )
            self._clients[key] = client
            logger.info(
                "Outbound async HTTP client initialized name=%s max_connections=%s "
                "keepalive=%s timeout=%s",
                normalized_name,
                self._config.max_connections,
                self._config.max_keepalive_connections,
                self._config.timeout_seconds,
            )
            return client

    async def prewarm(self) -> None:
        """Create the default client so its pool exists before first traffic."""
        self.get_client("default")

    async def close(self) -> None:
        """Close all pooled async clients and empty the pool."""
        with self.__class__._instance_lock:
            clients = list(self._clients.values())
            self._clients.clear()

        for client in clients:
            try:
                await client.aclose()
            except Exception:
                logger.debug("Failed to close pooled outbound HTTP client", exc_info=True)

    def stats(self) -> dict[str, Any]:
        """Return lightweight pool configuration and lifecycle stats."""
        with self.__class__._instance_lock:
            active_clients = [
                {"loop_id": loop_id, "name": name}
                for (loop_id, name), client in self._clients.items()
                if not client.is_closed
            ]

        return {
            "active": bool(active_clients),
            "client_count": len(active_clients),
            "clients": active_clients,
            "max_connections": self._config.max_connections,
            "max_keepalive_connections": self._config.max_keepalive_connections,
            "keepalive_expiry_seconds": self._config.keepalive_expiry_seconds,
            "timeout_seconds": self._config.timeout_seconds,
            "transport": "httpx.AsyncClient",
        }


def get_http_client_pool() -> AsyncHttpClientPool:
    """Return the process-local outbound HTTP client pool."""
    return AsyncHttpClientPool()


def get_http_client(name: str = "default") -> httpx.AsyncClient:
    """Return a named shared async HTTP client for the current event loop."""
    return get_http_client_pool().get_client(name)


async def prewarm_http_client_pool() -> None:
    """Pre-create the default outbound HTTP client."""
    await get_http_client_pool().prewarm()


async def close_http_client_pool() -> None:
    """Close all shared outbound HTTP clients."""
    await get_http_client_pool().close()


def get_http_client_pool_stats() -> dict[str, Any]:
    """Return shared outbound HTTP client pool stats."""
    return get_http_client_pool().stats()


def invalidate_http_client_pool() -> None:
    """Reset the pool singleton for tests."""
    AsyncHttpClientPool._instance = None
