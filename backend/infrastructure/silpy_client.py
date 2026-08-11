from __future__ import annotations

import asyncio
import random
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from backend.domain.silpy import SilpyExpedient
from backend.infrastructure.config import Settings, get_settings


class SilpyUnavailable(RuntimeError):
    pass


class SilpyClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.failures = 0
        self.open_until: datetime | None = None
        self.semaphore = asyncio.Semaphore(self.settings.silpy_concurrency)
        self.client: httpx.AsyncClient | None = None

    async def open(self) -> None:
        """Open one pooled connection for the whole synchronization run."""
        self.client = httpx.AsyncClient(
            base_url=self.settings.silpy_base_url,
            timeout=httpx.Timeout(self.settings.silpy_timeout_seconds),
            follow_redirects=True,
            limits=httpx.Limits(
                max_connections=self.settings.silpy_concurrency,
                max_keepalive_connections=self.settings.silpy_concurrency,
            ),
        )

    async def close(self) -> None:
        if self.client is not None:
            await self.client.aclose()
            self.client = None

    def _check_circuit(self) -> None:
        if self.open_until and datetime.now(UTC) < self.open_until:
            raise SilpyUnavailable("SILpy circuit is open")

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        self._check_circuit()
        if self.client is None:
            raise RuntimeError("SILpy client must be opened before requesting data")
        for attempt in range(self.settings.silpy_max_attempts):
            try:
                async with self.semaphore:
                    response = await self.client.get(path, params=params)
                response.raise_for_status()
                self.failures = 0
                return response.json()
            except (httpx.HTTPError, ValueError) as error:
                if attempt + 1 == self.settings.silpy_max_attempts:
                    self.failures += 1
                    if self.failures >= 3:
                        self.open_until = datetime.now(UTC) + timedelta(minutes=5)
                    raise SilpyUnavailable("SILpy request failed") from error
                await asyncio.sleep((2**attempt) + random.uniform(0, 0.5))
        raise AssertionError("unreachable")

    async def list_expedients(self, page: int) -> list[Any]:
        data = await self._get(
            "/data/proyecto", {"offset": page, "limit": self.settings.silpy_page_size}
        )
        if not isinstance(data, list):
            raise SilpyUnavailable("SILpy listing response is not an array")
        return data

    async def get_expedient(self, source_id: int) -> SilpyExpedient:
        return SilpyExpedient.model_validate(await self._get(f"/data/proyecto/{source_id}/detalle"))
